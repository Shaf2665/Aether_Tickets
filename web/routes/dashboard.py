"""Dashboard route for Aether Tickets Web UI."""

from flask import Blueprint, render_template, session, redirect, url_for
from database import TicketDatabase
from web.auth import guild_required

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

    # Get recent tickets
    recent_tickets = db.get_guild_tickets(guild_id, limit=10)

    # Get tickets by status for the period
    open_tickets = db.get_guild_ticket_count(guild_id, status='open')
    closed_tickets = db.get_guild_ticket_count(guild_id, status='closed')

    return render_template(
        'dashboard.html',
        stats=stats,
        recent_tickets=recent_tickets,
        open_count=open_tickets,
        closed_count=closed_tickets
    )
