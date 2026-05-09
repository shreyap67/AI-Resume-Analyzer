# services/skill_extractor.py
"""
Skill extraction pipeline.

Strategy:
1. Normalise the resume text to lowercase.
2. Match against our curated SKILLS_DICTIONARY using exact substring search
   (fast, deterministic, no model required for the dictionary pass).
3. Optionally use spaCy noun-chunks to surface skills not in the dictionary
   (tech terms, libraries, frameworks the user may have written differently).

This two-pass approach gives high recall without requiring a trained NER model.
"""

import re
import logging

logger = logging.getLogger(__name__)

# ─── Master skills dictionary ──────────────────────────────────────────────────
# Grouped by category for analytics and pie-chart breakdown.
# Keys are the canonical skill names used in matching and storage.
SKILLS_DICTIONARY: dict[str, str] = {
    # ── Programming Languages ──
    "python": "backend",
    "java": "backend",
    "c++": "backend",
    "c#": "backend",
    "golang": "backend",
    "rust": "backend",
    "kotlin": "backend",
    "swift": "backend",
    "php": "backend",
    "ruby": "backend",
    "scala": "backend",
    "typescript": "frontend",
    "javascript": "frontend",
    # ── Frontend ──
    "html": "frontend",
    "css": "frontend",
    "react": "frontend",
    "vue": "frontend",
    "angular": "frontend",
    "next.js": "frontend",
    "svelte": "frontend",
    "redux": "frontend",
    "tailwind": "frontend",
    "bootstrap": "frontend",
    "graphql": "frontend",
    "webpack": "frontend",
    # ── Backend / Frameworks ──
    "node.js": "backend",
    "express": "backend",
    "flask": "backend",
    "django": "backend",
    "fastapi": "backend",
    "spring": "backend",
    "rest api": "backend",
    "microservices": "backend",
    # ── Databases ──
    "sql": "backend",
    "mysql": "backend",
    "postgresql": "backend",
    "mongodb": "backend",
    "redis": "backend",
    "elasticsearch": "backend",
    "sqlite": "backend",
    "oracle": "backend",
    # ── Data Science / ML ──
    "machine learning": "data",
    "deep learning": "data",
    "data analysis": "data",
    "pandas": "data",
    "numpy": "data",
    "scikit-learn": "data",
    "tensorflow": "data",
    "pytorch": "data",
    "keras": "data",
    "matplotlib": "data",
    "tableau": "data",
    "power bi": "data",
    "nlp": "data",
    "computer vision": "data",
    "statistics": "data",
    # ── Cloud & DevOps ──
    "aws": "cloud",
    "azure": "cloud",
    "gcp": "cloud",
    "google cloud": "cloud",
    "docker": "cloud",
    "kubernetes": "cloud",
    "jenkins": "cloud",
    "terraform": "cloud",
    "ansible": "cloud",
    "ci/cd": "cloud",
    "github actions": "cloud",
    "linux": "cloud",
    # ── Tools ──
    "git": "tools",
    "github": "tools",
    "jira": "tools",
    "agile": "tools",
    "scrum": "tools",
    "excel": "tools",
    "figma": "tools",
    "postman": "tools",
    # ── Soft / Business ──
    "project management": "soft",
    "communication": "soft",
    "leadership": "soft",
    "problem solving": "soft",
}

# Build a sorted list (longest first) so multi-word skills match before subwords
_SORTED_SKILLS = sorted(SKILLS_DICTIONARY.keys(), key=len, reverse=True)


def extract_skills(text: str) -> list[str]:
    """
    Scan resume text and return a deduplicated list of matched skill names.

    Args:
        text: Raw text extracted from the PDF.

    Returns:
        List of skill name strings (lowercase, canonical form).
    """
    if not text:
        return []

    # Normalise: lowercase, collapse whitespace
    normalised = text.lower()
    normalised = re.sub(r"\s+", " ", normalised)

    found: set[str] = set()

    for skill in _SORTED_SKILLS:
        # Use word-boundary matching where possible so "c" doesn't match "css"
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, normalised):
            found.add(skill)

    # Special case: "node" → also counts as "node.js"
    if "node" in normalised and "node.js" not in found:
        found.add("node.js")

    result = sorted(found)
    logger.info("Extracted %d skills from resume text", len(result))
    return result


def skills_by_category(skill_names: list[str]) -> dict[str, list[str]]:
    """
    Group a flat list of skill names into category buckets.

    Returns:
        dict like {"backend": ["python", "flask"], "frontend": ["react"], ...}
    """
    buckets: dict[str, list[str]] = {}
    for skill in skill_names:
        cat = SKILLS_DICTIONARY.get(skill, "other")
        buckets.setdefault(cat, []).append(skill)
    return buckets


