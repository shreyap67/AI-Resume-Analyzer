# app.py
"""
Application factory for ResumeAI.

Usage:
    python app.py                       # development server
    flask --app app run --debug         # Flask CLI
    gunicorn "app:create_app('production')" --workers 4 --bind 0.0.0.0:8000
"""

import os
import logging
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, current_user

from config import config_map
from models.extensions import db
from models.user_model import User


# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Application factory ───────────────────────────────────────────────────────

def create_app(config_name: str | None = None) -> Flask:
    """
    Create and fully configure a Flask application instance.

    Args:
        config_name: 'development' | 'production' | 'default'
                     Falls back to FLASK_ENV environment variable.
    """
    app = Flask(__name__, instance_relative_config=True)

    # ── Load config ───────────────────────────────────────────────────────────
    env = config_name or os.environ.get("FLASK_ENV", "default")
    app.config.from_object(config_map[env])
    logger.info("Starting ResumeAI [%s mode]", env)

    # ── Ensure required directories exist ─────────────────────────────────────
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.instance_path, exist_ok=True)

    # ── Bind extensions ───────────────────────────────────────────────────────
    _init_extensions(app)

    # ── Register blueprints ───────────────────────────────────────────────────
    _register_blueprints(app)

    # ── Register error handlers ───────────────────────────────────────────────
    _register_error_handlers(app)

    # ── Register template filters / context processors ────────────────────────
    _register_template_helpers(app)

    return app


# ── Extensions ────────────────────────────────────────────────────────────────

def _init_extensions(app: Flask) -> None:
    """Initialise Flask extensions and bind them to the app."""

    # SQLAlchemy ORM
    db.init_app(app)

    # Flask-Login session management
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view             = "auth.login"
    login_manager.login_message          = "Please log in to access this page."
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id: str):
        """
        Called by Flask-Login on every request to reload the user object.
        Returns None (never raises) if the user_id is invalid or stale.
        """
        try:
            return User.query.get(int(user_id))
        except Exception:
            return None

    @login_manager.unauthorized_handler
    def unauthorized():
        """
        Fires when @login_required blocks an unauthenticated request.
        Saves the original destination in `next` so the user is redirected
        there after successful login.
        """
        flash("Please log in to access that page.", "info")
        return redirect(url_for("auth.login", next=request.path))


# ── Blueprints ────────────────────────────────────────────────────────────────

def _register_blueprints(app: Flask) -> None:
    """Import and register every route blueprint with its URL prefix."""

    from routes.main_routes      import main_bp       # /
    from routes.auth_routes      import auth_bp       # /auth/
    from routes.dashboard_routes import dashboard_bp  # /dashboard/
    from routes.resume_routes    import resume_bp     # /resume/
    from routes.analysis_routes  import analysis_bp   # /analyze/
    from routes.history_routes   import history_bp    # /history/
    from routes.admin_routes     import admin_bp      # /admin/

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(resume_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(admin_bp)

    logger.info("All 7 blueprints registered successfully")


# ── Error handlers ────────────────────────────────────────────────────────────

def _register_error_handlers(app: Flask) -> None:
    """
    Register HTTP error handlers.

    Every handler renders a dark-themed Jinja2 template that extends
    errors/base_error.html. Because these are rendered via render_template(),
    Flask-Login's current_user proxy is available inside the templates,
    allowing conditional navigation buttons (dashboard vs. home).
    """

    @app.errorhandler(403)
    def forbidden(error):
        """
        403 Forbidden – triggered by abort(403) in the @admin_required
        decorator when a non-admin user tries to access /admin/.
        Shows contextual buttons: 'Back to Dashboard' if logged in,
        'Log In' if not.
        """
        logger.warning("403 Forbidden at %s", request.path)
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(error):
        """
        404 Not Found – invalid URL, deleted resource, or typo.
        Shows dashboard link for logged-in users, home + login for guests.
        """
        logger.info("404 Not Found: %s", request.path)
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def request_entity_too_large(error):
        """
        413 Payload Too Large – fires when an uploaded PDF exceeds
        MAX_CONTENT_LENGTH (10 MB). Points the user to free compression tools.
        """
        logger.warning("413 Oversized upload from %s", request.remote_addr)
        return render_template("errors/413.html"), 413

    @app.errorhandler(500)
    def internal_server_error(error):
        """
        500 Internal Server Error – unhandled exception in a view function.
        Rolls back any broken DB transaction before rendering the error page
        so the session is left in a clean state.
        """
        logger.error("500 Internal Server Error: %s", error, exc_info=True)
        try:
            db.session.rollback()
        except Exception:
            pass
        return render_template("errors/500.html"), 500

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error):
        """
        Catch-all for any unhandled Python exception not caught by Flask's
        normal exception handling. In debug mode we re-raise so Werkzeug's
        interactive debugger works normally. In production we show the 500 page.
        """
        if app.debug:
            raise error  # Werkzeug debugger takes over in development
        logger.error("Unhandled exception: %s", error, exc_info=True)
        try:
            db.session.rollback()
        except Exception:
            pass
        return render_template("errors/500.html"), 500


