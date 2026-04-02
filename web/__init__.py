"""Flask app factory for Aether Tickets Web UI"""

from flask import Flask
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix


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

    # Apply ProxyFix when running behind a reverse proxy (Nginx, Caddy, Cloudflare, etc.)
    # This makes Flask trust X-Forwarded-For / X-Forwarded-Proto headers so that:
    #   - url_for() generates https:// URLs correctly
    #   - redirect_uri in OAuth matches the public HTTPS address
    # Controlled by the BEHIND_PROXY env var (set to "true" to enable).
    if app.config.get("BEHIND_PROXY"):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

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