def try_load_spacy():
    """
    Attempt to load the spaCy English model.
    Returns the model or None if not installed (so the app still works).
    """
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        logger.info("spaCy model loaded successfully")
        return nlp
    except OSError:
        logger.warning(
            "spaCy en_core_web_sm not found. Run: python -m spacy download en_core_web_sm"
        )
        return None
    except ImportError:
        logger.warning("spaCy not installed – dictionary-only skill extraction active")
        return None


# Load spaCy once at module level (None if unavailable)
_NLP = try_load_spacy()


def extract_skills_with_spacy(text: str) -> list[str]:
    """
    Enhanced extraction that combines dictionary matching with spaCy noun-chunk
    heuristics to surface skill-like tokens not in the dictionary.

    Falls back to pure dictionary matching if spaCy is unavailable.
    """
    # Always run dictionary pass first
    base_skills = extract_skills(text)

    if _NLP is None:
        return base_skills

    try:
        doc = _NLP(text[:50000])  # cap at 50k chars for performance

        extra: set[str] = set()
        for chunk in doc.noun_chunks:
            token = chunk.text.lower().strip()
            # Keep tokens that look like tech terms (short, no common words)
            if 2 <= len(token) <= 30 and token not in {"the", "a", "an", "my", "our", "i", "we"}:
                if token in SKILLS_DICTIONARY:
                    extra.add(token)

        combined = sorted(set(base_skills) | extra)
        return combined
    except Exception as e:
        logger.warning("spaCy extraction failed, using dictionary only: %s", e)
        return base_skills


# ── Predefined role → skills mapping (2025 industry standards) ───────────────

