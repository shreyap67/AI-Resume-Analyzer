# services/pdf_parser.py
"""
PDF text extraction using PyPDF2.
Falls back gracefully if a page cannot be decoded.
"""

import os
import logging
from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError

logger = logging.getLogger(__name__)


def extract_text_from_pdf(filepath: str) -> str:
    """
    Open a PDF file and extract all text content page-by-page.

    Args:
        filepath: Absolute path to the PDF file on disk.

    Returns:
        A single string containing all extracted text, or empty string on failure.
    """
    if not os.path.exists(filepath):
        logger.error("PDF not found: %s", filepath)
        return ""

    full_text = []

    try:
        reader = PdfReader(filepath)
        num_pages = len(reader.pages)
        logger.info("Parsing PDF: %s (%d pages)", os.path.basename(filepath), num_pages)

        for page_num, page in enumerate(reader.pages):
            try:
                text = page.extract_text()
                if text:
                    # Normalise whitespace so downstream NLP works cleanly
                    text = " ".join(text.split())
                    full_text.append(text)
            except Exception as page_err:
                # Log but continue – one bad page shouldn't kill the whole parse
                logger.warning("Could not extract page %d: %s", page_num + 1, page_err)

    except PdfReadError as e:
        logger.error("Failed to read PDF %s: %s", filepath, e)
        return ""
    except Exception as e:
        logger.error("Unexpected error parsing %s: %s", filepath, e)
        return ""

    combined = "\n".join(full_text)
    logger.info("Extracted %d characters from %s", len(combined), os.path.basename(filepath))
    return combined
