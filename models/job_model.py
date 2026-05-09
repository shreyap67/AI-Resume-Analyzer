# models/job_model.py
from datetime import datetime
from .extensions import db


# Association table linking JobRole ↔ Skill (many-to-many)
job_skills = db.Table(
    "job_skills",
    db.Column("job_role_id", db.Integer, db.ForeignKey("job_roles.id"), primary_key=True),
    db.Column("skill_id",    db.Integer, db.ForeignKey("skills.id"),    primary_key=True),
)


class Skill(db.Model):
    """
    Master list of skills. Shared across all job roles.
    e.g. "python", "react", "docker"
    """

    __tablename__ = "skills"

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100), unique=True, nullable=False, index=True)
    category   = db.Column(db.String(80), default="general")  # backend / frontend / data / cloud
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Skill {self.name}>"


class JobRole(db.Model):
    """
    Represents a target job role (e.g. 'Full Stack Developer').
    Each role has a set of required skills used to compute ATS score.
    """

    __tablename__ = "job_roles"

    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(150), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    experience_level = db.Column(db.String(30), default="mid")  # junior / mid / senior
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Many-to-many: a role requires many skills; a skill belongs to many roles
    required_skills = db.relationship(
        "Skill", secondary=job_skills, backref=db.backref("job_roles", lazy="dynamic")
    )

    def skill_names(self) -> list[str]:
        """Return list of skill name strings for this role."""
        return [s.name.lower() for s in self.required_skills]

    def __repr__(self):
        return f"<JobRole {self.title}>"
