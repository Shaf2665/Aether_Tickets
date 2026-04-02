# Aether Tickets — Web Dashboard Setup Guide

This guide covers setting up the Flask web dashboard for the Aether Tickets bot on a **VPS or local server**.

> **Pterodactyl users:** The current Pterodactyl egg runs the **bot only**. To add the web dashboard on Pterodactyl, set `LAUNCH_MODE=both` in the Startup tab and add the OAuth variables listed in [Step 3](#step-3--configure-environment-variables) as additional Startup Variables.

## Overview

The web dashboard allows admins to:
- 📊 **View Dashboard** — ticket statistics and analytics charts
- 📋 **Manage Tickets** — view, filter, search, claim, and close tickets from a browser
- 🔐 **Discord OAuth Login** — no separate credentials; sign in with your Discord account
- 🎯 **Multi-Guild Support** — switch between servers you admin
- ⚡ **REST API** — JSON endpoints at `/api/...` for programmatic access

## Prerequisites

- Python 3.10 or higher
- The Discord bot already set up and running (see [README.md](README.md))
- A Discord application (you can reuse the same one as the bot)

## Step 1: Enable OAuth2 on Your Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications) and open your bot's application.
2. Go to **OAuth2 → General**.
3. Copy your **Client ID** and **Client Secret** — you will need both.
4. Under **Redirects**, click **Add Redirect** and enter:
   ```
   http://<your-server-ip-or-domain>:<port>/auth/callback
   ```
   Examples:
   ```
   http://localhost:5000/auth/callback          # local development
   http://203.0.113.10:5000/auth/callback       # VPS with IP
   https://tickets.yourdomain.com/auth/callback # VPS with domain + SSL
   ```
5. Click **Save Changes**.

## Step 2: Install Dependencies

If you haven't already, install all dependencies:

```bash
pip install -r requirements.txt
```

This installs everything needed for both the bot and the web dashboard (Flask, requests, PyJWT, flask-cors, pytz).

## Step 3: Configure Environment Variables

Copy the example file and edit it:

```bash
cp env.example.txt .env
```

Add or update these values in your `.env`:

```env
# ── Bot (required) ────────────────────────────────────────────
DISCORD_BOT_TOKEN=your_bot_token_here

# ── Web Dashboard (required for web UI) ───────────────────────

# Client ID from Discord Developer Portal → OAuth2 → General
DISCORD_CLIENT_ID=your_client_id_here

# Client Secret from Discord Developer Portal → OAuth2 → General
DISCORD_CLIENT_SECRET=your_client_secret_here

# Random secret key for Flask sessions
# Generate one: python -c "import secrets; print(secrets.token_hex(32))"
FLASK_SECRET_KEY=your_generated_key_here

# Must exactly match the redirect URI you added in the Developer Portal
DISCORD_REDIRECT_URI=http://<your-ip-or-domain>:<port>/auth/callback

# ── Optional ───────────────────────────────────────────────────
FLASK_ENV=production          # Use 'development' for debug mode
PORT=5000                     # Port the web UI listens on
DATABASE_PATH=tickets.db      # Path to the SQLite database

# ── SSL / Reverse Proxy (only if applicable) ───────────────────
# Set BEHIND_PROXY=true if Nginx/Caddy/Cloudflare terminates SSL in front of Flask
BEHIND_PROXY=false
# Set FORCE_HTTPS=true only if running Flask directly with SSL (no proxy)
FORCE_HTTPS=false
```

## Step 4: Generate a Flask Secret Key

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output and set it as `FLASK_SECRET_KEY` in your `.env`. This key signs session cookies — keep it secret and don't change it while users are logged in.

## Step 5: Run the Application

### Option A — Bot + Web Dashboard together (recommended)

```bash
python app.py
```

This starts both the Discord bot and the Flask web UI in the same process.

### Option B — Web Dashboard only

```bash
LAUNCH_MODE=web python app.py
```

Use this if the bot is already running separately.

The web dashboard will be available at:
```
http://<your-ip-or-domain>:<PORT>
```

## Step 6: Access the Web Dashboard

1. Open your browser and go to `http://<your-ip-or-domain>:<PORT>`.
2. Click **Login with Discord**.
3. Authorize the application.
4. You will be redirected to the dashboard.

> **Access requirement:** You must be the **owner** or have the **Administrator** permission in at least one Discord server where the bot is present.

## Features

### 🏠 Dashboard
- Total tickets, open/closed counts
- Tickets by category (pie chart)
- Claimed vs. unclaimed tickets
- Recent tickets list

### 📋 Tickets Page
- View all tickets for the current guild
- **Filters:**
  - Status (Open/Closed/All)
  - Search by ticket ID or user
  - Pagination (25 tickets per page)
- **Actions:**
  - Click any ticket for details
  - View full ticket information
  - Change status
  - Claim/unclaim tickets

### 🎯 Ticket Details
- Complete ticket information
- User's description
- Created/closed dates
- Claim status
- **Actions:**
  - Claim/Unclaim ticket
  - Close ticket with reason
  - Discord channel link

### 👥 Multi-Guild Support
- Guild selector in navigation bar
- Switch between guilds you admin
- Automatic data isolation per guild

## File Structure

```
web/
├── __init__.py                 # Flask app factory
├── config.py                   # Flask configuration
├── auth.py                     # Discord OAuth logic
├── routes/
│   ├── __init__.py
│   ├── auth_routes.py          # Login/logout/callback
│   ├── dashboard.py            # Dashboard route
│   ├── tickets.py              # Ticket list/detail routes
│   └── api.py                  # JSON API endpoints
├── templates/
│   ├── base.html               # Base template
│   ├── login.html              # Login page
│   ├── dashboard.html          # Dashboard
│   ├── tickets.html            # Ticket list
│   └── ticket_detail.html      # Ticket details
└── static/
    ├── css/
    │   └── style.css           # Custom styling
    └── js/
        └── main.js             # JavaScript utilities
```

## Troubleshooting

### "Discord OAuth callback failed" / redirect_uri_mismatch
- The `DISCORD_REDIRECT_URI` in your `.env` must **exactly** match the redirect URI saved in the Discord Developer Portal (including `http`/`https`, port, and path).
- After changing it in the portal, save and wait a few seconds.

### "You don't have admin access to any guilds"
- You must be the **owner** or have the **Administrator** permission in a Discord server where the bot is present.
- Make sure the bot has been invited to that server.

### Session lost / login loop on HTTP
- Do **not** set `FORCE_HTTPS=true` or `BEHIND_PROXY=true` when running plain HTTP — this causes the session cookie to be rejected.
- Leave both as `false` (the default) for HTTP setups.

### Port already in use
- Change the port by setting `PORT=8000` (or any free port) in your `.env`.
- Update `DISCORD_REDIRECT_URI` to use the new port.
- Update the redirect URI in the Discord Developer Portal.

### "No module named 'flask'" or similar
- Run: `pip install -r requirements.txt`

### Database not found / empty dashboard
- Ensure `DATABASE_PATH` in `.env` points to the correct `tickets.db` file.
- The bot must have run at least once to create the database.

## API Endpoints (Optional)

The Flask UI includes JSON API endpoints for programmatic access:

```
GET  /api/tickets                    # List tickets
GET  /api/tickets/<id>               # Get ticket details
POST /api/tickets/<id>/status        # Update status
POST /api/tickets/<id>/claim         # Claim ticket
POST /api/tickets/<id>/unclaim       # Unclaim ticket
GET  /api/stats                      # Get guild statistics
```

All endpoints require authentication (Discord OAuth login).

## Production Deployment (VPS)

### Running with systemd

Create a service file so the app restarts automatically:

```ini
# /etc/systemd/system/aether-tickets.service
[Unit]
Description=Aether Tickets Bot + Web UI
After=network.target

[Service]
User=youruser
WorkingDirectory=/path/to/Aether_Tickets
EnvironmentFile=/path/to/Aether_Tickets/.env
ExecStart=/usr/bin/python3 app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable aether-tickets
sudo systemctl start aether-tickets
```

### Running Behind a Reverse Proxy (Nginx + SSL)

If you use Nginx (or Caddy/Cloudflare) to terminate SSL in front of Flask:

1. Set in `.env`:
   ```env
   BEHIND_PROXY=true
   DISCORD_REDIRECT_URI=https://tickets.yourdomain.com/auth/callback
   ```

2. Add the redirect URI to the Discord Developer Portal.

3. Example minimal Nginx config:
   ```nginx
   server {
       listen 443 ssl;
       server_name tickets.yourdomain.com;

       ssl_certificate     /etc/letsencrypt/live/tickets.yourdomain.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/tickets.yourdomain.com/privkey.pem;

       location / {
           proxy_pass         http://127.0.0.1:5000;
           proxy_set_header   Host $host;
           proxy_set_header   X-Real-IP $remote_addr;
           proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header   X-Forwarded-Proto $scheme;
       }
   }
   ```

## Need Help?

1. Re-read the error message in your terminal — it usually tells you exactly what's wrong.
2. Double-check all values in `.env` against the Discord Developer Portal.
3. Make sure the bot is running and has been invited to your server.
4. Check the [README.md](README.md) for general bot setup steps.
