"""מקלדות inline של הבוט.

מבנה ה-callback_data: "<פעולה>:<מזהה שיעור>[:פרמטר]".
"""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.content import LESSONS, Lesson, lesson_index

CB_LESSON = "lesson"
CB_EXAMPLE = "example"
CB_EXERCISE = "exercise"
CB_SOLUTION = "solution"
CB_HINT = "hint"
CB_QUIZ = "quiz"
CB_ANSWER = "answer"
CB_NEXT = "next"
CB_MENU = "menu"
CB_NOOP = "noop"


def menu_keyboard(completed: set[str]) -> InlineKeyboardMarkup:
    """תפריט כל השיעורים, עם וי ליד מה שהושלם."""
    rows = []
    for index, lesson in enumerate(LESSONS, start=1):
        mark = "✅" if lesson.id in completed else "▫️"
        rows.append(
            [
                InlineKeyboardButton(
                    f"{mark} {index}. {lesson.display_title}",
                    callback_data=f"{CB_LESSON}:{lesson.id}",
                )
            ]
        )
    return InlineKeyboardMarkup(rows)


def lesson_keyboard(lesson: Lesson) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                "💡 דוגמת קוד", callback_data=f"{CB_EXAMPLE}:{lesson.id}"
            ),
            InlineKeyboardButton(
                "✏️ תרגיל", callback_data=f"{CB_EXERCISE}:{lesson.id}"
            ),
        ],
        [
            InlineKeyboardButton("🧠 חידון", callback_data=f"{CB_QUIZ}:{lesson.id}:0"),
        ],
    ]
    rows.append(_nav_row(lesson))
    return InlineKeyboardMarkup(rows)


def example_keyboard(lesson: Lesson) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✏️ לתרגיל", callback_data=f"{CB_EXERCISE}:{lesson.id}"
                ),
                InlineKeyboardButton(
                    "📖 חזרה לשיעור", callback_data=f"{CB_LESSON}:{lesson.id}"
                ),
            ],
            _nav_row(lesson),
        ]
    )


def exercise_keyboard(lesson: Lesson) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔦 רמז", callback_data=f"{CB_HINT}:{lesson.id}"),
                InlineKeyboardButton(
                    "🔑 פתרון", callback_data=f"{CB_SOLUTION}:{lesson.id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    "🧠 לחידון", callback_data=f"{CB_QUIZ}:{lesson.id}:0"
                ),
                InlineKeyboardButton(
                    "📖 חזרה לשיעור", callback_data=f"{CB_LESSON}:{lesson.id}"
                ),
            ],
        ]
    )


def quiz_keyboard(lesson: Lesson, quiz_index: int) -> InlineKeyboardMarkup:
    quiz = lesson.quizzes[quiz_index]
    rows = [
        [
            InlineKeyboardButton(
                f"{chr(ord('א') + option_index)}. {option}",
                callback_data=f"{CB_ANSWER}:{lesson.id}:{quiz_index}:{option_index}",
            )
        ]
        for option_index, option in enumerate(quiz.options)
    ]
    return InlineKeyboardMarkup(rows)


def after_quiz_keyboard(lesson: Lesson, quiz_index: int) -> InlineKeyboardMarkup:
    rows = []
    if quiz_index + 1 < len(lesson.quizzes):
        rows.append(
            [
                InlineKeyboardButton(
                    "➡️ שאלה הבאה",
                    callback_data=f"{CB_QUIZ}:{lesson.id}:{quiz_index + 1}",
                )
            ]
        )
    rows.append(_nav_row(lesson))
    return InlineKeyboardMarkup(rows)


def _nav_row(lesson: Lesson) -> list[InlineKeyboardButton]:
    row = [InlineKeyboardButton("📚 כל השיעורים", callback_data=f"{CB_MENU}:-")]
    if lesson_index(lesson.id) + 1 < len(LESSONS):
        row.append(
            InlineKeyboardButton("⏭ השיעור הבא", callback_data=f"{CB_NEXT}:{lesson.id}")
        )
    return row
