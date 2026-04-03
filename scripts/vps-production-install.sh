#!/usr/bin/env bash
# =============================================================================
# Aether Tickets — interactive production setup for a Linux VPS
# =============================================================================
# Run after cloning the repo (or let this script clone it for you):
#
#   chmod +x scripts/vps-production-install.sh
#   ./scripts/vps-production-install.sh
#
# Requires: Python 3.10+, pip, git (for clone option). Tested on Debian/Ubuntu.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_REPO="https://github.com/Shaf2665/Aether_Tickets.git"
DEFAULT_BRANCH="main"

# ── helpers ──────────────────────────────────────────────────────────────────

die() { echo "ERROR: $*" >&2; exit 1; }

section() {
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo " $1"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

info() {
  echo ""
  echo "  [i] $*"
  echo ""
}

prompt() {
  # $1 = help text (optional multiline), $2 = var name, $3 = default value
  local help_text="$1"
  local var_name="$2"
  local default="$3"
  if [[ -n "$help_text" ]]; then
    echo "$help_text" | sed 's/^/  /'
    echo ""
  fi
  if [[ -n "$default" ]]; then
    read -r -p "  ${var_name} [${default}]: " input
    eval "$var_name=\${input:-$default}"
  else
    read -r -p "  ${var_name}: " input
    eval "$var_name=\$input"
  fi
}

prompt_secret() {
  local help_text="$1"
  local var_name="$2"
  if [[ -n "$help_text" ]]; then
    echo "$help_text" | sed 's/^/  /'
    echo ""
  fi
  read -r -s -p "  ${var_name} (hidden): " input
  echo ""
  eval "$var_name=\$input"
}

yes_no() {
  local prompt_text="$1"
  local default="${2:-n}"
  local yn="y/N"
  [[ "$default" == "y" ]] && yn="Y/n"
  read -r -p "  ${prompt_text} [${yn}]: " ans
  ans="${ans:-$default}"
  [[ "${ans,,}" == "y" || "${ans,,}" == "yes" ]]
}

# ── python3 check ────────────────────────────────────────────────────────────

command -v python3 >/dev/null 2>&1 || die "python3 not found. Install Python 3.10+ (e.g. apt install python3 python3-pip python3-venv)."

# ── welcome ──────────────────────────────────────────────────────────────────

section "Aether Tickets — VPS production installer"
echo ""
echo "  This script will:"
echo "    • Place or clone the application files"
echo "    • Ask for Discord bot and (optionally) web dashboard settings"
echo "    • Write a .env file and install Python dependencies"
echo ""
echo "  Have ready:"
echo "    • Bot token (Discord Developer Portal → Bot → Reset / copy token)"
echo "    • For the web UI: OAuth2 Client ID & Secret (OAuth2 → General)"
echo "    • The exact redirect URL you will add under OAuth2 → Redirects"
echo ""

read -r -p "  Press Enter to continue..."

# ── project location ─────────────────────────────────────────────────────────

section "1 — Application directory"

PROJECT_ROOT=""
if [[ -f "$SCRIPT_DIR/../requirements.txt" && -f "$SCRIPT_DIR/../bot.py" ]]; then
  PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
  info "Running from a copy of the repo at:
  $PROJECT_ROOT"
  if ! yes_no "Use this directory for installation?" "y"; then
    PROJECT_ROOT=""
  fi
fi

if [[ -z "$PROJECT_ROOT" ]]; then
  info "You can clone the official repository into a new folder, or quit and
  clone manually, then re-run this script from inside the repo."
  if yes_no "Clone the repository automatically now?" "y"; then
    command -v git >/dev/null 2>&1 || die "git not found. Install git (e.g. apt install git) or clone the repo manually."
    prompt "Parent directory where the project folder will be created (e.g. /opt or \$HOME):
  A subfolder 'Aether_Tickets' will be created unless you change the name below." \
      PARENT_DIR "${HOME}"
    [[ -d "$PARENT_DIR" ]] || die "Directory does not exist: $PARENT_DIR"
    prompt "Folder name for the project:" CLONE_NAME "Aether_Tickets"
    PROJECT_ROOT="${PARENT_DIR%/}/${CLONE_NAME}"
    if [[ -e "$PROJECT_ROOT" ]]; then
      die "Path already exists: $PROJECT_ROOT — remove it or choose another name."
    fi
    prompt "Git repository URL:" GIT_REPO "$DEFAULT_REPO"
    prompt "Git branch:" GIT_BRANCH "$DEFAULT_BRANCH"
    info "Cloning into $PROJECT_ROOT ..."
    git clone --depth=1 --branch "$GIT_BRANCH" "$GIT_REPO" "$PROJECT_ROOT"
  else
    prompt "Absolute path to your existing Aether_Tickets project (contains bot.py):" PROJECT_ROOT ""
    PROJECT_ROOT="${PROJECT_ROOT/#\~/$HOME}"
    [[ -f "$PROJECT_ROOT/bot.py" && -f "$PROJECT_ROOT/requirements.txt" ]] || \
      die "That path does not look like Aether Tickets (missing bot.py or requirements.txt)."
  fi
fi

cd "$PROJECT_ROOT" || die "Cannot cd to $PROJECT_ROOT"

# ── launch mode ────────────────────────────────────────────────────────────────

section "2 — What to run on this server"

echo "  Choose what this VPS will run:"
echo "    1) both   — Discord bot + Web UI together (typical single-VPS setup)"
echo "    2) bot    — Discord bot only (no Flask; OAuth not required in .env)"
echo "    3) web    — Web UI only (bot runs elsewhere; still need bot token for API)"
echo ""

LAUNCH_MODE="both"
read -r -p "  Enter 1, 2, or 3 [1]: " lm
case "${lm:-1}" in
  1|"") LAUNCH_MODE="both" ;;
  2) LAUNCH_MODE="bot" ;;
  3) LAUNCH_MODE="web" ;;
  *) die "Invalid choice." ;;
