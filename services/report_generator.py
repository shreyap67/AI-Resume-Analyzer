# services/report_generator.py
"""
Generate a downloadable PDF analysis report using ReportLab.
Called from the analysis route when the user clicks "Download Report".
"""

import io
import re
import logging
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

logger = logging.getLogger(__name__)

# ─── Brand colours ────────────────────────────────────────────────────────────
BLUE   = colors.HexColor("#00D1FF")
PURPLE = colors.HexColor("#7C3AED")
DARK   = colors.HexColor("#0F172A")
LIGHT  = colors.HexColor("#E2E8F0")
GREEN  = colors.HexColor("#22C55E")
RED    = colors.HexColor("#EF4444")


def _extract_candidate_name(text: str) -> str:
    """
    Extract the candidate's name from raw resume text.

    PyPDF2 collapses all whitespace into a single space-separated string, so
    splitlines() gives only one giant line.  We therefore tokenise by known
    section-header keywords and look at the very first token-group.

    Strategy:
      1. Split the flat text on common section-header words.
      2. The first chunk (before any section header) contains the name/contact block.
      3. Inside that chunk find the first sequence of 2-5 capitalised words that
         contain no digits, no email @, no common noise words.
    """
    # Section-header words that signal the name block has ended
    _SECTION_HEADERS = re.compile(
        r'\b(objective|summary|profile|education|experience|skills|projects|'
        r'certifications|achievements|declaration|contact|career|work history)\b',
        re.IGNORECASE
    )

    # Grab the text before the first section header – this is the name/contact block
    m = _SECTION_HEADERS.search(text)
    header_block = text[:m.start()] if m else text[:400]

    # Clean up: remove email addresses and phone numbers so they don't get
    # mistaken for name fragments
    header_block = re.sub(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', ' ', header_block)
    header_block = re.sub(r'\+?\d[\d\s\-().]{7,}\d', ' ', header_block)

    # Noise words that appear in resume headers but are NOT a person's name
    _NOISE = {
        'resume', 'cv', 'curriculum', 'vitae', 'page', 'linkedin',
        'github', 'portfolio', 'address', 'phone', 'mobile', 'email',
        'www', 'http', 'https',
    }

    # Slide a window of 2-4 words across the tokens, return first that looks like a name
    tokens = header_block.split()
    for window in range(4, 1, -1):          # try 4-word, then 3-word, then 2-word names
        for i in range(len(tokens) - window + 1):
            chunk = tokens[i:i + window]
            phrase = " ".join(chunk)
            # Each word must start with a capital, contain only letters/hyphens/dots,
            # have no digits, and not be a noise word
            if all(
                w[0].isupper()
                and re.fullmatch(r"[A-Za-z][A-Za-z\-\.]*", w)
                and w.lower() not in _NOISE
                for w in chunk
            ):
                return phrase

    return "N/A"


def generate_analysis_report(analysis, user) -> bytes:
    """
    Build a PDF report for an AnalysisResult and return it as bytes.

    Args:
        analysis: AnalysisResult ORM object.
        user:     User ORM object (kept for signature compatibility, not used for display).

    Returns:
        Raw PDF bytes suitable for sending as a file response.
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()

    # ── Custom styles ─────────────────────────────────────────────────────────
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=22,
        textColor=DARK,
        spaceAfter=6,
        alignment=TA_CENTER,
    )
    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=PURPLE,
        spaceBefore=14,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        leading=16,
        textColor=colors.HexColor("#1E293B"),
    )
    label_style = ParagraphStyle(
        "Label",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#64748B"),
        alignment=TA_CENTER,
    )

    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph("ResumeAI", title_style))
    story.append(Paragraph("ATS Analysis Report", label_style))
    story.append(HRFlowable(width="100%", thickness=2, color=BLUE, spaceAfter=12))

    # ── Extract candidate details from resume.extracted_text ─────────────────
    # PyPDF2 stores text as a single flat space-separated string (no real newlines).
    _resume = analysis.resume
    _text   = (_resume.extracted_text or "") if _resume else ""

    # Email
    _email_match    = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", _text)
    candidate_email = _email_match.group(0) if _email_match else "N/A"

    # Phone
    _phone_match    = re.search(r"(\+?\d[\d\s\-().]{7,}\d)", _text)
    candidate_phone = _phone_match.group(0).strip() if _phone_match else "N/A"

    # Name — uses the dedicated helper that handles flat PyPDF2 text
    candidate_name = _extract_candidate_name(_text)

    # Location — "City, State" or "City, Country" (two single capitalised words)
    _loc_match         = re.search(r"\b([A-Z][a-zA-Z]+,\s*[A-Z][a-zA-Z]+)\b", _text)
    candidate_location = _loc_match.group(1).strip() if _loc_match else "N/A"

    # ── Meta table ────────────────────────────────────────────────────────────
    meta = [
        ["Candidate",   candidate_name],
        ["Email",       candidate_email],
        ["Phone",       candidate_phone],
        ["Location",    candidate_location],
        ["Job Role",    analysis.job_role_title],
        ["Report Date", datetime.now().strftime("%B %d, %Y")],
        ["Resume File", _resume.original_name if _resume else "N/A"],
    ]
    meta_table = Table(meta, colWidths=[4 * cm, 12 * cm])
    meta_table.setStyle(TableStyle([
        ("FONTSIZE",       (0, 0), (-1, -1), 10),
        ("FONTNAME",       (0, 0), (0, -1), "Helvetica-Bold"),
        ("TEXTCOLOR",      (0, 0), (0, -1), colors.HexColor("#475569")),
        ("TEXTCOLOR",      (1, 0), (1, -1), DARK),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#F8FAFC"), colors.white]),
        ("TOPPADDING",     (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 6),
        ("LEFTPADDING",    (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 20))

    # ── ATS Score — rendered as stacked Paragraphs, no overlap ───────────────
    score_val   = analysis.ats_score
    score_color = GREEN if score_val >= 75 else (colors.HexColor("#F59E0B") if score_val >= 60 else RED)

    score_num_style = ParagraphStyle(
        "ScoreNum",
        parent=styles["Normal"],
        fontSize=48,
        leading=52,
        textColor=score_color,
        alignment=TA_CENTER,
        spaceAfter=0,
        spaceBefore=0,
    )
    score_sub_style = ParagraphStyle(
        "ScoreSub",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748B"),
        alignment=TA_CENTER,
        spaceAfter=0,
        spaceBefore=0,
    )

    story.append(Paragraph(f"{score_val:.0f}%", score_num_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("ATS Match Score", score_sub_style))
    story.append(Paragraph(f"Label: {analysis.score_label()}", score_sub_style))
    story.append(Spacer(1, 20))

    # ── Skill breakdown — Paragraph cells so text wraps cleanly ──────────────
    story.append(Paragraph("Skill Analysis", heading_style))

    _matched_style = ParagraphStyle(
        "MatchedSkill", parent=styles["Normal"],
        fontSize=9, leading=14,
        textColor=colors.HexColor("#166534"),
    )
    _missing_style = ParagraphStyle(
        "MissingSkill", parent=styles["Normal"],
        fontSize=9, leading=14,
        textColor=colors.HexColor("#991B1B"),
    )
    skill_data = [
        ["Matched Skills \u2713", "Missing Skills \u2717"],
        [
            Paragraph(", ".join(analysis.matched_skills) or "None", _matched_style),
            Paragraph(", ".join(analysis.missing_skills) or "None", _missing_style),
        ],
    ]
    skill_table = Table(skill_data, colWidths=[8 * cm, 8 * cm])
    skill_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 9),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(skill_table)
    story.append(Spacer(1, 12))

    # ── Suggestions ───────────────────────────────────────────────────────────
    story.append(Paragraph("Improvement Suggestions", heading_style))
    for i, suggestion in enumerate(analysis.suggestions, start=1):
        story.append(Paragraph(f"{i}. {suggestion}", body_style))
        story.append(Spacer(1, 4))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 24))
    story.append(HRFlowable(width="100%", thickness=1, color=LIGHT))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Generated by ResumeAI \u00b7 AI-Powered Resume Analysis Platform \u00b7 Confidential",
        label_style,
    ))

    # ── Build PDF ─────────────────────────────────────────────────────────────
    try:
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        logger.info("Generated PDF report for analysis %d (%d bytes)", analysis.id, len(pdf_bytes))
        return pdf_bytes
    except Exception as e:
        logger.error("Failed to build PDF report: %s", e)
        raise
    finally:
        buffer.close()
