"""Shared ticket creation flow: category select, description modal, channel create."""
import re
from typing import Optional, List, Dict

import discord
from discord.ext import commands

import asyncio

from config import Config
from utils.embeds import (
    create_error_embed,
    create_ticket_embed,
    create_claim_embed,
    create_close_embed,
)


def _slug_segment(text: str, max_len: int) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if not s:
        s = "x"
    return s[:max_len].strip("-")


def make_ticket_channel_name(label: str, user: discord.abc.User) -> str:
    """Build a valid Discord channel name from category label and username."""
    left = _slug_segment(label, 40)
    right = _slug_segment(getattr(user, "name", "user") or "user", 50)
    name = f"{left}-{right}"
    return name[:100]


def _is_staff(bot: commands.Bot, user: discord.Member) -> bool:
    """Check if a member is staff (mirrors TicketCommands.is_staff)."""
    if user.guild_permissions.administrator:
        return True
    guild_config = bot.db.get_guild_config(str(user.guild.id))
    if guild_config and guild_config.get("support_role_id"):
        sr = user.guild.get_role(int(guild_config["support_role_id"]))
        if sr and sr in user.roles:
            return True
    if Config.SUPPORT_ROLE_ID:
        sr = user.guild.get_role(Config.SUPPORT_ROLE_ID)
        if sr and sr in user.roles:
            return True
    return False


async def _get_or_create_closed_category(
    bot: commands.Bot, guild: discord.Guild
) -> Optional[discord.CategoryChannel]:
    """Return the configured closed category, or find/create 'Closed Tickets'."""
    guild_config = bot.db.get_guild_config(str(guild.id))
    if guild_config and guild_config.get("closed_category_id"):
        cat = discord.utils.get(guild.categories, id=int(guild_config["closed_category_id"]))
        if cat:
            return cat

    # Fallback: find by name or create
    category = discord.utils.get(guild.categories, name="Closed Tickets")
    if category:
        return category
    try:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                read_message_history=True,
            ),
        }
        return await guild.create_category("Closed Tickets", overwrites=overwrites)
    except discord.Forbidden:
        return None


async def _execute_close(bot: commands.Bot, interaction: discord.Interaction, reason: str = None) -> None:
    """Shared close logic: marks DB closed, moves channel to Closed Tickets, posts delete view."""
    ticket = bot.db.get_ticket_by_channel(str(interaction.channel.id))
    if not ticket:
        await interaction.response.send_message(
            embed=create_error_embed("Ticket not found in database."), ephemeral=True
        )
        return
    if ticket["status"] == "closed":
        await interaction.response.send_message(
            embed=create_error_embed("This ticket is already closed."), ephemeral=True
        )
        return

    is_owner = str(interaction.user.id) == ticket["user_id"]
    if not (is_owner or _is_staff(bot, interaction.user)):
        await interaction.response.send_message(
            embed=create_error_embed("Only the ticket owner or staff can close this ticket."),
            ephemeral=True,
        )
        return

    # Mark closed in DB first
    bot.db.close_ticket(str(interaction.channel.id), reason)

    # Send the closing embed
    embed = create_close_embed(interaction.user, reason)
    await interaction.response.send_message(embed=embed)

    channel = interaction.channel
    guild = interaction.guild

    # Try to move to Closed Tickets category and lock permissions
    closed_category = await _get_or_create_closed_category(bot, guild)
    new_overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_channels=True,
            read_message_history=True,
        ),
    }
    try:
        await channel.edit(
            category=closed_category,
            overwrites=new_overwrites,
            reason="Ticket closed",
        )
    except discord.Forbidden:
        # Bot lacks Manage Channels — log it but continue so the delete button still appears
        import logging
        logging.getLogger(__name__).warning(
            "Could not move ticket channel %s to Closed Tickets category — missing Manage Channels permission.",
            channel.id,
        )
    except Exception:
        pass

    # Always post the delete button so staff can clean up the channel
    try:
        delete_view = TicketDeleteView(bot)
        await channel.send(
            "🔒 **Ticket closed.** Only admins can see this channel.\n"
            "Use the button below or `/delete` to permanently remove it.",
            view=delete_view,
        )
    except discord.Forbidden:
        pass


