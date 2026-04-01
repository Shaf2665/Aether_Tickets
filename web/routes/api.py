"""API routes for AJAX and programmatic access."""

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
    """Update ticket status via AJAX."""
    guild_id = session.get("current_guild_id")
    db = TicketDatabase()

    ticket = db.get_ticket_by_id(ticket_id)

    if not ticket or ticket.get("guild_id") != guild_id:
        return jsonify({"error": "Ticket not found"}), 404

    data = request.get_json()
    new_status = data.get("status")
    reason = data.get("reason")

    if new_status not in ["open", "closed"]:
        return jsonify({"error": "Invalid status"}), 400

    if db.update_ticket_status(ticket_id, new_status, reason):
        return jsonify({
            "status": "success",
            "message": f"Ticket status updated to {new_status}"
        })
    else:
        return jsonify({"error": "Failed to update ticket"}), 500


@bp.route("/tickets/<int:ticket_id>/claim", methods=["POST"])
@guild_required
def claim_ticket(ticket_id):
    """Claim a ticket via AJAX."""
    guild_id = session.get("current_guild_id")
    user_id = session.get("user_id")
    db = TicketDatabase()

    ticket = db.get_ticket_by_id(ticket_id)

    if not ticket or ticket.get("guild_id") != guild_id:
        return jsonify({"error": "Ticket not found"}), 404

    if db.claim_ticket(ticket["channel_id"], user_id):
        return jsonify({
            "status": "success",
            "message": "Ticket claimed successfully"
        })
    else:
        return jsonify({"error": "Failed to claim ticket"}), 500


@bp.route("/tickets/<int:ticket_id>/unclaim", methods=["POST"])
@guild_required
def unclaim_ticket(ticket_id):
    """Unclaim a ticket via AJAX."""
    guild_id = session.get("current_guild_id")
    db = TicketDatabase()

    ticket = db.get_ticket_by_id(ticket_id)

    if not ticket or ticket.get("guild_id") != guild_id:
        return jsonify({"error": "Ticket not found"}), 404

    if db.unclaim_ticket(ticket["channel_id"]):
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
