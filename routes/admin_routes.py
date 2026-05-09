# routes/admin_routes.py
"""
Admin blueprint.
Only accessible to users with is_admin=True.
Handles: /admin/, /admin/roles, /admin/roles/add,
         /admin/roles/edit/<id>, /admin/roles/delete/<id>,
         /admin/skills, /admin/users
"""

import logging
from functools import wraps
from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, jsonify, abort
)
from flask_login import login_required, current_user
from models import db, User, JobRole, Skill, AnalysisResult, Resume

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ─── Admin-only decorator ─────────────────────────────────────────────────────
def admin_required(f):
    """
    Decorator that combines @login_required with an admin check.
    Returns 403 Forbidden if the logged-in user is not an admin.
    """
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ─── Dashboard ────────────────────────────────────────────────────────────────
@admin_bp.route("/")
@admin_required
def panel():
    """Admin overview with platform statistics."""
    stats = {
        "total_users":    User.query.count(),
        "total_analyses": AnalysisResult.query.count(),
        "total_resumes":  Resume.query.count(),
        "total_roles":    JobRole.query.count(),
        "total_skills":   Skill.query.count(),
    }
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_analyses = (
        AnalysisResult.query
        .order_by(AnalysisResult.created_at.desc())
        .limit(10)
        .all()
    )
    return render_template(
        "admin/admin_panel.html",
        stats=stats,
        recent_users=recent_users,
        recent_analyses=recent_analyses,
    )


# ─── Job Role management ──────────────────────────────────────────────────────
@admin_bp.route("/roles")
@admin_required
def roles():
    """List all job roles."""
    all_roles = JobRole.query.order_by(JobRole.title).all()
    return render_template("admin/admin_panel.html", roles=all_roles, view="roles")


@admin_bp.route("/roles/add", methods=["POST"])
@admin_required
def add_role():
    """
    Create a new job role.
    Expects form fields: title, description, experience_level, skills (comma-separated).
    """
    title       = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    exp_level   = request.form.get("experience_level", "mid").strip()
    skills_raw  = request.form.get("skills", "")

    if not title:
        flash("Role title is required.", "danger")
        return redirect(url_for("admin.panel"))

    if JobRole.query.filter_by(title=title).first():
        flash(f"A role named '{title}' already exists.", "danger")
        return redirect(url_for("admin.panel"))

    role = JobRole(title=title, description=description, experience_level=exp_level)

    # Parse comma-separated skills and link to role
    skill_names = [s.strip().lower() for s in skills_raw.split(",") if s.strip()]
    for skill_name in skill_names:
        skill = Skill.query.filter_by(name=skill_name).first()
        if not skill:
            # Auto-create skill if it doesn't exist yet
            skill = Skill(name=skill_name)
            db.session.add(skill)
        role.required_skills.append(skill)

    db.session.add(role)
    db.session.commit()

    logger.info("Admin %s added job role: %s", current_user.email, title)
    flash(f"Job role '{title}' added with {len(skill_names)} skills.", "success")
    return redirect(url_for("admin.panel"))


@admin_bp.route("/roles/edit/<int:role_id>", methods=["GET", "POST"])
@admin_required
def edit_role(role_id: int):
    """Edit an existing job role's title, description and skills."""
    role = JobRole.query.get_or_404(role_id)

    if request.method == "POST":
        role.title       = request.form.get("title", role.title).strip()
        role.description = request.form.get("description", "").strip()
        role.experience_level = request.form.get("experience_level", role.experience_level)

        skills_raw = request.form.get("skills", "")
        skill_names = [s.strip().lower() for s in skills_raw.split(",") if s.strip()]

        # Replace skills entirely
        role.required_skills = []
        for skill_name in skill_names:
            skill = Skill.query.filter_by(name=skill_name).first()
            if not skill:
                skill = Skill(name=skill_name)
                db.session.add(skill)
            role.required_skills.append(skill)

        db.session.commit()
        flash(f"Role '{role.title}' updated.", "success")
        return redirect(url_for("admin.panel"))

    # GET – render edit form
    current_skills = ", ".join(role.skill_names())
    return render_template(
        "admin/admin_panel.html",
        edit_role=role,
        current_skills=current_skills,
        view="edit_role",
    )


@admin_bp.route("/roles/delete/<int:role_id>", methods=["POST"])
@admin_required
def delete_role(role_id: int):
    """Delete a job role. Supports AJAX."""
    role = JobRole.query.get_or_404(role_id)
    db.session.delete(role)
    db.session.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True, "deleted_id": role_id})

    flash(f"Role '{role.title}' deleted.", "info")
    return redirect(url_for("admin.panel"))


# ─── Skill management ─────────────────────────────────────────────────────────
@admin_bp.route("/skills")
@admin_required
def skills():
    """List all skills in the master dictionary."""
    all_skills = Skill.query.order_by(Skill.name).all()
    return render_template("admin/admin_panel.html", skills=all_skills, view="skills")


@admin_bp.route("/skills/add", methods=["POST"])
@admin_required
def add_skill():
    """Add a new skill to the master list."""
    name     = request.form.get("name", "").strip().lower()
    category = request.form.get("category", "general").strip()

    if not name:
        flash("Skill name is required.", "danger")
        return redirect(url_for("admin.panel"))

    if Skill.query.filter_by(name=name).first():
        flash(f"Skill '{name}' already exists.", "danger")
        return redirect(url_for("admin.panel"))

    skill = Skill(name=name, category=category)
    db.session.add(skill)
    db.session.commit()
    flash(f"Skill '{name}' added.", "success")
    return redirect(url_for("admin.panel"))


@admin_bp.route("/skills/delete/<int:skill_id>", methods=["POST"])
@admin_required
def delete_skill(skill_id: int):
    """Delete a skill from the master list."""
    skill = Skill.query.get_or_404(skill_id)
    db.session.delete(skill)
    db.session.commit()
    flash(f"Skill '{skill.name}' deleted.", "info")
    return redirect(url_for("admin.panel"))


# ─── User management ──────────────────────────────────────────────────────────
@admin_bp.route("/users")
@admin_required
def users():
    """List all registered users."""
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/admin_panel.html", users=all_users, view="users")


@admin_bp.route("/users/toggle-admin/<int:user_id>", methods=["POST"])
@admin_required
def toggle_admin(user_id: int):
    """Promote or demote a user's admin status."""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot change your own admin status.", "danger")
    else:
        user.is_admin = not user.is_admin
        db.session.commit()
        status = "promoted to admin" if user.is_admin else "demoted to regular user"
        flash(f"{user.name} has been {status}.", "success")
    return redirect(url_for("admin.users"))
