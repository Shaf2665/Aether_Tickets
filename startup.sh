#!/bin/bash
# =============================================================================
# Aether Tickets — Pterodactyl startup script
# =============================================================================
# This script is used as the Startup Command in the Pterodactyl egg.
# It installs / updates Python dependencies and then launches the application.
#
# Pterodactyl egg startup command:
#   bash startup.sh
# =============================================================================

cd /home/container

echo "============================================================"
echo " Aether Tickets — Starting up"
echo "============================================================"

# ---------------------------------------------------------------------------
# 1. Install / upgrade Python dependencies
# ---------------------------------------------------------------------------
echo "[startup] Installing Python dependencies..."
pip install -U -r requirements.txt --quiet

if [ $? -ne 0 ]; then
    echo "[startup] ERROR: pip install failed. Check requirements.txt."
    exit 1
fi

echo "[startup] Dependencies installed successfully."

# ---------------------------------------------------------------------------
# 2. Decide which entry point to use
#
#    LAUNCH_MODE (env var, default: "both"):
#      both  — run Discord bot + Flask web UI together  (default)
#      bot   — run Discord bot only  (no Flask required)
#      web   — run Flask web UI only (bot must run separately)
# ---------------------------------------------------------------------------
LAUNCH_MODE="${LAUNCH_MODE:-both}"

echo "[startup] Launch mode: ${LAUNCH_MODE}"
echo "[startup] Port: ${PORT:-5000}"
echo "============================================================"

case "$LAUNCH_MODE" in
    bot)
        echo "[startup] Starting Discord bot only..."
        exec python bot.py
        ;;
    web)
        echo "[startup] Starting Flask web UI only..."
        exec python -c "
from dotenv import load_dotenv; load_dotenv()
from web import create_app
import os
app = create_app()
app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=False, use_reloader=False)
"
        ;;
    both|*)
        echo "[startup] Starting Discord bot + Flask web UI..."
        exec python app.py
        ;;
esac
