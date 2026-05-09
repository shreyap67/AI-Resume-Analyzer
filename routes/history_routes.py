# routes/history_routes.py
"""
Analysis history blueprint.
Handles: /history/, /history/delete/<id>
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db, AnalysisResult

history_bp = Blueprint("history", __name__, url_prefix="/history")


@history_bp.route("/")
@login_required
def index():
    """
    Display paginated analysis history for the current user.
    Supports optional filtering by job role.
    """
    page     = request.args.get("page", 1, type=int)
    per_page = 10
    role_filter = request.args.get("role", "").strip()

    query = (
        AnalysisResult.query
        .filter_by(user_id=current_user.id)
        .order_by(AnalysisResult.created_at.desc())
    )

    # Optional filter by job role title (case-insensitive contains)
    if role_filter:
        query = query.filter(
            AnalysisResult.job_role_title.ilike(f"%{role_filter}%")
        )

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    analyses   = pagination.items

    # Build unique job role list for the filter dropdown
    all_roles = (
        db.session.query(AnalysisResult.job_role_title)
        .filter_by(user_id=current_user.id)
        .distinct()
        .all()
    )
    role_options = [r[0] for r in all_roles]

    return render_template(
        "dashboard/history.html",
        analyses=analyses,
        pagination=pagination,
        role_filter=role_filter,
        role_options=role_options,
    )


@history_bp.route("/delete/<int:result_id>", methods=["POST"])
@login_required
def delete(result_id: int):
    """Delete a single analysis result. Supports both form POST and AJAX."""
    result = AnalysisResult.query.filter_by(
        id=result_id, user_id=current_user.id
    ).first_or_404()

    db.session.delete(result)
    db.session.commit()

    # Return JSON for AJAX delete (table row removal without page reload)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True, "deleted_id": result_id})

    flash("Analysis record deleted.", "info")
    return redirect(url_for("history.index"))
