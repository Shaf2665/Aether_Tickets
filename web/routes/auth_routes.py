"""Authentication routes for Discord OAuth."""

import secrets
from flask import Blueprint, redirect, url_for, session, request, render_template, current_app
from web.auth import DiscordOAuth, login_required

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/login")
def login():
    """Initiate Discord OAuth login flow."""
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state

    auth_url = DiscordOAuth.get_authorize_url(state)
    return redirect(auth_url)


@bp.route("/callback")
def callback():
    """Handle Discord OAuth callback."""
    # Verify state parameter
    state = request.args.get("state")
    if not state or state != session.get("oauth_state"):
        return {"error": "Invalid state parameter"}, 403

    # Get authorization code
    code = request.args.get("code")
    if not code:
        return {"error": "No authorization code provided"}, 400

    # Exchange code for token
    token_data = DiscordOAuth.exchange_code_for_token(code)
    if not token_data:
        return {"error": "Failed to exchange code for token"}, 400

    access_token = token_data.get("access_token")
    if not access_token:
        return {"error": "No access token received"}, 400

    # Get user info
    user_info = DiscordOAuth.get_user_info(access_token)
    if not user_info:
        return {"error": "Failed to get user info"}, 400

    # Get user's guilds
    guilds = DiscordOAuth.get_user_guilds(access_token)

    # Filter to only guilds where user is owner/admin
    admin_guilds = DiscordOAuth.filter_admin_guilds(guilds, user_info.get("id"))

    if not admin_guilds:
        return {"error": "You don't have admin access to any guilds"}, 403

    # Store in session
    session.permanent = True
    session["user_id"] = user_info.get("id")
    session["username"] = user_info.get("username")
    session["discord_avatar"] = user_info.get("avatar")
    session["discord_token"] = access_token
    session["accessible_guilds"] = [
        {
            "id": guild.get("id"),
            "name": guild.get("name"),
            "icon": guild.get("icon"),
        }
        for guild in admin_guilds
    ]

    # Set first guild as current if not already set
    if "current_guild_id" not in session:
        session["current_guild_id"] = admin_guilds[0]["id"]

    return redirect(url_for("dashboard.view"))


@bp.route("/select-guild/<guild_id>")
@login_required
def select_guild(guild_id):
    """Switch to a different guild."""
    # Verify guild is in accessible guilds
    accessible_guild_ids = [g["id"] for g in session.get("accessible_guilds", [])]

    if guild_id not in accessible_guild_ids:
        return {"error": "You don't have access to this guild"}, 403

    session["current_guild_id"] = guild_id
    return redirect(request.referrer or url_for("dashboard.view"))


@bp.route("/logout")
def logout():
    """Logout user and clear session."""
    session.clear()
    return redirect("/")


@bp.route("/")
def index():
    """Homepage - redirect to dashboard if logged in, else to login."""
    if "user_id" in session:
        return redirect(url_for("dashboard.view"))
    return redirect(url_for("auth.login"))
