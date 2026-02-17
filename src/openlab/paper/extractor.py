"""PDF text extraction.

Uses pymupdf4llm when available for high-quality Markdown extraction.
Falls back to basic pymupdf (fitz) text extraction.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """Raised when PDF extraction fails."""


def extract_text(pdf_path: str | Path, max_pages: int = 50) -> str:
    """Extract text from a PDF file as Markdown.

    Tries pymupdf4llm first (best quality), falls back to pymupdf.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise ExtractionError(f"PDF not found: {path}")

    if not path.suffix.lower() == ".pdf":
        raise ExtractionError(f"Not a PDF file: {path}")

    # Try pymupdf4llm first
    try:
        import pymupdf4llm  # type: ignore[import-untyped]
        text: str = pymupdf4llm.to_markdown(str(path), pages=list(range(max_pages)))
        if text.strip():
            return text
    except ImportError:
        logger.debug("pymupdf4llm not available, trying pymupdf")
    except Exception as e:
        logger.debug("pymupdf4llm failed: %s, trying pymupdf", e)

    # Fallback to pymupdf (fitz)
    try:
        import fitz  # type: ignore[import-untyped]
        doc = fitz.open(str(path))
        pages = []
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            pages.append(page.get_text())
        doc.close()
        return "\n\n".join(pages)
    except ImportError:
        logger.debug("pymupdf not available, trying plain text")
    except Exception as e:
        logger.debug("pymupdf failed: %s", e)

    raise ExtractionError(
        "No PDF extraction library available. Install pymupdf4llm or pymupdf."
    )


def extract_text_from_string(text: str) -> str:
    """Pass through for already-extracted text (testing convenience)."""
    return text
