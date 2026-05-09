# models/__init__.py
# Expose db instance and all models from a single import point
from .extensions import db
from .user_model import User
from .resume_model import Resume
from .job_model import JobRole, Skill
from .analysis_model import AnalysisResult

__all__ = ["db", "User", "Resume", "JobRole", "Skill", "AnalysisResult"]