class TicketCloseModal(discord.ui.Modal, title="Close Ticket"):
    reason = discord.ui.TextInput(
        label="Reason (optional)",
        style=discord.TextStyle.paragraph,
        placeholder="Why are you closing this ticket?",
        required=False,
        max_length=500,
    )

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        reason = str(self.reason.value).strip() if self.reason.value else None
        await _execute_close(self.bot, interaction, reason)


class TicketActionView(discord.ui.View):
    """Persistent view with Claim and Close buttons shown on every ticket welcome message."""

    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="Claim",
        style=discord.ButtonStyle.success,
        emoji="🙋",
        custom_id="ticket_action_claim",
    )
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not isinstance(interaction.user, discord.Member) or not _is_staff(self.bot, interaction.user):
            await interaction.response.send_message(
                embed=create_error_embed("Only staff can claim tickets."), ephemeral=True
            )
            return

        ticket = self.bot.db.get_ticket_by_channel(str(interaction.channel.id))
        if not ticket:
            await interaction.response.send_message(
                embed=create_error_embed("Ticket not found."), ephemeral=True
            )
            return
        if ticket.get("claimed_by"):
            await interaction.response.send_message(
                embed=create_error_embed("This ticket is already claimed."), ephemeral=True
            )
            return

        success = self.bot.db.claim_ticket(str(interaction.channel.id), str(interaction.user.id))
        if not success:
            await interaction.response.send_message(
                embed=create_error_embed("Failed to claim ticket. Please try again."), ephemeral=True
            )
            return

        embed = create_claim_embed(interaction.user, ticket["ticket_id"])
        await interaction.response.send_message(embed=embed)

    @discord.ui.button(
        label="Close",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="ticket_action_close",
    )
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketCloseModal(self.bot))


class TicketDeleteView(discord.ui.View):
    """Persistent view posted in closed ticket channels with a Delete button (admin only)."""

    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="Delete Ticket",
        style=discord.ButtonStyle.danger,
        emoji="🗑️",
        custom_id="ticket_action_delete",
    )
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                embed=create_error_embed("Only admins can permanently delete tickets."),
                ephemeral=True,
            )
            return
        await interaction.response.send_message("🗑️ Deleting ticket...", ephemeral=True)
        try:
            await interaction.channel.delete(reason=f"Ticket deleted by {interaction.user}")
        except discord.Forbidden:
            await interaction.followup.send(
                embed=create_error_embed("I don't have permission to delete this channel."),
                ephemeral=True,
            )


async def begin_ticket_creation(bot: commands.Bot, interaction: discord.Interaction) -> None:
    """Start ticket flow: error if no categories; one category opens modal; else show select."""
    open_tickets = bot.db.get_user_tickets(str(interaction.user.id), status="open")
    if open_tickets:
        await interaction.response.send_message(
            embed=create_error_embed(
                "You already have an open ticket. Please close it before creating a new one."
            ),
            ephemeral=True,
        )
        return

    guild = interaction.guild
    if not guild:
        await interaction.response.send_message(
            embed=create_error_embed("This can only be used in a server."),
            ephemeral=True,
        )
        return

    categories: List[Dict] = bot.db.get_ticket_categories(str(guild.id))
    if not categories:
        await interaction.response.send_message(
            embed=create_error_embed(
                "No ticket categories are configured yet. Ask an administrator to add "
                "categories with `/categories add`."
            ),
            ephemeral=True,
        )
        return

    if len(categories) == 1:
        modal = TicketDescriptionModal(bot, categories[0])
        await interaction.response.send_modal(modal)
        return

    # Multiple categories: show select (max 25)
    view = CategorySelectView(bot, categories[:25])
    embed = discord.Embed(
        title="New ticket",
        description="Choose a category, then describe your issue in the next step.",
        color=discord.Color.blue(),
    )
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class CategorySelectView(discord.ui.View):
    """Ephemeral string select for ticket category."""

    def __init__(self, bot: commands.Bot, categories: List[Dict]):
        super().__init__(timeout=300)
        self.bot = bot
        self.add_item(CategorySelect(bot, categories))


class CategorySelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot, categories: List[Dict]):
        opts = []
        for row in categories:
            lab = row["label"][:100]
            opts.append(
                discord.SelectOption(
                    label=lab,
                    value=str(row["id"]),
                    description=None,
                )
            )
        super().__init__(
            placeholder="Select a ticket category…",
            min_values=1,
            max_values=1,
            options=opts,
        )
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        cat_id = int(self.values[0])
        row = self.bot.db.get_ticket_category_by_id(cat_id)
        if not row or str(row["guild_id"]) != str(interaction.guild.id):
            await interaction.response.send_message(
                embed=create_error_embed("That category is no longer available. Try again."),
                ephemeral=True,
            )
            return
        await interaction.response.send_modal(TicketDescriptionModal(self.bot, row))


class TicketDescriptionModal(discord.ui.Modal):
    def __init__(self, bot: commands.Bot, category_row: Dict):
        super().__init__(title="Describe your issue")
        self.bot = bot
        self.category_row = category_row
        self.description = discord.ui.TextInput(
            label="Description",
            style=discord.TextStyle.paragraph,
            placeholder="What do you need help with?",
            required=True,
            max_length=4000,
        )
        self.add_item(self.description)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            await finalize_ticket_creation(
                self.bot,
                interaction,
                self.category_row,
                str(self.description.value),
            )
        except discord.Forbidden:
            await interaction.followup.send(
                embed=create_error_embed(
                    "I don't have permission to create channels. Please check my permissions."
                ),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.followup.send(
                embed=create_error_embed(f"An error occurred: {str(e)}"),
                ephemeral=True,
            )


def _resolve_parent_category(
    guild: discord.Guild,
    guild_config: Optional[dict],
    category_row: Dict,
) -> Optional[discord.CategoryChannel]:
    did = category_row.get("discord_category_id")
    if did:
        ch = discord.utils.get(guild.categories, id=int(did))
        if ch:
            return ch
    if guild_config and guild_config.get("ticket_category_id"):
        ch = discord.utils.get(guild.categories, id=int(guild_config["ticket_category_id"]))
        if ch:
            return ch
    if Config.TICKET_CATEGORY_ID:
        return discord.utils.get(guild.categories, id=Config.TICKET_CATEGORY_ID)
    return None


async def finalize_ticket_creation(
    bot: commands.Bot,
    interaction: discord.Interaction,
    category_row: Dict,
    description: str,
) -> None:
    """Create channel, DB row, welcome message; follow up to user."""
    guild = interaction.guild
    user = interaction.user
    if not guild or not isinstance(user, discord.Member):
        await interaction.followup.send(
            embed=create_error_embed("Invalid context."),
            ephemeral=True,
        )
        return

    row = bot.db.get_ticket_category_by_id(int(category_row["id"]))
    if not row or str(row["guild_id"]) != str(guild.id):
        await interaction.followup.send(
            embed=create_error_embed("That category is no longer available."),
            ephemeral=True,
        )
        return

    guild_config = bot.db.get_guild_config(str(guild.id))
    parent = _resolve_parent_category(guild, guild_config, row)

    ping_role_id = None
    support_role_id = None
    if guild_config:
        ping_role_id = guild_config.get("ping_role_id")
        support_role_id = guild_config.get("support_role_id")
    else:
        support_role_id = str(Config.SUPPORT_ROLE_ID) if Config.SUPPORT_ROLE_ID else None

    channel_name = make_ticket_channel_name(row["label"], user)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True,
        ),
    }
    if support_role_id:
        sr = guild.get_role(int(support_role_id))
        if sr:
            overwrites[sr] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
            )

    channel = await guild.create_text_channel(
        name=channel_name,
        category=parent,
        overwrites=overwrites,
        reason=f"Ticket created by {user}",
    )

    ticket_id = bot.db.create_ticket(
        str(channel.id),
        str(user.id),
        guild_id=str(guild.id),
        guild_ticket_category_id=int(row["id"]),
        initial_description=description,
    )
    ticket_data = bot.db.get_ticket_by_channel(str(channel.id))

    embed = create_ticket_embed(
        user,
        ticket_data,
        category_label=row["label"],
        initial_description=description,
    )
    embed.add_field(name="Ticket ID", value=f"#{ticket_id}", inline=False)

    ping_message = ""
    if ping_role_id:
        pr = guild.get_role(int(ping_role_id))
        if pr:
            ping_message = f"{pr.mention} "

    view = TicketActionView(bot)
    await channel.send(ping_message, embed=embed, view=view)
    await interaction.followup.send(
        f"Ticket created! {channel.mention}",
        ephemeral=True,
    )
