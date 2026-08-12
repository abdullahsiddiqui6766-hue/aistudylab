"""
services/test_engine.py

Builds a full multi-chapter test out of chapter-grounded MCQs, and scores it
once the student submits their answers. Weak topics are identified by
grouping incorrectly-answered questions by their `topic` tag (falling back
to chapter if no topic was produced).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from services import vector_store
from services.mcq_generator import generate_mcqs
from utils.schemas import MCQItem


@dataclass
class TestResult:
    score: int
    total: int
    percentage: float
    review: List[dict]  # per-question breakdown
    weak_topics: List[str]


def build_test(
    pdf_hash: str,
    chapters: List[str],
    num_questions: int,
    difficulty: str,
) -> tuple[List[MCQItem], List[str]]:
    """Distributes num_questions roughly evenly across the selected chapters."""
    if not chapters:
        return [], ["Please select at least one chapter."]

    per_chapter = max(1, num_questions // len(chapters))
    remainder = num_questions - per_chapter * len(chapters)

    all_items: List[MCQItem] = []
    warnings: List[str] = []

    for i, chapter in enumerate(chapters):
        count = per_chapter + (1 if i < remainder else 0)
        if count <= 0:
            continue
        chunks = vector_store.get_all_chunks_for_chapter(pdf_hash, chapter, limit=40)
        items, warns = generate_mcqs(chunks, count, difficulty, chapter_label=chapter)
        all_items.extend(items)
        warnings.extend(warns)

    if not all_items:
        warnings.append("No questions could be generated for the selected chapters.")

    return all_items[:num_questions], warnings


def score_test(questions: List[MCQItem], user_answers: Dict[int, str]) -> TestResult:
    review = []
    correct_count = 0
    weak_topic_counter: Counter = Counter()

    for idx, q in enumerate(questions):
        correct_answer = q.normalized_correct_answer()
        selected = user_answers.get(idx)
        is_correct = selected is not None and selected.strip() == correct_answer.strip()

        if is_correct:
            correct_count += 1
        else:
            topic_label = q.topic or q.chapter or "General"
            weak_topic_counter[topic_label] += 1

        review.append(
            {
                "question": q.question,
                "options": q.options,
                "selected": selected,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "explanation": q.explanation,
                "chapter": q.chapter,
                "page": q.page,
                "topic": q.topic,
            }
        )

    total = len(questions)
    percentage = round((correct_count / total) * 100, 1) if total else 0.0
    weak_topics = [topic for topic, _ in weak_topic_counter.most_common(5)]

    return TestResult(
        score=correct_count,
        total=total,
        percentage=percentage,
        review=review,
        weak_topics=weak_topics,
    )
