# Aether Tickets Flask Web UI Setup Guide

This guide will help you set up and run the Flask Web UI for the Aether Tickets Discord bot.

## Overview

The Flask Web UI allows admins to:
- 📊 **View Dashboard** with ticket statistics and analytics
- 📋 **Manage Tickets** - view, filter, search, and update tickets
- 🔐 **Authenticate** via Discord OAuth
- 🎯 **Handle Multiple Guilds** - manage tickets across different Discord servers
- ⚡ **Real-time Updates** - claim, close, and manage tickets from the web interface

## Prerequisites

Before setting up the Flask Web UI, ensure you have:
- Python 3.8 or higher
- The Discord bot already configured and running
- A Discord application with OAuth2 enabled (see below)
- All required packages from `requirements.txt`

## Step 1: Create Discord OAuth Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application or use your existing ticket bot application
3. Go to "OAuth2" → "General" tab
4. **Copy your Client ID** and **Client Secret** (you'll need these)
5. Go to "OAuth2" → "Redirects" tab
6. Add this redirect URI:
   ```
   http://localhost:5000/auth/callback
   ```
   (Change `localhost:5000` if running on a different host/port)
7. Save your changes

## Step 2: Install Dependencies

```bash
# Install Flask and related packages
pip install -r requirements.txt
```

If you already have the bot requirements installed, this will add:
- Flask==3.0.0
- requests>=2.31.0
- PyJWT>=2.8.0
- flask-cors>=4.0.0
- pytz>=2023.3

## Step 3: Configure Environment Variables

1. **Copy the template:**
   ```bash
   cp env.example.txt .env
   ```

2. **Edit `.env` and fill in:**

   **Discord Bot (existing):**
   ```
   DISCORD_BOT_TOKEN=your_bot_token_here
   GUILD_ID=
   TICKET_CATEGORY_ID=
   SUPPORT_ROLE_ID=
   TICKET_CHANNEL_ID=
   ```

   **Flask Web UI (new):**
   ```
   # OAuth Client ID from Discord Developer Portal
   DISCORD_CLIENT_ID=your_client_id_here

   # OAuth Client Secret from Discord Developer Portal
   DISCORD_CLIENT_SECRET=your_client_secret_here

   # Generate a random secret key
   # Run this: python -c "import secrets; print(secrets.token_hex(32))"
   FLASK_SECRET_KEY=your_generated_key_here

   # Environment
   FLASK_ENV=development

   # Redirect URI (must match Discord application settings)
   DISCORD_REDIRECT_URI=http://localhost:5000/auth/callback

   # Database path
   DATABASE_PATH=tickets.db
   ```

## Step 4: Generate Flask Secret Key

Generate a secure random key for Flask sessions:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output and paste it as `FLASK_SECRET_KEY` in your `.env` file.

## Step 5: Run the Application

### Option A: Run Both Bot and Flask Together

```bash
python app.py
```

This will start:
- 🤖 **Discord Bot** - listening for Discord events
- 🌐 **Flask Web UI** - available at http://localhost:5000

### Option B: Run Flask Only (Development)

```bash
cd web
flask run
```

This will start Flask at http://localhost:5000 (bot must be running separately)

## Step 6: Access the Web UI

1. Open your browser: **http://localhost:5000**
2. Click "Login with Discord"
3. Authorize the application
4. You'll be redirected to the dashboard if you're an admin of any guild

**Note:** You must be the owner or have admin permissions in the Discord guild to access the web UI.

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

### "Discord OAuth callback failed"
- Check that `DISCORD_REDIRECT_URI` in `.env` matches your Discord app settings
- Ensure it's exactly: `http://localhost:5000/auth/callback`

### "You don't have admin access to any guilds"
- You must be the **guild owner** or have **admin permissions** in the Discord server
- Your user must have the admin role configured in the bot

### Port 5000 already in use
- Change the port in `app.py`:
  ```python
  app.run(host='0.0.0.0', port=8000)  # Use 8000 instead
  ```
- Update `DISCORD_REDIRECT_URI` in `.env` accordingly

### "No module named 'discord'"
- Run: `pip install -r requirements.txt`

### Database not found
- Ensure `DATABASE_PATH` in `.env` is correct
- The bot must run at least once to create `tickets.db`

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

## Production Deployment

For production use:

1. **Set environment:**
   ```
   FLASK_ENV=production
   ```

2. **Use a production WSGI server** instead of Flask's built-in server:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
   ```

3. **Generate a strong `FLASK_SECRET_KEY`:**
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

4. **Use HTTPS** and update `DISCORD_REDIRECT_URI` accordingly:
   ```
   DISCORD_REDIRECT_URI=https://yourdomain.com/auth/callback
   ```

5. **Run behind a reverse proxy** (nginx/Apache) for security

## Need Help?

- Check `.env` file is correctly configured
- Ensure the Discord bot is running
- Check console logs for error messages
- Verify Discord OAuth application settings

## Future Enhancements

Potential features for future versions:
- Real-time updates via WebSocket
- Bulk ticket operations
- Custom ticket fields
- Email notifications
- Admin audit log
- Export/reporting features
- Dark mode theme
- Mobile app (PWA)
