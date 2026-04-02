"""API routes for AJAX and programmatic access."""

import json
from flask import Blueprint, request, jsonify, session
from database import TicketDatabase
from web.auth import guild_required

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/tickets", methods=["GET"])
@guild_required
def get_tickets():
    """Get tickets for the current guild (JSON API)."""
    guild_id = session.get("current_guild_id")
    db = TicketDatabase()

    status = request.args.get("status")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)

    tickets = db.get_guild_tickets(
        guild_id,
        status=status if status != "all" else None,
        limit=per_page,
        offset=(page - 1) * per_page
    )

    return jsonify({
        "status": "success",
        "data": [dict(t) for t in tickets],
        "page": page,
        "per_page": per_page
    })


@bp.route("/tickets/<int:ticket_id>", methods=["GET"])
@guild_required
def get_ticket(ticket_id):
    """Get a specific ticket by ID."""
    guild_id = session.get("current_guild_id")
    db = TicketDatabase()

    ticket = db.get_ticket_by_id(ticket_id)

    if not ticket or ticket.get("guild_id") != guild_id:
        return jsonify({"error": "Ticket not found"}), 404

    return jsonify({
        "status": "success",
        "data": dict(ticket)
    })


@bp.route("/tickets/<int:ticket_id>/status", methods=["POST"])
@guild_required
def update_status(ticket_id):
    """Update ticket status via AJAX. Closing also notifies Discord."""
    guild_id = session.get("current_guild_id")
    username = session.get("username", "Staff")
    db = TicketDatabase()

    ticket = db.get_ticket_by_id(ticket_id)

    if not ticket or ticket.get("guild_id") != guild_id:
        return jsonify({"error": "Ticket not found"}), 404

    data = request.get_json() or {}
    new_status = data.get("status")
    reason = data.get("reason")

    if new_status not in ["open", "closed"]:
        return jsonify({"error": "Invalid status"}), 400

    if db.update_ticket_status(ticket_id, new_status, reason):
        # When closing, queue a Discord action to lock the channel
        if new_status == "closed" and ticket.get("channel_id"):
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
        return jsonify({
            "status": "success",
            "message": f"Ticket status updated to {new_status}"
        })
    else:
        return jsonify({"error": "Failed to update ticket"}), 500


@bp.route("/tickets/<int:ticket_id>/claim", methods=["POST"])
@guild_required
def claim_ticket(ticket_id):
    """Claim a ticket via AJAX and notify Discord."""
    guild_id = session.get("current_guild_id")
    user_id = session.get("user_id")
    username = session.get("username", "Staff")
    db = TicketDatabase()

    ticket = db.get_ticket_by_id(ticket_id)

    if not ticket or ticket.get("guild_id") != guild_id:
        return jsonify({"error": "Ticket not found"}), 404

    if ticket.get("status") != "open":
        return jsonify({"error": "Cannot claim a closed ticket"}), 400

    if db.claim_ticket(ticket["channel_id"], user_id):
        # Queue Discord notification
        db.enqueue_bot_action(
            action="claim",
            ticket_id=ticket_id,
            channel_id=ticket["channel_id"],
            guild_id=guild_id,
            payload=json.dumps({"claimer_name": username, "claimer_id": str(user_id)}),
        )
        return jsonify({
            "status": "success",
            "message": "Ticket claimed successfully"
        })
    else:
        return jsonify({"error": "Failed to claim ticket"}), 500


@bp.route("/tickets/<int:ticket_id>/unclaim", methods=["POST"])
@guild_required
def unclaim_ticket(ticket_id):
    """Unclaim a ticket via AJAX and notify Discord."""
    guild_id = session.get("current_guild_id")
    username = session.get("username", "Staff")
    db = TicketDatabase()

    ticket = db.get_ticket_by_id(ticket_id)

    if not ticket or ticket.get("guild_id") != guild_id:
        return jsonify({"error": "Ticket not found"}), 404

    if db.unclaim_ticket(ticket["channel_id"]):
        # Queue Discord notification
        db.enqueue_bot_action(
            action="unclaim",
            ticket_id=ticket_id,
            channel_id=ticket["channel_id"],
            guild_id=guild_id,
            payload=json.dumps({"claimer_name": username}),
        )
        return jsonify({
            "status": "success",
            "message": "Ticket unclaimed successfully"
        })
    else:
        return jsonify({"error": "Failed to unclaim ticket"}), 500


