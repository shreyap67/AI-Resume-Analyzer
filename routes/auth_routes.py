# routes/auth_routes.py
"""
Authentication blueprint.
Handles: /register, /login, /logout
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# ─── Register ─────────────────────────────────────────────────────────────────
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Show registration form and create a new user account."""
    # If already logged in, skip to dashboard
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))

    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        # ── Basic validation ───────────────────────────────────────────────
        if not all([name, email, password, confirm]):
            flash("All fields are required.", "danger")
            return render_template("auth/register.html", name=name, email=email)

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html", name=name, email=email)

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return render_template("auth/register.html", name=name, email=email)

        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "danger")
            return render_template("auth/register.html", name=name, email=email)

        # ── Create user ────────────────────────────────────────────────────
        user = User(name=name, email=email)
        user.set_password(password)

        # First registered user becomes admin automatically
        if User.query.count() == 0:
            user.is_admin = True

        db.session.add(user)
        db.session.commit()

        flash("Account created! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


# ─── Login ────────────────────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate an existing user."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = request.form.get("remember_me") == "on"

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            # Redirect to the page the user was trying to access, or default to dashboard
            next_page = request.args.get("next")
            flash(f"Welcome back, {user.name}! 👋", "success")
            return redirect(next_page or url_for("dashboard.home"))
        else:
            flash("Invalid email or password.", "danger")

    return render_template("auth/login.html")


# ─── Logout ───────────────────────────────────────────────────────────────────
@auth_bp.route("/logout")
@login_required
def logout():
    """Log out the current user and clear session."""
    logout_user()
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))
