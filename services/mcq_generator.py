"""
services/mcq_generator.py

Generates chapter-grounded multiple-choice questions. The LLM is asked to
return a strict JSON array; every item is validated against MCQItem before
being trusted. Malformed items are silently dropped rather than crashing the
app, and the caller is told how many valid questions were actually produced.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from pydantic import ValidationError

from services.llm import chat_completion, LLMError
from utils.helpers import extract_json_block
from utils.schemas import MCQItem

SYSTEM_PROMPT = """You are an exam-question writer for a student study app.
Generate multiple-choice questions using ONLY the textbook content provided.
Do not use outside knowledge or invent facts not present in the content.

Return ONLY a JSON array (no markdown, no commentary) where each item has
exactly this shape:
{
  "question": "string",
  "options": ["string", "string", "string", "string"],
  "correct_answer": "must be the exact text of one of the 4 options",
  "explanation": "1-2 sentence explanation of why that answer is correct",
  "topic": "a short 2-4 word topic/concept tag for this question",
  "chapter": "chapter label if known, else null",
  "page": page number as an integer if known, else null
}
Return exactly the requested number of items if the content supports it.
"""


def _build_content_block(chunks: List[dict], max_chars: int = 6000) -> str:
    parts = []
    total = 0
    for c in chunks:
        piece = c["text"]
        if total + len(piece) > max_chars:
            break
        meta = []
        if c.get("chapter"):
            meta.append(f"Chapter: {c['chapter']}")
        if c.get("page"):
            meta.append(f"Page: {c['page']}")
        meta_str = f" ({', '.join(meta)})" if meta else ""
        parts.append(f"[Content{meta_str}]\n{piece}")
        total += len(piece)
    return "\n\n".join(parts)


def generate_mcqs(
    chunks: List[dict],
    num_mcqs: int,
    difficulty: str,
    chapter_label: Optional[str] = None,
) -> Tuple[List[MCQItem], List[str]]:
    """Returns (valid_items, warnings)."""
    warnings: List[str] = []

    if not chunks:
        return [], ["No textbook content was found for this chapter. Please re-check your selection."]

    content_block = _build_content_block(chunks)
    user_prompt = (
        f"Difficulty level: {difficulty}\n"
        f"Number of questions requested: {num_mcqs}\n"
        f"Chapter: {chapter_label or 'Not specified'}\n\n"
        f"Textbook content:\n\n{content_block}"
    )

    try:
        raw = chat_completion(
            SYSTEM_PROMPT, user_prompt, temperature=0.4, max_tokens=3000, json_mode=False
        )
    except LLMError as exc:
        return [], [str(exc)]

    parsed = extract_json_block(raw)
    if parsed is None:
        return [], ["The AI response could not be read as valid questions. Please try again."]

    items = parsed if isinstance(parsed, list) else parsed.get("questions", [])
    valid: List[MCQItem] = []
    for raw_item in items:
        try:
            valid.append(MCQItem(**raw_item))
        except (ValidationError, TypeError):
            continue

    if not valid:
        warnings.append("The AI could not generate valid questions from this content. Try a different chapter or fewer questions.")
    elif len(valid) < num_mcqs:
        warnings.append(f"Only {len(valid)} of {num_mcqs} requested questions could be reliably generated.")

    return valid[:num_mcqs], warnings
