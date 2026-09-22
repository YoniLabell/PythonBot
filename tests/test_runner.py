"""בדיקות למריץ הקוד המוגבל ולבדיקת הפתרונות לדוגמה."""

from __future__ import annotations

import pytest

from app.content import LESSONS
from app.runner import check_code, run_code

SOLUTIONS_WITH_OUTPUT = [
    lesson
    for lesson in LESSONS
    if lesson.exercise.expected_output is not None
    and "input(" not in lesson.exercise.solution
]


@pytest.mark.parametrize(
    "lesson", SOLUTIONS_WITH_OUTPUT, ids=lambda lesson: lesson.id
)
async def test_reference_solution_produces_expected_output(lesson):
    result = await run_code(lesson.exercise.solution)
    assert result.ok, result.combined
    assert result.output.strip() == lesson.exercise.expected_output.strip()


def test_blocks_dangerous_imports():
    assert check_code("import os") is not None
    assert check_code("from subprocess import run") is not None
    assert check_code("open('/etc/passwd')") is not None
    assert check_code("print('hi')") is None


def test_reports_syntax_errors_before_running():
    problem = check_code("print('hi'")
    assert problem is not None and "תחביר" in problem


async def test_runaway_loop_is_stopped():
    result = await run_code("while True:\n    pass")
    assert not result.ok
    assert "מגבלות" in result.error or "זמן" in result.error


async def test_runtime_error_is_reported_briefly():
    result = await run_code("print(1 / 0)")
    assert not result.ok
    assert "ZeroDivisionError" in result.error
    assert result.error.count("\n") == 0
