# routes/dashboard_routes.py
"""
Dashboard blueprint.
Handles: /dashboard (home), /dashboard/profile
All routes require login.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, AnalysisResult, Resume

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/")
@login_required
def home():
    """
    Main dashboard page.
    Passes stats and chart data to the template.
    """
    # ── Stats cards ───────────────────────────────────────────────────────────
    total_analyses = current_user.total_analyses()
    avg_score      = current_user.average_score()
    highest_score  = current_user.highest_score()
    last_date      = current_user.last_analysis_date()

    # ── Recent analyses (for activity table) ─────────────────────────────────
    recent = (
        AnalysisResult.query
        .filter_by(user_id=current_user.id)
        .order_by(AnalysisResult.created_at.desc())
        .limit(5)
        .all()
    )

    # ── Chart data: scores over last 6 analyses (chronological) ──────────────
    chart_analyses = (
        AnalysisResult.query
        .filter_by(user_id=current_user.id)
        .order_by(AnalysisResult.created_at.asc())
        .limit(6)
        .all()
    )
    chart_labels = [a.created_at.strftime("%b %d") for a in chart_analyses]
    chart_scores = [round(a.ats_score, 1) for a in chart_analyses]

    # ── Skills distribution across all analyses ───────────────────────────────
    from services.skill_extractor import SKILLS_DICTIONARY, skills_by_category
    all_matched: list[str] = []
    for analysis in AnalysisResult.query.filter_by(user_id=current_user.id).all():
        all_matched.extend(analysis.matched_skills)

    category_counts: dict[str, int] = {}
    for skill in all_matched:
        cat = SKILLS_DICTIONARY.get(skill, "other")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    pie_labels = list(category_counts.keys())
    pie_data   = list(category_counts.values())

    return render_template(
        "dashboard/home.html",
        total_analyses=total_analyses,
        avg_score=avg_score,
        highest_score=highest_score,
        last_date=last_date,
        recent=recent,
        chart_labels=chart_labels,
        chart_scores=chart_scores,
        pie_labels=pie_labels,
        pie_data=pie_data,
    )


@dashboard_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """User profile settings – update name, email, password."""
    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_profile":
            name  = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()

            if not name or not email:
                flash("Name and email are required.", "danger")
            else:
                # Check email uniqueness if changed
                existing = db.session.query(type(current_user)).filter_by(email=email).first()
                if existing and existing.id != current_user.id:
                    flash("That email is already in use.", "danger")
                else:
                    current_user.name  = name
                    current_user.email = email
                    db.session.commit()
                    flash("Profile updated successfully.", "success")

        elif action == "change_password":
            current_pw = request.form.get("current_password", "")
            new_pw     = request.form.get("new_password", "")
            confirm_pw = request.form.get("confirm_password", "")

            if not current_user.check_password(current_pw):
                flash("Current password is incorrect.", "danger")
            elif new_pw != confirm_pw:
                flash("New passwords do not match.", "danger")
            elif len(new_pw) < 6:
                flash("Password must be at least 6 characters.", "danger")
            else:
                current_user.set_password(new_pw)
                db.session.commit()
                flash("Password changed successfully.", "success")

        return redirect(url_for("dashboard.profile"))

    return render_template("dashboard/profile.html")
