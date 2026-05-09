# routes/analysis_routes.py
"""
Analysis blueprint.
Handles: /analyze (run ATS), /analyze/result/<id>,
         /analyze/report/<id> (PDF download), /analyze/job-matcher
"""

import logging
import os
import requests as http_requests
from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, jsonify, send_file, current_app
)
from flask_login import login_required, current_user
from io import BytesIO
from models import db, Resume, JobRole, AnalysisResult
from services.skill_extractor import extract_skills_with_spacy, analyze_resume_with_ai
from services.matcher import calculate_ats_score, calculate_all_job_matches
from services.report_generator import generate_analysis_report

# ── OpenRouter AI helper ──────────────────────────────────────────────────────
os.environ.setdefault("OPENROUTER_API_KEY", "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")

def generate_skills_from_ai(role):
    """Use OpenRouter API to generate required skills for a custom job role."""
    try:
        response = http_requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {
                        "role": "user",
                        "content": f"List 10-15 technical skills required for the job role: {role}. Return only comma-separated skills."
                    }
                ],
                "temperature": 0.3
            },
            timeout=10
        )
        data = response.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        skills = [s.strip().lower() for s in text.split(",") if s.strip()]
        return skills
    except Exception as e:
        logger.error("OpenRouter error: %s", e)
        return []
# ─────────────────────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)

analysis_bp = Blueprint("analysis", __name__, url_prefix="/analyze")


def _is_json_request():
    """Return True if the caller expects a JSON response."""
    return (
        request.headers.get("Accept") == "application/json"
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.content_type == "application/json"
    )


@analysis_bp.route("/", methods=["POST"])
@login_required
def run_analysis():
    """
    Core analysis endpoint — always returns JSON.
    Receives resume_id + job_role_id via form data, runs the full pipeline,
    saves the result, and returns a JSON payload the frontend can use.
    """
    try:
        resume_id   = request.form.get("resume_id",   type=int)
        job_role_id = request.form.get("job_role_id", type=int)
        custom_role = request.form.get("custom_role", "").strip()

        if not resume_id:
            return jsonify({
                "success": False,
                "error": "Please select a resume."
            }), 400

        if not job_role_id and not custom_role:
            return jsonify({
                "success": False,
                "error": "Please select a stream and job role, or enter a custom role."
            }), 400

        # Fetch resume
        resume = Resume.query.filter_by(
            id=resume_id, user_id=current_user.id
        ).first()
        if not resume:
            return jsonify({
                "success": False,
                "error": "Resume not found. Please upload again."
            }), 404

        # Resolve job role — prefer DB id, fall back to custom_role string match
        job_role_title_override = None
        if job_role_id:
            job_role = JobRole.query.get(job_role_id)
            if not job_role:
                return jsonify({
                    "success": False,
                    "error": "Job role not found. Please refresh and try again."
                }), 404
        else:
            # Try to find a matching DB job role by title (case-insensitive)
            job_role = JobRole.query.filter(
                JobRole.title.ilike(f"%{custom_role}%")
            ).first()
            if not job_role:
                # Fall back to the first available job role for skill extraction
                job_role = JobRole.query.order_by(JobRole.id).first()
            job_role_title_override = custom_role  # Always use what the user typed as display title

        if not job_role:
            return jsonify({
                "success": False,
                "error": "No job roles configured. Please ask an admin to add job roles."
            }), 404

        # ── AI-powered analysis pipeline (run_analysis) ─────────────────────────────────────
        role_label = job_role_title_override or job_role.title
        ai_data = analyze_resume_with_ai(
            resume_text=resume.extracted_text or "",
            job_role=role_label,
            experience_level="mid",
        )

        extracted_skills = ai_data["extracted_skills"]
        required_skills  = ai_data["industry_required_skills"]

        # Derive numeric ats_score from ai_data percentage string (e.g. "72%")
        try:
            ats_score = float(ai_data["skill_match_percentage"].replace("%", "").strip())
        except (ValueError, AttributeError):
            ats_score = 0.0

        # Persist result
        result = AnalysisResult(
            user_id=current_user.id,
            resume_id=resume.id,
            job_role_id=job_role.id,
            job_role_title=role_label,
            ats_score=ats_score,
            similarity_score=round(ats_score / 100, 4),
        )
        result.matched_skills   = sorted(set(extracted_skills) & set(required_skills))
        result.missing_skills   = ai_data["missing_skills"]
        result.extracted_skills = extracted_skills
        result.suggestions      = ai_data["recommendations"]

        db.session.add(result)
        db.session.commit()

        logger.info(
            "Analysis complete: user=%d resume=%d role=%s score=%.1f",
            current_user.id, resume.id, job_role.title, result.ats_score,
        )

        return jsonify({
            "success":        True,
            "result_id":      result.id,
            "ats_score":      result.ats_score,
            "matched_skills": result.matched_skills,
            "missing_skills": result.missing_skills,
            "suggestions":    result.suggestions,
            "redirect":       url_for("analysis.result", result_id=result.id),
        })

    except Exception as e:
        logger.error("Analysis error: %s", e, exc_info=True)
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({"success": False, "error": str(e)}), 500


