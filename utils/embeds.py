"""Embed message utilities for the Discord Ticket Bot."""
import discord
from datetime import datetime


def create_ticket_embed(user: discord.Member) -> discord.Embed:
    """Create an embed for when a ticket is created.
    
    Args:
        user: The user who created the ticket
        
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
    embed.set_footer(text="Ticket System")
    return embed


def create_close_embed(user: discord.Member) -> discord.Embed:
    """Create an embed for when a ticket is being closed.
    
    Args:
        user: The user who closed the ticket
        
    Returns:
        Discord embed object
    """
    embed = discord.Embed(
        title="Ticket Closing",
        description=f"This ticket is being closed by {user.mention}.",
        color=discord.Color.orange(),
        timestamp=datetime.utcnow()
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

