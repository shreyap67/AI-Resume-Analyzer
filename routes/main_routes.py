# routes/main_routes.py
"""
Main / landing page blueprint.
Handles the public-facing marketing site at /.
"""

from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """
    Landing page.
    If already logged in, redirect straight to the dashboard.
    """
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))
    return render_template("landing/index.html")
