"""Configuration management for the Discord Ticket Bot."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Bot configuration settings."""
    
    # Bot token from environment variable
    BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    
    # Guild (server) ID - optional, can be None for multi-server support
    GUILD_ID = os.getenv("GUILD_ID", None)
    if GUILD_ID:
        GUILD_ID = int(GUILD_ID)
    
    # Category ID where tickets will be created - optional
    TICKET_CATEGORY_ID = os.getenv("TICKET_CATEGORY_ID", None)
    if TICKET_CATEGORY_ID:
        TICKET_CATEGORY_ID = int(TICKET_CATEGORY_ID)
    
    # Support role ID for staff access to tickets - optional
    SUPPORT_ROLE_ID = os.getenv("SUPPORT_ROLE_ID", None)
    if SUPPORT_ROLE_ID:
        SUPPORT_ROLE_ID = int(SUPPORT_ROLE_ID)
    
    # Database file path
    DATABASE_PATH = "tickets.db"
    
    # Channel ID where ticket creation message will be sent - optional
    TICKET_CHANNEL_ID = os.getenv("TICKET_CHANNEL_ID", None)
    if TICKET_CHANNEL_ID:
        TICKET_CHANNEL_ID = int(TICKET_CHANNEL_ID)
    
    @staticmethod
    def validate():
        """Validate that required configuration is present."""
        if not Config.BOT_TOKEN:
            raise ValueError("DISCORD_BOT_TOKEN environment variable is required")

