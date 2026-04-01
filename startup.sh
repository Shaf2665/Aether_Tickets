#!/bin/bash
# =============================================================================
# Aether Tickets — Pterodactyl startup script
# =============================================================================
# Runs every time the server starts:
#   1. Clones the repo on first run  (no manual upload needed)
#   2. Pulls latest code on restart  (auto-update)
#   3. Installs Python dependencies
#   4. Prints setup guide on first run
#   5. Launches the bot / web dashboard
# =============================================================================

cd /home/container

echo "============================================================"
echo "         Aether Tickets — Starting up"
echo "============================================================"

# ---------------------------------------------------------------------------
# 1. Git — clone on first run, pull on every restart
# ---------------------------------------------------------------------------
GIT_REPO="${GIT_REPO:-https://github.com/Shaf2665/Aether_Tickets.git}"
GIT_BRANCH="${GIT_BRANCH:-main}"
AUTO_UPDATE="${AUTO_UPDATE:-1}"
FIRST_RUN=false

if [ ! -d ".git" ]; then
    FIRST_RUN=true
    echo "[git] First run — cloning ${GIT_REPO} (branch: ${GIT_BRANCH})..."
    git clone --depth=1 --branch "${GIT_BRANCH}" "${GIT_REPO}" .
    if [ $? -ne 0 ]; then
        echo "[git] ERROR: git clone failed."
        echo "[git] Check that GIT_REPO is correct in the Startup tab."
        exit 1
    fi
    echo "[git] Clone complete."
else
    if [ "$AUTO_UPDATE" = "1" ]; then
        echo "[git] Pulling latest changes from ${GIT_BRANCH}..."
        git fetch origin "${GIT_BRANCH}" --depth=1
        git reset --hard "origin/${GIT_BRANCH}"
        if [ $? -ne 0 ]; then
            echo "[git] WARNING: git pull failed — running with existing files."
        else
            echo "[git] Update complete."
        fi
    else
        echo "[git] AUTO_UPDATE=0 — skipping git pull."
    fi
fi

# ---------------------------------------------------------------------------
# 2. Install / upgrade Python dependencies
# ---------------------------------------------------------------------------
echo "[pip] Installing Python dependencies..."
pip install -U -r requirements.txt --quiet --no-warn-script-location

if [ $? -ne 0 ]; then
    echo "[pip] ERROR: pip install failed. Check requirements.txt."
    exit 1
fi
echo "[pip] Dependencies ready."

# ---------------------------------------------------------------------------
# 3. Print setup guide on first run
# ---------------------------------------------------------------------------
LAUNCH_MODE="${LAUNCH_MODE:-both}"

if [ "$FIRST_RUN" = "true" ]; then
    echo ""
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║           🎉  AETHER TICKETS — FIRST RUN GUIDE           ║"
    echo "╠══════════════════════════════════════════════════════════╣"
    echo "║                                                          ║"
    echo "║  The bot is now starting for the first time.             ║"
    echo "║  Follow these steps to finish setup:                     ║"
    echo "║                                                          ║"
    echo "║  STEP 1 — Invite the bot to your Discord server          ║"
    echo "║  ┌─────────────────────────────────────────────────────┐ ║"
    echo "║  │ Go to: discord.com/developers/applications          │ ║"
    echo "║  │ → Your App → OAuth2 → URL Generator                 │ ║"
    echo "║  │ Scopes: bot + applications.commands                  │ ║"
    echo "║  │ Permissions: Manage Channels, Manage Roles,          │ ║"
    echo "║  │   Send Messages, Read Messages, Embed Links,         │ ║"
    echo "║  │   Read Message History, Manage Messages              │ ║"
    echo "║  │ Open the URL and invite the bot to your server.      │ ║"
    echo "║  └─────────────────────────────────────────────────────┘ ║"
    echo "║                                                          ║"
    echo "║  STEP 2 — Configure the ticket system                    ║"
    echo "║  ┌─────────────────────────────────────────────────────┐ ║"
    echo "║  │ In your Discord server, run the slash command:      │ ║"
    echo "║  │                                                     │ ║"
    echo "║  │   /setup start                                      │ ║"
    echo "║  │                                                     │ ║"
    echo "║  │ The bot will guide you step by step to set up:      │ ║"
    echo "║  │   • Ticket panel channel                            │ ║"
    echo "║  │   • Staff / support role                            │ ║"
    echo "║  │   • Ping role for new tickets                       │ ║"
    echo "║  │   • Ticket category                                 │ ║"
    echo "║  │   • Closed tickets category                         │ ║"
    echo "║  │   • Custom panel title & description                │ ║"
    echo "║  └─────────────────────────────────────────────────────┘ ║"
    echo "║                                                          ║"
    if [ "$LAUNCH_MODE" != "bot" ]; then
    echo "║  STEP 3 — Access the web dashboard                       ║"
    echo "║  ┌─────────────────────────────────────────────────────┐ ║"
    echo "║  │ Open in your browser:                               │ ║"
    echo "║  │   http://<your-node-address>:${PORT:-5000}                  │ ║"
    echo "║  │ e.g. http://mtc.kovaihost.cloud:${PORT:-5000}               │ ║"
    echo "║  └─────────────────────────────────────────────────────┘ ║"
    echo "║                                                          ║"
    fi
    echo "║  USEFUL COMMANDS (run in your Discord server):           ║"
    echo "║    /setup start    — Configure the ticket system         ║"
    echo "║    /setup view     — View current configuration          ║"
    echo "║    /setup refresh  — Refresh the ticket panel            ║"
    echo "║    /setup reset    — Reset all configuration             ║"
    echo "║    /categories add — Add a ticket category               ║"
    echo "║    /ticket         — Create a new ticket                 ║"
    echo "║    /close          — Close current ticket                ║"
    echo "║    /claim          — Claim a ticket (staff only)         ║"
    echo "║    /ticketstats    — View statistics (admin only)        ║"
    echo "║                                                          ║"
    echo "║  To UPDATE the bot in future: just Restart this server.  ║"
    echo "║  Latest code is pulled from GitHub automatically.        ║"
    echo "║                                                          ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo ""
fi

# ---------------------------------------------------------------------------
# 4. Show access info on every start
# ---------------------------------------------------------------------------
echo "============================================================"
echo " Launch mode : ${LAUNCH_MODE}"
if [ "$LAUNCH_MODE" != "bot" ]; then
    echo " Web UI port : ${PORT:-5000}"
    echo " Access URL  : http://<node-alias>:${PORT:-5000}"
    echo "   e.g. http://mtc.kovaihost.cloud:${PORT:-5000}"
fi
echo "============================================================"

# ---------------------------------------------------------------------------
# 5. Launch
# ---------------------------------------------------------------------------
case "$LAUNCH_MODE" in
    bot)
        echo "[startup] Starting Discord bot only..."
        exec python bot.py
        ;;
    web)
        echo "[startup] Starting Flask web UI only..."
        exec python -c "
import os
from dotenv import load_dotenv
load_dotenv()
from web import create_app
app = create_app()
app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=False, use_reloader=False)
"
        ;;
    both|*)
        echo "[startup] Starting Discord bot + Flask web UI..."
        exec python app.py
        ;;
esac
