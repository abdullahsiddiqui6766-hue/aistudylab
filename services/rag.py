"""
services/rag.py

"Ask My Textbook" -- retrieval augmented generation over the uploaded PDF.

Design goals (from the spec):
 - Ground answers primarily in retrieved textbook passages.
 - Never invent chapter/page numbers.
 - Clearly say when the answer isn't in the textbook, instead of guessing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from services import vector_store
from services.llm import chat_completion, LLMError

# Chroma cosine "distance" -- lower is more similar. Above this, we treat the
# retrieved chunk as not relevant enough to trust.
MAX_RELEVANT_DISTANCE = 0.85

SYSTEM_PROMPT = """You are StudyAI, a strict textbook study assistant.
You must answer the student's question using ONLY the textbook excerpts
provided in the context below. Rules:

1. If the excerpts contain the answer, explain it clearly and simply, as a
   helpful tutor would, in your own words.
2. If the excerpts do NOT contain enough information to answer, you MUST say:
   "I couldn't find this in your uploaded textbook." Do not use outside
   knowledge to fill the gap, and do not guess.
3. Never state a chapter name or page number unless it is explicitly present
   in the context metadata given to you. If none is given, do not mention a
   source at all.
4. Keep answers focused and student-friendly. Use short paragraphs or bullet
   points where helpful.
"""


@dataclass
class RAGAnswer:
    answer: str
    sources: List[dict]
    found_in_textbook: bool


def _build_context_block(hits: List[dict]) -> str:
    lines = []
    for i, h in enumerate(hits, 1):
        meta_bits = []
        if h.get("chapter"):
            meta_bits.append(f"Chapter: {h['chapter']}")
        if h.get("page"):
            meta_bits.append(f"Page: {h['page']}")
        meta_str = f" ({', '.join(meta_bits)})" if meta_bits else ""
        lines.append(f"[Excerpt {i}{meta_str}]\n{h['text']}")
    return "\n\n".join(lines)


def ask_textbook(
    pdf_hash: str,
    question: str,
    top_k: int = 6,
    chapter_filter: Optional[str] = None,
) -> RAGAnswer:
    hits = vector_store.query(pdf_hash, question, top_k=top_k, chapter_filter=chapter_filter)

    relevant_hits = [
        h for h in hits if h.get("distance") is None or h["distance"] <= MAX_RELEVANT_DISTANCE
    ]

    if not relevant_hits:
        return RAGAnswer(
            answer="I couldn't find this in your uploaded textbook. Try rephrasing "
            "the question, or check that you've selected the right chapter.",
            sources=[],
            found_in_textbook=False,
        )

    context = _build_context_block(relevant_hits)
    user_prompt = f"Textbook excerpts:\n\n{context}\n\nStudent question: {question}"

    try:
        answer_text = chat_completion(SYSTEM_PROMPT, user_prompt, temperature=0.2, max_tokens=1200)
    except LLMError as exc:
        return RAGAnswer(answer=f"⚠️ {exc}", sources=[], found_in_textbook=False)

    not_found = "couldn't find this in your uploaded textbook" in answer_text.lower()

    sources = []
    seen = set()
    for h in relevant_hits:
        key = (h.get("chapter"), h.get("page"))
        if key in seen:
            continue
        seen.add(key)
        if h.get("chapter") or h.get("page"):
            sources.append({"chapter": h.get("chapter"), "page": h.get("page")})

    return RAGAnswer(answer=answer_text, sources=sources, found_in_textbook=not not_found)
