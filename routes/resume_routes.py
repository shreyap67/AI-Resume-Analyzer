# routes/resume_routes.py
"""
Resume upload and saved resumes blueprint.
Handles: /resume/upload, /resume/saved, /resume/delete/<id>
"""

import os
import uuid
import logging
from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, current_app, jsonify
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, Resume
from services.pdf_parser import extract_text_from_pdf

logger = logging.getLogger(__name__)

resume_bp = Blueprint("resume", __name__, url_prefix="/resume")


def _allowed_file(filename: str) -> bool:
    """Check that the file has an allowed extension."""
    allowed = current_app.config.get("ALLOWED_EXTENSIONS", {"pdf"})
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


@resume_bp.route("/upload", methods=["POST"])
@login_required
def upload():
    """
    Handle resume PDF upload.
    Saves the file to disk, extracts text, stores metadata in DB.
    Returns JSON so the frontend can update the UI without a full reload.
    """
    if "resume_file" not in request.files:
        return jsonify({"success": False, "error": "No file part in request"}), 400

    file = request.files["resume_file"]

    if file.filename == "":
        return jsonify({"success": False, "error": "No file selected"}), 400

    if not _allowed_file(file.filename):
        return jsonify({"success": False, "error": "Only PDF files are allowed"}), 400

    original_name = secure_filename(file.filename)

    # Prefix with a UUID to avoid filename collisions
    unique_filename = f"{uuid.uuid4().hex}_{original_name}"

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    filepath = os.path.join(upload_folder, unique_filename)

    file.save(filepath)
    file_size = os.path.getsize(filepath)

    # Extract text immediately after upload
    extracted_text = extract_text_from_pdf(filepath)

    # Persist resume record
    resume = Resume(
        user_id=current_user.id,
        filename=unique_filename,
        original_name=original_name,
        file_size=file_size,
        extracted_text=extracted_text,
        is_saved=False,
    )
    db.session.add(resume)
    db.session.commit()

    logger.info("Resume uploaded: %s (user=%d)", unique_filename, current_user.id)

    return jsonify({
        "success": True,
        "resume_id": resume.id,
        "filename": original_name,
        "file_size": resume.file_size_kb(),
        "text_length": len(extracted_text),
    })


@resume_bp.route("/saved")
@login_required
def saved():
    """Display the user's saved resumes."""
    saved_resumes = (
        Resume.query
        .filter_by(user_id=current_user.id, is_saved=True)
        .order_by(Resume.created_at.desc())
        .all()
    )
    # Also show all uploaded resumes (regardless of saved flag)
    all_resumes = (
        Resume.query
        .filter_by(user_id=current_user.id)
        .order_by(Resume.created_at.desc())
        .all()
    )
    return render_template("dashboard/saved_resumes.html", resumes=all_resumes)


@resume_bp.route("/save/<int:resume_id>", methods=["POST"])
@login_required
def save_resume(resume_id: int):
    """Toggle the is_saved flag for a resume."""
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first_or_404()
    resume.is_saved = not resume.is_saved
    db.session.commit()
    status = "saved" if resume.is_saved else "unsaved"
    return jsonify({"success": True, "status": status, "is_saved": resume.is_saved})


@resume_bp.route("/delete/<int:resume_id>", methods=["POST"])
@login_required
def delete_resume(resume_id: int):
    """Delete a resume and its file from disk."""
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first_or_404()

    # Remove the file from disk
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], resume.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        logger.info("Deleted file: %s", filepath)

    db.session.delete(resume)
    db.session.commit()

    flash("Resume deleted.", "info")
    return redirect(url_for("resume.saved"))
