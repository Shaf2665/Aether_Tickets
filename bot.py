"""Main bot file for the Discord Ticket Bot."""
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from config import Config
from database import TicketDatabase
from utils.embeds import create_ticket_panel_embed, create_error_embed


# Validate configuration on import
Config.validate()


class TicketBot(commands.Bot):
    """Main bot class."""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
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
        for guild in self.guilds:
            config = self.db.get_guild_config(str(guild.id))
            if config:
                try:
                    panel_channel = guild.get_channel(int(config.get('panel_channel_id', 0)))
                    if panel_channel:
                        # Check if panel already exists
                        panel_exists = False
                        async for message in panel_channel.history(limit=10):
                            if message.author == self.user and message.embeds:
                                panel_exists = True
                                break
                        
                        if not panel_exists:
                            # Create panel
                            ping_role = None
                            if config.get('ping_role_id'):
                                ping_role = guild.get_role(int(config['ping_role_id']))
                            
                            from utils.embeds import create_custom_panel_embed
                            embed = create_custom_panel_embed(
                                title=config.get('panel_title'),
                                description=config.get('panel_description'),
                                ping_role=ping_role
                            )
                            view = TicketButtonView(self)
                            await panel_channel.send(embed=embed, view=view)
                            print(f"Ticket panel created in {guild.name} - {panel_channel.name}")
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
            # Check if user already has an open ticket
            open_tickets = self.db.get_user_tickets(str(interaction.user.id), status='open')
            if open_tickets:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "You already have an open ticket. Please close it before creating a new one."
                    ),
                    ephemeral=True
                )
                return
            
            # Get guild and category
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    embed=create_error_embed("This can only be used in a server."),
                    ephemeral=True
                )
                return
            
            # Get guild config (v1.3) or fallback to .env
            guild_config = self.db.get_guild_config(str(guild.id))
            category = None
            ping_role_id = None
            support_role_id = None
            
            if guild_config:
                # Use guild config
                if guild_config.get('ticket_category_id'):
                    category = discord.utils.get(guild.categories, id=int(guild_config['ticket_category_id']))
                ping_role_id = guild_config.get('ping_role_id')
                support_role_id = guild_config.get('support_role_id')
            else:
                # Fallback to .env config
                if Config.TICKET_CATEGORY_ID:
                    category = discord.utils.get(guild.categories, id=Config.TICKET_CATEGORY_ID)
                support_role_id = str(Config.SUPPORT_ROLE_ID) if Config.SUPPORT_ROLE_ID else None
            
            # Create channel name
            username = interaction.user.name.lower().replace(" ", "-")
            channel_name = f"ticket-{username}"
            
            # Create overwrites for permissions
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                ),
                guild.me: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_channels=True
                )
            }
            
            # Add support role if configured
            if support_role_id:
                support_role = guild.get_role(int(support_role_id))
                if support_role:
                    overwrites[support_role] = discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True
                    )
            
            # Create the channel
            await interaction.response.defer(ephemeral=True)
            
            channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                reason=f"Ticket created by {interaction.user}"
            )
            
            # Log to database
            ticket_id = self.db.create_ticket(str(channel.id), str(interaction.user.id))
            
            # Get ticket data for embed
            ticket_data = self.db.get_ticket_by_channel(str(channel.id))
            
            # Send welcome message
            from utils.embeds import create_ticket_embed
            embed = create_ticket_embed(interaction.user, ticket_data)
            embed.add_field(
                name="Ticket ID",
                value=f"#{ticket_id}",
                inline=False
            )
            
            # Ping role if configured (v1.3)
            ping_message = ""
            if ping_role_id:
                ping_role = guild.get_role(int(ping_role_id))
                if ping_role:
                    ping_message = f"{ping_role.mention} "
            
            await channel.send(ping_message, embed=embed)
            
            # Respond to interaction
            await interaction.followup.send(
                f"Ticket created! {channel.mention}",
                ephemeral=True
            )
            
        except discord.Forbidden:
            await interaction.followup.send(
                embed=create_error_embed(
                    "I don't have permission to create channels. Please check my permissions."
                ),
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                embed=create_error_embed(f"An error occurred: {str(e)}"),
                ephemeral=True
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

