# Aether Tickets

A Discord ticket bot built with Python and discord.py, with a Flask web dashboard for admins. Users create private support channels; staff manage them from Discord or a browser.

**Current Version: 1.7**

---

## Features

| Feature | Description |
|---|---|
| Ticket Creation | `/ticket` command or panel button creates a private channel |
| Ticket Closing | `/close [reason]` or Close button locks the channel and posts a delete button |
| Ticket Claiming | `/claim` / `/unclaim` for staff |
| Categories | Per-server ticket categories with dropdown selection |
| Interactive Setup | `/setup start` — 6-step wizard, no config files needed |
| Statistics | `/ticketstats` for admins |
| Web Dashboard | Flask UI with Discord OAuth — view, search, claim, close tickets |
| Ticket Chat Sync | Messages sent in Discord appear in the Web UI; messages sent from the Web UI are forwarded to Discord in real-time |
| Web UI → Discord Sync | Claim, unclaim, and close actions in the Web UI are reflected in the Discord channel within seconds |
| Ticket Auto-Close | Inactive tickets are automatically closed after a configurable number of hours — set via `/autoclose set <hours>` in Discord or the Web UI dashboard (both are in sync) |
| Discord Delete Sync | Deleting a ticket channel in Discord marks it as deleted in the Web UI |
| Username Display | Ticket lists show Discord display names instead of raw user IDs |
| Multi-Guild | Each server has isolated config and ticket data |
| Pterodactyl Ready | Auto-clone from GitHub, auto-update on restart, no file uploads |

---

## Hosting Options

Choose the method that fits your setup:

