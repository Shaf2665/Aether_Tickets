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

    # Root redirect
    @app.route("/")
    def index():
        from flask import session, redirect, url_for
        if "user_id" in session:
            return redirect(url_for("dashboard.view"))
        return redirect(url_for("auth.login"))

    # Error handlers — return HTML so the user sees a proper page
    @app.errorhandler(404)
    def not_found(error):
        from flask import render_template, request
        if request.path.startswith("/api/"):
            return {"error": "Not found"}, 404
        return render_template("error.html", code=404, message="Page not found"), 404

    @app.errorhandler(500)
    def server_error(error):
        from flask import render_template, request
        if request.path.startswith("/api/"):
            return {"error": "Internal server error"}, 500
        return render_template("error.html", code=500, message="Internal server error"), 500

    return app
