"""בדיקות זרימה: מריצות את ההנדלרים האמיתיים מול טלגרם מדומה."""

from __future__ import annotations

from html.parser import HTMLParser
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app import handlers
from app.ai import Tutor
from app.content import LESSONS
from app.storage import Storage

ALLOWED_TAGS = {"b", "i", "u", "s", "code", "pre", "a", "tg-spoiler", "blockquote"}
USER_ID = 42


class _TelegramHTMLValidator(HTMLParser):
    """מוודא שהתגיות מאוזנות ושכולן נתמכות בטלגרם."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.problems: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED_TAGS:
            self.problems.append(f"תגית לא נתמכת: {tag}")
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack.pop() != tag:
            self.problems.append(f"סגירה לא תואמת: {tag}")


def assert_valid_telegram_html(text: str) -> None:
    validator = _TelegramHTMLValidator()
    validator.feed(text)
    assert not validator.problems, (validator.problems, text[:200])
    assert not validator.stack, (validator.stack, text[:200])
    assert len(text) <= handlers.TELEGRAM_LIMIT


class FakeBot:
    def __init__(self) -> None:
        self.send_chat_action = AsyncMock()


class Recorder:
    """אוסף כל טקסט שהבוט שלח או ערך, ומאמת אותו."""

    def __init__(self) -> None:
        self.sent: list[str] = []

    async def reply_html(self, text, **kwargs):
        assert_valid_telegram_html(text)
        self.sent.append(text)

    async def edit_message_text(self, text, **kwargs):
        assert_valid_telegram_html(text)
        self.sent.append(text)

    @property
    def last(self) -> str:
        assert self.sent, "הבוט לא שלח שום הודעה"
        return self.sent[-1]


def make_update(recorder: Recorder, *, text: str = "", callback: str | None = None):
    message = SimpleNamespace(text=text, reply_html=recorder.reply_html)
    message.reply_text = AsyncMock()
    query = None
    if callback is not None:
        query = SimpleNamespace(
            data=callback,
            answer=AsyncMock(),
            edit_message_text=recorder.edit_message_text,
        )
    return SimpleNamespace(
        effective_message=message,
        effective_user=SimpleNamespace(id=USER_ID, first_name="דנה", username="dana"),
        effective_chat=SimpleNamespace(id=USER_ID),
        callback_query=query,
    )


@pytest.fixture
async def context(tmp_path):
    storage = Storage(tmp_path / "flow.sqlite3")
    await storage.init()
    application = SimpleNamespace(
        bot_data={
            "storage": storage,
            "tutor": Tutor(None),  # בלי מפתח - נתיב הבדיקה ההיוריסטית
            "enable_code_runner": True,
        }
    )
    return SimpleNamespace(
        application=application,
        bot_data=application.bot_data,
        user_data={},
        bot=FakeBot(),
        args=[],
    )


async def test_start_greets_and_lists_lessons(context):
    recorder = Recorder()
    await handlers.start(make_update(recorder), context)
    assert "דנה" in recorder.last
    assert "רצף למידה" in recorder.last


async def test_lesson_command_opens_the_requested_lesson(context):
    recorder = Recorder()
    context.args = ["3"]
    await handlers.lesson_command(make_update(recorder), context)
    assert LESSONS[2].title in recorder.last
    assert context.user_data[handlers.CURRENT_KEY] == LESSONS[2].id


async def test_lesson_command_rejects_out_of_range(context):
    recorder = Recorder()
    context.args = ["99"]
    await handlers.lesson_command(make_update(recorder), context)
    assert "יש שיעורים" in recorder.last


async def test_every_lesson_renders_through_the_callback_router(context):
    """המסלול המלא של כל שיעור: הסבר, דוגמה, תרגיל, רמז, פתרון וחידון."""
    recorder = Recorder()
    for lesson in LESSONS:
        for action in ("lesson", "example", "exercise", "hint", "solution"):
            await handlers.on_callback(
                make_update(recorder, callback=f"{action}:{lesson.id}"), context
            )
        for index in range(len(lesson.quizzes)):
            await handlers.on_callback(
                make_update(recorder, callback=f"quiz:{lesson.id}:{index}"), context
            )
    assert len(recorder.sent) > len(LESSONS) * 5


async def test_correct_quiz_answers_complete_the_lesson(context):
    recorder = Recorder()
    lesson = LESSONS[0]
    for index, quiz in enumerate(lesson.quizzes):
        await handlers.on_callback(
            make_update(recorder, callback=f"answer:{lesson.id}:{index}:{quiz.answer}"),
            context,
        )
    assert "נכון" in recorder.last
    storage = context.bot_data["storage"]
    assert lesson.id in await storage.completed_lessons(USER_ID)
    assert (await storage.stats(USER_ID)).quiz_correct == len(lesson.quizzes)


async def test_wrong_quiz_answer_explains_without_completing(context):
    recorder = Recorder()
    lesson = LESSONS[1]
    quiz = lesson.quizzes[0]
    wrong = (quiz.answer + 1) % len(quiz.options)
    await handlers.on_callback(
        make_update(recorder, callback=f"answer:{lesson.id}:0:{wrong}"), context
    )
    assert "לא מדויק" in recorder.last
    assert quiz.explanation.split("<")[0][:20] in recorder.last
    assert lesson.id not in await context.bot_data["storage"].completed_lessons(USER_ID)


async def test_exercise_submission_runs_and_passes(context):
    recorder = Recorder()
    lesson = next(l for l in LESSONS if l.exercise.expected_output == "75")
    await handlers.on_callback(
        make_update(recorder, callback=f"exercise:{lesson.id}"), context
    )
    assert context.user_data[handlers.AWAITING_KEY] == lesson.id

    await handlers.on_text(
        make_update(recorder, text=lesson.exercise.solution), context
    )
    assert "יפה מאוד" in recorder.last
    assert handlers.AWAITING_KEY not in context.user_data
    assert (await context.bot_data["storage"].stats(USER_ID)).exercises_passed == 1


async def test_wrong_output_keeps_the_exercise_open(context):
    recorder = Recorder()
    lesson = next(l for l in LESSONS if l.exercise.expected_output == "75")
    context.user_data[handlers.AWAITING_KEY] = lesson.id

    await handlers.on_text(make_update(recorder, text="print(1)"), context)
    assert "ציפיתי לפלט" in recorder.last
    assert context.user_data[handlers.AWAITING_KEY] == lesson.id


async def test_broken_code_is_reported_not_crashed(context):
    recorder = Recorder()
    lesson = LESSONS[1]
    context.user_data[handlers.AWAITING_KEY] = lesson.id

    await handlers.on_text(make_update(recorder, text="print(1/0)"), context)
    assert "לא רץ בהצלחה" in recorder.last
    assert "ZeroDivisionError" in recorder.last


async def test_markdown_fences_in_submissions_are_stripped(context):
    recorder = Recorder()
    lesson = next(l for l in LESSONS if l.exercise.expected_output == "75")
    context.user_data[handlers.AWAITING_KEY] = lesson.id

    fenced = f"```python\n{lesson.exercise.solution}```"
    await handlers.on_text(make_update(recorder, text=fenced), context)
    assert "יפה מאוד" in recorder.last


async def test_question_without_ai_explains_the_limitation(context):
    recorder = Recorder()
    await handlers.on_text(make_update(recorder, text="מה זה לולאה?"), context)
    assert "ANTHROPIC_API_KEY" in recorder.last


async def test_progress_reports_real_numbers(context):
    recorder = Recorder()
    storage = context.bot_data["storage"]
    await storage.touch_user(USER_ID)
    await storage.complete_lesson(USER_ID, LESSONS[0].id)
    await storage.record_quiz_answer(USER_ID, LESSONS[0].id, 0, True)

    await handlers.progress_command(make_update(recorder), context)
    assert f"1/{len(LESSONS)}" in recorder.last
    assert "1/1 נכון (100%)" in recorder.last


async def test_next_command_skips_completed_lessons(context):
    recorder = Recorder()
    await context.bot_data["storage"].complete_lesson(USER_ID, LESSONS[0].id)
    await handlers.next_command(make_update(recorder), context)
    assert LESSONS[1].title in recorder.last


async def test_reset_flow_clears_progress(context):
    recorder = Recorder()
    storage = context.bot_data["storage"]
    await storage.complete_lesson(USER_ID, LESSONS[0].id)

    await handlers.reset_command(make_update(recorder), context)
    assert "לאפס" in recorder.last

    await handlers.on_callback(make_update(recorder, callback="reset:yes"), context)
    assert "אופסה" in recorder.last
    assert await storage.completed_lessons(USER_ID) == set()


async def test_unknown_lesson_in_callback_is_handled(context):
    recorder = Recorder()
    await handlers.on_callback(make_update(recorder, callback="lesson:nope"), context)
    assert "לא מצאתי" in recorder.last


async def test_run_command_reports_output(context):
    recorder = Recorder()
    update = make_update(recorder, text="/run print(6 * 7)")
    await handlers.run_command(update, context)
    assert "42" in recorder.last


async def test_run_command_blocks_dangerous_code(context):
    recorder = Recorder()
    update = make_update(recorder, text="/run import os\nos.listdir('/')")
    await handlers.run_command(update, context)
    assert "חסום" in recorder.last