- **[Option A — Pterodactyl Panel](#option-a--pterodactyl-panel)** — Recommended for most users. Import the egg, fill in your bot token, done.
- **[Option B — VPS / Local Server](#option-b--vps--local-server)** — Clone the repo and run with Python directly.

---

## Option A — Pterodactyl Panel

> No file uploads or SSH needed. The egg handles everything automatically.

### Step 1 — Import the Egg

1. Log in to your **Pterodactyl admin panel**.
2. Go to **Admin → Nests** → select or create a nest (e.g. "Bots").
3. Click **Import Egg** and upload `egg-aether-tickets.json` from this repository.

### Step 2 — Create the Server

1. Go to **Admin → Servers → Create New Server**.
2. Select the **Aether Tickets** egg.
3. Set an **Allocation** (any port — the bot doesn't need a public port unless you enable the web dashboard).
4. Click **Create Server**.

### Step 3 — Installation

Pterodactyl will run the installation script automatically. It will:
- Install Git, Python, and pip inside the container.
- Clone this repository from GitHub.
- Install all Python dependencies.

Wait for the status to change from **Installing** to **Offline** before proceeding.

### Step 4 — Configure the Startup Variables

Go to your server's **Startup** tab and fill in:

| Variable | Required | Description |
|---|---|---|
| **Discord Bot Token** | ✅ Yes | Your bot token from the Discord Developer Portal |
| **Guild ID** | Optional | Your server ID for instant slash command sync |
| **Auto Update on Restart** | Optional | Pull latest code from GitHub on every start (default: on) |
| Git Repository URL | Advanced | Pre-filled — only change if you forked the repo |
| Git Branch | Advanced | Pre-filled as `main` |
| Database Path | Advanced | Pre-filled as `tickets.db` — do not change |

> **Where to get your Bot Token:**
> Discord Developer Portal → Your App → Bot → Reset Token → Copy.

### Step 5 — Start the Server

Click **Start**. The bot will launch and print a first-run setup guide in the console.

### Step 6 — Invite the Bot to Your Server

1. Go to [Discord Developer Portal](https://discord.com/developers/applications) → Your App → **OAuth2 → URL Generator**.
2. Scopes: `bot` + `applications.commands`.
3. Permissions: `Manage Channels`, `Manage Roles`, `Send Messages`, `View Channels`, `Read Message History`, `Embed Links`, `Manage Messages`.
4. Open the generated URL and invite the bot.

### Step 7 — Configure the Ticket System

In your Discord server, run:

```
/setup start
```

The bot will guide you through:
1. Panel channel
2. Support / staff role
3. Ping role for new tickets
4. Ticket category
5. Custom panel title
6. Custom panel description

### Updating the Bot

Just **Restart** the server. If **Auto Update** is enabled, the latest code is pulled from GitHub automatically before the bot starts.

---

## Option B — VPS / Local Server

### Prerequisites

- Python 3.10 or higher
- Git
- A Discord bot token (see below)

### Step 1 — Clone the Repository

```bash
git clone https://github.com/Shaf2665/Aether_Tickets.git
cd Aether_Tickets
```

### Step 2 — Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3 — Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications) → **New Application**.
2. Go to the **Bot** tab → **Reset Token** → copy the token.
3. Enable all three **Privileged Gateway Intents**:
   - ✅ Presence Intent
   - ✅ Server Members Intent
   - ✅ Message Content Intent
4. Go to **OAuth2 → URL Generator**:
   - Scopes: `bot` + `applications.commands`
   - Permissions: `Manage Channels`, `Manage Roles`, `Send Messages`, `View Channels`, `Read Message History`, `Embed Links`, `Manage Messages`
5. Open the generated URL and invite the bot to your server.

### Step 4 — Configure Environment Variables

Copy the example file and edit it:

```bash
cp env.example.txt .env
```

Minimum required for **bot only**:

```env
DISCORD_BOT_TOKEN=your_bot_token_here
```

Optional — for faster slash command sync during development:

```env
GUILD_ID=your_server_id_here
```

> For the **web dashboard**, see [FLASK_SETUP.md](FLASK_SETUP.md) for the additional variables needed.

### Step 5 — Run the Bot

**Bot only:**
```bash
python bot.py
```

**Bot + Web Dashboard together:**
```bash
python app.py
```

You should see output like:
```
[BotName] has logged in!
```

Keep the terminal open (or use a process manager like `systemd`, `pm2`, or `screen`).

### Step 6 — Configure the Ticket System

In your Discord server, run `/setup start` and follow the prompts (same as Pterodactyl Step 7 above).

### Keeping the Bot Running (VPS)

Use a process manager so the bot restarts automatically:

**systemd (recommended for Linux VPS):**

```ini
# /etc/systemd/system/aether-tickets.service
[Unit]
Description=Aether Tickets Bot
After=network.target

[Service]
User=youruser
WorkingDirectory=/path/to/Aether_Tickets
ExecStart=/usr/bin/python3 bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable aether-tickets
sudo systemctl start aether-tickets
```

**Updating (VPS):**
```bash
git pull
pip install -U -r requirements.txt
sudo systemctl restart aether-tickets
```

---

## Commands Reference

| Command | Description | Who Can Use |
|---|---|---|
| `/ticket` | Create a new support ticket | Everyone |
| `/close [reason]` | Close the current ticket | Ticket owner or Admin |
| `/claim` | Claim the current ticket | Staff or Admin |
| `/unclaim` | Unclaim the current ticket | Claimer or Admin |
| `/ticketstats` | View ticket statistics | Admin only |
| `/delete` | Permanently delete a ticket channel | Admin only |
| `/setup start` | Start interactive setup | Admin only |
| `/setup view` | View current configuration | Admin only |
| `/setup reset` | Reset configuration | Admin only |
| `/setup refresh` | Refresh/recreate ticket panel | Admin only |
| `/categories list` | List ticket categories | Admin only |
| `/categories add` | Add a ticket category | Admin only |
| `/categories remove` | Remove a ticket category | Admin only |
| `/categories edit` | Edit a ticket category | Admin only |
| `/autoclose set <hours>` | Enable auto-close after N hours of inactivity | Admin only |
| `/autoclose disable` | Disable automatic ticket closing | Admin only |
| `/autoclose status` | Show current auto-close setting | Admin only |

---

## Required Bot Permissions

| Permission | Why |
|---|---|
| Manage Channels | Create and move ticket channels |
| Manage Roles | Set channel permission overwrites |
| Send Messages | Send messages and embeds |
| View Channels | See channels |
| Read Message History | Read ticket history |
| Embed Links | Send rich embeds |
| Manage Messages | Pin messages in ticket channels |

> **Role hierarchy tip:** The bot's role must be **above** any roles it manages in your server's role list.

---

## Web Dashboard

The Flask web dashboard lets admins manage tickets from a browser using Discord OAuth login.

See **[FLASK_SETUP.md](FLASK_SETUP.md)** for full setup instructions.

**Quick summary:**
- Login with Discord (OAuth2) — no separate credentials
- View ticket stats, search/filter tickets, claim/close from the web
- **Ticket Chat** — read and send messages that sync with the Discord channel in real-time
- **Auto-Close** — configure inactivity timeout (hours) per server from the dashboard
- Claim/unclaim/close actions are reflected in Discord within seconds
- Username display — shows Discord display names instead of raw user IDs
- Multi-guild support
- REST API endpoints at `/api/...`

---

## Project Structure

```
Aether_Tickets/
├── app.py                    # Entrypoint: runs bot + Flask concurrently
├── bot.py                    # TicketBot class, cog loader, persistent views
├── config.py                 # Bot config (reads env vars)
├── database.py               # SQLite database (tickets, guild_config, categories)
├── requirements.txt          # Python dependencies
├── startup.sh                # Pterodactyl startup script
├── egg-aether-tickets.json   # Pterodactyl egg (import this into your panel)
├── env.example.txt           # Example .env for local/VPS setup
│
├── commands/
│   ├── ticket.py             # /ticket /close /claim /unclaim /ticketstats /delete
│   ├── setup.py              # /setup start|view|reset|refresh
│   └── categories.py         # /categories list|add|remove|edit
│
├── utils/
│   ├── embeds.py             # All embed builders
│   └── ticket_creation.py    # Shared ticket open/close logic, persistent views
│
└── web/
    ├── __init__.py           # Flask app factory
    ├── config.py             # Flask config (OAuth, session, SSL)
    ├── auth.py               # Discord OAuth + login_required decorator
    └── routes/
        ├── auth_routes.py    # /auth/login, /auth/callback, /auth/logout
        ├── dashboard.py      # /dashboard
        ├── tickets.py        # /tickets list and detail
        └── api.py            # /api JSON endpoints
```

---

## Troubleshooting

### Slash commands don't appear
- Wait up to 1 hour for global sync, or set `GUILD_ID` for instant sync.
- Restart the bot.

### Bot can't create channels / manage roles
- Check the bot's permissions and role hierarchy position.

### `/setup` not working
- You must have the **Administrator** permission in the server.

### Web dashboard OAuth fails
- Ensure `DISCORD_REDIRECT_URI` in your `.env` exactly matches the redirect URI added in the Discord Developer Portal.
- On HTTP (no SSL), make sure `FORCE_HTTPS` and `BEHIND_PROXY` are not set to `true`.

### Pterodactyl — server stuck on "Installing"
- Check the installation log in the panel for errors.
- Verify `GIT_REPO` and `GIT_BRANCH` are correct in the Startup tab.

### Pterodactyl — bot won't start
- Check the console for errors.
- Ensure `DISCORD_BOT_TOKEN` is set correctly in the Startup tab.

---

## License

MIT License — open source, free to modify and use.
