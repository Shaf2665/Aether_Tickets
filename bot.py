"""Main bot file for the Discord Ticket Bot."""
import os
import logging
import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
from config import Config
from database import TicketDatabase
from utils.embeds import create_ticket_panel_embed, create_error_embed
from utils.ticket_creation import begin_ticket_creation, TicketActionView, TicketDeleteView

logger = logging.getLogger(__name__)


class TicketBot(commands.Bot):
    """Main bot class."""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )
        
        self.db = TicketDatabase()
    
    async def setup_hook(self):
        """Called when the bot is starting up."""
        # Load ticket commands
        await self.load_extension("commands.ticket")
        # Load setup commands
        await self.load_extension("commands.setup")
        # Load category commands
        await self.load_extension("commands.categories")
        
        # Add persistent views so buttons survive restarts
        self.add_view(TicketButtonView(self))
        self.add_view(TicketActionView(self))
        self.add_view(TicketDeleteView(self))
        
        # Sync commands
        if Config.GUILD_ID:
            # Sync to specific guild (faster for testing)
            guild = discord.Object(id=Config.GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            # Sync globally (can take up to an hour)
            await self.tree.sync()
    
    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f"{self.user} has logged in!")
        logger.info(f"Bot ID: {self.user.id}")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")
        
        # Initialize database
        self.db.init_database()
        logger.info("Database initialized")
        
        # Load panels from guild configs (v1.3)
        from utils.embeds import create_custom_panel_embed
        for guild in self.guilds:
            config = self.db.get_guild_config(str(guild.id))
            if config:
                try:
                    panel_channel = guild.get_channel(int(config.get('panel_channel_id', 0)))
                    if panel_channel:
                        # Collect all existing bot panel messages and delete duplicates
                        panel_messages = []
                        async for message in panel_channel.history(limit=50):
                            if message.author == self.user and message.embeds:
                                panel_messages.append(message)

                        # Keep the most recent panel (index 0, history is newest-first)
                        # and delete any duplicates after it.
                        for msg in panel_messages[1:]:
                            try:
                                await msg.delete()
                            except Exception:
                                pass

                        if not panel_messages:
                            # No panel exists, create one
                            ping_role = None
                            if config.get('ping_role_id'):
                                ping_role = guild.get_role(int(config['ping_role_id']))

                            embed = create_custom_panel_embed(
                                title=config.get('panel_title'),
                                description=config.get('panel_description'),
                                ping_role=ping_role
                            )
                            view = TicketButtonView(self)
                            await panel_channel.send(embed=embed, view=view)
                            logger.info(f"Ticket panel created in {guild.name} - {panel_channel.name}")
                        elif len(panel_messages) > 1:
                            logger.info(f"Removed {len(panel_messages) - 1} duplicate panel(s) in {guild.name}")
                except Exception as e:
                    logger.error(f"Error creating panel for {guild.name}: {e}")
        
        # Start background tasks
        if not self.autoclose_task.is_running():
            self.autoclose_task.start()
        if not self.process_bot_actions_task.is_running():
            self.process_bot_actions_task.start()

        # Fallback: Send ticket panel if .env is configured (backward compatibility)
        if Config.TICKET_CHANNEL_ID:
            try:
                channel = self.get_channel(Config.TICKET_CHANNEL_ID)
                if channel:
                    # Check if panel already exists
                    async for message in channel.history(limit=10):
                        if message.author == self.user and message.embeds:
                            # Panel already exists, don't create another
                            return
                    
                    # Create ticket panel
                    embed = create_ticket_panel_embed()
                    view = TicketButtonView(self)
                    await channel.send(embed=embed, view=view)
                    logger.info(f"Ticket panel sent to {channel.name} (from .env config)")
            except Exception as e:
                logger.error(f"Error sending ticket panel: {e}")
    
    # ── Web UI → Discord action processor ────────────────────────────────────

    @tasks.loop(seconds=3)
    async def process_bot_actions_task(self):
        """Poll the bot_actions table and execute pending Web UI actions in Discord."""
        import json as _json
        pending = self.db.get_pending_bot_actions()
        for action_row in pending:
            action_id = action_row["id"]
            action = action_row["action"]
            channel_id = action_row.get("channel_id")
            guild_id = action_row.get("guild_id")
            ticket_id = action_row.get("ticket_id")
            payload_raw = action_row.get("payload") or "{}"
            try:
                payload = _json.loads(payload_raw)
            except Exception:
                payload = {}

            try:
                if action == "send_message":
                    await self._action_send_message(channel_id, payload)
                elif action == "claim":
                    await self._action_claim(channel_id, guild_id, payload)
                elif action == "unclaim":
                    await self._action_unclaim(channel_id, guild_id, payload)
                elif action == "close":
                    await self._action_close(channel_id, guild_id, payload)
                else:
                    logger.warning("Unknown bot action: %s", action)
                self.db.mark_bot_action_done(action_id, "done")
            except Exception as e:
                logger.error("Failed to process bot action %s (%s): %s", action_id, action, e)
                self.db.mark_bot_action_done(action_id, "failed")

    async def _action_send_message(self, channel_id: str, payload: dict):
        """Send a Web UI message to the Discord ticket channel."""
        channel = self.get_channel(int(channel_id))
        if channel is None:
            return
        author_name = payload.get("author_name", "Web UI")
        content = payload.get("content", "")
        if not content:
            return
        embed = discord.Embed(
            description=content,
            color=discord.Color.blurple(),
        )
        embed.set_author(name=f"{author_name} (via Web UI)")
        embed.set_footer(text="Sent from Web Dashboard")
        await channel.send(embed=embed)

    async def _action_claim(self, channel_id: str, guild_id: str, payload: dict):
        """Post a claim notification in the Discord ticket channel."""
        channel = self.get_channel(int(channel_id))
        if channel is None:
            return
        claimer_name = payload.get("claimer_name", "Staff")
        embed = discord.Embed(
            title="Ticket Claimed",
            description=f"**{claimer_name}** has claimed this ticket via the Web Dashboard.",
            color=discord.Color.green(),
        )
        embed.set_footer(text="Ticket System")
        await channel.send(embed=embed)

    async def _action_unclaim(self, channel_id: str, guild_id: str, payload: dict):
        """Post an unclaim notification in the Discord ticket channel."""
        channel = self.get_channel(int(channel_id))
        if channel is None:
            return
        claimer_name = payload.get("claimer_name", "Staff")
        embed = discord.Embed(
            title="Ticket Unclaimed",
            description=f"**{claimer_name}** has unclaimed this ticket via the Web Dashboard.",
            color=discord.Color.orange(),
        )
        embed.set_footer(text="Ticket System")
        await channel.send(embed=embed)

    async def _action_close(self, channel_id: str, guild_id: str, payload: dict):
        """Close a ticket from the Web UI: lock channel and post delete button."""
        from utils.ticket_creation import TicketDeleteView, _get_or_create_closed_category
        channel = self.get_channel(int(channel_id))
        if channel is None:
            return
        guild = channel.guild
        closer_name = payload.get("closer_name", "Web Dashboard")
        reason = payload.get("reason") or "Closed via Web Dashboard"

        embed = discord.Embed(
            title="Ticket Closed",
            description=f"This ticket was closed by **{closer_name}** via the Web Dashboard.",
            color=discord.Color.red(),
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text="Ticket System")
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass

        # Lock channel permissions
        new_overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(
                view_channel=True, send_messages=True,
                manage_channels=True, read_message_history=True,
            ),
        }
        try:
            await channel.edit(overwrites=new_overwrites, reason="Ticket closed via Web UI")
        except discord.Forbidden:
            logger.warning("Could not lock ticket channel %s — missing Manage Channels permission.", channel_id)

        # Post delete button
        try:
            delete_view = TicketDeleteView(self)
            await channel.send(
                "🔒 **Ticket closed.** Only admins can see this channel.\n"
                "Use the button below or `/delete` to permanently remove it.",
                view=delete_view,
            )
        except discord.Forbidden:
            pass

    @process_bot_actions_task.before_loop
    async def before_process_actions(self):
        await self.wait_until_ready()

    # ── Feature 1: auto-close background task ────────────────────────────────

    @tasks.loop(minutes=10)
    async def autoclose_task(self):
        """Check for inactive tickets and auto-close them."""
        from utils.ticket_creation import _execute_close_system
        for guild in self.guilds:
            hours = self.db.get_autoclose_hours(str(guild.id))
            if not hours:
                continue
            inactive = self.db.get_inactive_tickets(str(guild.id), hours)
            for ticket in inactive:
                channel = guild.get_channel(int(ticket["channel_id"]))
                if channel is None:
                    # Channel already deleted — just mark it
                    self.db.mark_ticket_deleted(ticket["channel_id"])
                    continue
                try:
                    await _execute_close_system(
                        self, channel, guild,
                        reason=f"Auto-closed after {hours}h of inactivity."
                    )
                except Exception as e:
                    logger.warning("Auto-close failed for ticket %s: %s", ticket["ticket_id"], e)

    @autoclose_task.before_loop
    async def before_autoclose(self):
        await self.wait_until_ready()

    # ── Feature 2: message sync listener ─────────────────────────────────────

    async def on_message(self, message: discord.Message):
        """Sync Discord messages in ticket channels to the database."""
        if message.author.bot:
            await self.process_commands(message)
            return
        if not message.guild:
            await self.process_commands(message)
            return

        # Cache user info for Feature 3
        user = message.author
        avatar_url = str(user.display_avatar.url) if user.display_avatar else None
        self.db.upsert_discord_user(
            str(user.id),
            user.name,
            display_name=getattr(user, "display_name", None),
            avatar_url=avatar_url,
        )

        # Only sync messages in ticket channels
        ticket = self.db.get_ticket_by_channel(str(message.channel.id))
        if ticket and ticket["status"] == "open":
            # Avoid duplicates
            if not self.db.message_already_saved(str(message.id)):
                self.db.save_ticket_message(
                    ticket_id=ticket["ticket_id"],
                    author_id=str(user.id),
                    author_name=user.display_name or user.name,
                    content=message.content,
                    source="discord",
                    discord_message_id=str(message.id),
                    author_avatar=avatar_url,
                )
            # Update last activity timestamp
            self.db.update_ticket_activity(str(message.channel.id))

        await self.process_commands(message)

    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        """Sync Discord channel deletion to the database."""
        if isinstance(channel, discord.TextChannel):
            self.db.mark_ticket_deleted(str(channel.id))

    async def handle_ticket_button(self, interaction: discord.Interaction):
        """Handle ticket creation button click."""
        try:
            await begin_ticket_creation(self, interaction)
        except discord.NotFound:
            pass
        except Exception as e:
            if interaction.response.is_done():
                await interaction.followup.send(
                    embed=create_error_embed(f"An error occurred: {str(e)}"),
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    embed=create_error_embed(f"An error occurred: {str(e)}"),
                    ephemeral=True,
                )


class TicketButtonView(discord.ui.View):
    """View containing the ticket creation button."""
    
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.primary,
        emoji="🎫",
        custom_id="create_ticket"
    )
    async def create_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle ticket creation button click."""
        await self.bot.handle_ticket_button(interaction)


def main():
    """Main function to run the bot standalone (python bot.py)."""
    # Setup basic logging when running standalone
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    Config.validate()

    if not Config.BOT_TOKEN:
        logger.error("DISCORD_BOT_TOKEN not found in environment variables!")
        logger.error("Please create a .env file with your bot token.")
        return

    bot = TicketBot()
    bot.run(Config.BOT_TOKEN)


if __name__ == "__main__":
    main()
