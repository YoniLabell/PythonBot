"""בדיקות תקינות לתוכן הקורס."""

from __future__ import annotations

import re

import pytest

from app.content import LESSONS, LESSONS_BY_ID, find_lesson, lesson_index, next_lesson

ALLOWED_TAGS = {"b", "i", "u", "s", "code", "pre", "a"}
TAG_RE = re.compile(r"</?([a-zA-Z0-9]+)")


def _tags(text: str) -> set[str]:
    return {match.lower() for match in TAG_RE.findall(text)}


def test_lessons_exist_and_ids_are_unique():
    assert len(LESSONS) >= 10
    ids = [lesson.id for lesson in LESSONS]
    assert len(ids) == len(set(ids))
    assert len(LESSONS_BY_ID) == len(LESSONS)


@pytest.mark.parametrize("lesson", LESSONS, ids=lambda lesson: lesson.id)
def test_lesson_fields_are_filled(lesson):
    assert lesson.title and lesson.goal and lesson.body
    assert lesson.example.strip()
    assert lesson.exercise.prompt.strip()
    assert lesson.exercise.hint.strip()
    assert lesson.exercise.solution.strip()


@pytest.mark.parametrize("lesson", LESSONS, ids=lambda lesson: lesson.id)
def test_only_telegram_safe_html(lesson):
    """טלגרם תומך בתת-קבוצה קטנה של תגיות HTML בלבד."""
    for field in (lesson.body, lesson.goal, lesson.exercise.prompt):
        assert _tags(field) <= ALLOWED_TAGS, field
    for quiz in lesson.quizzes:
        assert _tags(quiz.question) <= ALLOWED_TAGS
        assert _tags(quiz.explanation) <= ALLOWED_TAGS


@pytest.mark.parametrize("lesson", LESSONS, ids=lambda lesson: lesson.id)
def test_examples_and_solutions_compile(lesson):
    compile(lesson.example, f"{lesson.id}-example", "exec")
    compile(lesson.exercise.solution, f"{lesson.id}-solution", "exec")


@pytest.mark.parametrize("lesson", LESSONS, ids=lambda lesson: lesson.id)
def test_quizzes_are_valid(lesson):
    assert lesson.quizzes, "לכל שיעור חייב להיות לפחות חידון אחד"
    for quiz in lesson.quizzes:
        assert len(quiz.options) >= 2
        assert 0 <= quiz.answer < len(quiz.options)
        assert quiz.explanation.strip()
        assert len(set(quiz.options)) == len(quiz.options)


@pytest.mark.parametrize("lesson", LESSONS, ids=lambda lesson: lesson.id)
def test_required_tokens_appear_in_reference_solution(lesson):
    normalized = lesson.exercise.solution.replace(" ", "")
    for token in lesson.exercise.required:
        assert token.replace(" ", "") in normalized, (lesson.id, token)


@pytest.mark.parametrize("lesson", LESSONS, ids=lambda lesson: lesson.id)
def test_callback_data_fits_telegram_limit(lesson):
    """callback_data מוגבל ל-64 בתים."""
    for quiz_index, quiz in enumerate(lesson.quizzes):
        for option_index in range(len(quiz.options)):
            data = f"answer:{lesson.id}:{quiz_index}:{option_index}"
            assert len(data.encode("utf-8")) <= 64, data


def test_navigation_helpers():
    assert lesson_index(LESSONS[0].id) == 0
    assert lesson_index("nope") == -1
    assert next_lesson(LESSONS[0].id) is LESSONS[1]
    assert next_lesson(LESSONS[-1].id) is None
    assert find_lesson(LESSONS[3].id) is LESSONS[3]
    assert find_lesson("nope") is None