esac

info "Selected LAUNCH_MODE=$LAUNCH_MODE

  • 'both' uses one process (python app.py) — recommended if this machine runs everything.
  • 'bot' skips Flask/OAuth validation — use if you only want the Discord bot here.
  • 'web' is for a dashboard-only node; ensure your bot + database are consistent if split."

NEEDS_WEB=0
[[ "$LAUNCH_MODE" == "both" || "$LAUNCH_MODE" == "web" ]] && NEEDS_WEB=1

# ── Discord bot ────────────────────────────────────────────────────────────────

section "3 — Discord bot"

prompt_secret "Required. From https://discord.com/developers/applications → Your app → Bot.
  Reset/copy the token. Anyone with this token controls your bot — keep it secret." \
  DISCORD_BOT_TOKEN
[[ -n "$DISCORD_BOT_TOKEN" ]] || die "DISCORD_BOT_TOKEN is required."

prompt_secret "Optional. If set, slash commands sync to this server immediately (good for testing).
  Leave empty for global sync (can take up to ~1 hour for commands to appear everywhere).
  Developer Mode: right-click server → Copy Server ID." \
  GUILD_ID
# trim
GUILD_ID="$(echo "$GUILD_ID" | tr -d '[:space:]')"

prompt "Optional. Category where new ticket channels are created (folder in Discord).
  Leave empty to create tickets at the server root (or configure per-guild via /setup).
  Developer Mode: right-click category → Copy ID." \
  TICKET_CATEGORY_ID ""

prompt "Optional. Role ID for staff ticket access fallback (guild config from /setup can override).
  Leave empty if you will rely only on /setup. Right-click role → Copy ID." \
  SUPPORT_ROLE_ID ""

prompt "Optional. Channel ID for auto-posting the ticket panel (you can use /setup instead).
  Leave empty to skip. Right-click channel → Copy ID." \
  TICKET_CHANNEL_ID ""

