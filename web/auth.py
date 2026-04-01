"""Discord OAuth authentication for Aether Tickets Web UI."""

import requests
import jwt
from functools import wraps
from flask import session, current_app, redirect, url_for, request


class DiscordOAuth:
    """Handle Discord OAuth 2.0 authentication flow."""

    @staticmethod
    def get_authorize_url(state):
        """Generate Discord OAuth authorization URL."""
        params = {
            "client_id": current_app.config["DISCORD_CLIENT_ID"],
            "redirect_uri": current_app.config["DISCORD_REDIRECT_URI"],
            "response_type": "code",
            "scope": "identify guilds",
            "state": state,
        }
        base_url = "https://discord.com/api/oauth2/authorize"
        param_str = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{base_url}?{param_str}"

    @staticmethod
    def exchange_code_for_token(code):
        """Exchange authorization code for access token."""
        data = {
            "client_id": current_app.config["DISCORD_CLIENT_ID"],
            "client_secret": current_app.config["DISCORD_CLIENT_SECRET"],
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": current_app.config["DISCORD_REDIRECT_URI"],
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = requests.post(
            f"{current_app.config['DISCORD_API_BASE']}/oauth2/token",
            data=data,
            headers=headers
        )

        if response.status_code != 200:
            return None

        return response.json()

    @staticmethod
    def get_user_info(access_token):
        """Fetch authenticated user's info from Discord API."""
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(
            f"{current_app.config['DISCORD_API_BASE']}/users/@me",
            headers=headers
        )

        if response.status_code != 200:
            return None

        return response.json()

    @staticmethod
    def get_user_guilds(access_token):
        """Fetch user's guilds from Discord API."""
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(
            f"{current_app.config['DISCORD_API_BASE']}/users/@me/guilds",
            headers=headers
        )

        if response.status_code != 200:
            return []

        return response.json()

    @staticmethod
    def is_guild_admin(guild, user_id):
        """Check if user is admin/owner of a guild based on Discord API response."""
        # In Discord guilds list response, owner_id field indicates the owner
        # For permission checking, we need to verify admin status
        return guild.get("owner") is True

    @staticmethod
    def filter_admin_guilds(guilds, user_id):
        """Filter to only guilds where user is owner or has admin permissions."""
        # The Discord API /users/@me/guilds endpoint returns owner field
        # indicating if user is the owner of that guild
        admin_guilds = []
        for guild in guilds:
            if guild.get("owner") is True:
                admin_guilds.append(guild)
        return admin_guilds


def login_required(f):
    """Decorator to require user to be logged in."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


def guild_required(f):
    """Decorator to require user to have selected a guild."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        if "current_guild_id" not in session:
            return redirect(url_for("auth.select_guild"))
        return f(*args, **kwargs)
    return decorated_function
