# models/resume_model.py
from datetime import datetime
from .extensions import db


class Resume(db.Model):
    """
    Stores metadata about an uploaded resume PDF.
    The actual file lives on disk at static/uploads/<filename>.
    """

    __tablename__ = "resumes"

    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    filename      = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    file_size     = db.Column(db.Integer, default=0)
    extracted_text = db.Column(db.Text, nullable=True)
    is_saved      = db.Column(db.Boolean, default=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    # lazy="dynamic" returns a Query object so .first(), .all(), .count() work.
    # order_by string expression orders newest analysis first.
    analyses = db.relationship(
        "AnalysisResult",
        backref="resume",
        lazy="dynamic",
        order_by="AnalysisResult.created_at.desc()",
        cascade="all, delete-orphan",
    )

    def file_size_kb(self) -> str:
        """Return human-readable file size."""
        return f"{self.file_size // 1024} KB" if self.file_size else "Unknown"

    def __repr__(self):
        return f"<Resume {self.original_name} (user={self.user_id})>"