# Trim whitespace from optional snowflake IDs
TICKET_CATEGORY_ID="$(echo "$TICKET_CATEGORY_ID" | tr -d '[:space:]')"
SUPPORT_ROLE_ID="$(echo "$SUPPORT_ROLE_ID" | tr -d '[:space:]')"
TICKET_CHANNEL_ID="$(echo "$TICKET_CHANNEL_ID" | tr -d '[:space:]')"

# ── Web / OAuth ──────────────────────────────────────────────────────────────

DISCORD_CLIENT_ID=""
DISCORD_CLIENT_SECRET=""
FLASK_SECRET_KEY=""
DISCORD_REDIRECT_URI=""
BEHIND_PROXY="false"
FLASK_ENV="production"
PORT="5000"
DATABASE_PATH="tickets.db"

if [[ "$NEEDS_WEB" -eq 1 ]]; then
  section "4 — Web dashboard (Flask + Discord OAuth)"

  info "Use the same application as your bot: Developer Portal → OAuth2 → General.
  Add a Redirect URL that matches EXACTLY what you enter below (including http/https and port)."

  prompt "OAuth2 Client ID (OAuth2 → General)." DISCORD_CLIENT_ID ""
  [[ -n "$DISCORD_CLIENT_ID" ]] || die "DISCORD_CLIENT_ID is required for the web UI."

  prompt_secret "OAuth2 Client Secret (OAuth2 → General → Reset if needed)." DISCORD_CLIENT_SECRET
  [[ -n "$DISCORD_CLIENT_SECRET" ]] || die "DISCORD_CLIENT_SECRET is required for the web UI."

  info "Redirect URI must match one of the URLs listed under OAuth2 → Redirects.
  Example: https://tickets.example.com/auth/callback
  Example: http://YOUR_VPS_IP:5000/auth/callback"

  if yes_no "Build redirect URI from a public base URL? (recommended)" "y"; then
    prompt "Public base URL with NO trailing slash — how users open the dashboard in a browser.
  Examples: https://tickets.example.com  or  http://203.0.113.10:5000" PUBLIC_BASE ""
    [[ -n "$PUBLIC_BASE" ]] || die "Public base URL is required."
    PUBLIC_BASE="${PUBLIC_BASE%/}"
    DISCORD_REDIRECT_URI="${PUBLIC_BASE}/auth/callback"
    echo "  → DISCORD_REDIRECT_URI=$DISCORD_REDIRECT_URI"
  else
    prompt "Full redirect URI (must match Developer Portal exactly)." DISCORD_REDIRECT_URI ""
    [[ -n "$DISCORD_REDIRECT_URI" ]] || die "DISCORD_REDIRECT_URI is required."
  fi

  if yes_no "Is Flask behind Nginx, Caddy, or another reverse proxy that handles HTTPS?" "n"; then
    BEHIND_PROXY="true"
    info "BEHIND_PROXY=true enables correct HTTPS/scheme behind a proxy. Ensure your proxy
  forwards X-Forwarded-* headers (see FLASK_SETUP.md)."
  fi

  if yes_no "Generate a random FLASK_SECRET_KEY automatically? (recommended for production)" "y"; then
    FLASK_SECRET_KEY="$(python3 -c "import secrets; print(secrets.token_hex(32))")"
    echo "  → FLASK_SECRET_KEY generated (${#FLASK_SECRET_KEY} hex chars)."
  else
    prompt_secret "FLASK_SECRET_KEY — signs session cookies; keep stable across restarts.
  Or run: python3 -c \"import secrets; print(secrets.token_hex(32))\"" FLASK_SECRET_KEY
    [[ -n "$FLASK_SECRET_KEY" ]] || die "FLASK_SECRET_KEY is required in production."
  fi

  prompt "TCP port for the web UI (use 5000 unless another service uses it; set 80 only if not using a reverse proxy on the same port).
  Remember this port in your redirect URL if you use http://IP:PORT." \
    PORT "5000"

  prompt "FLASK_ENV: use 'production' on a VPS; 'development' enables debug (not for public servers)." \
    FLASK_ENV "production"

  prompt "DATABASE_PATH — SQLite file path (relative to app dir or absolute).
  Default is fine for a single-server install." \
    DATABASE_PATH "tickets.db"
