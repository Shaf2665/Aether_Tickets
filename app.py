#!/usr/bin/env python3
"""
Main application entry point for Aether Tickets.
Runs both the Discord bot and Flask web UI concurrently.
"""

import threading
import logging
from dotenv import load_dotenv
from config import Config

# Load environment variables
load_dotenv()

# Validate configuration
try:
    Config.validate()
except ValueError as e:
    print(f"Configuration Error: {e}")
    exit(1)

# Import bot and Flask app after config validation
from bot import DiscordBot
from web import create_app
from web.config import Config as FlaskConfig

# Validate Flask config
try:
    FlaskConfig.validate()
except ValueError as e:
    print(f"Flask Configuration Error: {e}")
    exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_bot():
    """Run the Discord bot."""
    logger.info("Starting Discord bot...")
    bot = DiscordBot()
    try:
        bot.run(Config.BOT_TOKEN)
    except Exception as e:
        logger.error(f"Bot error: {e}")


def run_flask():
    """Run the Flask web UI."""
    logger.info("Starting Flask web UI...")
    app = create_app()

    # Configure app
    app.config['JSON_SORT_KEYS'] = False

    # Run Flask
    try:
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=FlaskConfig.DEBUG,
            use_reloader=False  # Disable reloader to avoid bot restarts
        )
    except Exception as e:
        logger.error(f"Flask error: {e}")


def main():
    """Main entry point - runs both bot and Flask in separate threads."""
    logger.info("=" * 60)
    logger.info("Aether Tickets - Discord Bot + Web UI")
    logger.info("=" * 60)
    logger.info(f"Flask running on: http://0.0.0.0:5000")
    logger.info(f"Discord bot connecting...")
    logger.info("=" * 60)

    # Create threads
    bot_thread = threading.Thread(target=run_bot, daemon=False)
    flask_thread = threading.Thread(target=run_flask, daemon=False)

    # Start threads
    try:
        bot_thread.start()
        flask_thread.start()

        # Wait for threads
        bot_thread.join()
        flask_thread.join()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        exit(0)


if __name__ == "__main__":
    main()
