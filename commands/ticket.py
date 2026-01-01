"""Ticket-related commands for the Discord Ticket Bot."""
import discord
from discord import app_commands
from discord.ext import commands
from database import TicketDatabase
from utils.embeds import (
    create_ticket_embed,
    create_close_embed,
    create_error_embed,
    create_permission_error_embed,
    create_not_ticket_error_embed
)
from config import Config


class TicketCommands(commands.Cog):
    """Commands for managing tickets."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = TicketDatabase()
    
    @app_commands.command(name="ticket", description="Create a new support ticket")
    async def create_ticket(self, interaction: discord.Interaction):
        """Create a new ticket channel."""
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
                    embed=create_error_embed("This command can only be used in a server."),
                    ephemeral=True
                )
                return
            
            category = None
            if Config.TICKET_CATEGORY_ID:
                category = discord.utils.get(guild.categories, id=Config.TICKET_CATEGORY_ID)
            
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
            if Config.SUPPORT_ROLE_ID:
                support_role = guild.get_role(Config.SUPPORT_ROLE_ID)
                if support_role:
                    overwrites[support_role] = discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True
                    )
            
            # Create the channel
            channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                reason=f"Ticket created by {interaction.user}"
            )
            
            # Log to database
            ticket_id = self.db.create_ticket(str(channel.id), str(interaction.user.id))
            
            # Send welcome message
            embed = create_ticket_embed(interaction.user)
            embed.add_field(
                name="Ticket ID",
                value=f"#{ticket_id}",
                inline=False
            )
            await channel.send(embed=embed)
            
            # Respond to interaction
            await interaction.response.send_message(
                f"Ticket created! {channel.mention}",
                ephemeral=True
            )
            
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "I don't have permission to create channels. Please check my permissions."
                ),
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"An error occurred: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="close", description="Close the current ticket")
    async def close_ticket(self, interaction: discord.Interaction):
        """Close the current ticket channel."""
        try:
            # Check if this is a ticket channel
            if not self.db.is_ticket_channel(str(interaction.channel.id)):
                await interaction.response.send_message(
                    embed=create_not_ticket_error_embed(),
                    ephemeral=True
                )
                return
            
            # Get ticket info
            ticket = self.db.get_ticket_by_channel(str(interaction.channel.id))
            if not ticket:
                await interaction.response.send_message(
                    embed=create_error_embed("Ticket not found in database."),
                    ephemeral=True
                )
                return
            
            # Check permissions (ticket owner or admin)
            is_owner = str(interaction.user.id) == ticket['user_id']
            is_admin = interaction.user.guild_permissions.administrator
            
            if not (is_owner or is_admin):
                await interaction.response.send_message(
                    embed=create_permission_error_embed(),
                    ephemeral=True
                )
                return
            
            # Check if already closed
            if ticket['status'] == 'closed':
                await interaction.response.send_message(
                    embed=create_error_embed("This ticket is already closed."),
                    ephemeral=True
                )
                return
            
            # Update database
            self.db.close_ticket(str(interaction.channel.id))
            
            # Send closing message
            embed = create_close_embed(interaction.user)
            await interaction.response.send_message(embed=embed)
            
            # Wait a bit then delete channel
            import asyncio
            await asyncio.sleep(5)
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
            
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "I don't have permission to delete this channel."
                ),
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"An error occurred: {str(e)}"),
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Setup function for the cog."""
    await bot.add_cog(TicketCommands(bot))