# ── Template helpers ──────────────────────────────────────────────────────────

def _register_template_helpers(app: Flask) -> None:
    """
    Jinja2 filters and context processors available in every template,
    including error pages.
    """

    # ── Custom filters ────────────────────────────────────────────────────────

    @app.template_filter("datefmt")
    def date_format(value, fmt: str = "%b %d, %Y") -> str:
        """
        Format a Python datetime object.
        Usage: {{ analysis.created_at | datefmt }}
               {{ analysis.created_at | datefmt('%d/%m/%Y %H:%M') }}
        """
        if value is None:
            return "N/A"
        try:
            return value.strftime(fmt)
        except (AttributeError, ValueError):
            return str(value)

    @app.template_filter("score_color")
    def score_color(value: float) -> str:
        """
        Map an ATS score (0–100) to a semantic CSS class suffix.
        Used as: <span class="badge badge-{{ score | score_color }}">

        Returns: 'success' | 'info' | 'warning' | 'danger'
        """
        try:
            v = float(value)
        except (TypeError, ValueError):
            return "info"
        if v >= 90:  return "success"
        if v >= 75:  return "info"
        if v >= 60:  return "warning"
        return "danger"

    @app.template_filter("score_label")
    def score_label(value: float) -> str:
        """
        Map an ATS score to a human-readable label.
        Usage: {{ analysis.ats_score | score_label }}

        Returns: 'Excellent' | 'Good' | 'Average' | 'Needs Work'
        """
        try:
            v = float(value)
        except (TypeError, ValueError):
            return "Unknown"
        if v >= 90:  return "Excellent"
        if v >= 75:  return "Good"
        if v >= 60:  return "Average"
        return "Needs Work"

    # ── Context processor ─────────────────────────────────────────────────────

    @app.context_processor
    def inject_globals() -> dict:
        """
        Inject variables into every Jinja2 template context automatically.
        These are accessible in all templates including error pages,
        base layouts, and partials.
        """
        from datetime import datetime
        return {
            "current_year": datetime.utcnow().year,
            "app_name":     "ResumeAI",
        }


# ── Flask CLI commands ────────────────────────────────────────────────────────

def _register_cli_commands(app: Flask) -> None:
    """
    Register Flask CLI commands callable via: flask <command>
    These run inside the app context automatically.
    """

    @app.cli.command("init-db")
    def init_db_command():
        """Create database tables and seed default data."""
        from init_db import init_database
        init_database()

    @app.cli.command("create-admin")
    def create_admin_command():
        """Promote the first registered user to admin status."""
        user = User.query.first()
        if user:
            user.is_admin = True
            db.session.commit()
            print(f"✅ {user.email} has been promoted to admin.")
        else:
            print("❌ No users found. Register an account first.")

    @app.cli.command("list-users")
    def list_users_command():
        """Print all registered users."""
        users = User.query.order_by(User.created_at).all()
        if not users:
            print("No users registered.")
            return
        print(f"\n{'ID':<5} {'Name':<20} {'Email':<30} {'Admin':<6} {'Joined'}")
        print("-" * 75)
        for u in users:
            print(f"{u.id:<5} {u.name:<20} {u.email:<30} {'Yes' if u.is_admin else 'No':<6} {u.created_at.strftime('%Y-%m-%d')}")


# ── Development entry point ───────────────────────────────────────────────────

if __name__ == "__main__":
    flask_app = create_app("development")
    _register_cli_commands(flask_app)
    flask_app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=True,
    )