fi

# Optional tuning when bot-only
if [[ "$NEEDS_WEB" -eq 0 ]]; then
  section "4 — Web dashboard"
  info "Skipping OAuth and Flask settings (LAUNCH_MODE=$LAUNCH_MODE)."
  prompt "DATABASE_PATH for the bot (SQLite)." DATABASE_PATH "tickets.db"
fi

# ── write .env ─────────────────────────────────────────────────────────────────

section "5 — Writing .env"

export DISCORD_BOT_TOKEN GUILD_ID TICKET_CATEGORY_ID SUPPORT_ROLE_ID TICKET_CHANNEL_ID
export LAUNCH_MODE PORT FLASK_ENV DATABASE_PATH
export DISCORD_CLIENT_ID DISCORD_CLIENT_SECRET FLASK_SECRET_KEY DISCORD_REDIRECT_URI BEHIND_PROXY

python3 <<'PY'
import os
import re

def esc(s: str) -> str:
    if s is None:
        return ""
    if "\n" in s or "\r" in s:
        raise SystemExit("Values must not contain newlines.")
    if re.search(r'[\s#"]', s) or "=" in s:
        s = s.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{s}"'
    return s

order = [
    ("DISCORD_BOT_TOKEN", True),
    ("GUILD_ID", False),
    ("TICKET_CATEGORY_ID", False),
    ("SUPPORT_ROLE_ID", False),
    ("TICKET_CHANNEL_ID", False),
    ("LAUNCH_MODE", True),
    ("DISCORD_CLIENT_ID", False),
    ("DISCORD_CLIENT_SECRET", False),
    ("FLASK_SECRET_KEY", False),
    ("DISCORD_REDIRECT_URI", False),
    ("FLASK_ENV", True),
    ("PORT", True),
    ("DATABASE_PATH", True),
    ("BEHIND_PROXY", True),
]

lines = [
    "# Generated by scripts/vps-production-install.sh",
    "# Edit with care; restart the app after changes.",
    "",
]

lm = os.environ.get("LAUNCH_MODE", "both")
web_keys = {"DISCORD_CLIENT_ID", "DISCORD_CLIENT_SECRET", "FLASK_SECRET_KEY", "DISCORD_REDIRECT_URI", "BEHIND_PROXY"}

for key, always in order:
    if lm == "bot" and key in web_keys:
        continue
    val = os.environ.get(key, "")
    if not always and not val.strip():
        continue
    lines.append(f"{key}={esc(val)}")

