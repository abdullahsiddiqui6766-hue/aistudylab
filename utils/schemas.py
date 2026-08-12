"""
Pydantic models used to validate structured (JSON) output coming back from the
Groq LLM. Every place in the app that asks the LLM for MCQs, short/long
questions, or topic tags runs the raw JSON through one of these models first.
If a model fails validation it is simply dropped (never crashes the app) and
the caller decides how to react (retry / show a warning to the student).
"""

from typing import List, Optional
from pydantic import BaseModel, field_validator


class MCQItem(BaseModel):
    question: str
    options: List[str]
    correct_answer: str
    explanation: str
    topic: Optional[str] = None
    chapter: Optional[str] = None
    page: Optional[int] = None

    @field_validator("options")
    @classmethod
    def must_have_four_options(cls, v: List[str]) -> List[str]:
        if len(v) != 4:
            raise ValueError("MCQ must have exactly 4 options")
        return v

    @field_validator("correct_answer")
    @classmethod
    def correct_answer_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("correct_answer cannot be empty")
        return v.strip()

    def normalized_correct_answer(self) -> str:
        """
        Some models return the correct answer as 'A' / 'B' / '1' / '2' instead
        of the literal option text. This resolves it back to the exact option
        string so the UI can compare selections reliably.
        """
        raw = self.correct_answer.strip()
        letter_map = {"A": 0, "B": 1, "C": 2, "D": 3}
        if raw.upper() in letter_map:
            idx = letter_map[raw.upper()]
            if idx < len(self.options):
                return self.options[idx]
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(self.options):
                return self.options[idx]
        # Fall back to matching against option text (case-insensitive)
        for opt in self.options:
            if opt.strip().lower() == raw.lower():
                return opt
        return raw


class QAItem(BaseModel):
    question: str
    answer: str
    topic: Optional[str] = None
    chapter: Optional[str] = None
    page: Optional[int] = None


class ChunkMeta(BaseModel):
    chapter: Optional[str] = None
    page: Optional[int] = None
    chunk_id: str