ROLE_SKILLS = {
    # ── Computer Science ──────────────────────────────────────────────────────
    "python developer": [
        "python", "sql", "git", "flask", "django",
        "rest apis", "data structures", "debugging",
    ],
    "java developer": [
        "java", "spring boot", "rest apis", "hibernate",
        "sql", "microservices", "maven", "junit",
    ],
    "frontend developer": [
        "html", "css", "javascript", "react",
        "typescript", "responsive design", "git", "api integration",
    ],
    "backend developer": [
        "python", "node.js", "rest apis", "sql",
        "authentication", "git", "docker", "system design",
    ],
    "full stack developer": [
        "html", "css", "javascript", "react",
        "node.js", "sql", "git", "rest apis",
    ],
    "data analyst": [
        "python", "sql", "excel", "pandas",
        "power bi", "tableau", "data visualization", "numpy",
    ],
    "data scientist": [
        "python", "pandas", "scikit-learn", "machine learning",
        "numpy", "statistics", "data visualization", "jupyter",
    ],
    "machine learning engineer": [
        "python", "machine learning", "tensorflow", "pytorch",
        "scikit-learn", "feature engineering", "docker", "git",
    ],
    "cloud engineer": [
        "aws", "azure", "docker", "kubernetes",
        "linux", "networking", "terraform", "git",
    ],
    "devops engineer": [
        "docker", "kubernetes", "ci/cd", "jenkins",
        "terraform", "linux", "git", "aws",
    ],
    "cyber security analyst": [
        "network security", "linux", "wireshark", "nmap",
        "penetration testing", "siem", "firewalls", "vulnerability assessment",
    ],
    "qa engineer": [
        "manual testing", "test cases", "bug tracking", "regression testing",
        "selenium", "api testing", "jira", "test planning",
    ],
    "android developer": [
        "java", "kotlin", "android sdk", "xml",
        "rest apis", "firebase", "git", "sqlite",
    ],
    "ios developer": [
        "swift", "xcode", "ios sdk", "rest apis",
        "auto layout", "core data", "git", "cocoapods",
    ],
    "ui/ux designer": [
        "figma", "wireframing", "prototyping", "user research",
        "adobe xd", "usability testing", "typography", "design systems",
    ],
    "database administrator": [
        "sql", "mysql", "postgresql", "oracle",
        "mongodb", "database design", "query optimization", "backup and recovery",
        "replication", "performance tuning",
    ],
    "mobile app developer": [
        "java", "kotlin", "swift", "react native",
        "flutter", "firebase", "rest apis", "sqlite",
        "android sdk", "ios sdk",
    ],
    "cloud architect": [
        "aws", "azure", "gcp", "cloud architecture",
        "kubernetes", "terraform", "networking", "security",
        "microservices", "cost optimization",
    ],
    # ── Civil ─────────────────────────────────────────────────────────────────
    "site engineer": [
        "autocad", "construction management", "site supervision", "surveying",
        "quantity estimation", "ms project", "quality control", "safety management",
    ],
    "structural engineer": [
        "structural analysis", "etabs", "staad pro", "autocad",
        "design codes", "safe", "revit", "load calculation",
    ],
    "land surveyor": [
        "total station", "gps surveying", "levelling", "autocad",
        "gis", "topographic survey", "quantity surveying", "cadastral survey",
    ],
    "construction manager": [
        "construction management", "project planning", "ms project", "budgeting",
        "contract management", "site supervision", "quality control", "safety management",
        "stakeholder management", "scheduling",
    ],
    "environmental engineer": [
        "environmental impact assessment", "wastewater treatment", "air quality monitoring",
        "gis", "environmental regulations", "soil testing", "hazardous waste management",
        "autocad", "sustainability", "epa standards",
    ],
    "geotechnical engineer": [
        "soil mechanics", "foundation design", "site investigation", "autocad",
        "plaxis", "geological mapping", "slope stability", "borehole analysis",
        "retaining wall design", "ground improvement",
    ],
    "transportation engineer": [
        "traffic engineering", "highway design", "autocad civil 3d", "hec-ras",
        "traffic simulation", "pavement design", "transportation planning",
        "vissim", "gis", "road safety audit",
    ],
    "urban planner": [
        "gis", "urban design", "land use planning", "autocad",
        "arcgis", "zoning regulations", "environmental planning",
        "community engagement", "transportation planning", "sustainable development",
    ],
    # ── Mechanical ────────────────────────────────────────────────────────────
    "mechanical design engineer": [
        "solidworks", "autocad", "catia", "gd&t",
        "product design", "ansys", "material selection", "bom",
    ],
    "production engineer": [
        "manufacturing processes", "quality control", "lean manufacturing", "production planning",
        "erp", "kaizen", "5s methodology", "capacity planning",
    ],
    "manufacturing engineer": [
        "manufacturing processes", "cnc programming", "lean manufacturing", "autocad",
        "solidworks", "quality control", "process improvement", "gd&t",
        "production planning", "six sigma",
    ],
    "automotive engineer": [
        "catia", "solidworks", "vehicle dynamics", "powertrain",
        "fea", "ansys", "embedded systems", "can bus",
        "matlab", "engine design",
    ],
    "hvac engineer": [
        "hvac design", "autocad", "revit mep", "heat load calculation",
        "ductwork design", "ashrae standards", "refrigeration", "energy modeling",
        "hvac software", "building codes",
    ],
    "quality control engineer": [
        "quality control", "iso standards", "six sigma", "spc",
        "failure analysis", "fmea", "inspection techniques", "minitab",
        "calibration", "non-destructive testing",
    ],
    "maintenance engineer": [
        "predictive maintenance", "preventive maintenance", "plc programming", "hydraulics",
        "pneumatics", "electrical troubleshooting", "cmms", "root cause analysis",
        "mechanical systems", "safety procedures",
    ],
    "robotics engineer": [
        "ros", "python", "c++", "robot kinematics",
        "computer vision", "matlab", "embedded systems", "plc programming",
        "sensors and actuators", "automation",
    ],
    # ── Electrical ────────────────────────────────────────────────────────────
    "electrical engineer": [
        "circuit design", "power systems", "electrical machines", "matlab",
        "autocad electrical", "plc programming", "protection systems", "load flow analysis",
    ],
    "embedded systems engineer": [
        "c", "microcontrollers", "embedded c", "rtos",
        "iot", "uart/spi/i2c", "debugging", "keil ide",
    ],
    "power systems engineer": [
        "power systems", "load flow analysis", "pscad", "etap",
        "protection relays", "electrical machines", "grid analysis",
        "autocad electrical", "scada", "high voltage systems",
    ],
    "iot engineer": [
        "iot", "mqtt", "embedded c", "python",
        "microcontrollers", "raspberry pi", "arduino", "cloud iot",
        "sensors", "edge computing",
    ],
    "control systems engineer": [
        "plc programming", "scada", "control theory", "matlab simulink",
        "pid controller", "hmi", "industrial automation", "ladder logic",
        "dcs", "motion control",
    ],
    "electronics engineer": [
        "circuit design", "pcb design", "altium designer", "signal processing",
        "analog circuits", "digital circuits", "oscilloscope", "microcontrollers",
        "embedded systems", "spice simulation",
    ],
    "vlsi design engineer": [
        "vlsi design", "verilog", "vhdl", "cadence",
        "synopsys", "asic design", "fpga", "timing analysis",
        "physical design", "rtl design",
    ],
    "instrumentation engineer": [
        "instrumentation", "plc programming", "scada", "calibration",
        "pid control", "sensors", "process control", "p&id",
        "field instruments", "dcs",
    ],
    # ── Commerce ──────────────────────────────────────────────────────────────
    "accountant": [
        "accounting", "tally", "gst", "taxation",
        "financial reporting", "ms excel", "tds", "bank reconciliation",
    ],
    "financial analyst": [
        "financial modeling", "valuation", "excel", "forecasting",
        "power bi", "sql", "dcf analysis", "budgeting",
    ],
    "auditor": [
        "auditing", "internal controls", "risk assessment", "financial statements",
        "ifrs", "gaap", "ms excel", "audit planning",
        "compliance", "taxation",
    ],
    "tax consultant": [
        "taxation", "gst", "income tax", "tds",
        "tax planning", "tax compliance", "tally", "ms excel",
        "direct tax", "indirect tax",
    ],
    "banking officer": [
        "banking operations", "credit analysis", "kyc", "ms excel",
        "loan processing", "risk management", "financial products", "customer service",
        "regulatory compliance", "anti-money laundering",
    ],
    "investment analyst": [
        "financial modeling", "equity research", "valuation", "excel",
        "bloomberg", "dcf analysis", "portfolio management", "financial statements",
        "market research", "risk assessment",
    ],
    "financial controller": [
        "financial reporting", "ifrs", "gaap", "budgeting",
        "forecasting", "ms excel", "erp", "internal controls",
        "audit", "cost accounting",
    ],
    "cost accountant": [
        "cost accounting", "cma", "cost analysis", "budgeting",
        "variance analysis", "product costing", "tally", "ms excel",
        "standard costing", "inventory valuation",
    ],
    "management consultant": [
        "business analysis", "project management", "data analysis", "excel",
        "powerpoint", "strategic planning", "process improvement", "stakeholder management",
        "financial modeling", "change management",
    ],
    # ── Marketing ─────────────────────────────────────────────────────────────
    "digital marketing executive": [
        "seo", "sem", "social media marketing", "google analytics",
        "content marketing", "email marketing", "google ads", "meta ads",
    ],
    "digital marketing specialist": [
        "seo", "sem", "google ads", "meta ads",
        "social media marketing", "google analytics", "email marketing",
        "content marketing", "marketing automation", "crm",
    ],
    "seo specialist": [
        "seo", "keyword research", "on-page seo", "google analytics",
        "link building", "technical seo", "google search console", "semrush",
    ],
    "content strategist": [
        "content strategy", "content writing", "seo", "editorial planning",
        "social media", "analytics", "copywriting", "audience research",
        "cms", "brand storytelling",
    ],
    "brand manager": [
        "brand management", "marketing strategy", "market research", "campaign management",
        "advertising", "social media", "budgeting", "product positioning",
        "consumer insights", "cross-functional collaboration",
    ],
    "social media manager": [
        "social media marketing", "content creation", "community management", "instagram",
        "facebook ads", "tiktok", "hootsuite", "analytics",
        "copywriting", "influencer marketing",
    ],
    "marketing analyst": [
        "data analysis", "google analytics", "excel", "sql",
        "market research", "power bi", "tableau", "crm",
        "campaign performance", "a/b testing",
    ],
    "growth hacker": [
        "growth marketing", "a/b testing", "seo", "python",
        "sql", "google analytics", "email marketing", "viral marketing",
        "product analytics", "conversion rate optimization",
    ],
    "email marketing specialist": [
        "email marketing", "mailchimp", "klaviyo", "email automation",
        "a/b testing", "copywriting", "segmentation", "html",
        "campaign analytics", "crm",
    ],
    # ── Medicine ──────────────────────────────────────────────────────────────
    "general physician": [
        "diagnosis", "patient care", "clinical examination", "medical history",
        "prescription writing", "icd coding", "differential diagnosis", "clinical documentation",
    ],
    "nurse": [
        "patient care", "clinical procedures", "medication administration", "vital signs",
        "wound care", "iv therapy", "patient monitoring", "medical records",
    ],
    "surgeon": [
        "surgical procedures", "patient assessment", "pre-operative planning", "post-operative care",
        "clinical documentation", "anatomy", "sterile technique", "surgical instruments",
        "emergency surgery", "wound management",
    ],
    "clinical researcher": [
        "clinical trials", "gcp guidelines", "data collection", "biostatistics",
        "research protocol", "irb submissions", "spss", "patient recruitment",
        "literature review", "regulatory compliance",
    ],
    "pharmacist": [
        "drug dispensing", "pharmacology", "medication counselling", "drug interactions",
        "inventory management", "clinical pharmacy", "compounding", "pharmaceutical care",
        "patient safety", "drug therapy management",
    ],
    "medical lab technician": [
        "laboratory techniques", "blood analysis", "microbiology", "hematology",
        "clinical chemistry", "lims", "sample processing", "quality control",
        "immunology", "pathology",
    ],
    "radiologist": [
        "radiology", "mri interpretation", "ct scan", "x-ray",
        "ultrasound", "pacs", "interventional radiology", "diagnostic imaging",
        "clinical documentation", "anatomy",
    ],
    "cardiologist": [
        "ecg interpretation", "echocardiography", "cardiac catheterization", "patient assessment",
        "cardiology", "clinical documentation", "heart failure management",
        "arrhythmia management", "cardiovascular pharmacology", "critical care",
    ],
    # ── Law ───────────────────────────────────────────────────────────────────
    "lawyer": [
        "legal research", "drafting", "litigation", "case analysis",
        "client counselling", "court procedures", "legal documentation", "negotiation",
    ],
    "corporate lawyer": [
        "corporate law", "contracts", "compliance", "due diligence",
        "mergers and acquisitions", "regulatory filings", "legal drafting", "company law",
    ],
    "criminal defense attorney": [
        "criminal law", "litigation", "legal research", "trial advocacy",
        "case investigation", "client counselling", "bail applications",
        "evidence analysis", "legal drafting", "court procedures",
    ],
    "legal consultant": [
        "legal research", "legal advisory", "contract review", "compliance",
        "risk assessment", "legal documentation", "negotiation", "regulatory framework",
        "corporate law", "client counselling",
    ],
    "intellectual property attorney": [
        "patent law", "trademark registration", "copyright law", "ip litigation",
        "patent drafting", "ip strategy", "legal research", "licensing agreements",
        "trade secrets", "ip due diligence",
    ],
    "family law attorney": [
        "family law", "divorce proceedings", "child custody", "mediation",
        "legal drafting", "client counselling", "court procedures", "domestic relations",
        "property settlement", "litigation",
    ],
    "paralegal": [
        "legal research", "drafting", "case management", "document review",
        "court filings", "client communication", "legal software", "evidence organization",
        "billing", "compliance",
    ],
    # ── Data Science ──────────────────────────────────────────────────────────
    "business intelligence analyst": [
        "power bi", "tableau", "sql", "data modeling",
        "excel", "etl", "dax", "data warehousing",
        "reporting", "business analysis",
    ],
    "data engineer": [
        "python", "sql", "apache spark", "airflow",
        "etl", "data warehousing", "kafka", "aws",
        "dbt", "data pipelines",
    ],
    "ai research scientist": [
        "python", "machine learning", "deep learning", "pytorch",
        "tensorflow", "research methodology", "mathematics", "nlp",
        "computer vision", "paper writing",
    ],
    "nlp engineer": [
        "python", "nlp", "transformers", "hugging face",
        "pytorch", "tensorflow", "text classification", "named entity recognition",
        "language models", "spacy",
    ],
    "computer vision engineer": [
        "python", "computer vision", "opencv", "deep learning",
        "pytorch", "tensorflow", "image segmentation", "object detection",
        "yolo", "convolutional neural networks",
    ],
}


