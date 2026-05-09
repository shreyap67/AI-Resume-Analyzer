# models/analysis_model.py
import json
from datetime import datetime
from .extensions import db


class AnalysisResult(db.Model):
    """
    Stores one ATS analysis result for a specific (resume, job_role) pair.
    Skills lists and suggestions are serialised as JSON strings.
    """

    __tablename__ = "analysis_results"

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"),    nullable=False, index=True)
    resume_id    = db.Column(db.Integer, db.ForeignKey("resumes.id"),  nullable=False, index=True)
    job_role_id  = db.Column(db.Integer, db.ForeignKey("job_roles.id"), nullable=True)
    job_role_title = db.Column(db.String(150), nullable=False)          # Cached title for quick display

    # ─── Core scores ───────────────────────────────────────────────────────────
    ats_score       = db.Column(db.Float, default=0.0)   # 0–100 match percentage
    similarity_score = db.Column(db.Float, default=0.0)  # raw cosine similarity

    # ─── JSON-serialised lists ─────────────────────────────────────────────────
    # These are stored as JSON strings and decoded on access via properties
    _matched_skills  = db.Column("matched_skills",  db.Text, default="[]")
    _missing_skills  = db.Column("missing_skills",  db.Text, default="[]")
    _extracted_skills = db.Column("extracted_skills", db.Text, default="[]")
    _suggestions     = db.Column("suggestions",     db.Text, default="[]")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ─── JSON property helpers ─────────────────────────────────────────────────
    @property
    def matched_skills(self) -> list:
        return json.loads(self._matched_skills or "[]")

    @matched_skills.setter
    def matched_skills(self, value: list):
        self._matched_skills = json.dumps(value)

    @property
    def missing_skills(self) -> list:
        return json.loads(self._missing_skills or "[]")

    @missing_skills.setter
    def missing_skills(self, value: list):
        self._missing_skills = json.dumps(value)

    @property
    def extracted_skills(self) -> list:
        return json.loads(self._extracted_skills or "[]")

    @extracted_skills.setter
    def extracted_skills(self, value: list):
        self._extracted_skills = json.dumps(value)

    @property
    def suggestions(self) -> list:
        return json.loads(self._suggestions or "[]")

    @suggestions.setter
    def suggestions(self, value: list):
        self._suggestions = json.dumps(value)

    # ─── Display helpers ───────────────────────────────────────────────────────
    def score_label(self) -> str:
        """Return a human-readable label based on ATS score band."""
        s = self.ats_score
        if s >= 90:
            return "Excellent"
        elif s >= 75:
            return "Good"
        elif s >= 60:
            return "Average"
        else:
            return "Needs Work"

    def score_color(self) -> str:
        """Return a CSS colour class based on score band."""
        s = self.ats_score
        if s >= 90:
            return "success"
        elif s >= 75:
            return "info"
        elif s >= 60:
            return "warning"
        else:
            return "danger"

    def __repr__(self):
        return f"<AnalysisResult user={self.user_id} score={self.ats_score}>"
