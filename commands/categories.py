"""Admin commands for per-guild ticket categories (dropdown types)."""
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from database import TicketDatabase
from utils.embeds import create_error_embed, create_permission_error_embed


class CategoryCommands(commands.Cog):
    """Manage ticket categories for the dropdown and optional Discord folders."""

    categories = app_commands.Group(
        name="categories",
        description="Configure ticket categories (types) for this server",
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = TicketDatabase()

    def is_admin(self, user: discord.Member) -> bool:
        return user.guild_permissions.administrator or user.id == user.guild.owner_id

    @categories.command(name="list", description="List all ticket categories (admin only)")
    async def list_categories(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member) or not self.is_admin(interaction.user):
            await interaction.response.send_message(
                embed=create_permission_error_embed(),
                ephemeral=True,
            )
            return

        rows = self.db.get_ticket_categories(str(interaction.guild.id))
        if not rows:
            await interaction.response.send_message(
                "No ticket categories yet. Use `/categories add` to create one.",
                ephemeral=True,
            )
            return

        lines = []
        for r in rows:
            folder = "default (from /setup)"
            if r.get("discord_category_id"):
                cat = discord.utils.get(
                    interaction.guild.categories, id=int(r["discord_category_id"])
                )
                folder = f"#{cat.name}" if cat else f"id:{r['discord_category_id']}"
            lines.append(f"**#{r['id']}** — {r['label'][:80]} → {folder}")

        embed = discord.Embed(
            title="Ticket categories",
            description="\n".join(lines)[:4000],
            color=discord.Color.green(),
        )
        embed.set_footer(text="Max 25 categories per server (Discord limit).")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @categories.command(name="add", description="Add a ticket category (admin only)")
    @app_commands.describe(
        label="Name shown in the ticket dropdown (must be unique in this server)",
        discord_category="Optional Discord folder for tickets of this type; omit to use /setup default",
    )
    async def add_category(
        self,
        interaction: discord.Interaction,
        label: str,
        discord_category: Optional[discord.CategoryChannel] = None,
    ):
        if not isinstance(interaction.user, discord.Member) or not self.is_admin(interaction.user):
            await interaction.response.send_message(
                embed=create_permission_error_embed(),
                ephemeral=True,
            )
            return

        label = label.strip()
        if not label or len(label) > 100:
            await interaction.response.send_message(
                embed=create_error_embed("Label must be 1–100 characters."),
                ephemeral=True,
            )
            return

        existing = self.db.get_ticket_categories(str(interaction.guild.id))
        if len(existing) >= 25:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "This server already has 25 categories (Discord limit). "
                    "Remove one before adding another."
                ),
                ephemeral=True,
            )
            return

        cid = str(discord_category.id) if discord_category else None
        new_id = self.db.add_ticket_category(str(interaction.guild.id), label, cid)
        if new_id is None:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "A category with that label already exists. Choose a different name."
                ),
                ephemeral=True,
            )
            return

        extra = f" Folder: {discord_category.name}" if discord_category else " Using default folder from /setup."
        await interaction.response.send_message(
            f"Added ticket category **{label}** (id `{new_id}`).{extra}",
            ephemeral=True,
        )

    @categories.command(name="remove", description="Remove a ticket category (admin only)")
    @app_commands.describe(
        ticket_category_id="ID from /categories list",
        label="Exact label to remove (if you prefer not to use id)",
    )
    async def remove_category(
        self,
        interaction: discord.Interaction,
        ticket_category_id: Optional[int] = None,
        label: Optional[str] = None,
    ):
        if not isinstance(interaction.user, discord.Member) or not self.is_admin(interaction.user):
            await interaction.response.send_message(
                embed=create_permission_error_embed(),
                ephemeral=True,
            )
            return

        tid = ticket_category_id
        if tid is None and label:
            row = self.db.get_ticket_category_by_guild_and_label(
                str(interaction.guild.id), label
            )
            if not row:
                await interaction.response.send_message(
                    embed=create_error_embed("No category with that label."),
                    ephemeral=True,
                )
                return
            tid = row["id"]
        if tid is None:
            await interaction.response.send_message(
                embed=create_error_embed("Provide `ticket_category_id` or `label`."),
                ephemeral=True,
            )
            return

        ok = self.db.delete_ticket_category(str(interaction.guild.id), int(tid))
        if not ok:
            await interaction.response.send_message(
                embed=create_error_embed("Category not found for this server."),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"Removed ticket category id `{tid}`.",
            ephemeral=True,
        )

    @categories.command(name="edit", description="Rename a category or change its Discord folder (admin only)")
    @app_commands.describe(
        ticket_category_id="ID from /categories list",
        new_label="New display name (optional)",
        discord_category="New Discord folder for this type (optional)",
        clear_folder="If true, use the guild default folder from /setup instead of a per-type folder",
    )
    async def edit_category(
        self,
        interaction: discord.Interaction,
        ticket_category_id: int,
        new_label: Optional[str] = None,
        discord_category: Optional[discord.CategoryChannel] = None,
        clear_folder: bool = False,
    ):
        if not isinstance(interaction.user, discord.Member) or not self.is_admin(interaction.user):
            await interaction.response.send_message(
                embed=create_permission_error_embed(),
                ephemeral=True,
            )
            return

        if clear_folder and discord_category is not None:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Use either `clear_folder` or `discord_category`, not both."
                ),
                ephemeral=True,
            )
            return

        if new_label is not None:
            new_label = new_label.strip()
            if not new_label or len(new_label) > 100:
                await interaction.response.send_message(
                    embed=create_error_embed("new_label must be 1–100 characters."),
                    ephemeral=True,
                )
                return

        dc_id = None
        unset = clear_folder
        if discord_category is not None:
            dc_id = str(discord_category.id)
            unset = False

        ok = self.db.update_ticket_category(
            str(interaction.guild.id),
            ticket_category_id,
            label=new_label,
            discord_category_id=dc_id,
            unset_discord_category=unset,
        )
        if not ok:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Update failed (category not found, or duplicate label)."
                ),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "Category updated.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(CategoryCommands(bot))
