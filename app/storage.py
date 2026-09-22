"""שמירת התקדמות משתמשים ב-SQLite.

כל הגישות ל-DB רצות ב-thread נפרד (``asyncio.to_thread``) כדי לא לחסום את
לולאת האירועים של הבוט.
"""

from __future__ import annotations

import asyncio
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,
    first_name  TEXT,
    username    TEXT,
    created_at  TEXT NOT NULL,
    last_seen   TEXT NOT NULL,
    streak      INTEGER NOT NULL DEFAULT 0,
    last_active_day TEXT
);

CREATE TABLE IF NOT EXISTS lesson_progress (
    user_id      INTEGER NOT NULL,
    lesson_id    TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    PRIMARY KEY (user_id, lesson_id)
);

CREATE TABLE IF NOT EXISTS quiz_answers (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    lesson_id  TEXT NOT NULL,
    quiz_index INTEGER NOT NULL,
    correct    INTEGER NOT NULL,
    answered_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_quiz_answers_user ON quiz_answers(user_id);

CREATE TABLE IF NOT EXISTS exercise_results (
    user_id     INTEGER NOT NULL,
    lesson_id   TEXT NOT NULL,
    passed      INTEGER NOT NULL,
    attempts    INTEGER NOT NULL DEFAULT 1,
    updated_at  TEXT NOT NULL,
    PRIMARY KEY (user_id, lesson_id)
);
"""


@dataclass(frozen=True)
class Stats:
    lessons_done: int
    quiz_total: int
    quiz_correct: int
    exercises_passed: int
    streak: int

    @property
    def quiz_accuracy(self) -> int:
        if self.quiz_total == 0:
            return 0
        return round(100 * self.quiz_correct / self.quiz_total)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Storage:
    """עטיפה דקה מעל SQLite עם API אסינכרוני."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------ setup
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_sync(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    async def init(self) -> None:
        await asyncio.to_thread(self._init_sync)

    # ------------------------------------------------------------------ users
    def _touch_user_sync(
        self, user_id: int, first_name: str | None, username: str | None
    ) -> int:
        now = _utcnow()
        today = date.today().isoformat()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT streak, last_active_day FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()

            if row is None:
                conn.execute(
                    "INSERT INTO users (user_id, first_name, username, created_at,"
                    " last_seen, streak, last_active_day) VALUES (?,?,?,?,?,?,?)",
                    (user_id, first_name, username, now, now, 1, today),
                )
                return 1

            streak = int(row["streak"] or 0)
            last_day = row["last_active_day"]
            if last_day != today:
                if last_day:
                    gap = (date.today() - date.fromisoformat(last_day)).days
                    streak = streak + 1 if gap == 1 else 1
                else:
                    streak = 1
            streak = max(streak, 1)

            conn.execute(
                "UPDATE users SET first_name = ?, username = ?, last_seen = ?,"
                " streak = ?, last_active_day = ? WHERE user_id = ?",
                (first_name, username, now, streak, today, user_id),
            )
            return streak

    async def touch_user(
        self, user_id: int, first_name: str | None = None, username: str | None = None
    ) -> int:
        """מעדכן פעילות אחרונה ומחזיר את אורך הרצף היומי."""
        async with self._lock:
            return await asyncio.to_thread(
                self._touch_user_sync, user_id, first_name, username
            )

    # --------------------------------------------------------------- progress
    def _complete_lesson_sync(self, user_id: int, lesson_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO lesson_progress (user_id, lesson_id,"
                " completed_at) VALUES (?,?,?)",
                (user_id, lesson_id, _utcnow()),
            )

    async def complete_lesson(self, user_id: int, lesson_id: str) -> None:
        async with self._lock:
            await asyncio.to_thread(self._complete_lesson_sync, user_id, lesson_id)

    def _completed_lessons_sync(self, user_id: int) -> set[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT lesson_id FROM lesson_progress WHERE user_id = ?", (user_id,)
            ).fetchall()
        return {row["lesson_id"] for row in rows}

    async def completed_lessons(self, user_id: int) -> set[str]:
        async with self._lock:
            return await asyncio.to_thread(self._completed_lessons_sync, user_id)

    # ------------------------------------------------------------------- quiz
    def _record_quiz_sync(
        self, user_id: int, lesson_id: str, quiz_index: int, correct: bool
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO quiz_answers (user_id, lesson_id, quiz_index, correct,"
                " answered_at) VALUES (?,?,?,?,?)",
                (user_id, lesson_id, quiz_index, int(correct), _utcnow()),
            )

    async def record_quiz_answer(
        self, user_id: int, lesson_id: str, quiz_index: int, correct: bool
    ) -> None:
        async with self._lock:
            await asyncio.to_thread(
                self._record_quiz_sync, user_id, lesson_id, quiz_index, correct
            )

    # --------------------------------------------------------------- exercise
    def _record_exercise_sync(self, user_id: int, lesson_id: str, passed: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO exercise_results (user_id, lesson_id, passed, attempts,"
                " updated_at) VALUES (?,?,?,1,?)"
                " ON CONFLICT(user_id, lesson_id) DO UPDATE SET"
                " passed = MAX(passed, excluded.passed),"
                " attempts = attempts + 1,"
                " updated_at = excluded.updated_at",
                (user_id, lesson_id, int(passed), _utcnow()),
            )

    async def record_exercise(self, user_id: int, lesson_id: str, passed: bool) -> None:
        async with self._lock:
            await asyncio.to_thread(
                self._record_exercise_sync, user_id, lesson_id, passed
            )

    # ------------------------------------------------------------------ stats
    def _stats_sync(self, user_id: int) -> Stats:
        with self._connect() as conn:
            lessons = conn.execute(
                "SELECT COUNT(*) AS c FROM lesson_progress WHERE user_id = ?",
                (user_id,),
            ).fetchone()["c"]
            quiz = conn.execute(
                "SELECT COUNT(*) AS total, COALESCE(SUM(correct), 0) AS correct"
                " FROM quiz_answers WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            exercises = conn.execute(
                "SELECT COUNT(*) AS c FROM exercise_results"
                " WHERE user_id = ? AND passed = 1",
                (user_id,),
            ).fetchone()["c"]
            user = conn.execute(
                "SELECT streak FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()

        return Stats(
            lessons_done=int(lessons),
            quiz_total=int(quiz["total"]),
            quiz_correct=int(quiz["correct"]),
            exercises_passed=int(exercises),
            streak=int(user["streak"]) if user else 0,
        )

    async def stats(self, user_id: int) -> Stats:
        async with self._lock:
            return await asyncio.to_thread(self._stats_sync, user_id)

    # ------------------------------------------------------------------ reset
    def _reset_sync(self, user_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM lesson_progress WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM quiz_answers WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM exercise_results WHERE user_id = ?", (user_id,))
            conn.execute(
                "UPDATE users SET streak = 1, last_active_day = ? WHERE user_id = ?",
                (date.today().isoformat(), user_id),
            )

    async def reset(self, user_id: int) -> None:
        async with self._lock:
            await asyncio.to_thread(self._reset_sync, user_id)
