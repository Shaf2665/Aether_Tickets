"""Flask-specific configuration for Aether Tickets Web UI."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Flask configuration settings."""

    # Flask configuration
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-key-change-in-production")
    DEBUG = os.getenv("FLASK_ENV") == "development"
    FLASK_ENV = os.getenv("FLASK_ENV", "production")

    # Session configuration
    PERMANENT_SESSION_LIFETIME = 86400 * 7  # 7 days
    SESSION_COOKIE_SECURE = os.getenv("FLASK_ENV") != "development"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Discord OAuth configuration
    DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
    DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
    DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:5000/auth/callback")

    # Discord API
    DISCORD_API_BASE = "https://discord.com/api/v10"

    # Database configuration
    DATABASE_PATH = os.getenv("DATABASE_PATH", "tickets.db")

    # Bot token (for API calls if needed)
    BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

    @staticmethod
    def validate():
        """Validate that required configuration is present."""
        if not Config.DISCORD_CLIENT_ID:
            raise ValueError("DISCORD_CLIENT_ID environment variable is required")
        if not Config.DISCORD_CLIENT_SECRET:
            raise ValueError("DISCORD_CLIENT_SECRET environment variable is required")
        if not Config.BOT_TOKEN:
            raise ValueError("DISCORD_BOT_TOKEN environment variable is required")
        if not Config.SECRET_KEY or Config.SECRET_KEY == "dev-key-change-in-production":
            if Config.FLASK_ENV == "production":
                raise ValueError("FLASK_SECRET_KEY must be set in production")
