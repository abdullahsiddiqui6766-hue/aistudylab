"""
services/pdf_processor.py

Responsible for turning an uploaded PDF into a list of clean, metadata-tagged
text chunks ready for embedding:

    PDF bytes -> per-page text (+ OCR fallback for scanned pages) -> chapter map -> chunks

Extraction strategy per page:
1. Try normal PyMuPDF text extraction first (fast, exact).
2. If a page has little/no extractable text, render that page as an image
   and run it through Tesseract OCR (services/ocr.py) as a fallback.
3. Normal text and OCR text are combined into the same per-page pipeline, so
   downstream chunking/embeddings/RAG work identically either way.

Chapter detection is heuristic (regex heading patterns / font-size). It is
intentionally conservative: if we are not confident about a heading, we do
NOT invent a chapter label. Chunks without a detected chapter simply carry
chapter=None, and the UI/RAG layer must never fabricate one. Page numbers
always come from the PDF's real page index, whether the page's text came
from normal extraction or OCR -- so page references stay accurate either way.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional

import pymupdf as fitz  # PyMuPDF (the `fitz` import name is deprecated upstream)

from services import ocr

# A page with fewer real characters than this is treated as "no usable text"
# and becomes an OCR candidate, rather than being judged against the whole
# document at once -- this is what lets a partially-scanned book (some text
# pages, some scanned pages) work correctly.
PAGE_MIN_CHARS = 40

# Render DPI used when rasterizing a page for OCR. Higher = more accurate but
# slower; 200 is a reasonable balance for typical textbook scans.
OCR_RENDER_DPI = 200

ProgressCallback = Callable[[int, int, int], None]  # (done, total, page_number)


class PDFProcessingError(Exception):
    """Raised for any PDF problem that should be shown to the student as a
    clean message instead of a stack trace."""


@dataclass
class PageText:
    page_number: int  # 1-indexed
    text: str
    max_font_size: float = 0.0
    used_ocr: bool = False


@dataclass
class Chapter:
    title: str
    start_page: int


@dataclass
class Chunk:
    chunk_id: str
    text: str
    page: Optional[int]
    chapter: Optional[str]


@dataclass
class ProcessResult:
    chunks: List[Chunk]
    chapters: List[Chapter]
    page_count: int
    ocr_pages_used: int
    warnings: List[str] = field(default_factory=list)


CHAPTER_PATTERNS = [
    re.compile(r"^\s*chapter\s+\d+[:.\-]?\s*.*$", re.IGNORECASE),
    re.compile(r"^\s*unit\s+\d+[:.\-]?\s*.*$", re.IGNORECASE),
    re.compile(r"^\s*section\s+\d+[:.\-]?\s*.*$", re.IGNORECASE),
]


def load_pdf(file_bytes: bytes) -> "fitz.Document":
    if not file_bytes:
        raise PDFProcessingError("The uploaded file is empty.")
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:  # PyMuPDF raises generic exceptions
        raise PDFProcessingError(
            "This file could not be opened as a PDF. Please upload a valid PDF."
        ) from exc
    if doc.page_count == 0:
        raise PDFProcessingError("The PDF has no pages.")
    return doc


def extract_pages(
    doc: "fitz.Document",
    progress_callback: Optional[ProgressCallback] = None,
) -> tuple[List[PageText], List[str]]:
    """
    Extract text per page. Pages with little/no extractable text are
    automatically OCR'd as a fallback (no manual conversion needed).
    Returns (pages, warnings) -- warnings covers OCR being unavailable or
    failing on specific pages; those pages are skipped, not fatal.
    """
    pages: List[PageText] = []
    warnings: List[str] = []

    # Pass 1: fast normal extraction for every page.
    for i in range(doc.page_count):
        page = doc[i]
        text = page.get_text("text") or ""

        max_font = 0.0
        try:
            raw = page.get_text("dict")
            for block in raw.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        max_font = max(max_font, span.get("size", 0.0))
        except Exception:
            pass

        pages.append(PageText(page_number=i + 1, text=text, max_font_size=max_font))

    # Pass 2: OCR fallback, only for pages that didn't yield usable text.
    ocr_candidates = [i for i, p in enumerate(pages) if len(p.text.strip()) < PAGE_MIN_CHARS]

    if ocr_candidates:
        if not ocr.is_tesseract_available():
            warnings.append(
                "Some pages appear to be scanned/image-only, but the OCR "
                "engine (Tesseract) is not available in this environment, "
                "so those pages were skipped. See the README for OCR setup "
                "instructions."
            )
        else:
            total = len(ocr_candidates)
            for done, page_idx in enumerate(ocr_candidates, start=1):
                page_number = pages[page_idx].page_number
                if progress_callback:
                    try:
                        progress_callback(done, total, page_number)
                    except Exception:
                        pass  # progress reporting must never break OCR itself
                try:
                    pix = doc[page_idx].get_pixmap(dpi=OCR_RENDER_DPI)
                    image_bytes = pix.tobytes("png")
                    ocr_text = ocr.ocr_image_bytes(image_bytes)
                    if ocr_text.strip():
                        pages[page_idx].text = ocr_text
                        pages[page_idx].used_ocr = True
                except ocr.OCRError:
                    warnings.append(
                        f"OCR failed on page {page_number}; that page was skipped."
                    )
                except Exception:
                    warnings.append(
                        f"OCR failed on page {page_number}; that page was skipped."
                    )

    total_chars = sum(len(p.text.strip()) for p in pages)
    if total_chars < 20:
        raise PDFProcessingError(
            "No readable text could be extracted from this PDF, even after "
            "attempting OCR. The file may be corrupted, blank, or in a format "
            "OCR could not read. Please try a different PDF."
        )

    return pages, warnings


def detect_chapters(pages: List[PageText]) -> List[Chapter]:
    """
    Heuristic chapter detection:
    1. Look for lines matching common heading patterns ('Chapter 3: ...').
       This works on both normally-extracted and OCR'd text.
    2. As a fallback, look for short lines rendered in an unusually large
       font relative to the page's body text (only applies to
       normally-extracted pages, since OCR'd pages carry no font data).
    Returns an empty list if nothing reliable is found -- callers must treat
    that as 'no chapter metadata available' rather than guessing.
    """
    chapters: List[Chapter] = []
    seen_titles = set()

    for p in pages:
        lines = [l.strip() for l in p.text.splitlines() if l.strip()]
        for line in lines[:15]:  # headings usually appear near the top of a page
            if len(line) > 90:
                continue
            for pattern in CHAPTER_PATTERNS:
                if pattern.match(line):
                    title = re.sub(r"\s+", " ", line).strip()
                    key = title.lower()
                    if key not in seen_titles:
                        seen_titles.add(key)
                        chapters.append(Chapter(title=title, start_page=p.page_number))
                    break

    if chapters:
        return chapters

    # Fallback: large-font short lines (skips OCR'd pages, which have no font data)
    font_sizes = [p.max_font_size for p in pages if p.max_font_size > 0 and not p.used_ocr]
    if not font_sizes:
        return []
    body_font = sorted(font_sizes)[len(font_sizes) // 2]  # median as proxy for body text
    threshold = body_font * 1.35

    for p in pages:
        if p.used_ocr:
            continue
        if p.max_font_size >= threshold and p.max_font_size > 0:
            lines = [l.strip() for l in p.text.splitlines() if l.strip()]
            if lines:
                candidate = lines[0]
                if 3 <= len(candidate) <= 80:
                    key = candidate.lower()
                    if key not in seen_titles:
                        seen_titles.add(key)
                        chapters.append(Chapter(title=candidate, start_page=p.page_number))

    return chapters


def _chapter_for_page(page_number: int, chapters: List[Chapter]) -> Optional[str]:
    if not chapters:
        return None
    current = None
    for ch in chapters:
        if ch.start_page <= page_number:
            current = ch.title
        else:
            break
    return current


def chunk_pages(
    pages: List[PageText],
    chapters: List[Chapter],
    chunk_size: int = 900,
    overlap: int = 150,
) -> List[Chunk]:
    """Recursive-style splitting: split on paragraph -> sentence -> hard cut,
    while carrying page + chapter metadata for every chunk. Works identically
    whether a page's text came from normal extraction or OCR."""
    chunks: List[Chunk] = []
    counter = 0

    for p in pages:
        text = re.sub(r"[ \t]+", " ", p.text).strip()
        if not text:
            continue
        chapter = _chapter_for_page(p.page_number, chapters)

        start = 0
        n = len(text)
        while start < n:
            end = min(start + chunk_size, n)
            # try not to cut mid-sentence
            if end < n:
                boundary = text.rfind(". ", start, end)
                if boundary != -1 and boundary > start + int(chunk_size * 0.4):
                    end = boundary + 1
            piece = text[start:end].strip()
            if piece:
                counter += 1
                chunks.append(
                    Chunk(
                        chunk_id=f"c{counter}",
                        text=piece,
                        page=p.page_number,
                        chapter=chapter,
                    )
                )
            if end >= n:
                break
            start = max(end - overlap, start + 1)

    return chunks


def process_pdf(
    file_bytes: bytes,
    progress_callback: Optional[ProgressCallback] = None,
) -> ProcessResult:
    """Full pipeline entry point used by the UI layer.
    `progress_callback(done, total, page_number)` is called during the OCR
    fallback phase only (normal extraction is fast enough not to need one)."""
    doc = load_pdf(file_bytes)
    try:
        pages, warnings = extract_pages(doc, progress_callback=progress_callback)
        chapters = detect_chapters(pages)
        chunks = chunk_pages(pages, chapters)
        ocr_pages_used = sum(1 for p in pages if p.used_ocr)
        return ProcessResult(
            chunks=chunks,
            chapters=chapters,
            page_count=doc.page_count,
            ocr_pages_used=ocr_pages_used,
            warnings=warnings,
        )
    finally:
        doc.close()

