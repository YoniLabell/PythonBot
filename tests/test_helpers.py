"""בדיקות לעיבוד טקסט, לבדיקה ההיוריסטית ולפענוח תשובות המודל."""

from __future__ import annotations

import pytest

from app.ai import AIUnavailable, _parse_grade
from app.content import LESSONS_BY_ID
from app.handlers import (
    TELEGRAM_LIMIT,
    _chunks,
    _looks_like_code,
    _markdown_code_to_html,
    _strip_fences,
    heuristic_grade,
)


def test_short_text_is_not_split():
    assert _chunks("שלום") == ["שלום"]


def test_long_text_is_split_under_the_limit():
    text = "\n".join(f"שורה מספר {i}" for i in range(2000))
    parts = _chunks(text)
    assert len(parts) > 1
    assert all(len(part) <= TELEGRAM_LIMIT for part in parts)
    assert "".join(part.replace("\n", "") for part in parts) == text.replace("\n", "")


def test_text_without_newlines_is_still_split():
    parts = _chunks("א" * (TELEGRAM_LIMIT * 2 + 5))
    assert len(parts) == 3
    assert all(len(part) <= TELEGRAM_LIMIT for part in parts)


def test_strip_fences_removes_markdown_wrapper():
    assert _strip_fences("```python\nprint(1)\n```") == "print(1)"
    assert _strip_fences("```\nprint(1)\n```") == "print(1)"
    assert _strip_fences("print(1)") == "print(1)"


def test_looks_like_code_detects_multiline_snippets():
    assert _looks_like_code("for i in range(3):\n    print(i)")
    assert _looks_like_code("```print(1)```")
    assert not _looks_like_code("מה זה לולאה?")
    assert not _looks_like_code("איך עושים if בפייתון")


def test_markdown_is_converted_to_telegram_html():
    converted = _markdown_code_to_html(
        "הנה **דוגמה**:\n```python\nif 1 < 2:\n    print('כן')\n```\nוזה `int`"
    )
    assert "<b>דוגמה</b>" in converted
    assert "<pre><code>" in converted and "</code></pre>" in converted
    assert "1 &lt; 2" in converted  # סימני < בתוך קוד חייבים לברוח
    assert "<code>int</code>" in converted


def test_unclosed_code_fence_is_closed():
    assert _markdown_code_to_html("```\nprint(1)").endswith("</code></pre>")


def test_raw_html_from_the_model_is_escaped():
    assert "<script>" not in _markdown_code_to_html("<script>alert(1)</script>")


def test_heuristic_grade_accepts_the_reference_solution():
    lesson = LESSONS_BY_ID["02-variables"]
    assert heuristic_grade(lesson, lesson.exercise.solution).passed


def test_heuristic_grade_rejects_syntax_errors():
    lesson = LESSONS_BY_ID["02-variables"]
    grade = heuristic_grade(lesson, "price = 100\nprint(price")
    assert not grade.passed and "תחביר" in grade.feedback


def test_heuristic_grade_reports_missing_pieces():
    lesson = LESSONS_BY_ID["02-variables"]
    grade = heuristic_grade(lesson, "price = 100")
    assert not grade.passed and "discount" in grade.feedback


def test_parse_grade_reads_plain_json():
    grade = _parse_grade('{"passed": true, "feedback": "יפה"}')
    assert grade.passed and grade.feedback == "יפה"


def test_parse_grade_reads_json_inside_a_code_fence():
    grade = _parse_grade('```json\n{"passed": false, "feedback": "חסר return"}\n```')
    assert not grade.passed and grade.feedback == "חסר return"


def test_parse_grade_reads_json_with_surrounding_prose():
    grade = _parse_grade('בדקתי:\n{"passed": true, "feedback": "נכון"}\nבהצלחה')
    assert grade.passed


def test_parse_grade_raises_on_garbage():
    with pytest.raises(AIUnavailable):
        _parse_grade("אין לי מושג")
