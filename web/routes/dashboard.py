"""Dashboard route for Aether Tickets Web UI."""

from flask import Blueprint, render_template, session, redirect, url_for
from database import TicketDatabase
from web.auth import guild_required


def _resolve_user(db: TicketDatabase, user_id: str) -> str:
    if not user_id:
        return "-"
    cached = db.get_discord_user(user_id)
    if cached:
        return cached.get("display_name") or cached.get("username") or user_id
    return user_id


def _enrich_tickets(db: TicketDatabase, tickets: list) -> list:
    enriched = []
    for t in tickets:
        t = dict(t)
        t["user_display"] = _resolve_user(db, t.get("user_id"))
        t["claimed_display"] = _resolve_user(db, t.get("claimed_by")) if t.get("claimed_by") else None
        enriched.append(t)
    return enriched

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@bp.route("")
def dashboard_redirect():
    """Redirect /dashboard (no trailing slash) to /dashboard/."""
    return redirect(url_for("dashboard.view"))


@bp.route("/")
@guild_required
def view():
    """Display the main dashboard with statistics."""
    guild_id = session.get("current_guild_id")
    db = TicketDatabase()

    # Get guild statistics
    stats = db.get_guild_statistics(guild_id)

    # Get recent tickets (with resolved usernames)
    recent_tickets = _enrich_tickets(db, db.get_guild_tickets(guild_id, limit=10))

    # Get tickets by status for the period
    open_tickets = db.get_guild_ticket_count(guild_id, status='open')
    closed_tickets = db.get_guild_ticket_count(guild_id, status='closed')

    # Auto-close setting
    autoclose_hours = db.get_autoclose_hours(guild_id)

    return render_template(
        'dashboard.html',
        stats=stats,
        recent_tickets=recent_tickets,
        open_count=open_tickets,
        closed_count=closed_tickets,
        autoclose_hours=autoclose_hours,
    )
