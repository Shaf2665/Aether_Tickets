"""Flask app factory for Aether Tickets Web UI"""

from flask import Flask
from flask_cors import CORS


def create_app(config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')

    # Load configuration
    if config is None:
        from .config import Config
        app.config.from_object(Config)
    else:
        app.config.update(config)

    # Initialize CORS
    CORS(app)

    # Register blueprints
    from .routes import auth_routes, dashboard, tickets, api

    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(tickets.bp)
    app.register_blueprint(api.bp)

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Not found"}, 404

    @app.errorhandler(500)
    def server_error(error):
        return {"error": "Internal server error"}, 500

    return app