def _normalise_role(role: str) -> str:
    """Map freetext role input to a ROLE_SKILLS key where possible."""
    key = role.lower().strip()
    if "python" in key:
        return "python developer"
    if "data analyst" in key:
        return "data analyst"
    if "data scien" in key:
        return "data scientist"
    if "machine learning" in key or "ml engineer" in key:
        return "machine learning engineer"
    if "frontend" in key or "front-end" in key or "front end" in key:
        return "frontend developer"
    if "backend" in key or "back-end" in key or "back end" in key:
        return "backend developer"
    if "full stack" in key or "fullstack" in key:
        return "full stack developer"
    if "devops" in key or "dev ops" in key:
        return "devops engineer"
    if "cloud architect" in key:
        return "cloud architect"
    if "cloud" in key:
        return "cloud engineer"
    if "android" in key:
        return "android developer"
    if "ios" in key:
        return "ios developer"
    if "java" in key:
        return "java developer"
    if "cyber" in key or "cybersecurity" in key or "security analyst" in key:
        return "cyber security analyst"
    if "qa" in key or "quality assurance" in key or "tester" in key:
        return "qa engineer"
    if "ui" in key or "ux" in key:
        return "ui/ux designer"
    if "database administrator" in key or "dba" in key:
        return "database administrator"
    if "mobile app" in key:
        return "mobile app developer"
    if "embedded" in key:
        return "embedded systems engineer"
    if "structural" in key:
        return "structural engineer"
    if "site engineer" in key:
        return "site engineer"
    if "land surveyor" in key or "surveyor" in key:
        return "land surveyor"
    if "construction manager" in key:
        return "construction manager"
    if "environmental engineer" in key:
        return "environmental engineer"
    if "geotechnical" in key:
        return "geotechnical engineer"
    if "transportation engineer" in key:
        return "transportation engineer"
    if "urban planner" in key:
        return "urban planner"
    if "mechanical design" in key:
        return "mechanical design engineer"
    if "manufacturing engineer" in key:
        return "manufacturing engineer"
    if "automotive" in key:
        return "automotive engineer"
    if "hvac" in key:
        return "hvac engineer"
    if "quality control engineer" in key:
        return "quality control engineer"
    if "production engineer" in key:
        return "production engineer"
    if "maintenance engineer" in key:
        return "maintenance engineer"
    if "robotics" in key:
        return "robotics engineer"
    if "power systems" in key:
        return "power systems engineer"
    if "iot engineer" in key:
        return "iot engineer"
    if "control systems" in key:
        return "control systems engineer"
    if "vlsi" in key:
        return "vlsi design engineer"
    if "instrumentation" in key:
        return "instrumentation engineer"
    if "electronics engineer" in key:
        return "electronics engineer"
    if "electrical" in key:
        return "electrical engineer"
    if "cost accountant" in key:
        return "cost accountant"
    if "accountant" in key:
        return "accountant"
    if "financial controller" in key:
        return "financial controller"
    if "financial analyst" in key or "finance analyst" in key:
        return "financial analyst"
    if "investment analyst" in key:
        return "investment analyst"
    if "auditor" in key:
        return "auditor"
    if "tax consultant" in key:
        return "tax consultant"
    if "banking officer" in key:
        return "banking officer"
    if "management consultant" in key:
        return "management consultant"
    if "digital marketing specialist" in key:
        return "digital marketing specialist"
    if "digital marketing" in key:
        return "digital marketing executive"
    if "seo" in key:
        return "seo specialist"
    if "content strategist" in key:
        return "content strategist"
    if "brand manager" in key:
        return "brand manager"
    if "social media manager" in key:
        return "social media manager"
    if "marketing analyst" in key:
        return "marketing analyst"
    if "growth hacker" in key or "growth market" in key:
        return "growth hacker"
    if "email marketing" in key:
        return "email marketing specialist"
    if "physician" in key or "doctor" in key:
        return "general physician"
    if "surgeon" in key:
        return "surgeon"
    if "clinical researcher" in key:
        return "clinical researcher"
    if "pharmacist" in key:
        return "pharmacist"
    if "medical lab" in key or "lab technician" in key:
        return "medical lab technician"
    if "radiologist" in key:
        return "radiologist"
    if "cardiologist" in key:
        return "cardiologist"
    if "nurse" in key:
        return "nurse"
    if "intellectual property" in key or "ip attorney" in key:
        return "intellectual property attorney"
    if "family law" in key:
        return "family law attorney"
    if "criminal defense" in key or "criminal defence" in key:
        return "criminal defense attorney"
    if "legal consultant" in key:
        return "legal consultant"
    if "paralegal" in key:
        return "paralegal"
    if "corporate lawyer" in key:
        return "corporate lawyer"
    if "lawyer" in key or "advocate" in key or "attorney" in key:
        return "lawyer"
    if "business intelligence" in key or "bi analyst" in key:
        return "business intelligence analyst"
    if "data engineer" in key:
        return "data engineer"
    if "ai research" in key or "research scientist" in key:
        return "ai research scientist"
    if "nlp engineer" in key:
        return "nlp engineer"
    if "computer vision engineer" in key:
        return "computer vision engineer"
    return key   # unknown → triggers AI fallback


