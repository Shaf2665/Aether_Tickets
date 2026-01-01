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

