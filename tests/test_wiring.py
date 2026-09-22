"""בדיקות חיווט: שהאפליקציה נבנית ושכל כפתור מוביל לפעולה מוכרת."""

from __future__ import annotations

from pathlib import Path

import pytest
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler

import main
from app.config import Config
from app.content import LESSONS
from app import keyboards as kb

FAKE_TOKEN = "123456789:AAExampleTokenForTestsOnly_0000000000000"

KNOWN_ACTIONS = {
    kb.CB_LESSON,
    kb.CB_EXAMPLE,
    kb.CB_EXERCISE,
    kb.CB_SOLUTION,
    kb.CB_HINT,
    kb.CB_QUIZ,
    kb.CB_ANSWER,
    kb.CB_NEXT,
    kb.CB_MENU,
    "reset",
}


@pytest.fixture
def config(tmp_path: Path) -> Config:
    return Config(
        telegram_token=FAKE_TOKEN,
        anthropic_api_key=None,
        claude_model="claude-opus-5",
        webhook_url=None,
        webhook_secret=None,
        port=10000,
        data_dir=tmp_path,
        enable_code_runner=False,
    )


def _all_callback_data() -> list[str]:
    data: list[str] = ["reset:yes", "reset:no"]
    for lesson in LESSONS:
        markups = [
            kb.lesson_keyboard(lesson),
            kb.example_keyboard(lesson),
            kb.exercise_keyboard(lesson),
            kb.menu_keyboard({lesson.id}),
        ]
        for index in range(len(lesson.quizzes)):
            markups.append(kb.quiz_keyboard(lesson, index))
            markups.append(kb.after_quiz_keyboard(lesson, index))
        for markup in markups:
            for row in markup.inline_keyboard:
                for button in row:
                    if button.callback_data:
                        data.append(button.callback_data)
    return data


def test_application_builds_with_all_handlers(config):
    application = main.build_application(config)
    handlers = application.handlers[0]

    assert any(isinstance(handler, CallbackQueryHandler) for handler in handlers)
    assert any(isinstance(handler, MessageHandler) for handler in handlers)

    commands = {
        name
        for handler in handlers
        if isinstance(handler, CommandHandler)
        for name in handler.commands
    }
    assert {
        "start", "help", "lessons", "lesson", "next", "quiz",
        "practice", "progress", "ask", "run", "cancel", "reset",
    } <= commands

    assert application.bot_data["enable_code_runner"] is False
    assert application.bot_data["tutor"].enabled is False


def test_menu_commands_are_registered_handlers(config):
    application = main.build_application(config)
    registered = {
        name
        for handler in application.handlers[0]
        if isinstance(handler, CommandHandler)
        for name in handler.commands
    }
    for command in main.COMMANDS:
        assert command.command in registered


def test_every_button_maps_to_a_known_action():
    for data in _all_callback_data():
        action = data.split(":")[0]
        assert action in KNOWN_ACTIONS, data


def test_callback_data_stays_within_telegram_limit():
    for data in _all_callback_data():
        assert len(data.encode("utf-8")) <= 64, data


def test_quiz_buttons_cover_every_option():
    lesson = LESSONS[0]
    markup = kb.quiz_keyboard(lesson, 0)
    assert len(markup.inline_keyboard) == len(lesson.quizzes[0].options)


def test_last_lesson_has_no_next_button():
    markup = kb.lesson_keyboard(LESSONS[-1])
    data = [
        button.callback_data
        for row in markup.inline_keyboard
        for button in row
    ]
    assert not any(item.startswith(f"{kb.CB_NEXT}:") for item in data)