# ── Partial-match keywords: skills mentioned with these words score 0.5 ───────
PARTIAL_KEYWORDS = ["basic", "basics", "fundamentals", "fundamental",
                    "intro", "introduction", "beginner", "elementary",
                    "overview", "exposure"]

# ── Framework groups: having ANY member satisfies the whole group ───────────
FRAMEWORK_GROUPS = {
    "backend_framework": ["flask", "django", "fastapi"],
    "js_framework":      ["react", "vue", "angular", "svelte"],
    "cloud_provider":    ["aws", "azure", "gcp", "google cloud"],
    "css_framework":     ["bootstrap", "tailwind"],
}

# Pre-compute skill → group name for O(1) lookup
_SKILL_TO_GROUP: dict[str, str] = {
    skill: grp
    for grp, skills in FRAMEWORK_GROUPS.items()
    for skill in skills
}


def _score_skills(
    resume_text_lower: str,
    extracted_set: set,
    required: list,
) -> tuple[list, list, list, float]:
    """
    Score required skills against the resume with three tiers:
      - full match  (1.0) : skill present in extracted_set
      - partial match (0.5): skill appears in resume alongside a PARTIAL_KEYWORD
      - framework flex    : if ANY member of a FRAMEWORK_GROUP is fully matched,
                            the rest of that group are silently satisfied
      - true missing (0.0): none of the above

    Returns:
        full_matched   : skills with score 1.0
        partial_matched: skills with score 0.5
        true_missing   : skills with score 0.0
        pct            : weighted percentage score
    """
    # Which framework groups are already satisfied by extracted skills?
    satisfied_groups: set[str] = set()
    for skill in extracted_set:
        grp = _SKILL_TO_GROUP.get(skill)
        if grp:
            satisfied_groups.add(grp)

    full_matched:    list[str] = []
    partial_matched: list[str] = []
    true_missing:    list[str] = []
    match_score: float = 0.0

    for skill in required:
        # 1. Full match
        if skill in extracted_set:
            full_matched.append(skill)
            match_score += 1.0
            continue

        # 2. Framework group flexibility
        grp = _SKILL_TO_GROUP.get(skill)
        if grp and grp in satisfied_groups:
            # Group already satisfied — treat as full match, don’t flag as missing
            full_matched.append(skill)
            match_score += 1.0
            continue

        # 3. Partial match — skill word appears near a partial keyword in resume
        skill_present = skill in resume_text_lower
        near_partial  = any(
            kw in resume_text_lower
            for kw in PARTIAL_KEYWORDS
            if skill in resume_text_lower  # only test if skill token exists at all
        )
        if skill_present and near_partial:
            partial_matched.append(skill)
            match_score += 0.5
            continue

        # 4. True missing
        true_missing.append(skill)

    total = max(len(required), 1)
    pct   = round((match_score / total) * 100, 1)
    return sorted(full_matched), sorted(partial_matched), sorted(true_missing), pct


