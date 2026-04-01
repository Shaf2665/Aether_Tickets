"""Shared ticket creation flow: category select, description modal, channel create."""
import re
from typing import Optional, List, Dict

import discord
from discord.ext import commands

from config import Config
from utils.embeds import create_error_embed, create_ticket_embed


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

    await channel.send(ping_message, embed=embed)
    await interaction.followup.send(
        f"Ticket created! {channel.mention}",
        ephemeral=True,
    )
