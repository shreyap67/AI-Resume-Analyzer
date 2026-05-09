# init_db.py
"""
Database initialisation script.
Run once with:  python init_db.py

Creates all tables and seeds:
  - Default skill dictionary (50+ skills)
  - 8 job roles with realistic required skills
  - One demo admin user  (admin@resumeai.com / admin123)
  - One demo regular user (demo@resumeai.com / demo123)
"""

import os
import sys

# Make sure project root is on the path when running directly
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from models import db, User, JobRole, Skill

# ─── Skill seed data ─────────────────────────────────────────────────────────
SEED_SKILLS = [
    # Backend / Languages
    ("python",        "backend"),
    ("java",          "backend"),
    ("c++",           "backend"),
    ("c#",            "backend"),
    ("golang",        "backend"),
    ("rust",          "backend"),
    ("kotlin",        "backend"),
    ("php",           "backend"),
    ("ruby",          "backend"),
    ("scala",         "backend"),
    ("node.js",       "backend"),
    ("express",       "backend"),
    ("flask",         "backend"),
    ("django",        "backend"),
    ("fastapi",       "backend"),
    ("spring",        "backend"),
    ("rest api",      "backend"),
    ("microservices", "backend"),
    ("sql",           "backend"),
    ("mysql",         "backend"),
    ("postgresql",    "backend"),
    ("mongodb",       "backend"),
    ("redis",         "backend"),
    ("elasticsearch", "backend"),
    ("sqlite",        "backend"),
    # Frontend
    ("javascript",    "frontend"),
    ("typescript",    "frontend"),
    ("html",          "frontend"),
    ("css",           "frontend"),
    ("react",         "frontend"),
    ("vue",           "frontend"),
    ("angular",       "frontend"),
    ("next.js",       "frontend"),
    ("svelte",        "frontend"),
    ("redux",         "frontend"),
    ("graphql",       "frontend"),
    ("tailwind",      "frontend"),
    ("bootstrap",     "frontend"),
    # Data / ML
    ("machine learning", "data"),
    ("deep learning",    "data"),
    ("data analysis",    "data"),
    ("pandas",           "data"),
    ("numpy",            "data"),
    ("scikit-learn",     "data"),
    ("tensorflow",       "data"),
    ("pytorch",          "data"),
    ("keras",            "data"),
    ("matplotlib",       "data"),
    ("tableau",          "data"),
    ("power bi",         "data"),
    ("nlp",              "data"),
    ("statistics",       "data"),
    # Cloud / DevOps
    ("aws",              "cloud"),
    ("azure",            "cloud"),
    ("gcp",              "cloud"),
    ("docker",           "cloud"),
    ("kubernetes",       "cloud"),
    ("jenkins",          "cloud"),
    ("terraform",        "cloud"),
    ("ansible",          "cloud"),
    ("ci/cd",            "cloud"),
    ("github actions",   "cloud"),
    ("linux",            "cloud"),
    # Tools
    ("git",              "tools"),
    ("github",           "tools"),
    ("jira",             "tools"),
    ("agile",            "tools"),
    ("scrum",            "tools"),
    ("excel",            "tools"),
    ("figma",            "tools"),
    ("postman",          "tools"),
]