@bp.route("/stats", methods=["GET"])
@guild_required
def get_stats():
    """Get statistics for current guild."""
    guild_id = session.get("current_guild_id")
    db = TicketDatabase()

    stats = db.get_guild_statistics(guild_id)

    return jsonify({
        "status": "success",
        "data": stats
    })


# ── Feature 1: auto-close settings ───────────────────────────────────────────

@bp.route("/settings/autoclose", methods=["GET"])
@guild_required
def get_autoclose():
    """Get auto-close setting for current guild."""
    guild_id = session.get("current_guild_id")
    db = TicketDatabase()
    hours = db.get_autoclose_hours(guild_id)
    return jsonify({"status": "success", "autoclose_hours": hours})


@bp.route("/settings/autoclose", methods=["POST"])
@guild_required
def set_autoclose():
    """Set or clear auto-close hours for current guild."""
    guild_id = session.get("current_guild_id")
    db = TicketDatabase()
    data = request.get_json() or {}
    hours = data.get("hours")
    if hours is not None:
        try:
            hours = int(hours)
            if hours <= 0:
                hours = None
        except (ValueError, TypeError):
            hours = None
    ok = db.set_autoclose_hours(guild_id, hours)
    if ok:
        return jsonify({"status": "success", "autoclose_hours": hours})
    return jsonify({"error": "Guild config not found. Run /setup start first."}), 404


# ── Feature 2: ticket message sync ───────────────────────────────────────────

@bp.route("/tickets/<int:ticket_id>/messages", methods=["GET"])
@guild_required
def get_messages(ticket_id):
    """Get chat messages for a ticket."""
    guild_id = session.get("current_guild_id")
    db = TicketDatabase()

    ticket = db.get_ticket_by_id(ticket_id)
    if not ticket or ticket.get("guild_id") != guild_id:
        return jsonify({"error": "Ticket not found"}), 404

    messages = db.get_ticket_messages(ticket_id)
    return jsonify({"status": "success", "data": messages})


@bp.route("/tickets/<int:ticket_id>/messages", methods=["POST"])
@guild_required
def send_message(ticket_id):
    """Send a message from the web UI into a ticket (stored in DB only; Discord sync via bot)."""
    guild_id = session.get("current_guild_id")
    user_id = session.get("user_id")
    username = session.get("username", "Web User")
    db = TicketDatabase()

    ticket = db.get_ticket_by_id(ticket_id)
    if not ticket or ticket.get("guild_id") != guild_id:
        return jsonify({"error": "Ticket not found"}), 404

    if ticket.get("status") != "open":
        return jsonify({"error": "Cannot send messages to a closed ticket"}), 400

    data = request.get_json() or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "Message content is required"}), 400
    if len(content) > 2000:
        return jsonify({"error": "Message too long (max 2000 characters)"}), 400

    msg_id = db.save_ticket_message(
        ticket_id=ticket_id,
        author_id=str(user_id),
        author_name=username,
        content=content,
        source="web",
    )
    # Update activity timestamp
    db.update_ticket_activity(ticket["channel_id"])

    # Queue Discord message delivery
    db.enqueue_bot_action(
        action="send_message",
        ticket_id=ticket_id,
        channel_id=ticket["channel_id"],
        guild_id=guild_id,
        payload=json.dumps({"author_name": username, "content": content}),
    )

    return jsonify({
        "status": "success",
        "data": {
            "id": msg_id,
            "author_name": username,
            "content": content,
            "source": "web",
        }
    })