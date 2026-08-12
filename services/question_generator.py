"""
services/question_generator.py

Generates Short / Long / Conceptual questions (with answers kept separate)
for a chapter, grounded in the retrieved textbook content.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from pydantic import ValidationError

from services.llm import chat_completion, LLMError
from services.mcq_generator import _build_content_block
from utils.helpers import extract_json_block
from utils.schemas import QAItem

SYSTEM_PROMPT = """You are a study-question writer for a student app.
Generate practice questions using ONLY the provided textbook content.

Return ONLY a JSON array (no markdown, no commentary) where each item has
exactly this shape:
{
  "question": "string",
  "answer": "a clear, complete model answer based on the content",
  "topic": "short topic tag",
  "chapter": "chapter label if known, else null",
  "page": page number as integer if known, else null
}
"""

TYPE_INSTRUCTIONS = {
    "Short Questions": "Write short-answer questions, each answerable in 1-3 sentences.",
    "Long Questions": "Write long-answer / essay-style questions that require a detailed, multi-paragraph answer.",
    "Conceptual Questions": "Write conceptual 'why/how' questions that test understanding of underlying concepts, not just recall.",
}


def generate_additional_questions(
    chunks: List[dict],
    question_type: str,
    num_questions: int,
    chapter_label: Optional[str] = None,
) -> Tuple[List[QAItem], List[str]]:
    warnings: List[str] = []
    if not chunks:
        return [], ["No textbook content was found for this chapter. Please re-check your selection."]

    content_block = _build_content_block(chunks)
    instruction = TYPE_INSTRUCTIONS.get(question_type, TYPE_INSTRUCTIONS["Short Questions"])

    user_prompt = (
        f"{instruction}\n"
        f"Number of questions requested: {num_questions}\n"
        f"Chapter: {chapter_label or 'Not specified'}\n\n"
        f"Textbook content:\n\n{content_block}"
    )

    try:
        raw = chat_completion(SYSTEM_PROMPT, user_prompt, temperature=0.4, max_tokens=3000)
    except LLMError as exc:
        return [], [str(exc)]

    parsed = extract_json_block(raw)
    if parsed is None:
        return [], ["The AI response could not be read as valid questions. Please try again."]

    items = parsed if isinstance(parsed, list) else parsed.get("questions", [])
    valid: List[QAItem] = []
    for raw_item in items:
        try:
            valid.append(QAItem(**raw_item))
        except (ValidationError, TypeError):
            continue

    if not valid:
        warnings.append("The AI could not generate valid questions from this content. Try a different chapter.")
    elif len(valid) < num_questions:
        warnings.append(f"Only {len(valid)} of {num_questions} requested questions could be reliably generated.")

    return valid[:num_questions], warnings
