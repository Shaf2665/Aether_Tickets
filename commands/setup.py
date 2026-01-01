"""Setup commands for configuring the ticket system."""
import discord
from discord import app_commands
from discord.ext import commands
from database import TicketDatabase
from utils.embeds import (
    create_setup_embed,
    create_config_view_embed,
    create_error_embed,
    create_permission_error_embed,
    create_custom_panel_embed
)
from bot import TicketButtonView
import re


class SetupCommands(commands.Cog):
    """Commands for setting up the ticket system."""
    
    # Create command group as a class attribute
    setup = app_commands.Group(name="setup", description="Configure the ticket system")
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = TicketDatabase()
        # Store active setup sessions: {user_id: {step: int, data: dict}}
        self.setup_sessions = {}
    
    def is_admin(self, user: discord.Member) -> bool:
        """Check if user is admin or owner."""
        return user.guild_permissions.administrator or user.id == user.guild.owner_id
    
    def extract_channel_id(self, text: str) -> int:
        """Extract channel ID from mention or raw ID."""
        # Try to extract from mention format <#123456789>
        match = re.search(r'<#(\d+)>', text)
        if match:
            return int(match.group(1))
        
        # Try to extract raw ID
        match = re.search(r'(\d+)', text)
        if match:
            return int(match.group(1))
        
        return None
    
    def extract_role_id(self, text: str) -> int:
        """Extract role ID from mention or raw ID."""
        # Try to extract from mention format <@&123456789>
        match = re.search(r'<@&(\d+)>', text)
        if match:
            return int(match.group(1))
        
        # Try to extract raw ID
        match = re.search(r'(\d+)', text)
        if match:
            return int(match.group(1))
        
        return None
    
    def extract_category_id(self, text: str, guild: discord.Guild) -> int:
        """Extract category ID from mention, name, or raw ID."""
        # Try to extract raw ID
        match = re.search(r'(\d+)', text)
        if match:
            try:
                return int(match.group(1))
            except:
                pass
        
        # Try to find by name
        category = discord.utils.get(guild.categories, name=text.strip())
        if category:
            return category.id
        
        return None
    
    async def safe_send(self, message: discord.Message, content=None, embed=None):
        """Safely send a message, checking permissions and falling back to DM if needed.
        
        Args:
            message: The original message object
            content: Text content to send (optional)
            embed: Embed to send (optional)
        """
        # Check if bot can send messages in the channel
        if message.channel.permissions_for(message.guild.me).send_messages:
            try:
                if embed:
                    await message.channel.send(content=content, embed=embed)
                else:
                    await message.channel.send(content=content)
                return
            except discord.Forbidden:
                # Permission was revoked between check and send, fall through to DM
                pass
            except Exception:
                # Other error, try DM
                pass
        
        # Fallback: Try to DM the user
        try:
            if embed:
                await message.author.send(content=content, embed=embed)
            else:
                await message.author.send(content=content)
        except discord.Forbidden:
            # Can't DM either (user has DMs disabled), log it
            print(f"Warning: Could not send message to user {message.author.id} - no permissions in channel and DMs disabled")
        except Exception as e:
            print(f"Error sending DM to user {message.author.id}: {e}")
    
    @setup.command(name="start", description="Start the interactive setup process (admin only)")
    async def setup_start(self, interaction: discord.Interaction):
        """Start the interactive setup process."""
        if not self.is_admin(interaction.user):
            await interaction.response.send_message(
                embed=create_permission_error_embed(),
                ephemeral=True
            )
            return
        
        # Initialize setup session
        self.setup_sessions[str(interaction.user.id)] = {
            'step': 1,
            'data': {},
            'guild_id': str(interaction.guild.id)
        }
        
        embed = create_setup_embed(
            1,
            "Which channel should the ticket panel appear in?\n\n"
            "**How to provide:**\n"
            "• Mention the channel: `#support-tickets`\n"
            "• Or provide the channel ID (a long number)\n\n"
            "**Note:** Make sure the bot has permission to send messages in that channel."
        )
        
        await interaction.response.send_message(embed=embed)
    
    @setup.command(name="view", description="View current configuration (admin only)")
    async def setup_view(self, interaction: discord.Interaction):
        """View current configuration."""
        if not self.is_admin(interaction.user):
            await interaction.response.send_message(
                embed=create_permission_error_embed(),
                ephemeral=True
            )
            return
        
        config = self.db.get_guild_config(str(interaction.guild.id))
        if not config:
            await interaction.response.send_message(
                embed=create_error_embed("No configuration found. Use `/setup start` to configure the ticket system."),
                ephemeral=True
            )
            return
        
        embed = create_config_view_embed(config, interaction.guild)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @setup.command(name="reset", description="Reset ticket system configuration (admin only)")
    async def setup_reset(self, interaction: discord.Interaction):
        """Reset the configuration."""
        if not self.is_admin(interaction.user):
            await interaction.response.send_message(
                embed=create_permission_error_embed(),
                ephemeral=True
            )
            return
        
        config = self.db.get_guild_config(str(interaction.guild.id))
        if not config:
            await interaction.response.send_message(
                embed=create_error_embed("No configuration found to reset."),
                ephemeral=True
            )
            return
        
        # Delete configuration
        self.db.delete_guild_config(str(interaction.guild.id))
        
        # Try to delete panel
        panel_channel = interaction.guild.get_channel(int(config.get('panel_channel_id', 0)))
        if panel_channel:
            async for msg in panel_channel.history(limit=10):
                if msg.author == self.bot.user and msg.embeds:
                    await msg.delete()
                    break
        
        await interaction.response.send_message(
            "✅ Configuration reset! Use `/setup start` to configure again.",
            ephemeral=True
        )
    
    @setup.command(name="refresh", description="Refresh the ticket panel (admin only)")
    async def setup_refresh(self, interaction: discord.Interaction):
        """Refresh the ticket panel."""
        if not self.is_admin(interaction.user):
            await interaction.response.send_message(
                embed=create_permission_error_embed(),
                ephemeral=True
            )
            return
        
        config = self.db.get_guild_config(str(interaction.guild.id))
        if not config:
            await interaction.response.send_message(
                embed=create_error_embed("No configuration found. Use `/setup start` to configure the ticket system."),
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Find and delete old panel
        panel_channel = interaction.guild.get_channel(int(config.get('panel_channel_id', 0)))
        if panel_channel:
            async for msg in panel_channel.history(limit=10):
                if msg.author == self.bot.user and msg.embeds:
                    await msg.delete()
                    break
            
            # Create new panel
            ping_role = None
            if config.get('ping_role_id'):
                ping_role = interaction.guild.get_role(int(config['ping_role_id']))
            
            embed = create_custom_panel_embed(
                title=config.get('panel_title'),
                description=config.get('panel_description'),
                ping_role=ping_role
            )
            view = TicketButtonView(self.bot)
            await panel_channel.send(embed=embed, view=view)
            
            await interaction.followup.send("✅ Panel refreshed!", ephemeral=True)
        else:
            await interaction.followup.send(
                embed=create_error_embed("Panel channel not found."),
                ephemeral=True
            )
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle setup responses."""
        # Ignore bot messages
        if message.author.bot:
            return
        
        user_id = str(message.author.id)
        
        # Check if user has active setup session
        if user_id not in self.setup_sessions:
            return
        
        session = self.setup_sessions[user_id]
        guild = message.guild
        
        # Check if message is in the same guild
        if str(guild.id) != session['guild_id']:
            return
        
        # Check for cancel
        if message.content.lower().strip() == 'cancel':
            del self.setup_sessions[user_id]
            await self.safe_send(message, content="Setup cancelled.")
            return
        
        step = session['step']
        data = session['data']
        
        try:
            if step == 1:  # Channel
                channel_id = self.extract_channel_id(message.content)
                if not channel_id:
                    await self.safe_send(
                        message,
                        embed=create_error_embed(
                            "Invalid channel. Please mention a channel (e.g., #support-tickets) or provide the channel ID."
                        )
                    )
                    return
                
                channel = guild.get_channel(channel_id)
                if not channel or not isinstance(channel, discord.TextChannel):
                    await self.safe_send(
                        message,
                        embed=create_error_embed("Channel not found. Please make sure it's a valid text channel.")
                    )
                    return
                
                # Check bot permissions
                if not channel.permissions_for(guild.me).send_messages:
                    await self.safe_send(
                        message,
                        embed=create_error_embed("I don't have permission to send messages in that channel.")
                    )
                    return
                
                data['panel_channel_id'] = str(channel_id)
                session['step'] = 2
                
                embed = create_setup_embed(
                    2,
                    f"Great! Panel channel set to {channel.mention}.\n\n"
                    "Which role should be pinged when tickets are created?\n\n"
                    "**How to provide:**\n"
                    "• Mention the role: `@Support Team`\n"
                    "• Or provide the role ID (a long number)\n"
                    "• Or type `none` to skip (no role will be pinged)"
                )
                await self.safe_send(message, embed=embed)
            
            elif step == 2:  # Ping Role
                if message.content.lower().strip() in ['none', 'skip', '']:
                    data['ping_role_id'] = None
                else:
                    role_id = self.extract_role_id(message.content)
                    if not role_id:
                        await self.safe_send(
                            message,
                            embed=create_error_embed(
                                "Invalid role. Please mention a role (e.g., @Support Team) or type 'none' to skip."
                            )
                        )
                        return
                    
                    role = guild.get_role(role_id)
                    if not role:
                        await self.safe_send(
                            message,
                            embed=create_error_embed("Role not found. Please try again or type 'none' to skip.")
                        )
                        return
                    
                    data['ping_role_id'] = str(role_id)
                
                session['step'] = 3
                
                embed = create_setup_embed(
                    3,
                    f"Perfect! Ping role set.\n\n"
                    "Which category should tickets be created in?\n\n"
                    "**Important:** The category must already exist in your server.\n"
                    "• Type the **category name** (e.g., `Tickets` or `Support`)\n"
                    "• Or type the **category ID** (if you know it)\n"
                    "• Or type `none` to skip (tickets will be created at root level)\n\n"
                    "**Note:** Categories cannot be mentioned like channels or roles. Just type the name."
                )
                await self.safe_send(message, embed=embed)
            
            elif step == 3:  # Category
                if message.content.lower().strip() in ['none', 'skip', '']:
                    data['ticket_category_id'] = None
                else:
                    category_id = self.extract_category_id(message.content, guild)
                    if not category_id:
                        await self.safe_send(
                            message,
                            embed=create_error_embed(
                                "❌ Category not found!\n\n"
                                "**Make sure:**\n"
                                "• The category already exists in your server\n"
                                "• You typed the exact category name (case-sensitive)\n"
                                "• Or provide the category ID\n\n"
                                "Type `none` to skip this step."
                            )
                        )
                        return
                    
                    category = discord.utils.get(guild.categories, id=category_id)
                    if not category:
                        await self.safe_send(
                            message,
                            embed=create_error_embed(
                                "❌ Category not found!\n\n"
                                "The category might have been deleted or the name doesn't match.\n"
                                "Please try again with the exact category name, or type `none` to skip."
                            )
                        )
                        return
                    
                    data['ticket_category_id'] = str(category_id)
                
                session['step'] = 4
                
                embed = create_setup_embed(
                    4,
                    "Category set!\n\n"
                    "Would you like to customize the panel title?\n"
                    "Type a custom title or 'none' to use the default."
                )
                await self.safe_send(message, embed=embed)
            
            elif step == 4:  # Panel Title
                if message.content.lower().strip() in ['none', 'skip', '']:
                    data['panel_title'] = None
                else:
                    title = message.content.strip()
                    if len(title) > 256:
                        await self.safe_send(
                            message,
                            embed=create_error_embed("Title is too long (max 256 characters). Please try again.")
                        )
                        return
                    data['panel_title'] = title
                
                session['step'] = 5
                
                embed = create_setup_embed(
                    5,
                    "Title set!\n\n"
                    "Would you like to customize the panel description?\n"
                    "Type a custom description or 'none' to use the default."
                )
                await self.safe_send(message, embed=embed)
            
            elif step == 5:  # Panel Description
                if message.content.lower().strip() in ['none', 'skip', '']:
                    data['panel_description'] = None
                else:
                    description = message.content.strip()
                    if len(description) > 2000:
                        await self.safe_send(
                            message,
                            embed=create_error_embed("Description is too long (max 2000 characters). Please try again.")
                        )
                        return
                    data['panel_description'] = description
                
                # Setup complete - save configuration
                guild_id = session['guild_id']
                self.db.save_guild_config(guild_id, data)
                
                # Create panel
                panel_channel = guild.get_channel(int(data['panel_channel_id']))
                ping_role = None
                if data.get('ping_role_id'):
                    ping_role = guild.get_role(int(data['ping_role_id']))
                
                # Check if panel already exists
                panel_message = None
                async for msg in panel_channel.history(limit=10):
                    if msg.author == self.bot.user and msg.embeds:
                        panel_message = msg
                        break
                
                # Create or update panel
                embed = create_custom_panel_embed(
                    title=data.get('panel_title'),
                    description=data.get('panel_description'),
                    ping_role=ping_role
                )
                view = TicketButtonView(self.bot)
                
                if panel_message:
                    await panel_message.edit(embed=embed, view=view)
                    await self.safe_send(message, content="✅ Configuration saved! Ticket panel updated.")
                else:
                    await panel_channel.send(embed=embed, view=view)
                    await self.safe_send(message, content="✅ Setup complete! Ticket panel created.")
                
                # Clean up session
                del self.setup_sessions[user_id]
        
        except Exception as e:
            await self.safe_send(
                message,
                embed=create_error_embed(f"An error occurred: {str(e)}")
            )


async def setup(bot: commands.Bot):
    """Setup function for the cog."""
    await bot.add_cog(SetupCommands(bot))
