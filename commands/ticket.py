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
    create_not_ticket_error_embed,
    create_claim_embed,
    create_unclaim_embed,
    create_stats_embed
)
from config import Config


class TicketCommands(commands.Cog):
    """Commands for managing tickets."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = TicketDatabase()
    
    def is_staff(self, user: discord.Member) -> bool:
        """Check if a user is staff (has support role or is admin).
        
        Args:
            user: Discord member to check
            
        Returns:
            True if user is staff
        """
        if user.guild_permissions.administrator:
            return True
        
        if Config.SUPPORT_ROLE_ID:
            support_role = user.guild.get_role(Config.SUPPORT_ROLE_ID)
            if support_role and support_role in user.roles:
                return True
        
        return False
    
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
            ticket_data = self.db.get_ticket_by_channel(str(channel.id))
            embed = create_ticket_embed(interaction.user, ticket_data)
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
    @app_commands.describe(reason="Optional reason for closing the ticket")
    async def close_ticket(self, interaction: discord.Interaction, reason: str = None):
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
            
            # Update database with reason
            self.db.close_ticket(str(interaction.channel.id), reason)
            
            # Send closing message
            embed = create_close_embed(interaction.user, reason)
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
    
    @app_commands.command(name="claim", description="Claim the current ticket (staff only)")
    async def claim_ticket(self, interaction: discord.Interaction):
        """Claim the current ticket."""
        try:
            # Check if this is a ticket channel
            if not self.db.is_ticket_channel(str(interaction.channel.id)):
                await interaction.response.send_message(
                    embed=create_not_ticket_error_embed(),
                    ephemeral=True
                )
                return
            
            # Check if user is staff
            if not self.is_staff(interaction.user):
                await interaction.response.send_message(
                    embed=create_permission_error_embed(),
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
            
            # Check if ticket is open
            if ticket['status'] != 'open':
                await interaction.response.send_message(
                    embed=create_error_embed("You can only claim open tickets."),
                    ephemeral=True
                )
                return
            
            # Check if already claimed
            if ticket.get('claimed_by'):
                await interaction.response.send_message(
                    embed=create_error_embed("This ticket is already claimed by another staff member."),
                    ephemeral=True
                )
                return
            
            # Claim the ticket
            success = self.db.claim_ticket(str(interaction.channel.id), str(interaction.user.id))
            if not success:
                await interaction.response.send_message(
                    embed=create_error_embed("Failed to claim ticket. Please try again."),
                    ephemeral=True
                )
                return
            
            # Send confirmation
            embed = create_claim_embed(interaction.user, ticket['ticket_id'])
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"An error occurred: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="unclaim", description="Unclaim the current ticket (staff only)")
    async def unclaim_ticket(self, interaction: discord.Interaction):
        """Unclaim the current ticket."""
        try:
            # Check if this is a ticket channel
            if not self.db.is_ticket_channel(str(interaction.channel.id)):
                await interaction.response.send_message(
                    embed=create_not_ticket_error_embed(),
                    ephemeral=True
                )
                return
            
            # Check if user is staff
            if not self.is_staff(interaction.user):
                await interaction.response.send_message(
                    embed=create_permission_error_embed(),
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
            
            # Check if ticket is claimed
            if not ticket.get('claimed_by'):
                await interaction.response.send_message(
                    embed=create_error_embed("This ticket is not claimed."),
                    ephemeral=True
                )
                return
            
            # Check if user is the claimer or admin
            is_claimer = str(interaction.user.id) == ticket['claimed_by']
            is_admin = interaction.user.guild_permissions.administrator
            
            if not (is_claimer or is_admin):
                await interaction.response.send_message(
                    embed=create_error_embed("You can only unclaim tickets that you claimed, or you must be an admin."),
                    ephemeral=True
                )
                return
            
            # Unclaim the ticket
            success = self.db.unclaim_ticket(str(interaction.channel.id))
            if not success:
                await interaction.response.send_message(
                    embed=create_error_embed("Failed to unclaim ticket. Please try again."),
                    ephemeral=True
                )
                return
            
            # Send confirmation
            embed = create_unclaim_embed(interaction.user, ticket['ticket_id'])
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"An error occurred: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="ticketstats", description="View ticket statistics (admin only)")
    async def ticket_stats(self, interaction: discord.Interaction):
        """Show ticket statistics."""
        try:
            # Check if user is admin
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    embed=create_permission_error_embed(),
                    ephemeral=True
                )
                return
            
            # Get overall statistics
            stats = self.db.get_ticket_statistics()
            
            # Get period statistics
            period_stats = {
                'today': self.db.get_tickets_by_period(1),
                'week': self.db.get_tickets_by_period(7),
                'month': self.db.get_tickets_by_period(30)
            }
            
            # Create and send embed
            embed = create_stats_embed(stats, period_stats)
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"An error occurred: {str(e)}"),
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Setup function for the cog."""
    await bot.add_cog(TicketCommands(bot))