# ── LLM-powered full resume analysis ───────────────────────────────────────────

def analyze_resume_with_ai(resume_text: str, job_role: str, experience_level: str = "mid") -> dict:
    """
    Hybrid analysis:
      - Known roles  → use ROLE_SKILLS (fast, deterministic, no API cost)
      - Custom roles → call OpenRouter AI to generate required skills

    Scoring uses three tiers (full / partial / missing) and framework
    group flexibility so semantically equivalent skills are not penalised.

    Output structure (unchanged):
        {
            "extracted_skills": [...],
            "industry_required_skills": [...],
            "missing_skills": [...],
            "skill_match_percentage": "72%",
            "recommendations": [...]
        }
    """
    import os, json
    try:
        import requests as _req
    except ImportError:
        logger.warning("requests not installed — falling back to dictionary extraction")
        return _fallback_analysis(resume_text, job_role)

    # ── Step 1: resolve industry-required skills ───────────────────────────────────
    role_key = _normalise_role(job_role)

    if role_key in ROLE_SKILLS:
        industry_required = list(ROLE_SKILLS[role_key])
        logger.info("Known role ‘%s’ → predefined skills (%d)", role_key, len(industry_required))
    else:
        industry_required = []
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if api_key:
            ai_prompt = (
                f"List 8-10 core technical skills required for a {job_role} "
                f"({experience_level}) in 2025. "
                "Only technical skills. No soft skills. Keep it realistic. "
                "Return comma-separated skills only, no numbering, no explanation."
            )
            try:
                resp = _req.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "openai/gpt-4o-mini",
                        "messages": [{"role": "user", "content": ai_prompt}],
                        "temperature": 0.2,
                        "max_tokens": 200,
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                raw = (
                    resp.json()
                    .get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )
                industry_required = [s.strip().lower() for s in raw.split(",") if s.strip()]
                logger.info("AI: %d required skills for custom role ‘%s’", len(industry_required), job_role)
            except Exception as ai_err:
                logger.error("OpenRouter error (required skills): %s", ai_err)
        if not industry_required:
            logger.warning("No required skills resolved for ‘%s’ — using fallback", job_role)
            return _fallback_analysis(resume_text, job_role)

    # ── Step 2: extract skills present in the resume ────────────────────────────────
    extracted_skills    = extract_skills_with_spacy(resume_text)
    resume_text_lower   = resume_text.lower()

    # ── API integration keyword detection ────────────────────────────────────────────────
    # Catches project descriptions: 'REST API', 'using API', 'API-based', etc.
    _API_TRIGGERS = ["rest api", "restful api", "api integration", "api-based",
                     "using api", "via api", "consumed api", "built api", " api "]
    if "api integration" not in extracted_skills and any(
        kw in resume_text_lower for kw in _API_TRIGGERS
    ):
        extracted_skills = list(extracted_skills) + ["api integration"]
        logger.debug("API integration inferred from resume text keywords")

    # ── Domain-skill fallback (civil, mechanical, commerce, etc.) ─────────────────
    # Fires only when spaCy/LLM extraction returns too few skills (<3),
    # which happens for non-CS domains whose terms aren't in the spaCy dict.
    if len(extracted_skills) < 3 and role_key in ROLE_SKILLS:
        extracted_set_lower = {s.lower() for s in extracted_skills}
        for _skill in ROLE_SKILLS[role_key]:
            _sk = _skill.lower()
            if _sk not in extracted_set_lower and re.search(
                r'\b' + re.escape(_sk) + r'\b', resume_text_lower
            ):
                extracted_skills = list(extracted_skills) + [_skill]
                extracted_set_lower.add(_sk)
        logger.debug(
            "Domain fallback for role '%s': extracted_skills now %d",
            role_key, len(extracted_skills),
        )

    # ── Step 3: smart scoring (full / partial / framework-flex) ────────────────────
    full_matched, partial_matched, true_missing, pct = _score_skills(
        resume_text_lower,
        set(extracted_skills),
        industry_required,
    )

    # ── Step 4: smart recommendations ───────────────────────────────────────────────
    recommendations: list[str] = []

    # Partial-skill upgrade hints
    for skill in partial_matched:
        recommendations.append(
            f"Strengthen your understanding of ‘{skill}’ beyond basics — "
            "aim to demonstrate hands-on project experience."
        )

    # Framework expansion hints (only when user already has one from a group)
    for grp, members in FRAMEWORK_GROUPS.items():
        user_has  = [m for m in members if m in set(extracted_skills)]
        grp_req   = [m for m in members if m in set(industry_required)]
        if user_has and grp_req:
            missing_in_grp = [m for m in grp_req if m not in set(extracted_skills)]
            if missing_in_grp:
                others = ", ".join(missing_in_grp)
                recommendations.append(
                    f"You know {user_has[0]} — consider also learning {others} "
                    "to broaden your backend expertise."
                )

    # True-missing skills block
    if true_missing:
        top = ", ".join(true_missing[:5])
        recommendations.append(f"Add these missing skills to your resume: {top}.")

    # Low overall score nudge
    if pct < 50:
        recommendations.append(
            f"Your match for ‘{job_role}’ is {pct}%. "
            "Consider focused upskilling before applying."
        )

    # Always-present quality hints
    recommendations += [
        "Quantify achievements with metrics (e.g. ‘reduced load time by 35%’).",
        "Tailor your resume summary to mirror keywords from the job description.",
        "Add project links (GitHub, portfolio) to demonstrate hands-on experience.",
    ]

    # ── Fix 2+3: prevent false 100% ────────────────────────────────────────────────────────
    # Rule A: a resume with zero or suspiciously few extracted skills
    #         cannot legitimately score 100%.
    # Rule B: hard cap — 100% is only valid when the candidate has more
    #         extracted skills than required (clearly over-qualified).
    if pct >= 100.0:
        if len(extracted_skills) == 0:
            # Validation: no skills at all → score cannot be meaningful
            pct = 0.0
        elif len(extracted_skills) <= len(industry_required):
            # Safety cap: matched every required skill but has no surplus
            # → realistic ceiling is 90% (there is always room to grow)
            pct = 90.0
            logger.debug(
                "Score capped 100→990%: extracted=%d required=%d",
                len(extracted_skills), len(industry_required),
            )

    result = {
        "extracted_skills":         extracted_skills,
        "industry_required_skills": industry_required,
        "missing_skills":           true_missing,          # only TRUE missing
        "skill_match_percentage":   f"{pct}%",
        "recommendations":          recommendations[:5],
    }

    logger.info(
        "Analysis done: role=‘%s’ extracted=%d required=%d "
        "full=%d partial=%d missing=%d match=%s",
        job_role, len(extracted_skills), len(industry_required),
        len(full_matched), len(partial_matched), len(true_missing),
        result["skill_match_percentage"],
    )
    return result
def _fallback_analysis(resume_text: str, job_role: str) -> dict:
    """
    Dictionary-based fallback when the OpenRouter API is unavailable.
    Returns the same JSON structure as analyze_resume_with_ai().
    """
    extracted = extract_skills_with_spacy(resume_text)
    # Best-effort: use all dictionary skills as a stand-in for required skills
    required = list(SKILLS_DICTIONARY.keys())
    extracted_set = set(extracted)
    required_set = set(required)
    missing = sorted(required_set - extracted_set)
    pct = round((len(extracted_set & required_set) / max(len(required_set), 1)) * 100, 1)
    return {
        "extracted_skills": extracted,
        "industry_required_skills": required,
        "missing_skills": missing,
        "skill_match_percentage": f"{pct}%",
        "recommendations": [
            f"Add missing skills relevant to {job_role} to improve your ATS score.",
            "Quantify achievements with metrics (e.g. 'reduced build time by 40%').",
            "Tailor your resume summary to match the job description keywords.",
        ],
    }
