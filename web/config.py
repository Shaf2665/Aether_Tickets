"""Flask-specific configuration for Aether Tickets Web UI."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Detect whether the app is running behind a reverse proxy that terminates SSL.
# Set BEHIND_PROXY=true in the environment if your node uses Nginx/Caddy/Cloudflare
# to serve HTTPS — this enables ProxyFix and sets the preferred URL scheme to https.
_BEHIND_PROXY = os.getenv("BEHIND_PROXY", "false").lower() in ("true", "1", "yes")

# Detect whether the public-facing URL is HTTPS.
# This is true when BEHIND_PROXY=true (proxy handles SSL) OR when FORCE_HTTPS=true.
_USE_HTTPS = _BEHIND_PROXY


class Config:
    """Flask configuration settings."""

    # Flask configuration
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-key-change-in-production")
    DEBUG = os.getenv("FLASK_ENV") == "development"
    FLASK_ENV = os.getenv("FLASK_ENV", "production")

    # Port — Pterodactyl sets PORT automatically; fall back to FLASK_PORT or 5000.
    PORT = int(os.getenv("PORT", os.getenv("FLASK_PORT", 5000)))

    # Proxy / SSL settings
    BEHIND_PROXY = _BEHIND_PROXY
    # Preferred URL scheme: 'https' when behind a TLS-terminating proxy, else 'http'
    PREFERRED_URL_SCHEME = "https" if _USE_HTTPS else "http"

    # Session configuration
    PERMANENT_SESSION_LIFETIME = 86400 * 7  # 7 days
    # Only mark cookies Secure when we are actually serving over HTTPS.
    # Setting this to True on a plain HTTP server causes the browser to silently
    # drop the session cookie, breaking OAuth state validation.
    SESSION_COOKIE_SECURE = _USE_HTTPS
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
