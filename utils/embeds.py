"""Embed message utilities for the Discord Ticket Bot."""
import discord
from datetime import datetime


def create_ticket_embed(user: discord.Member, ticket_data: dict = None) -> discord.Embed:
    """Create an embed for when a ticket is created.
    
    Args:
        user: The user who created the ticket
        ticket_data: Optional ticket data dictionary to show claim status
        
    Returns:
        Discord embed object
    """
    embed = discord.Embed(
        title="Ticket Created",
        description=f"Welcome {user.mention}! A support ticket has been created for you.",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(
        name="Instructions",
        value="Please describe your issue or question. A staff member will assist you shortly.\n\n"
              "Use `/close` to close this ticket when your issue is resolved.",
        inline=False
    )
    
    # Show claim status if ticket is claimed
    if ticket_data and ticket_data.get('claimed_by'):
        embed.add_field(
            name="Status",
            value=f"✅ Claimed by staff",
            inline=True
        )
    
    embed.set_footer(text="Ticket System")
    return embed


def create_close_embed(user: discord.Member, reason: str = None) -> discord.Embed:
    """Create an embed for when a ticket is being closed.
    
    Args:
        user: The user who closed the ticket
        reason: Optional reason for closing the ticket
        
    Returns:
        Discord embed object
    """
    embed = discord.Embed(
        title="Ticket Closing",
        description=f"This ticket is being closed by {user.mention}.",
        color=discord.Color.orange(),
        timestamp=datetime.utcnow()
    )
    
    if reason:
        embed.add_field(
            name="Reason",
            value=reason,
            inline=False
        )
    
    embed.add_field(
        name="Notice",
        value="This channel will be deleted in a few seconds.",
        inline=False
    )
    embed.set_footer(text="Ticket System")
    return embed


def create_error_embed(error_message: str) -> discord.Embed:
    """Create an error embed.
    
    Args:
        error_message: The error message to display
        
    Returns:
        Discord embed object
    """
    embed = discord.Embed(
        title="Error",
        description=error_message,
        color=discord.Color.red(),
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text="Ticket System")
    return embed


def create_ticket_panel_embed() -> discord.Embed:
    """Create an embed for the ticket creation panel.
    
    Returns:
        Discord embed object
    """
    embed = discord.Embed(
        title="Support Tickets",
        description="Click the button below to create a support ticket.",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(
        name="How it works",
        value="1. Click the button below\n"
              "2. A private channel will be created for you\n"
              "3. Describe your issue or question\n"
              "4. A staff member will assist you\n"
              "5. Use `/close` to close the ticket when done",
        inline=False
    )
    embed.set_footer(text="Ticket System")
    return embed


def create_permission_error_embed() -> discord.Embed:
    """Create an embed for permission errors.
    
    Returns:
        Discord embed object
    """
    return create_error_embed(
        "You don't have permission to perform this action."
    )


def create_not_ticket_error_embed() -> discord.Embed:
    """Create an embed for when a command is used outside a ticket channel.
    
    Returns:
        Discord embed object
    """
    return create_error_embed(
        "This command can only be used in ticket channels."
    )


def create_claim_embed(user: discord.Member, ticket_id: int) -> discord.Embed:
    """Create an embed for when a ticket is claimed.
    
    Args:
        user: The user who claimed the ticket
        ticket_id: The ticket ID
        
    Returns:
        Discord embed object
    """
    embed = discord.Embed(
        title="Ticket Claimed",
        description=f"Ticket #{ticket_id} has been claimed by {user.mention}.",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(
        name="Status",
        value="A staff member is now handling this ticket.",
        inline=False
    )
    embed.set_footer(text="Ticket System")
    return embed


def create_unclaim_embed(user: discord.Member, ticket_id: int) -> discord.Embed:
    """Create an embed for when a ticket is unclaimed.
    
    Args:
        user: The user who unclaimed the ticket
        ticket_id: The ticket ID
        
    Returns:
        Discord embed object
    """
    embed = discord.Embed(
        title="Ticket Unclaimed",
        description=f"Ticket #{ticket_id} has been unclaimed by {user.mention}.",
        color=discord.Color.orange(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(
        name="Status",
        value="This ticket is now available for staff to claim.",
        inline=False
    )
    embed.set_footer(text="Ticket System")
    return embed


def create_stats_embed(stats: dict, period_stats: dict = None) -> discord.Embed:
    """Create an embed for ticket statistics.
    
    Args:
        stats: Dictionary with overall statistics
        period_stats: Optional dictionary with period-specific statistics
        
    Returns:
        Discord embed object
    """
    embed = discord.Embed(
        title="Ticket Statistics",
        description="Overview of ticket system statistics",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )
    
    # Overall statistics
    embed.add_field(
        name="📊 Overall Statistics",
        value=f"**Total Tickets:** {stats.get('total', 0)}\n"
              f"**Open:** {stats.get('open', 0)}\n"
              f"**Closed:** {stats.get('closed', 0)}",
        inline=True
    )
    
    embed.add_field(
        name="🎫 Open Tickets",
        value=f"**Claimed:** {stats.get('claimed', 0)}\n"
              f"**Unclaimed:** {stats.get('unclaimed', 0)}",
        inline=True
    )
    
    # Period statistics if provided
    if period_stats:
        embed.add_field(
            name="📅 Recent Activity",
            value=f"**Last 24 Hours:**\n"
                  f"Total: {period_stats.get('today', {}).get('total', 0)}\n"
                  f"Open: {period_stats.get('today', {}).get('open', 0)}\n"
                  f"Closed: {period_stats.get('today', {}).get('closed', 0)}\n\n"
                  f"**Last 7 Days:**\n"
                  f"Total: {period_stats.get('week', {}).get('total', 0)}\n"
                  f"Open: {period_stats.get('week', {}).get('open', 0)}\n"
                  f"Closed: {period_stats.get('week', {}).get('closed', 0)}\n\n"
                  f"**Last 30 Days:**\n"
                  f"Total: {period_stats.get('month', {}).get('total', 0)}\n"
                  f"Open: {period_stats.get('month', {}).get('open', 0)}\n"
                  f"Closed: {period_stats.get('month', {}).get('closed', 0)}",
            inline=False
        )
    
    embed.set_footer(text="Ticket System")
    return embed


def create_custom_panel_embed(title: str = None, description: str = None, ping_role: discord.Role = None) -> discord.Embed:
    """Create a customizable panel embed.
    
    Args:
        title: Custom title for the panel (defaults to "Support Tickets")
        description: Custom description for the panel
        ping_role: Role to mention in the panel
        
    Returns:
        Discord embed object
    """
    embed = discord.Embed(
        title=title or "Support Tickets",
        description=description or "Click the button below to create a support ticket.",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    
    if ping_role:
        embed.add_field(
            name="Support Team",
            value=f"{ping_role.mention} will be notified when you create a ticket.",
            inline=False
        )
    
    embed.add_field(
        name="How it works",
        value="1. Click the button below\n"
              "2. A private channel will be created for you\n"
              "3. Describe your issue or question\n"
              "4. A staff member will assist you\n"
              "5. Use `/close` to close the ticket when done",
        inline=False
    )
    embed.set_footer(text="Ticket System")
    return embed


def create_setup_embed(step: int, question: str) -> discord.Embed:
    """Create an embed for setup instructions.
    
    Args:
        step: Current step number
        question: The question to ask
        
    Returns:
        Discord embed object
    """
    embed = discord.Embed(
        title=f"Setup - Step {step}",
        description=question,
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(
        name="Note",
        value="Type 'cancel' to abort the setup process.",
        inline=False
    )
    embed.set_footer(text="Ticket System Setup")
    return embed


def create_config_view_embed(config: dict, guild: discord.Guild) -> discord.Embed:
    """Create an embed showing current configuration.
    
    Args:
        config: Configuration dictionary
        guild: Discord guild object
        
    Returns:
        Discord embed object
    """
    embed = discord.Embed(
        title="Current Configuration",
        description="Your ticket system configuration:",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )
    
    # Panel Channel
    panel_channel = guild.get_channel(int(config.get('panel_channel_id', 0)))
    embed.add_field(
        name="Panel Channel",
        value=panel_channel.mention if panel_channel else "Not set",
        inline=True
    )
    
    # Ping Role
    ping_role_id = config.get('ping_role_id')
    if ping_role_id:
        ping_role = guild.get_role(int(ping_role_id))
        embed.add_field(
            name="Ping Role",
            value=ping_role.mention if ping_role else "Role not found",
            inline=True
        )
    else:
        embed.add_field(
            name="Ping Role",
            value="Not set",
            inline=True
        )
    
    # Support Role
    support_role_id = config.get('support_role_id')
    if support_role_id:
        support_role = guild.get_role(int(support_role_id))
        embed.add_field(
            name="Support Role",
            value=support_role.mention if support_role else "Role not found",
            inline=True
        )
    else:
        embed.add_field(
            name="Support Role",
            value="Not set",
            inline=True
        )
    
    # Category
    category_id = config.get('ticket_category_id')
    if category_id:
        category = discord.utils.get(guild.categories, id=int(category_id))
        embed.add_field(
            name="Ticket Category",
            value=category.name if category else "Category not found",
            inline=True
        )
    else:
        embed.add_field(
            name="Ticket Category",
            value="Not set",
            inline=True
        )
    
    # Custom Title
    panel_title = config.get('panel_title')
    if panel_title:
        embed.add_field(
            name="Panel Title",
            value=panel_title,
            inline=False
        )
    
    # Custom Description
    panel_description = config.get('panel_description')
    if panel_description:
        embed.add_field(
            name="Panel Description",
            value=panel_description[:1024] if len(panel_description) > 1024 else panel_description,
            inline=False
        )
    
    embed.set_footer(text="Ticket System")
    return embed