path = ".env"
with open(path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print(f"Wrote {os.path.abspath(path)}")
PY

chmod 600 .env 2>/dev/null || true

# ── pip install ──────────────────────────────────────────────────────────────

section "6 — Python dependencies"

info "Installing packages from requirements.txt. A virtual environment keeps dependencies isolated from system Python (recommended on a shared VPS)."

if [[ -d ".venv" ]]; then
  info "Found existing .venv — using it for pip install."
  # shellcheck source=/dev/null
  source ".venv/bin/activate"
elif yes_no "Create a new virtual environment at .venv in this project?" "y"; then
  python3 -m venv .venv
  # shellcheck source=/dev/null
  source ".venv/bin/activate"
  info "Activated .venv — pip will install into this environment."
fi

python3 -m pip install -U pip
python3 -m pip install -r requirements.txt

# ── SSL / Nginx / Certbot ─────────────────────────────────────────────────────

SSL_CONFIGURED=0
SSL_DOMAIN=""

section "7 — SSL certificate (HTTPS via Certbot + Nginx)"

if [[ "$NEEDS_WEB" -eq 0 ]]; then
  info "LAUNCH_MODE=$LAUNCH_MODE — no web UI, skipping SSL setup."
else
  echo "  Setting up SSL with Certbot + Nginx gives you:"
  echo "    • A free, auto-renewing Let's Encrypt certificate"
  echo "    • Nginx as a reverse proxy (handles HTTPS, forwards to Flask on port 5000)"
  echo "    • Correct HTTPS URLs in Discord OAuth callbacks"
  echo ""
  echo "  Requirements:"
  echo "    • A domain name (e.g. tickets.example.com) pointed at this server's IP"
  echo "    • Port 80 and 443 open in your firewall / security group"
  echo "    • Root / sudo access on this machine"
  echo ""

  if yes_no "Set up SSL with Certbot + Nginx now?" "y"; then

    # ── root check ──────────────────────────────────────────────────────────
    if [[ $EUID -ne 0 ]]; then
      echo ""
      echo "  [!] This step requires root. Re-running the SSL section with sudo..."
      echo "      (you may be prompted for your sudo password)"
      echo ""
      SUDO="sudo"
    else
      SUDO=""
    fi

    # ── detect package manager ───────────────────────────────────────────────
    if command -v apt-get >/dev/null 2>&1; then
      PKG_INSTALL="$SUDO apt-get install -y"
      PKG_UPDATE="$SUDO apt-get update -y"
    elif command -v dnf >/dev/null 2>&1; then
      PKG_INSTALL="$SUDO dnf install -y"
      PKG_UPDATE="$SUDO dnf check-update -y || true"
    elif command -v yum >/dev/null 2>&1; then
      PKG_INSTALL="$SUDO yum install -y"
      PKG_UPDATE="$SUDO yum check-update -y || true"
    else
      die "Unsupported package manager. Install Nginx and certbot manually, then set BEHIND_PROXY=true in .env."
    fi

    # ── domain ──────────────────────────────────────────────────────────────
    prompt "Domain name for this server — must already point to this IP in DNS.
  Example: tickets.example.com  (no http:// prefix, no trailing slash)" \
      SSL_DOMAIN ""
    [[ -n "$SSL_DOMAIN" ]] || die "Domain is required for SSL setup."
    # strip any accidental scheme/slash
    SSL_DOMAIN="${SSL_DOMAIN#http://}"
    SSL_DOMAIN="${SSL_DOMAIN#https://}"
    SSL_DOMAIN="${SSL_DOMAIN%%/*}"

    prompt "Email address for Let's Encrypt expiry notices and account registration.
  Certbot will create a Let's Encrypt account with this address." \
      SSL_EMAIL ""
    [[ -n "$SSL_EMAIL" ]] || die "Email is required for Certbot."

    # ── install nginx + certbot ──────────────────────────────────────────────
    echo ""
    echo "  [>] Updating package lists..."
    $PKG_UPDATE

    if ! command -v nginx >/dev/null 2>&1; then
      echo "  [>] Installing Nginx..."
      $PKG_INSTALL nginx
    else
      echo "  [i] Nginx already installed."
    fi

    if ! command -v certbot >/dev/null 2>&1; then
      echo "  [>] Installing Certbot and the Nginx plugin..."
      if command -v apt-get >/dev/null 2>&1; then
        $PKG_INSTALL certbot python3-certbot-nginx
      elif command -v dnf >/dev/null 2>&1; then
        $PKG_INSTALL certbot python3-certbot-nginx
      else
        $PKG_INSTALL certbot python3-certbot-nginx
      fi
    else
      echo "  [i] Certbot already installed."
    fi

    # ── write initial Nginx config (HTTP only — certbot will upgrade to HTTPS) ──
    NGINX_CONF="/etc/nginx/sites-available/aether-tickets"
    NGINX_ENABLED="/etc/nginx/sites-enabled/aether-tickets"

    # Detect whether this distro uses sites-available/sites-enabled or conf.d
    if [[ -d /etc/nginx/sites-available ]]; then
      NGINX_CONF_DIR="sites-available"
      NGINX_CONF="/etc/nginx/sites-available/aether-tickets"
      NGINX_ENABLED_DIR="/etc/nginx/sites-enabled"
    else
      NGINX_CONF_DIR="conf.d"
      NGINX_CONF="/etc/nginx/conf.d/aether-tickets.conf"
      NGINX_ENABLED_DIR=""
    fi

    echo ""
    echo "  [>] Writing Nginx config to $NGINX_CONF ..."

    $SUDO tee "$NGINX_CONF" > /dev/null <<NGINXCONF
# Aether Tickets — Nginx reverse proxy
# Generated by scripts/vps-production-install.sh
# Certbot will append/replace the SSL block below automatically.

server {
    listen 80;
    server_name ${SSL_DOMAIN};

    # Let's Encrypt ACME challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # Proxy all other traffic to Flask
    location / {
        proxy_pass         http://127.0.0.1:${PORT};
        proxy_http_version 1.1;
        proxy_set_header   Host              \$host;
        proxy_set_header   X-Real-IP         \$remote_addr;
        proxy_set_header   X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }
}
NGINXCONF

    # Enable site (Debian/Ubuntu only)
    if [[ -n "$NGINX_ENABLED_DIR" && ! -L "$NGINX_ENABLED_DIR/aether-tickets" ]]; then
      $SUDO ln -s "$NGINX_CONF" "$NGINX_ENABLED_DIR/aether-tickets"
    fi

    # Remove default site if it conflicts on port 80
    if [[ -L /etc/nginx/sites-enabled/default ]]; then
      echo "  [i] Disabling default Nginx site to free port 80..."
      $SUDO rm -f /etc/nginx/sites-enabled/default
    fi

    echo "  [>] Testing Nginx configuration..."
    $SUDO nginx -t || die "Nginx config test failed. Check $NGINX_CONF for errors."

    echo "  [>] Reloading Nginx..."
    $SUDO systemctl enable nginx 2>/dev/null || true
    $SUDO systemctl reload nginx 2>/dev/null || $SUDO systemctl restart nginx

    # ── run certbot ──────────────────────────────────────────────────────────
    echo ""
    echo "  [>] Running Certbot to obtain and install the SSL certificate..."
    echo "      (Certbot will modify the Nginx config to add HTTPS automatically)"
    echo ""

    $SUDO certbot --nginx \
      --non-interactive \
      --agree-tos \
      --email "$SSL_EMAIL" \
      --domains "$SSL_DOMAIN" \
      --redirect

    echo ""
    echo "  [i] Certificate obtained and Nginx updated for HTTPS."

    # ── verify auto-renewal ──────────────────────────────────────────────────
    echo "  [>] Verifying Certbot auto-renewal timer..."
    if $SUDO systemctl is-enabled certbot.timer >/dev/null 2>&1; then
      echo "  [i] certbot.timer is enabled — certificates will renew automatically."
    elif $SUDO systemctl is-enabled certbot-renew.timer >/dev/null 2>&1; then
      echo "  [i] certbot-renew.timer is enabled — certificates will renew automatically."
    else
      echo "  [!] Auto-renewal timer not detected. Adding a cron job as fallback..."
      (crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet --post-hook 'systemctl reload nginx'") | \
        $SUDO crontab -
      echo "  [i] Cron job added: certbot renew runs daily at 03:00."
    fi

    # ── patch .env ───────────────────────────────────────────────────────────
    echo ""
    echo "  [>] Updating .env: BEHIND_PROXY=true, DISCORD_REDIRECT_URI → https://..."

    HTTPS_BASE="https://${SSL_DOMAIN}"
    NEW_REDIRECT_URI="${HTTPS_BASE}/auth/callback"

    python3 - "$PROJECT_ROOT/.env" "$NEW_REDIRECT_URI" <<'PYEOF'
import sys, re

env_path = sys.argv[1]
new_redirect = sys.argv[2]

with open(env_path, "r", encoding="utf-8") as f:
    content = f.read()

# Update or append BEHIND_PROXY
if re.search(r'^BEHIND_PROXY=', content, re.MULTILINE):
    content = re.sub(r'^BEHIND_PROXY=.*$', 'BEHIND_PROXY=true', content, flags=re.MULTILINE)
else:
    content += "\nBEHIND_PROXY=true\n"

# Update or append DISCORD_REDIRECT_URI
if re.search(r'^DISCORD_REDIRECT_URI=', content, re.MULTILINE):
    content = re.sub(r'^DISCORD_REDIRECT_URI=.*$', f'DISCORD_REDIRECT_URI={new_redirect}', content, flags=re.MULTILINE)
else:
    content += f"\nDISCORD_REDIRECT_URI={new_redirect}\n"

with open(env_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"  .env updated:")
print(f"    BEHIND_PROXY=true")
print(f"    DISCORD_REDIRECT_URI={new_redirect}")
PYEOF

    DISCORD_REDIRECT_URI="$NEW_REDIRECT_URI"
    PUBLIC_BASE="$HTTPS_BASE"
    BEHIND_PROXY="true"
    SSL_CONFIGURED=1

    echo ""
    echo "  [i] SSL setup complete."
    echo "      Remember to add the new redirect URI in the Discord Developer Portal:"
    echo "        $DISCORD_REDIRECT_URI"

  else
    info "SSL setup skipped. You can run this script again later, or configure Nginx + Certbot manually (see FLASK_SETUP.md)."
  fi
fi

# ── done ─────────────────────────────────────────────────────────────────────

section "Done"

echo "  Next steps:"
echo ""
echo "  1) Discord Developer Portal → OAuth2 → Redirects: add EXACTLY:"
if [[ "$NEEDS_WEB" -eq 1 ]]; then
  echo "       $DISCORD_REDIRECT_URI"
else
  echo "       (skipped — web UI not enabled on this install)"
fi
echo ""
echo "  2) Invite the bot (OAuth2 → URL Generator): scopes bot + applications.commands;"
echo "     grant channel/message permissions as in README/CLAUDE.md."
echo ""
echo "  3) In your server, run:  /setup start   (configures panel, roles, categories in DB)"
echo ""
PY_RUN="python3"
if [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
  PY_RUN="$PROJECT_ROOT/.venv/bin/python"
fi
echo "  4) Run the app from this directory:"
echo "       cd $PROJECT_ROOT"
echo "       $PY_RUN app.py"
echo ""
echo "     Or use a process manager (systemd, pm2, supervisord). Example systemd unit:"
echo "       [Unit]"
echo "       Description=Aether Tickets"
echo "       After=network.target"
echo "       [Service]"
echo "       WorkingDirectory=$PROJECT_ROOT"
echo "       ExecStart=$PY_RUN $PROJECT_ROOT/app.py"
echo "       EnvironmentFile=$PROJECT_ROOT/.env"
echo "       Restart=on-failure"
echo "       [Install]"
echo "       WantedBy=multi-user.target"
echo ""
if [[ "$SSL_CONFIGURED" -eq 1 ]]; then
  echo "  5) Firewall: ensure port 80 and 443 are open (Nginx handles them)."
  echo "     Flask port $PORT does NOT need to be public — Nginx proxies to it internally."
elif [[ "$NEEDS_WEB" -eq 1 ]]; then
  echo "  5) For HTTPS + domain, put Nginx/Caddy in front; set BEHIND_PROXY=true and use"
  echo "     an https://... redirect URI. See FLASK_SETUP.md."
fi
echo ""

if [[ "$NEEDS_WEB" -eq 1 ]]; then
  echo "  Dashboard URL:"
  if [[ -n "${PUBLIC_BASE:-}" ]]; then
    echo "       ${PUBLIC_BASE%/}"
  else
    echo "       http://<your-server-ip>:$PORT"
  fi
  echo ""
fi

echo "  Configuration reference: env.example.txt"
echo ""
