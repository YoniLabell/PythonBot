"""בדיקות לשכבת האחסון."""

from __future__ import annotations

import pytest

from app.storage import Storage


@pytest.fixture
async def storage(tmp_path):
    store = Storage(tmp_path / "test.sqlite3")
    await store.init()
    return store


async def test_new_user_starts_with_streak_one(storage):
    assert await storage.touch_user(1, "דנה", "dana") == 1
    assert await storage.touch_user(1, "דנה", "dana") == 1


async def test_lesson_completion_is_idempotent(storage):
    await storage.touch_user(2)
    await storage.complete_lesson(2, "01-hello")
    await storage.complete_lesson(2, "01-hello")
    await storage.complete_lesson(2, "02-variables")

    assert await storage.completed_lessons(2) == {"01-hello", "02-variables"}
    assert (await storage.stats(2)).lessons_done == 2


async def test_quiz_stats_are_accumulated(storage):
    await storage.touch_user(3)
    await storage.record_quiz_answer(3, "01-hello", 0, True)
    await storage.record_quiz_answer(3, "01-hello", 1, False)
    await storage.record_quiz_answer(3, "02-variables", 0, True)

    stats = await storage.stats(3)
    assert stats.quiz_total == 3
    assert stats.quiz_correct == 2
    assert stats.quiz_accuracy == 67


async def test_exercise_pass_is_sticky(storage):
    await storage.touch_user(4)
    await storage.record_exercise(4, "05-conditions", False)
    await storage.record_exercise(4, "05-conditions", True)
    await storage.record_exercise(4, "05-conditions", False)

    assert (await storage.stats(4)).exercises_passed == 1


async def test_reset_clears_progress_only_for_that_user(storage):
    await storage.touch_user(5)
    await storage.touch_user(6)
    await storage.complete_lesson(5, "01-hello")
    await storage.complete_lesson(6, "01-hello")

    await storage.reset(5)

    assert await storage.completed_lessons(5) == set()
    assert await storage.completed_lessons(6) == {"01-hello"}


async def test_stats_for_unknown_user_are_empty(storage):
    stats = await storage.stats(999)
    assert stats.lessons_done == 0
    assert stats.quiz_accuracy == 0
    assert stats.streak == 0
