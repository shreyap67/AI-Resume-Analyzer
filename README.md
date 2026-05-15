# ResumeAI – AI Resume Analyzer & Job Match SaaS

> **AI-powered resume analysis and job matching platform that helps you improve your resume and increase your chances of getting hired.**

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-black?logo=flask)](https://flask.palletsprojects.com)
[![SQLite](https://img.shields.io/badge/Database-SQLite-lightblue?logo=sqlite)](https://sqlite.org)
[![spaCy](https://img.shields.io/badge/NLP-spaCy-09A3D5?logo=spacy)](https://spacy.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Screenshots](#screenshots)
4. [Tech Stack](#tech-stack)
5. [Project Structure](#project-structure)
6. [Installation — Windows](#installation--windows)
7. [Installation — macOS / Linux](#installation--macoslinux)
8. [How the Algorithm Works](#how-the-algorithm-works)
9. [Database Schema](#database-schema)
10. [API & Routes Reference](#api--routes-reference)
11. [Deployment Guide](#deployment-guide)
12. [Demo Credentials](#demo-credentials)
13. [Environment Variables](#environment-variables)
14. [Contributing](#contributing)

---

## Overview

ResumeAI is a full-stack SaaS web application built with **Python Flask** that analyses PDF resumes against real job role requirements and produces an **ATS (Applicant Tracking System) compatibility score**.

Unlike simple keyword checkers, ResumeAI uses **TF-IDF cosine similarity** (scikit-learn) combined with **spaCy NLP** to give a nuanced match score, then generates contextual improvement suggestions tailored to the specific missing skills.

The platform includes a complete **dark SaaS dashboard UI** with Chart.js analytics, drag-and-drop file upload, downloadable PDF reports, paginated history, and a full admin panel.

---

## Features

### 🔐 Authentication
- Secure register / login / logout with session management
- Password hashing via Werkzeug's PBKDF2-SHA256
- "Remember me" persistent sessions
- First registered user auto-promoted to admin
- Protected routes via Flask-Login `@login_required`

### 📄 Resume Management
- Drag-and-drop PDF upload (max 10 MB)
- UUID-prefixed filenames to prevent collisions
- Immediate text extraction on upload (PyPDF2)
- Save / unsave resumes for quick re-analysis
- Delete resumes with cascading file removal

### 🤖 AI Analysis
- **spaCy NLP** noun-chunk pass + 70+ skill dictionary matching
- **TF-IDF cosine similarity** (scikit-learn) for semantic overlap
- Blended ATS score: 70% exact match + 30% cosine similarity
- Matched skills (green tags) and missing skills (red tags)
- 5 contextual AI-generated improvement suggestions
- Full result persisted to SQLite for history tracking

### 💼 Job Matcher
- Score resume against ALL job roles simultaneously
- Ranked results with match percentage and visual bars
- Best match highlighted with career path recommendation
- Instant re-analysis: click any role to deep-dive

### 📊 Dashboard Analytics
- Line chart: ATS score trend over last 6 analyses
- Donut chart: skill distribution by category
- 4 stat cards with animated counters
- Recent activity table

### 📥 PDF Report Generator
- Professional A4 PDF via ReportLab
- Includes: candidate info, ATS score, skill breakdown table, all suggestions
- Downloaded on-demand, never stored server-side

### 🛠 Admin Panel
- Add / edit / delete job roles and required skills
- Manage the master skill dictionary with categories
- View all registered users, toggle admin status
- Platform-wide usage statistics

### 🌓 Dark / Light Mode
- Toggle persisted in localStorage
- CSS variables for full theme switching — no flash on load
- Responsive: works on mobile, tablet, and desktop

---

## Screenshots


| Page | Description |
|------|-------------|
| `screenshots/landing.png`   | Marketing landing page with hero, features, how-it-works |
| `screenshots/login.png`     | Auth page with dark glassmorphism card |
| `screenshots/dashboard.png` | Home dashboard with charts and stat cards |
| `screenshots/analyzer.png`  | Resume upload + job role selector |
| `screenshots/results.png`   | ATS score circle, skill tags, AI suggestions |
| `screenshots/matcher.png`   | Job matcher ranked results |
| `screenshots/history.png`   | Paginated analysis history table |
| `screenshots/admin.png`     | Admin panel with role management |

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend** | Python 3.11+ · Flask 3.0 | Web framework, routing, templating |
| **ORM** | Flask-SQLAlchemy 3.1 · SQLite | Database abstraction |
| **Auth** | Flask-Login 0.6 · Werkzeug | Session management, password hashing |
| **PDF Parsing** | PyPDF2 3.0 | Text extraction from uploaded PDFs |
| **NLP** | spaCy 3.7 (en_core_web_sm) | Noun-chunk skill detection |
| **ML Scoring** | scikit-learn 1.4 · numpy | TF-IDF vectorisation + cosine similarity |
| **Reports** | ReportLab 4.1 | Downloadable PDF report generation |
| **Frontend** | Jinja2 · Chart.js 4.4 | Server-rendered HTML + animated charts |
| **Fonts** | Syne (display) · DM Sans (body) | Google Fonts via CDN |
| **CSS** | Pure custom CSS (4 files, ~1,500 lines) | Dark SaaS UI, animations, responsive |
| **JS** | Vanilla ES6 (5 files) | Upload, charts, dark mode, interactions |

---

## Project Structure

```
AI-Resume-Analyzer/
│
├── app.py                    ← Application factory (blueprints, error handlers)
├── config.py                 ← Dev / Prod configuration classes
├── init_db.py                ← Database initialisation + seed data script
├── requirements.txt          ← Python dependencies
│
├── instance/
│   └── database.db           ← SQLite database (auto-created by init_db.py)
│
├── models/
│   ├── __init__.py           ← Exposes db + all models
│   ├── extensions.py         ← SQLAlchemy instance (avoids circular imports)
│   ├── user_model.py         ← User (Flask-Login UserMixin, password hashing)
│   ├── resume_model.py       ← Resume file metadata + extracted text
│   ├── job_model.py          ← JobRole + Skill (many-to-many relationship)
│   └── analysis_model.py     ← AnalysisResult (JSON-serialised skill lists)
│
├── routes/
│   ├── __init__.py
│   ├── main_routes.py        ← GET /  →  landing page
│   ├── auth_routes.py        ← /auth/register|login|logout
│   ├── dashboard_routes.py   ← /dashboard/ home + profile
│   ├── resume_routes.py      ← /resume/ upload|saved|save|delete
│   ├── analysis_routes.py    ← /analyze/ run|result|report|job-matcher
│   ├── history_routes.py     ← /history/ list (paginated) + delete
│   └── admin_routes.py       ← /admin/ panel|roles|skills|users
│
├── services/                 ← AI / business logic (no Flask imports)
│   ├── __init__.py
│   ├── pdf_parser.py         ← PyPDF2 multi-page text extraction
│   ├── skill_extractor.py    ← Dictionary matching + spaCy NLP pass
│   ├── matcher.py            ← TF-IDF cosine similarity ATS scoring
│   └── report_generator.py   ← ReportLab A4 PDF report builder
│
├── static/
│   ├── css/
│   │   ├── main.css          ← Core dark theme (sidebar, cards, tables…)
│   │   ├── dashboard.css     ← Landing page + light-mode overrides
│   │   ├── auth.css          ← Login / register pages
│   │   └── animations.css    ← Keyframes + micro-interactions
│   │
│   ├── js/
│   │   ├── main.js           ← Sidebar, flash, scroll animations, counters
│   │   ├── darkmode.js       ← Theme toggle with localStorage persistence
│   │   ├── charts.js         ← Chart.js line, pie, bar + score arc helpers
│   │   ├── upload.js         ← Fetch-based upload + live analysis rendering
│   │   └── dashboard.js      ← Score arc, AJAX delete, profile validation
│   │
│   └── uploads/              ← Uploaded PDFs (UUID-prefixed, auto-created)
│
├── templates/
│   ├── layout/
│   │   ├── base.html         ← Master layout (sidebar + topbar shell)
│   │   ├── sidebar.html      ← Responsive sidebar nav with active states
│   │   └── navbar.html       ← Topbar: title, AI badge, theme toggle, avatar
│   │
│   ├── landing/
│   │   └── index.html        ← Public marketing page
│   │
│   ├── auth/
│   │   ├── login.html        ← Login form with remember-me
│   │   └── register.html     ← Registration form with confirm password
│   │
│   ├── dashboard/
│   │   ├── home.html         ← Stats cards + line chart + pie chart
│   │   ├── resume_analyzer.html  ← Upload zone + job config + live results
│   │   ├── results.html      ← Full analysis result page
│   │   ├── job_matcher.html  ← All job matches ranked by score
│   │   ├── history.html      ← Paginated analysis history table
│   │   ├── saved_resumes.html← Resume card grid
│   │   └── profile.html      ← Account info + change password
│   │
│   ├── admin/
│   │   └── admin_panel.html  ← Tabbed admin: roles, skills, users, activity
│   │
│   └── errors/
│       ├── base_error.html   ← Shared dark error page base template
│       ├── 403.html          ← Access Denied (contextual nav buttons)
│       ├── 404.html          ← Page Not Found
│       ├── 413.html          ← File Too Large (10 MB limit exceeded)
│       └── 500.html          ← Internal Server Error (with retry button)
│
└── README.md
```

---

## Installation – Windows

```powershell
# 1. Clone or unzip the project
cd AI-Resume-Analyzer

# 2. Create a virtual environment
python -m venv venv

# 3. Activate it
venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Download the spaCy English model
python -m spacy download en_core_web_sm

# 6. Initialise the database (creates tables + seeds data)
python init_db.py

# 7. Start the development server
python app.py
```

Open **http://localhost:5000** in your browser.

---

## Installation – macOS/Linux

```bash
# 1. Clone or unzip the project
cd AI-Resume-Analyzer

# 2. Create a virtual environment
python3 -m venv venv

# 3. Activate it
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Download the spaCy English model
python -m spacy download en_core_web_sm

# 6. Initialise the database
python init_db.py

# 7. Run the development server
python app.py
```

> **Note:** The spaCy model is optional. The app falls back to pure dictionary
> matching if the model is unavailable, so step 5 can be skipped if you have
> network restrictions.

---

## How the Algorithm Works

### Step 1 – PDF Text Extraction (PyPDF2)

```
resume.pdf  →  PdfReader(filepath)  →  page.extract_text()  →  raw_text (string)
```

Each page is extracted independently and joined. Whitespace is normalised so
downstream NLP produces clean tokens.

### Step 2 – Skill Extraction (Dictionary + spaCy)

```
raw_text
  │
  ├─ Pass 1: Dictionary scan
  │    Iterate 70+ canonical skills (sorted longest→shortest to catch
  │    "machine learning" before "machine"). Word-boundary regex match.
  │    → matched_skills_set (e.g. {"python", "react", "docker"})
  │
  └─ Pass 2: spaCy noun-chunks (optional)
       Load en_core_web_sm, extract noun chunks, cross-reference with
       dictionary for additional coverage.
       → combined deduplicated skill list
```

### Step 3 – ATS Score Calculation (scikit-learn)

```python
# Exact match component (70% weight)
matched     = extracted_skills ∩ required_skills
exact_pct   = (len(matched) / len(required_skills)) * 100

# Cosine similarity component (30% weight)
vectorizer  = TfidfVectorizer(ngram_range=(1, 2))
tfidf       = vectorizer.fit_transform([resume_doc, job_doc])
similarity  = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]

# Blended ATS score
ats_score   = (exact_pct * 0.70) + (similarity * 100 * 0.30)
ats_score   = min(round(ats_score, 1), 100.0)
```

The blending prevents edge cases where high semantic similarity but zero exact
matches (or vice versa) produce misleading scores.

### Step 4 – Suggestion Generation

Missing skills are grouped and mapped to actionable suggestion templates:
- **Projects**: "Add a project demonstrating {missing_skills}"
- **Certifications**: "Get certified in {skills}"
- **Achievements**: "Quantify impact using {skills}"
- **Keywords**: "Add ATS keywords: {missing_skills}"
- **Learning**: "Upskill in {skills} via online platforms"

---

## Database Schema

### `users`
| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `name` | VARCHAR(120) | Full name |
| `email` | VARCHAR(200) | Unique, indexed |
| `password_hash` | VARCHAR(256) | PBKDF2-SHA256 via Werkzeug |
| `is_admin` | BOOLEAN | Default False |
| `created_at` | DATETIME | UTC |
| `updated_at` | DATETIME | Auto-updated |

### `resumes`
| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `user_id` | FK → users | Indexed |
| `filename` | VARCHAR(255) | UUID-prefixed stored filename |
| `original_name` | VARCHAR(255) | Filename shown to user |
| `file_size` | INTEGER | Bytes |
| `extracted_text` | TEXT | Full PDF text (nullable) |
| `is_saved` | BOOLEAN | User bookmark flag |
| `created_at` | DATETIME | |

### `skills`
| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `name` | VARCHAR(100) | Unique, lowercase, indexed |
| `category` | VARCHAR(80) | backend/frontend/data/cloud/tools |
| `created_at` | DATETIME | |

### `job_roles`
| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `title` | VARCHAR(150) | Unique |
| `description` | TEXT | |
| `experience_level` | VARCHAR(30) | junior/mid/senior |
| `created_at` | DATETIME | |
| `updated_at` | DATETIME | |

### `job_skills` (Association)
| Column | Type | Notes |
|--------|------|-------|
| `job_role_id` | FK → job_roles | Composite PK |
| `skill_id` | FK → skills | Composite PK |

### `analysis_results`
| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `user_id` | FK → users | Indexed |
| `resume_id` | FK → resumes | Indexed |
| `job_role_id` | FK → job_roles | Nullable (role may be deleted) |
| `job_role_title` | VARCHAR(150) | Cached for display |
| `ats_score` | FLOAT | 0–100 blended score |
| `similarity_score` | FLOAT | 0–1 raw cosine similarity |
| `matched_skills` | TEXT | JSON array |
| `missing_skills` | TEXT | JSON array |
| `extracted_skills` | TEXT | JSON array |
| `suggestions` | TEXT | JSON array of strings |
| `created_at` | DATETIME | |

---

## API & Routes Reference

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| GET | `/` | No | Landing page |
| GET | `/auth/login` | No | Login form |
| POST | `/auth/login` | No | Authenticate user |
| GET | `/auth/register` | No | Register form |
| POST | `/auth/register` | No | Create account |
| GET | `/auth/logout` | ✅ | Clear session |
| GET | `/dashboard/` | ✅ | Home with stats + charts |
| GET/POST | `/dashboard/profile` | ✅ | Update profile / password |
| POST | `/resume/upload` | ✅ | Upload PDF → JSON response |
| GET | `/resume/saved` | ✅ | Saved resumes page |
| POST | `/resume/save/<id>` | ✅ | Toggle save flag → JSON |
| POST | `/resume/delete/<id>` | ✅ | Delete resume + file |
| GET | `/analyze/analyzer` | ✅ | Resume analyzer page |
| POST | `/analyze/` | ✅ | Run ATS analysis |
| GET | `/analyze/result/<id>` | ✅ | Full result page |
| GET | `/analyze/report/<id>` | ✅ | Download PDF report |
| GET | `/analyze/job-matcher` | ✅ | Job matcher page |
| GET | `/history/` | ✅ | Paginated history |
| POST | `/history/delete/<id>` | ✅ | Delete record → JSON |
| GET | `/admin/` | 🔒 Admin | Admin dashboard |
| POST | `/admin/roles/add` | 🔒 Admin | Add job role |
| GET/POST | `/admin/roles/edit/<id>` | 🔒 Admin | Edit job role |
| POST | `/admin/roles/delete/<id>` | 🔒 Admin | Delete role |
| GET | `/admin/skills` | 🔒 Admin | List skills |
| POST | `/admin/skills/add` | 🔒 Admin | Add skill |
| POST | `/admin/skills/delete/<id>` | 🔒 Admin | Delete skill |
| GET | `/admin/users` | 🔒 Admin | List users |
| POST | `/admin/users/toggle-admin/<id>` | 🔒 Admin | Promote/demote |

---

## Deployment Guide

### Option 1 – Render (recommended, free tier available)

1. Push your project to a GitHub repository.

2. Create a `render.yaml` in the project root:

```yaml
services:
  - type: web
    name: resumeai
    env: python
    buildCommand: "pip install -r requirements.txt && python -m spacy download en_core_web_sm && python init_db.py"
    startCommand: "gunicorn 'app:create_app(\"production\")' --workers 4 --bind 0.0.0.0:$PORT"
    envVars:
      - key: SECRET_KEY
        generateValue: true
      - key: FLASK_ENV
        value: production
```

3. Connect your GitHub repo to Render → **New Web Service**.

4. Render will detect `render.yaml` and deploy automatically.

> **SQLite note:** Render's free tier uses an ephemeral filesystem.
> For persistent data, either upgrade to a paid plan with a persistent disk,
> or switch `DATABASE_URL` to a PostgreSQL connection string.

---

### Option 2 – Railway

1. Install Railway CLI: `npm install -g @railway/cli`

2. Login: `railway login`

3. Create project: `railway init`

4. Deploy: `railway up`

5. Set environment variables in the Railway dashboard:
   ```
   SECRET_KEY=your-secret-key
   FLASK_ENV=production
   ```

6. Add a `Procfile` to the project root:
   ```
   web: gunicorn "app:create_app('production')" --workers 4 --bind 0.0.0.0:$PORT
   ```

---

### Option 3 – VPS / Ubuntu Server

```bash
# Install dependencies
sudo apt update && sudo apt install python3 python3-pip python3-venv nginx -y

# Clone project
git clone <your-repo-url> /var/www/resumeai
cd /var/www/resumeai

# Set up virtualenv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt gunicorn
python -m spacy download en_core_web_sm

# Set environment
cp .env.example .env   # Edit SECRET_KEY and FLASK_ENV=production

# Initialise DB
python init_db.py

# Create systemd service
sudo nano /etc/systemd/system/resumeai.service
```

```ini
[Unit]
Description=ResumeAI Flask App
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/resumeai
Environment="FLASK_ENV=production"
Environment="SECRET_KEY=your-secret-key-here"
ExecStart=/var/www/resumeai/venv/bin/gunicorn "app:create_app('production')" --workers 4 --bind unix:/tmp/resumeai.sock
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable resumeai && sudo systemctl start resumeai
```

Configure Nginx to proxy `/tmp/resumeai.sock`.

---

## Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| **Admin** | `admin@resumeai.com` | `admin123` |
| **User** | `demo@resumeai.com` | `demo123` |

The admin account has full access to `/admin/` — add job roles, manage skills, and view all users. The demo user account shows a standard user experience.

---

## Environment Variables

Create a `.env` file in the project root (never commit this):

```env
# Required in production — change this to a long random string
SECRET_KEY=super-secret-key-replace-me-in-production

# Database — defaults to SQLite in instance/database.db
# For PostgreSQL: postgresql://user:password@host:5432/dbname
DATABASE_URL=sqlite:///instance/database.db

# Environment: development | production
FLASK_ENV=development
```

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes with clear comments
4. Test locally: `python app.py`
5. Submit a pull request with a clear description

### Code Style
- Python: follow PEP 8, use type hints where possible
- Templates: Jinja2 with proper indentation
- JS: ES6+, no external runtime dependencies beyond Chart.js
- CSS: BEM-inspired class names, CSS variables for all colours

---

## License

MIT License — free to use, modify, and distribute with attribution.

---

*Built with ❤️ using Flask, spaCy, scikit-learn, and ReportLab.*
"# AI-Resume-Analyzer" 
