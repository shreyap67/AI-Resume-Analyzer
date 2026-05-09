# models/user_model.py
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db


class User(UserMixin, db.Model):
    """
    Represents a registered user of the platform.
    UserMixin provides Flask-Login helpers: is_authenticated, is_active, etc.
    """

    __tablename__ = "users"

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(120), nullable=False)
    email      = db.Column(db.String(200), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin   = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships – lazy="dynamic" keeps queries efficient for large sets
    resumes  = db.relationship("Resume",         backref="owner",  lazy="dynamic", cascade="all, delete-orphan")
    analyses = db.relationship("AnalysisResult", backref="author", lazy="dynamic", cascade="all, delete-orphan")

    # ─── Password helpers ──────────────────────────────────────────────────────
    def set_password(self, raw_password: str) -> None:
        """Hash and store the password. Never store plaintext."""
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        """Return True if raw_password matches the stored hash."""
        return check_password_hash(self.password_hash, raw_password)

    # ─── Stats helpers ─────────────────────────────────────────────────────────
    def total_analyses(self) -> int:
        return self.analyses.count()

    def average_score(self) -> float:
        results = [a.ats_score for a in self.analyses.all() if a.ats_score is not None]
        return round(sum(results) / len(results), 1) if results else 0.0

    def highest_score(self) -> float:
        results = [a.ats_score for a in self.analyses.all() if a.ats_score is not None]
        return max(results) if results else 0.0

    def last_analysis_date(self):
        latest = self.analyses.order_by(AnalysisResult.created_at.desc()).first()
        return latest.created_at if latest else None

    def __repr__(self):
        return f"<User {self.email}>"


# Late import to avoid circular dependency inside the helper methods
from .analysis_model import AnalysisResult  # noqa: E402
