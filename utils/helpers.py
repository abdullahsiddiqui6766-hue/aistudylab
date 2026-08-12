"""
Small, dependency-free helper functions shared across services and UI pages.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Optional


def hash_bytes(data: bytes) -> str:
    """Stable content hash used to detect whether a PDF has already been
    processed in this session (avoids re-chunking/re-embedding on rerun)."""
    return hashlib.sha256(data).hexdigest()[:16]


def extract_json_block(raw_text: str) -> Optional[Any]:
    """
    LLMs sometimes wrap JSON in markdown fences or add stray commentary
    before/after the JSON. This strips fences and pulls out the first
    top-level JSON array or object it can find, then parses it.
    Returns None (never raises) if nothing parseable is found.
    """
    if not raw_text:
        return None

    text = raw_text.strip()

    # Strip ```json ... ``` or ``` ... ``` fences
    fence_match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    # Try a direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fall back to locating the first '[' or '{' and the matching last ']' / '}'
    for open_ch, close_ch in (("[", "]"), ("{", "}")):
        start = text.find(open_ch)
        end = text.rfind(close_ch)
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

    return None


def truncate(text: str, max_chars: int = 400) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "…"


def format_source(chapter: Optional[str], page: Optional[int]) -> str:
    """Builds a human-readable source string, only from real metadata.
    Never invents a chapter or page number."""
    parts = []
    if chapter:
        parts.append(f"Chapter: {chapter}")
    if page:
        parts.append(f"Page {page}")
    if not parts:
        return "Source not available in this textbook"
    return " · ".join(parts)


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(value, high))