@analysis_bp.route("/result/<int:result_id>")
@login_required
def result(result_id: int):
    """Display the analysis result page for a given result ID."""
    analysis = AnalysisResult.query.filter_by(
        id=result_id, user_id=current_user.id
    ).first_or_404()

    return render_template("dashboard/results.html", analysis=analysis)


@analysis_bp.route("/report/<int:result_id>")
@login_required
def download_report(result_id: int):
    """Generate and stream a PDF analysis report to the browser."""
    analysis = AnalysisResult.query.filter_by(
        id=result_id, user_id=current_user.id
    ).first_or_404()

    try:
        pdf_bytes = generate_analysis_report(analysis, current_user)
    except Exception as e:
        logger.error("Report generation failed: %s", e)
        flash("Failed to generate report. Please try again.", "danger")
        return redirect(url_for("analysis.result", result_id=result_id))

    filename = (
        f"ats_report_{analysis.job_role_title.replace(' ', '_')}_{result_id}.pdf"
    )

    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


@analysis_bp.route("/analyzer")
@login_required
def analyzer_page():
    """
    Render the Resume Analyzer page.
    Passes available job roles and the user's uploaded resumes.
    """
    job_roles = JobRole.query.order_by(JobRole.title).all()
    resumes   = (
        Resume.query
        .filter_by(user_id=current_user.id)
        .order_by(Resume.created_at.desc())
        .all()
    )
    return render_template(
        "dashboard/resume_analyzer.html",
        job_roles=job_roles,
        resumes=resumes,
    )


@analysis_bp.route("/job-matcher")
@login_required
def job_matcher():
    """
    Job Matcher page.
    Uses the most recent resume to score against all job roles.
    """
    latest_resume = (
        Resume.query
        .filter_by(user_id=current_user.id)
        .order_by(Resume.created_at.desc())
        .first()
    )

    job_matches = []
    best_match  = None

    if latest_resume and latest_resume.extracted_text:
        extracted_skills = extract_skills_with_spacy(latest_resume.extracted_text)
        all_roles        = JobRole.query.all()
        job_matches      = calculate_all_job_matches(extracted_skills, all_roles)
        if job_matches:
            best_match = job_matches[0]

    job_roles = JobRole.query.order_by(JobRole.title).all()
    return render_template(
        "dashboard/job_matcher.html",
        job_matches=job_matches,
        best_match=best_match,
        latest_resume=latest_resume,
        job_roles=job_roles,
    )


