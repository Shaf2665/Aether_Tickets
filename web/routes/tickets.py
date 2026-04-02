"""Tickets routes for viewing and managing tickets."""

import json
from flask import Blueprint, render_template, session, request, jsonify, flash, redirect, url_for
from database import TicketDatabase
from web.auth import guild_required

bp = Blueprint("tickets", __name__, url_prefix="/tickets")


def _resolve_user(db: TicketDatabase, user_id: str) -> str:
    """Return a display name for a user ID, falling back to the raw ID."""
    if not user_id:
        return "-"
    cached = db.get_discord_user(user_id)
    if cached:
        return cached.get("display_name") or cached.get("username") or user_id
    return user_id


def _enrich_tickets(db: TicketDatabase, tickets: list) -> list:
    """Add resolved username fields to a list of ticket dicts."""
    enriched = []
    for t in tickets:
        t = dict(t)
        t["user_display"] = _resolve_user(db, t.get("user_id"))
        t["claimed_display"] = _resolve_user(db, t.get("claimed_by")) if t.get("claimed_by") else None
        enriched.append(t)
    return enriched


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
            or search.lower() in _resolve_user(db, t.get("user_id")).lower()
        ]
        total = len(tickets_filtered)
        offset = (page - 1) * per_page
        tickets = tickets_filtered[offset: offset + per_page]
    else:
        tickets = db.get_guild_tickets(guild_id, status=status_arg, limit=per_page, offset=(page - 1) * per_page)
        total = db.get_guild_ticket_count(guild_id, status=status_arg)

    total_pages = max(1, (total + per_page - 1) // per_page)
    tickets = _enrich_tickets(db, tickets)

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
        from flask import abort
        abort(404)

    ticket = dict(ticket)
    ticket["user_display"] = _resolve_user(db, ticket.get("user_id"))
    ticket["claimed_display"] = _resolve_user(db, ticket.get("claimed_by")) if ticket.get("claimed_by") else None

    messages = db.get_ticket_messages(ticket_id)

    return render_template('ticket_detail.html', ticket=ticket, messages=messages)


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
    username = session.get("username", "Staff")
    user_id = session.get("user_id")

    if action == "close":
        reason = request.form.get("reason", "").strip() or None
        if db.update_ticket_status(ticket_id, "closed", reason):
            # Queue Discord close action
            if ticket.get("channel_id"):
                db.enqueue_bot_action(
                    action="close",
                    ticket_id=ticket_id,
                    channel_id=ticket["channel_id"],
                    guild_id=guild_id,
                    payload=json.dumps({
                        "closer_name": username,
                        "reason": reason or "Closed via Web Dashboard",
                    }),
                )
            flash("Ticket closed successfully", "success")
        else:
            flash("Failed to close ticket", "error")

    elif action == "claim":
        if db.claim_ticket(ticket["channel_id"], user_id):
            # Queue Discord claim notification
            db.enqueue_bot_action(
                action="claim",
                ticket_id=ticket_id,
                channel_id=ticket["channel_id"],
                guild_id=guild_id,
                payload=json.dumps({"claimer_name": username, "claimer_id": str(user_id)}),
            )
            flash("Ticket claimed successfully", "success")
        else:
            flash("Failed to claim ticket", "error")

    elif action == "unclaim":
        if db.unclaim_ticket(ticket["channel_id"]):
            # Queue Discord unclaim notification
            db.enqueue_bot_action(
                action="unclaim",
                ticket_id=ticket_id,
                channel_id=ticket["channel_id"],
                guild_id=guild_id,
                payload=json.dumps({"claimer_name": username}),
            )
            flash("Ticket unclaimed successfully", "success")
        else:
            flash("Failed to unclaim ticket", "error")

    return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))