# ─── Job role seed data ──────────────────────────────────────────────────────
# Each entry: (title, experience_level, description, [required_skill_names])
SEED_ROLES = [
    (
        "Full Stack Developer", "mid",
        "Build end-to-end web applications across frontend and backend stacks.",
        ["javascript", "typescript", "react", "node.js", "python", "sql",
         "postgresql", "rest api", "git", "docker", "html", "css", "redux",
         "graphql", "mongodb", "agile"],
    ),
    (
        "Backend Engineer", "mid",
        "Design and maintain server-side logic, APIs, and databases.",
        ["python", "java", "flask", "django", "fastapi", "rest api",
         "sql", "postgresql", "redis", "docker", "git", "microservices", "linux"],
    ),
    (
        "Frontend Developer", "mid",
        "Create responsive, performant user interfaces.",
        ["javascript", "typescript", "react", "vue", "html", "css",
         "redux", "graphql", "next.js", "tailwind", "git", "figma", "agile"],
    ),
    (
        "Data Scientist", "mid",
        "Extract insights from data using ML and statistical analysis.",
        ["python", "machine learning", "deep learning", "pandas", "numpy",
         "scikit-learn", "tensorflow", "sql", "statistics", "matplotlib",
         "tableau", "git", "nlp"],
    ),
    (
        "DevOps Engineer", "mid",
        "Automate, build, and maintain CI/CD pipelines and cloud infrastructure.",
        ["docker", "kubernetes", "jenkins", "terraform", "ansible",
         "aws", "linux", "python", "git", "ci/cd", "github actions",
         "bash", "monitoring"],
    ),
    (
        "Cloud Architect", "senior",
        "Design scalable, secure cloud infrastructure for enterprise systems.",
        ["aws", "azure", "gcp", "docker", "kubernetes", "terraform",
         "microservices", "linux", "python", "ci/cd", "postgresql",
         "elasticsearch", "redis", "agile"],
    ),
    (
        "ML Engineer", "mid",
        "Deploy and optimise machine learning models in production.",
        ["python", "machine learning", "deep learning", "tensorflow", "pytorch",
         "docker", "kubernetes", "aws", "sql", "pandas", "numpy",
         "git", "ci/cd", "fastapi"],
    ),
    (
        "Mobile Developer", "mid",
        "Build native and cross-platform mobile applications.",
        ["kotlin", "swift", "react", "javascript", "typescript",
         "rest api", "sql", "git", "agile", "figma"],
    ),
]


def seed_skills(session) -> dict[str, Skill]:
    """Insert skills and return a name→Skill mapping."""
    skill_map: dict[str, Skill] = {}
    for name, category in SEED_SKILLS:
        existing = Skill.query.filter_by(name=name).first()
        if existing:
            skill_map[name] = existing
        else:
            skill = Skill(name=name, category=category)
            session.add(skill)
            skill_map[name] = skill
    session.flush()  # assign IDs without committing
    return skill_map


def seed_roles(session, skill_map: dict[str, Skill]):
    """Insert job roles and link required skills."""
    for title, exp_level, description, skill_names in SEED_ROLES:
        if JobRole.query.filter_by(title=title).first():
            print(f"  Role already exists: {title}")
            continue
        role = JobRole(title=title, experience_level=exp_level, description=description)
        for skill_name in skill_names:
            skill = skill_map.get(skill_name)
            if skill:
                role.required_skills.append(skill)
            else:
                # Create skill if missing from seed list
                new_skill = Skill(name=skill_name, category="other")
                session.add(new_skill)
                role.required_skills.append(new_skill)
        session.add(role)
        print(f"  Added role: {title} ({len(skill_names)} skills)")


def seed_users(session):
    """Create demo admin and regular user if they don't exist."""
    if not User.query.filter_by(email="admin@resumeai.com").first():
        admin = User(name="Admin User", email="admin@resumeai.com", is_admin=True)
        admin.set_password("admin123")
        session.add(admin)
        print("  Created admin: admin@resumeai.com / admin123")

    if not User.query.filter_by(email="demo@resumeai.com").first():
        demo = User(name="Demo User", email="demo@resumeai.com", is_admin=False)
        demo.set_password("demo123")
        session.add(demo)
        print("  Created demo user: demo@resumeai.com / demo123")


def init_database():
    """Main entry point: create tables and seed data."""
    app = create_app()
    with app.app_context():
        # Ensure the instance directory exists
        os.makedirs(os.path.join(os.path.dirname(__file__), "instance"), exist_ok=True)

        print("Creating database tables...")
        db.create_all()
        print("Tables created.")

        print("\nSeeding skills...")
        skill_map = seed_skills(db.session)
        print(f"  {len(skill_map)} skills ready.")

        print("\nSeeding job roles...")
        seed_roles(db.session, skill_map)

        print("\nSeeding demo users...")
        seed_users(db.session)

        db.session.commit()
        print("\n✅ Database initialised successfully!")
        print("\nDemo credentials:")
        print("  Admin : admin@resumeai.com / admin123")
        print("  User  : demo@resumeai.com  / demo123")


if __name__ == "__main__":
    init_database()
