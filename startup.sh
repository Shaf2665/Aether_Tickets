#!/bin/bash
# =============================================================================
# Aether Tickets — Pterodactyl startup script
# =============================================================================
# This script is the Startup Command for the Pterodactyl egg.
#
# What it does every time the server starts:
#   1. Clones the GitHub repo on first run (no manual upload needed)
#   2. Pulls the latest code from GitHub on every restart (auto-update)
#   3. Installs / upgrades Python dependencies
#   4. Launches the bot (and optionally the web dashboard)
#
# Environment variables (set in Pterodactyl Startup tab):
#   GIT_REPO      — GitHub repo URL  (e.g. https://github.com/user/repo.git)
#   GIT_BRANCH    — Branch to track  (default: main)
#   AUTO_UPDATE   — Pull on restart? (1 = yes [default], 0 = no)
#   LAUNCH_MODE   — both | bot | web  (default: both)
#   PORT          — Set by Pterodactyl automatically
# =============================================================================

cd /home/container

echo "============================================================"
echo " Aether Tickets — Starting up"
echo "============================================================"

# ---------------------------------------------------------------------------
# 1. Git — clone on first run, pull on every restart
# ---------------------------------------------------------------------------
GIT_REPO="${GIT_REPO:-}"
GIT_BRANCH="${GIT_BRANCH:-main}"
AUTO_UPDATE="${AUTO_UPDATE:-1}"

if [ -z "$GIT_REPO" ]; then
    echo "[git] WARNING: GIT_REPO is not set."
    echo "[git] Skipping git operations — files must already be present."
else
    if [ ! -d ".git" ]; then
        echo "[git] No repository found. Cloning ${GIT_REPO} (branch: ${GIT_BRANCH})..."
        git clone --depth=1 --branch "${GIT_BRANCH}" "${GIT_REPO}" .
        if [ $? -ne 0 ]; then
            echo "[git] ERROR: git clone failed. Check GIT_REPO and GIT_BRANCH."
            exit 1
        fi
        echo "[git] Clone complete."
    else
        if [ "$AUTO_UPDATE" = "1" ]; then
            echo "[git] Pulling latest changes from ${GIT_BRANCH}..."
            git fetch origin "${GIT_BRANCH}" --depth=1
            git reset --hard "origin/${GIT_BRANCH}"
            if [ $? -ne 0 ]; then
                echo "[git] WARNING: git pull failed. Running with existing files."
            else
                echo "[git] Update complete."
            fi
        else
            echo "[git] AUTO_UPDATE=0 — skipping git pull."
        fi
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
# 3. Show access info
# ---------------------------------------------------------------------------
LAUNCH_MODE="${LAUNCH_MODE:-both}"
echo "============================================================"
echo " Launch mode : ${LAUNCH_MODE}"
if [ "$LAUNCH_MODE" != "bot" ]; then
    echo " Web UI port : ${PORT:-5000}"
    echo " Access URL  : http://<node-alias>:${PORT:-5000}"
    echo "   (replace <node-alias> with your Pterodactyl node address)"
    echo "   e.g. http://mtc.kovaihost.cloud:${PORT:-5000}"
fi
echo "============================================================"

# ---------------------------------------------------------------------------
# 4. Launch
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
