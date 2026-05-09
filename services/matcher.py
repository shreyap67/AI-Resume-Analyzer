# services/matcher.py
"""
ATS Score calculation using TF-IDF vectorisation + cosine similarity.

Pipeline:
1. Build a "resume skill document" from extracted skills.
2. Build a "job requirement document" from the role's required skills.
3. Vectorise both with TfidfVectorizer.
4. Compute cosine similarity → raw 0-1 score.
5. Also compute exact match percentage for display.
6. Generate contextual suggestions based on missing skills.
"""

import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# ─── Suggestion templates ─────────────────────────────────────────────────────
# Keyed by skill category; used to generate personalised suggestions.
SUGGESTION_TEMPLATES = {
    "projects": "Add 1–2 portfolio projects demonstrating {skills} — employers look for applied experience.",
    "certification": "Consider getting certified in {skills} to validate your knowledge (e.g. AWS, Google Cloud, or Coursera specialisations).",
    "achievements": "Quantify your achievements: 'Reduced load time by 40% using {skills}' stands out over generic descriptions.",
    "keywords": "Add these ATS keywords to your resume: {skills}. Many ATS systems reject resumes that lack them.",
    "learning": "Upskill in {skills} via online platforms (Udemy, Pluralsight, freeCodeCamp) to close critical gaps.",
}


def calculate_ats_score(
    extracted_skills: list[str],
    required_skills: list[str],
) -> dict:
    """
    Main scoring function.

    Args:
        extracted_skills: Skills found in the candidate's resume.
        required_skills:  Skills required by the target job role.

    Returns:
        dict with keys:
            ats_score        – float 0-100, the final displayed score
            similarity_score – float 0-1, raw cosine similarity
            matched_skills   – list of skills present in both
            missing_skills   – list of required skills absent from resume
            suggestions      – list of actionable suggestion strings
    """

    # ── Guard against empty inputs ──────────────────────────────────────────
    if not required_skills:
        logger.warning("No required skills provided for matching")
        return _empty_result()

    if not extracted_skills:
        logger.info("No skills extracted from resume – score will be 0")
        return {
            "ats_score": 0.0,
            "similarity_score": 0.0,
            "matched_skills": [],
            "missing_skills": required_skills,
            "suggestions": _generate_suggestions(required_skills),
        }

    # ── Exact match calculation ───────────────────────────────────────────────
    # Normalise to lowercase sets for reliable comparison
    extracted_set = {s.lower().strip() for s in extracted_skills}
    required_set  = {s.lower().strip() for s in required_skills}

    matched_skills = sorted(extracted_set & required_set)
    missing_skills = sorted(required_set - extracted_set)

    # Simple match percentage (main ATS score component)
    exact_match_pct = (len(matched_skills) / len(required_set)) * 100

    # ── Cosine similarity (semantic overlap) ─────────────────────────────────
    resume_doc = " ".join(extracted_skills)
    job_doc    = " ".join(required_skills)

    try:
        vectorizer = TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),    # unigrams + bigrams capture "machine learning"
            lowercase=True,
        )
        tfidf_matrix = vectorizer.fit_transform([resume_doc, job_doc])
        similarity = float(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0])
    except Exception as e:
        logger.warning("TF-IDF similarity failed, using exact match only: %s", e)
        similarity = len(matched_skills) / max(len(required_set), 1)

    # ── Blend exact match (70%) + cosine similarity (30%) ─────────────────────
    # Blending prevents high-similarity-but-zero-exact-match edge cases
    ats_score = round(
        (exact_match_pct * 0.70) + (similarity * 100 * 0.30),
        1,
    )
    ats_score = min(ats_score, 100.0)  # cap at 100

    suggestions = _generate_suggestions(missing_skills)

    logger.info(
        "ATS score: %.1f%% | exact: %.1f%% | cosine: %.3f | matched: %d/%d",
        ats_score,
        exact_match_pct,
        similarity,
        len(matched_skills),
        len(required_set),
    )

    return {
        "ats_score": ats_score,
        "similarity_score": round(similarity, 4),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "suggestions": suggestions,
    }


def calculate_all_job_matches(
    extracted_skills: list[str],
    all_job_roles,           # list of JobRole ORM objects
) -> list[dict]:
    """
    Score the resume against ALL available job roles.
    Returns a list sorted by ats_score descending, used for the Job Matcher page.
    """
    results = []
    for role in all_job_roles:
        required = role.skill_names()
        score_data = calculate_ats_score(extracted_skills, required)
        results.append(
            {
                "job_role_id":    role.id,
                "job_role_title": role.title,
                "ats_score":      score_data["ats_score"],
                "matched":        len(score_data["matched_skills"]),
                "required":       len(required),
            }
        )
    results.sort(key=lambda x: x["ats_score"], reverse=True)
    return results


# ─── Private helpers ──────────────────────────────────────────────────────────

def _generate_suggestions(missing_skills: list[str]) -> list[str]:
    """
    Produce up to 5 actionable suggestions from the missing skills list.
    """
    if not missing_skills:
        return [
            "Great match! Your resume covers all required skills for this role.",
            "Highlight your strongest matching skills prominently at the top.",
            "Add measurable impact metrics (e.g. 'improved performance by 35%').",
        ]

    suggestions = []

    # Split missing skills into batches for different suggestion types
    chunk = missing_skills[:3]
    chunk_str = ", ".join(chunk)

    suggestions.append(SUGGESTION_TEMPLATES["projects"].format(skills=chunk_str))

    if len(missing_skills) > 3:
        cert_skills = ", ".join(missing_skills[3:5])
        suggestions.append(SUGGESTION_TEMPLATES["certification"].format(skills=cert_skills))

    suggestions.append(SUGGESTION_TEMPLATES["achievements"].format(skills=chunk_str))

    if missing_skills:
        suggestions.append(SUGGESTION_TEMPLATES["keywords"].format(skills=", ".join(missing_skills)))

    if len(missing_skills) > 5:
        learn_skills = ", ".join(missing_skills[5:8])
        suggestions.append(SUGGESTION_TEMPLATES["learning"].format(skills=learn_skills))

    return suggestions[:5]  # cap at 5 suggestions


def _empty_result() -> dict:
    return {
        "ats_score": 0.0,
        "similarity_score": 0.0,
        "matched_skills": [],
        "missing_skills": [],
        "suggestions": ["No job role data available. Contact an admin to add job roles."],
    }
