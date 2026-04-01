"""Main bot file for the Discord Ticket Bot."""
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from config import Config
from database import TicketDatabase
from utils.embeds import create_ticket_panel_embed, create_error_embed
from utils.ticket_creation import begin_ticket_creation


# Validate configuration on import
Config.validate()


class TicketBot(commands.Bot):
    """Main bot class."""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        
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
        
        # Add persistent view for ticket button
        self.add_view(TicketButtonView(self))
        
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
        print(f"{self.user} has logged in!")
        print(f"Bot ID: {self.user.id}")
        print(f"Connected to {len(self.guilds)} guild(s)")
        
        # Initialize database
        self.db.init_database()
        print("Database initialized")
        
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

                        # Delete all but keep none — we'll re-post a clean one if needed
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
                            print(f"Ticket panel created in {guild.name} - {panel_channel.name}")
                        elif len(panel_messages) > 1:
                            print(f"Removed {len(panel_messages) - 1} duplicate panel(s) in {guild.name}")
                except Exception as e:
                    print(f"Error creating panel for {guild.name}: {e}")
        
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
                    print(f"Ticket panel sent to {channel.name} (from .env config)")
            except Exception as e:
                print(f"Error sending ticket panel: {e}")
    
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
    """Main function to run the bot."""
    if not Config.BOT_TOKEN:
        print("Error: DISCORD_BOT_TOKEN not found in environment variables!")
        print("Please create a .env file with your bot token.")
        return
    
    bot = TicketBot()
    bot.run(Config.BOT_TOKEN)


if __name__ == "__main__":
    main()

