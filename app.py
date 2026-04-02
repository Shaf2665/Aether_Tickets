#!/usr/bin/env python3
"""
Main application entry point for Aether Tickets.
Runs both the Discord bot and Flask web UI concurrently.

Pterodactyl-compatible:
  - Reads PORT from environment (Pterodactyl sets this automatically).
  - Reads DATABASE_PATH from environment so the DB lives in /home/container.
  - Handles SIGTERM gracefully so the panel process shuts down cleanly.
  - No PID lock files (containers are single-instance by design).
  - Supports LAUNCH_MODE env var: 'both' (default), 'bot', or 'web'.
"""

import os
import signal
import sys
import threading
import logging
from dotenv import load_dotenv

# Load environment variables (.env file is optional in containers;
# Pterodactyl injects variables directly into the environment).
load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────
# Use stdout so Pterodactyl's console captures all output.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ── Launch mode ───────────────────────────────────────────────────────────────
# LAUNCH_MODE controls what gets started:
#   both  — Discord bot + Flask web UI (default)
#   bot   — Discord bot only (Flask/OAuth vars not required)
#   web   — Flask web UI only (bot must run separately)
LAUNCH_MODE = os.getenv("LAUNCH_MODE", "both").lower().strip()
if LAUNCH_MODE not in ("both", "bot", "web"):
    logger.warning(f"Unknown LAUNCH_MODE '{LAUNCH_MODE}', defaulting to 'both'")
    LAUNCH_MODE = "both"

# ── Port configuration ────────────────────────────────────────────────────────
# Pterodactyl exposes the allocated port via the PORT env var.
# Fall back to FLASK_PORT, then 5000 for local development.
FLASK_PORT = int(os.getenv("PORT", os.getenv("FLASK_PORT", 5000)))

# ── Validate bot config ───────────────────────────────────────────────────────
from config import Config

try:
    Config.validate()
except ValueError as e:
    logger.error(f"Configuration Error: {e}")
    sys.exit(1)

# ── Conditionally import and validate Flask config ────────────────────────────
# Only required when the web UI is being launched.
if LAUNCH_MODE in ("both", "web"):
    from web import create_app
    from web.config import Config as FlaskConfig
    try:
        FlaskConfig.validate()
    except ValueError as e:
        logger.error(f"Flask Configuration Error: {e}")
        logger.error(
            "Tip: Set LAUNCH_MODE=bot to run the Discord bot without the web UI."
        )
        sys.exit(1)

# ── Import bot after config validation ───────────────────────────────────────
if LAUNCH_MODE in ("both", "bot"):
    from bot import TicketBot

# ── Shutdown handling ─────────────────────────────────────────────────────────

def _handle_signal(signum, frame):
    """Handle SIGTERM / SIGINT for clean container shutdown."""
    logger.info(f"Received signal {signum}. Shutting down...")
    sys.exit(0)


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


# ── Worker functions ──────────────────────────────────────────────────────────

def run_bot():
    """Run the Discord bot."""
    logger.info("Starting Discord bot...")
    bot = TicketBot()
    try:
        bot.run(Config.BOT_TOKEN)
    except Exception as e:
        logger.error(f"Bot error: {e}")


def run_flask():
    """Run the Flask web UI."""
    logger.info(f"Starting Flask web UI on port {FLASK_PORT}...")
    logger.info(f"Web dashboard will be available at: http://0.0.0.0:{FLASK_PORT}")
    try:
        app = create_app()
        app.config["JSON_SORT_KEYS"] = False
        app.run(
            host="0.0.0.0",
            port=FLASK_PORT,
            debug=FlaskConfig.DEBUG,
            use_reloader=False,  # Must be False — reloader forks the process
                                 # and would restart the bot thread too.
        )
    except Exception as e:
        logger.error(f"Flask failed to start: {e}")
        logger.error("Web dashboard is unavailable. Check port allocation and env vars.")
        os._exit(1)  # Kill the whole process so Pterodactyl shows the failure clearly.


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    logger.info("=" * 60)
    logger.info("Aether Tickets - Discord Bot + Web UI")
    logger.info(f"Launch mode : {LAUNCH_MODE}")
    if LAUNCH_MODE in ("both", "web"):
        logger.info(f"Flask port  : {FLASK_PORT}")
        logger.info(f"Access URL  : http://<your-node-address>:{FLASK_PORT}")
    logger.info("=" * 60)

    threads = []

    if LAUNCH_MODE in ("both", "bot"):
        t = threading.Thread(target=run_bot, name="discord-bot", daemon=True)
        threads.append(t)

    if LAUNCH_MODE in ("both", "web"):
        # Non-daemon so a Flask crash is visible rather than silently swallowed.
        t = threading.Thread(target=run_flask, name="flask-web", daemon=False)
        threads.append(t)

    for t in threads:
        t.start()

    try:
        for t in threads:
            t.join()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")
        sys.exit(0)


if __name__ == "__main__":
    main()
