"""Tickets routes for viewing and managing tickets."""

from flask import Blueprint, render_template, session, request, jsonify, flash, redirect, url_for
from database import TicketDatabase
from web.auth import guild_required

bp = Blueprint("tickets", __name__, url_prefix="/tickets")


@bp.route("/")
@guild_required
def list_tickets():
    """Display list of tickets with filtering and search."""
    guild_id = session.get("current_guild_id")
    db = TicketDatabase()

    # Get filters from request
    status_filter = request.args.get("status", "all")
    search = request.args.get("search", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 25

    status_arg = status_filter if status_filter != "all" else None

    if search:
        # Search across ALL tickets for this guild (no pagination offset) so we
        # don't miss matches that fall on other pages.
        all_tickets = db.get_guild_tickets(guild_id, status=status_arg, limit=10000, offset=0)
        tickets_filtered = [
            t for t in all_tickets
            if search.lower() in str(t.get("ticket_id", "")).lower()
            or search.lower() in t.get("user_id", "").lower()
        ]
        total = len(tickets_filtered)
        offset = (page - 1) * per_page
        tickets = tickets_filtered[offset: offset + per_page]
    else:
        tickets = db.get_guild_tickets(guild_id, status=status_arg, limit=per_page, offset=(page - 1) * per_page)
        total = db.get_guild_ticket_count(guild_id, status=status_arg)

    total_pages = max(1, (total + per_page - 1) // per_page)

    return render_template(
        'tickets.html',
        tickets=tickets,
        status_filter=status_filter,
        search=search,
        page=page,
        total_pages=total_pages,
        total=total
    )


@bp.route("/<int:ticket_id>")
@guild_required
def view_ticket(ticket_id):
    """Display ticket details."""
    guild_id = session.get("current_guild_id")
    db = TicketDatabase()

    ticket = db.get_ticket_by_id(ticket_id)

    if not ticket or ticket.get('guild_id') != guild_id:
        return {"error": "Ticket not found"}, 404

    return render_template('ticket_detail.html', ticket=ticket)


@bp.route("/<int:ticket_id>/update", methods=["POST"])
@guild_required
def update_ticket(ticket_id):
    """Update ticket (status, claim, etc.)."""
    guild_id = session.get("current_guild_id")
    db = TicketDatabase()

    ticket = db.get_ticket_by_id(ticket_id)

    if not ticket or ticket.get('guild_id') != guild_id:
        flash("Ticket not found", "error")
        return redirect(url_for("tickets.list_tickets"))

    action = request.form.get("action")

    if action == "close":
        reason = request.form.get("reason", "")
        if db.update_ticket_status(ticket_id, "closed", reason):
            flash("Ticket closed successfully", "success")
        else:
            flash("Failed to close ticket", "error")

    elif action == "claim":
        user_id = session.get("user_id")
        if db.claim_ticket(ticket["channel_id"], user_id):
            flash("Ticket claimed successfully", "success")
        else:
            flash("Failed to claim ticket", "error")

    elif action == "unclaim":
        if db.unclaim_ticket(ticket["channel_id"]):
            flash("Ticket unclaimed successfully", "success")
        else:
            flash("Failed to unclaim ticket", "error")

    return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))
