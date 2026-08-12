"""
services/ocr.py

Local, free OCR fallback for scanned/image-only PDF pages, using Tesseract
OCR (via the pytesseract wrapper). No image or text is ever sent to an LLM
or any external API for OCR -- everything runs locally.

Tesseract itself is a separate system binary (not a pip package):
 - Streamlit Community Cloud: installed automatically via packages.txt
 - Windows/Mac/Linux local dev: must be installed separately (see README).
   If it's not on PATH, set TESSERACT_CMD in .streamlit/secrets.toml or as
   an environment variable to point directly at the executable.
"""

from __future__ import annotations

import io
import os
from typing import Optional

import streamlit as st


class OCRError(Exception):
    """Raised when OCR cannot be performed (engine missing or page failed)."""


def _configure_tesseract_cmd() -> None:
    import pytesseract

    cmd: Optional[str] = None
    try:
        if "TESSERACT_CMD" in st.secrets:
            cmd = st.secrets["TESSERACT_CMD"]
    except Exception:
        pass
    cmd = cmd or os.environ.get("TESSERACT_CMD")
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd


@st.cache_resource(show_spinner=False)
def is_tesseract_available() -> bool:
    """Checked once per server process and cached, so we don't retry a
    missing engine on every single page."""
    try:
        import pytesseract

        _configure_tesseract_cmd()
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def ocr_image_bytes(image_bytes: bytes, lang: str = "eng") -> str:
    """Runs OCR on a single rendered page image (PNG bytes) and returns the
    extracted text. Raises OCRError on failure -- callers must catch this
    and skip the page gracefully rather than crashing."""
    try:
        import pytesseract
        from PIL import Image

        _configure_tesseract_cmd()
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image, lang=lang)
        return text or ""
    except Exception as exc:
        raise OCRError(str(exc)) from exc