@analysis_bp.route("/custom-match", methods=["POST"])
@login_required
def run_custom_match():
    """
    Handles the 'Analyse for Specific Role' form on the Job Matcher page.
    Supports both dropdown selection and free-text custom role entry.
    Always returns a redirect to the result page (not an AJAX/JSON route).
    """
    try:
        resume_id       = request.form.get("resume_id", type=int)
        selected_role_id = request.form.get("job_role", "").strip()
        custom_role_raw  = request.form.get("custom_role", "").strip()

        # ── Validation ────────────────────────────────────────────────────────
        if not resume_id:
            flash("Resume not found. Please try again.", "danger")
            return redirect(url_for("analysis.job_matcher"))

        resume = Resume.query.filter_by(
            id=resume_id, user_id=current_user.id
        ).first()
        if not resume:
            flash("Resume not found.", "danger")
            return redirect(url_for("analysis.job_matcher"))

        if not custom_role_raw and not selected_role_id:
            flash("Please select a job role or type a custom role.", "warning")
            return redirect(url_for("analysis.job_matcher"))

        # ── Resolve role title and required skills ────────────────────────────
        if custom_role_raw:
            # Custom free-text role — generate required skills via OpenRouter AI
            job_role_title = custom_role_raw
            job_role_id_val = None

            required_skills = generate_skills_from_ai(custom_role_raw)
            if not required_skills:
                # Failsafe: fall back to skills extracted from the resume itself
                from services.skill_extractor import extract_skills_with_spacy as _ex
                required_skills = _ex(resume.extracted_text or "")

        else:
            # Standard dropdown selection.
            # The frontend sends the role TITLE (e.g. "Python Developer") as the
            # value, not a DB integer ID. Try integer lookup first for backwards
            # compatibility, then fall back to a case-insensitive title match.
            job_role = None
            try:
                role_id_int = int(selected_role_id)
                job_role = JobRole.query.get(role_id_int)
            except (ValueError, TypeError):
                pass

            if not job_role:
                # Exact title match (case-insensitive)
                job_role = JobRole.query.filter(
                    JobRole.title.ilike(selected_role_id)
                ).first()

            if not job_role:
                # Partial title match fallback
                job_role = JobRole.query.filter(
                    JobRole.title.ilike(f"%{selected_role_id}%")
                ).first()

            if not job_role:
                # Role title from stream dropdown doesn't exist in DB —
                # generate skills via OpenRouter AI
                job_role_title  = selected_role_id
                job_role_id_val = None
                required_skills = generate_skills_from_ai(selected_role_id)
                if not required_skills:
                    # Failsafe: fall back to skills extracted from the resume itself
                    from services.skill_extractor import extract_skills_with_spacy as _ex
                    required_skills = _ex(resume.extracted_text or "")
            else:
                job_role_title  = job_role.title
                job_role_id_val = job_role.id
                required_skills = job_role.skill_names()

        # ── AI-powered analysis pipeline (run_custom_match) ─────────────────────
        ai_data = analyze_resume_with_ai(
            resume_text=resume.extracted_text or "",
            job_role=job_role_title,
            experience_level="mid",
        )

        extracted_skills = ai_data["extracted_skills"]

        # Derive numeric ats_score from percentage string (e.g. "72%")
        try:
            ats_score = float(ai_data["skill_match_percentage"].replace("%", "").strip())
        except (ValueError, AttributeError):
            ats_score = 0.0

        # ── Persist result ────────────────────────────────────────────────────
        result = AnalysisResult(
            user_id=current_user.id,
            resume_id=resume.id,
            job_role_id=job_role_id_val,
            job_role_title=job_role_title,
            ats_score=ats_score,
            similarity_score=round(ats_score / 100, 4),
        )
        result.matched_skills   = sorted(set(extracted_skills) & set(ai_data["industry_required_skills"]))
        result.missing_skills   = ai_data["missing_skills"]
        result.extracted_skills = extracted_skills
        result.suggestions      = ai_data["recommendations"]

        db.session.add(result)
        db.session.commit()

        logger.info(
            "Custom match analysis: user=%d role='%s' score=%.1f",
            current_user.id, job_role_title, result.ats_score,
        )

        flash(
            f"Analysis complete for '{job_role_title}' — score: {result.ats_score:.1f}%",
            "success",
        )
        return redirect(url_for("analysis.result", result_id=result.id))

    except Exception as e:
        logger.error("Custom match error: %s", e, exc_info=True)
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f"Analysis failed: {e}", "danger")
        return redirect(url_for("analysis.job_matcher"))
