"""הפקודות, הכפתורים וזרימת השיחה של הבוט."""

from __future__ import annotations

import html
import logging
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app import keyboards as kb
from app.ai import AIUnavailable, Grade, Tutor
from app.content import LESSONS, Lesson, find_lesson, lesson_index, next_lesson
from app.runner import run_code
from app.storage import Storage

logger = logging.getLogger(__name__)

TELEGRAM_LIMIT = 3900  # מתחת למגבלת 4096 של טלגרם, עם מרווח ביטחון
AWAITING_KEY = "awaiting_exercise"
CURRENT_KEY = "current_lesson"


# --------------------------------------------------------------------- utils
def _storage(context: ContextTypes.DEFAULT_TYPE) -> Storage:
    return context.application.bot_data["storage"]


def _tutor(context: ContextTypes.DEFAULT_TYPE) -> Tutor:
    return context.application.bot_data["tutor"]


def _code_runner_enabled(context: ContextTypes.DEFAULT_TYPE) -> bool:
    return bool(context.application.bot_data.get("enable_code_runner"))


def _code_block(code: str) -> str:
    return f"<pre><code>{html.escape(code)}</code></pre>"


def _chunks(text: str, limit: int = TELEGRAM_LIMIT) -> list[str]:
    """מפצל טקסט ארוך להודעות, עדיף בגבול שורה."""
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    remaining = text
    while len(remaining) > limit:
        cut = remaining.rfind("\n", 0, limit)
        if cut <= 0:
            cut = limit
        parts.append(remaining[:cut])
        remaining = remaining[cut:].lstrip("\n")
    if remaining:
        parts.append(remaining)
    return parts


async def _reply(update: Update, text: str, **kwargs) -> None:
    """שולח הודעה, ומפצל אותה אם היא ארוכה מדי."""
    message = update.effective_message
    if message is None:
        return
    parts = _chunks(text)
    for index, part in enumerate(parts):
        is_last = index == len(parts) - 1
        await message.reply_html(part, **(kwargs if is_last else {}))


async def _edit_or_send(update: Update, text: str, **kwargs) -> None:
    """מעדכן את ההודעה של הכפתור, ואם אי אפשר - שולח חדשה."""
    query = update.callback_query
    parts = _chunks(text)
    if query is not None and len(parts) == 1:
        try:
            await query.edit_message_text(
                text, parse_mode=ParseMode.HTML, **kwargs
            )
            return
        except BadRequest as exc:
            if "not modified" in str(exc).lower():
                return
            logger.debug("עריכת ההודעה נכשלה, שולח חדשה: %s", exc)
    await _reply(update, text, **kwargs)


async def _track(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    if user is None:
        return 0
    return await _storage(context).touch_user(user.id, user.first_name, user.username)


# ------------------------------------------------------------------ rendering
def _lesson_text(lesson: Lesson) -> str:
    position = lesson_index(lesson.id) + 1
    return (
        f"<b>{lesson.display_title}</b>  <i>({position}/{len(LESSONS)})</i>\n"
        f"🎯 {lesson.goal}\n\n"
        f"{lesson.body}"
    )


def _example_text(lesson: Lesson) -> str:
    return (
        f"<b>💡 דוגמה - {lesson.title}</b>\n\n"
        f"{_code_block(lesson.example)}\n"
        "נסו להעתיק את הקוד ולשנות אותו. ככה לומדים הכי מהר."
    )


def _exercise_text(lesson: Lesson, can_run: bool) -> str:
    tail = (
        "שלחו לי את הקוד שלכם בהודעה רגילה ואבדוק אותו."
        if not can_run
        else "שלחו לי את הקוד שלכם בהודעה רגילה - אריץ אותו ואבדוק את התוצאה."
    )
    return (
        f"<b>✏️ תרגיל - {lesson.title}</b>\n\n"
        f"{lesson.exercise.prompt}\n\n"
        f"{tail}"
    )


def _quiz_text(lesson: Lesson, quiz_index: int) -> str:
    quiz = lesson.quizzes[quiz_index]
    return (
        f"<b>🧠 חידון - {lesson.title}</b>\n"
        f"<i>שאלה {quiz_index + 1} מתוך {len(lesson.quizzes)}</i>\n\n"
        f"{quiz.question}"
    )


# ------------------------------------------------------------------- commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    streak = await _track(update, context)
    user = update.effective_user
    name = html.escape(user.first_name or "חבר") if user else "חבר"
    completed = await _storage(context).completed_lessons(user.id) if user else set()

    text = (
        f"שלום {name}! 🐍\n\n"
        "אני בוט שמלמד <b>Python מאפס</b>. יש כאן "
        f"{len(LESSONS)} שיעורים קצרים, ובכל אחד הסבר, דוגמת קוד, תרגיל וחידון.\n\n"
        "<b>איך מתחילים:</b>\n"
        "• /lessons - תפריט כל השיעורים\n"
        "• /next - להמשיך מאיפה שהפסקתם\n"
        "• /ask שאלה - לשאול אותי כל דבר על Python\n"
        "• /progress - לראות את ההתקדמות\n"
        "• /help - כל הפקודות\n\n"
        f"🔥 רצף למידה: {streak} ימים"
    )
    await _reply(update, text, reply_markup=kb.menu_keyboard(completed))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _track(update, context)
    ai_line = (
        "• /ask &lt;שאלה&gt; - שאלה חופשית על Python\n"
        if _tutor(context).enabled
        else "• /ask - כבוי כרגע (דורש מפתח ANTHROPIC_API_KEY)\n"
    )
    run_line = (
        "• /run &lt;קוד&gt; - הרצת קוד ובדיקת הפלט\n"
        if _code_runner_enabled(context)
        else ""
    )
    await _reply(
        update,
        "<b>הפקודות שלי</b>\n\n"
        "• /lessons - תפריט השיעורים\n"
        "• /lesson &lt;מספר&gt; - מעבר ישיר לשיעור, למשל <code>/lesson 5</code>\n"
        "• /next - השיעור הבא שלא השלמתם\n"
        "• /quiz - חידון על השיעור הנוכחי\n"
        "• /practice - התרגיל של השיעור הנוכחי\n"
        f"{ai_line}"
        f"{run_line}"
        "• /progress - סטטיסטיקות והתקדמות\n"
        "• /cancel - ביטול תרגיל פתוח\n"
        "• /reset - איפוס כל ההתקדמות\n\n"
        "טיפ: אפשר פשוט לשלוח לי שאלה בהודעה רגילה.",
    )


async def lessons_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _track(update, context)
    user = update.effective_user
    completed = await _storage(context).completed_lessons(user.id) if user else set()
    await _reply(
        update,
        f"<b>📚 תוכנית הלימודים</b>\n\nהושלמו {len(completed)} מתוך {len(LESSONS)} שיעורים.\nבחרו שיעור:",
        reply_markup=kb.menu_keyboard(completed),
    )


async def lesson_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _track(update, context)
    if not context.args:
        await lessons_menu(update, context)
        return

    raw = context.args[0].strip()
    if not raw.isdigit():
        await _reply(update, "צריך מספר שיעור, למשל <code>/lesson 3</code>.")
        return

    number = int(raw)
    if not 1 <= number <= len(LESSONS):
        await _reply(update, f"יש שיעורים מ-1 עד {len(LESSONS)}.")
        return

    await _show_lesson(update, context, LESSONS[number - 1])


async def next_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _track(update, context)
    user = update.effective_user
    completed = await _storage(context).completed_lessons(user.id) if user else set()

    target = next((lesson for lesson in LESSONS if lesson.id not in completed), None)
    if target is None:
        await _reply(
            update,
            "🎉 סיימתם את כל השיעורים! אפשר לחזור על שיעור מ-/lessons "
            "או לשאול אותי שאלות עם /ask.",
        )
        return
    await _show_lesson(update, context, target)


async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _track(update, context)
    lesson = _current_lesson(context)
    if lesson is None:
        await _reply(update, "קודם בחרו שיעור דרך /lessons.")
        return
    await _show_quiz(update, context, lesson, 0)


async def practice_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _track(update, context)
    lesson = _current_lesson(context)
    if lesson is None:
        await _reply(update, "קודם בחרו שיעור דרך /lessons.")
        return
    await _show_exercise(update, context, lesson)


async def progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _track(update, context)
    user = update.effective_user
    if user is None:
        return

    storage = _storage(context)
    stats = await storage.stats(user.id)
    completed = await storage.completed_lessons(user.id)

    done = len(completed)
    total = len(LESSONS)
    filled = round(10 * done / total) if total else 0
    bar = "▓" * filled + "░" * (10 - filled)

    lines = [
        "<b>📊 ההתקדמות שלך</b>\n",
        f"{bar}  {done}/{total} שיעורים",
        f"🧠 חידונים: {stats.quiz_correct}/{stats.quiz_total} נכון ({stats.quiz_accuracy}%)",
        f"✏️ תרגילים שנפתרו: {stats.exercises_passed}",
        f"🔥 רצף: {stats.streak} ימים",
    ]

    upcoming = next((lesson for lesson in LESSONS if lesson.id not in completed), None)
    if upcoming:
        lines.append(f"\nהבא בתור: {upcoming.display_title} (/next)")
    else:
        lines.append("\nסיימתם את כל התוכנית! 🎉")

    await _reply(update, "\n".join(lines))


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _track(update, context)
    question = " ".join(context.args).strip() if context.args else ""
    if not question:
        await _reply(
            update,
            "כתבו את השאלה אחרי הפקודה, למשל:\n"
            "<code>/ask מה ההבדל בין רשימה למילון?</code>",
        )
        return
    await _answer_question(update, context, question)


async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _track(update, context)
    if not _code_runner_enabled(context):
        await _reply(
            update,
            "הרצת קוד כבויה בשרת הזה. אפשר להפעיל אותה עם "
            "<code>ENABLE_CODE_RUNNER=true</code> (ראו README).",
        )
        return

    code = update.effective_message.text.partition(" ")[2].strip()
    code = _strip_fences(code)
    if not code:
        await _reply(
            update,
            "שלחו קוד אחרי הפקודה, למשל:\n<code>/run print(2 + 2)</code>",
        )
        return
    await _run_and_report(update, code)


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.pop(AWAITING_KEY, None):
        await _reply(update, "ביטלתי את התרגיל. אפשר להמשיך עם /next או /lessons.")
    else:
        await _reply(update, "אין תרגיל פתוח כרגע.")


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _track(update, context)
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("כן, אפס הכול", callback_data="reset:yes"),
                InlineKeyboardButton("לא, בטל", callback_data="reset:no"),
            ]
        ]
    )
    await _reply(
        update,
        "לאפס את כל ההתקדמות, הציונים והרצף? אי אפשר לבטל את הפעולה.",
        reply_markup=keyboard,
    )


# -------------------------------------------------------------------- display
def _current_lesson(context: ContextTypes.DEFAULT_TYPE) -> Lesson | None:
    lesson_id = context.user_data.get(CURRENT_KEY)
    return find_lesson(lesson_id) if lesson_id else None


async def _show_lesson(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lesson: Lesson
) -> None:
    context.user_data[CURRENT_KEY] = lesson.id
    context.user_data.pop(AWAITING_KEY, None)
    await _edit_or_send(
        update, _lesson_text(lesson), reply_markup=kb.lesson_keyboard(lesson)
    )


async def _show_example(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lesson: Lesson
) -> None:
    context.user_data[CURRENT_KEY] = lesson.id
    await _edit_or_send(
        update, _example_text(lesson), reply_markup=kb.example_keyboard(lesson)
    )


async def _show_exercise(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lesson: Lesson
) -> None:
    context.user_data[CURRENT_KEY] = lesson.id
    context.user_data[AWAITING_KEY] = lesson.id
    await _edit_or_send(
        update,
        _exercise_text(lesson, _code_runner_enabled(context)),
        reply_markup=kb.exercise_keyboard(lesson),
    )


async def _show_quiz(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lesson: Lesson, index: int
) -> None:
    context.user_data[CURRENT_KEY] = lesson.id
    context.user_data.pop(AWAITING_KEY, None)
    if not lesson.quizzes:
        await _edit_or_send(update, "אין חידון לשיעור הזה.")
        return
    index = max(0, min(index, len(lesson.quizzes) - 1))
    await _edit_or_send(
        update, _quiz_text(lesson, index), reply_markup=kb.quiz_keyboard(lesson, index)
    )


# ------------------------------------------------------------------- callbacks
async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or not query.data:
        return
    await query.answer()
    await _track(update, context)

    action, _, rest = query.data.partition(":")
    parts = rest.split(":") if rest else []
    lesson_id = parts[0] if parts else ""
    lesson = find_lesson(lesson_id)

    if action == kb.CB_MENU:
        user = update.effective_user
        completed = (
            await _storage(context).completed_lessons(user.id) if user else set()
        )
        await _edit_or_send(
            update,
            f"<b>📚 תוכנית הלימודים</b>\n\nהושלמו {len(completed)} מתוך "
            f"{len(LESSONS)} שיעורים.\nבחרו שיעור:",
            reply_markup=kb.menu_keyboard(completed),
        )
        return

    if action == "reset":
        user = update.effective_user
        if lesson_id == "yes" and user:
            await _storage(context).reset(user.id)
            context.user_data.clear()
            await _edit_or_send(update, "ההתקדמות אופסה. אפשר להתחיל מחדש עם /next 🙂")
        else:
            await _edit_or_send(update, "ביטלתי - ההתקדמות נשמרה.")
        return

    if lesson is None:
        await _edit_or_send(update, "לא מצאתי את השיעור הזה. נסו /lessons.")
        return

    if action == kb.CB_LESSON:
        await _show_lesson(update, context, lesson)
    elif action == kb.CB_EXAMPLE:
        await _show_example(update, context, lesson)
    elif action == kb.CB_EXERCISE:
        await _show_exercise(update, context, lesson)
    elif action == kb.CB_HINT:
        await _reply(update, f"🔦 <b>רמז:</b> {lesson.exercise.hint}")
    elif action == kb.CB_SOLUTION:
        await _reply(
            update,
            f"🔑 <b>פתרון אפשרי</b>\n\n{_code_block(lesson.exercise.solution)}\n"
            "יש עוד דרכים נכונות - העיקר שהתוצאה נכונה.",
        )
    elif action == kb.CB_QUIZ:
        index = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        await _show_quiz(update, context, lesson, index)
    elif action == kb.CB_ANSWER:
        await _handle_quiz_answer(update, context, lesson, parts)
    elif action == kb.CB_NEXT:
        upcoming = next_lesson(lesson.id)
        if upcoming is None:
            await _edit_or_send(update, "זה היה השיעור האחרון 🎉 כל הכבוד!")
        else:
            await _show_lesson(update, context, upcoming)


async def _handle_quiz_answer(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    lesson: Lesson,
    parts: list[str],
) -> None:
    if len(parts) < 3 or not parts[1].isdigit() or not parts[2].isdigit():
        return
    quiz_index, chosen = int(parts[1]), int(parts[2])
    if quiz_index >= len(lesson.quizzes):
        return

    quiz = lesson.quizzes[quiz_index]
    correct = chosen == quiz.answer
    user = update.effective_user
    if user:
        await _storage(context).record_quiz_answer(
            user.id, lesson.id, quiz_index, correct
        )

    head = "✅ <b>נכון!</b>" if correct else "❌ <b>לא מדויק</b>"
    body = (
        f"{head}\n\n{quiz.question}\n\n"
        f"התשובה הנכונה: <b>{quiz.options[quiz.answer]}</b>\n\n"
        f"{quiz.explanation}"
    )

    is_last = quiz_index + 1 >= len(lesson.quizzes)
    if is_last and user:
        await _storage(context).complete_lesson(user.id, lesson.id)
        body += "\n\n🎉 סיימתם את השיעור! הוא סומן כהושלם."

    await _edit_or_send(
        update, body, reply_markup=kb.after_quiz_keyboard(lesson, quiz_index)
    )


# ---------------------------------------------------------------- free messages
async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """הודעה חופשית: פתרון תרגיל אם יש תרגיל פתוח, אחרת שאלה למורה."""
    await _track(update, context)
    message = update.effective_message
    if message is None or not message.text:
        return
    text = message.text.strip()

    lesson_id = context.user_data.get(AWAITING_KEY)
    lesson = find_lesson(lesson_id) if lesson_id else None
    if lesson is not None:
        await _check_submission(update, context, lesson, _strip_fences(text))
        return

    if _looks_like_code(text):
        await _reply(
            update,
            "נראה שזה קוד 🙂 כדי שאבדוק אותו פתחו קודם תרגיל עם /practice, "
            "או שאלו אותי שאלה במילים.",
        )
        return

    await _answer_question(update, context, text)


async def _answer_question(
    update: Update, context: ContextTypes.DEFAULT_TYPE, question: str
) -> None:
    tutor = _tutor(context)
    if not tutor.enabled:
        await _reply(
            update,
            "שאלות חופשיות דורשות מפתח <code>ANTHROPIC_API_KEY</code> בשרת. "
            "בינתיים אפשר ללמוד דרך /lessons - כל החומר שם זמין.",
        )
        return

    chat = update.effective_chat
    if chat:
        await context.bot.send_chat_action(chat.id, ChatAction.TYPING)

    lesson = _current_lesson(context)
    try:
        answer = await tutor.answer(question, lesson.title if lesson else None)
    except AIUnavailable:
        await _reply(update, "התכונה הזו אינה זמינה כרגע.")
        return
    except Exception:  # noqa: BLE001 - לא מפילים את הבוט בגלל שגיאת רשת
        logger.exception("קריאה למודל נכשלה")
        await _reply(update, "לא הצלחתי להגיע למורה החכם כרגע. נסו שוב בעוד רגע.")
        return

    await _reply(update, _markdown_code_to_html(answer))


async def _check_submission(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lesson: Lesson, code: str
) -> None:
    chat = update.effective_chat
    if chat:
        await context.bot.send_chat_action(chat.id, ChatAction.TYPING)

    run_note = ""
    if _code_runner_enabled(context):
        result = await run_code(code)
        if not result.ok:
            await _reply(
                update,
                f"❌ הקוד לא רץ בהצלחה:\n{_code_block(result.combined)}\n"
                "תקנו ושלחו שוב, או בקשו 🔦 רמז.",
            )
            return
        run_note = f"\n\n<b>הפלט שקיבלתי:</b>\n{_code_block(result.output or '(ריק)')}"
        expected = lesson.exercise.expected_output
        if expected is not None and result.output.strip() != expected.strip():
            if update.effective_user:
                await _storage(context).record_exercise(
                    update.effective_user.id, lesson.id, False
                )
            await _reply(
                update,
                f"כמעט! ציפיתי לפלט <code>{html.escape(expected)}</code>."
                f"{run_note}\n\nנסו שוב 💪",
            )
            return

    grade = await _grade(context, lesson, code)
    user = update.effective_user
    if user:
        await _storage(context).record_exercise(user.id, lesson.id, grade.passed)

    if grade.passed:
        context.user_data.pop(AWAITING_KEY, None)
        await _reply(
            update,
            f"✅ <b>יפה מאוד!</b> {grade.feedback}{run_note}",
            reply_markup=kb.exercise_keyboard(lesson),
        )
    else:
        await _reply(
            update,
            f"🔍 {grade.feedback}{run_note}\n\nנסו שוב, או לחצו 🔦 רמז.",
            reply_markup=kb.exercise_keyboard(lesson),
        )


async def _grade(
    context: ContextTypes.DEFAULT_TYPE, lesson: Lesson, code: str
) -> Grade:
    """בדיקה חכמה עם Claude, ואם אינה זמינה - בדיקה היוריסטית."""
    tutor = _tutor(context)
    if tutor.enabled:
        try:
            return await tutor.grade(
                lesson.exercise.prompt, lesson.exercise.solution, code
            )
        except AIUnavailable:
            pass
        except Exception:  # noqa: BLE001
            logger.exception("בדיקת תרגיל נכשלה, עובר לבדיקה היוריסטית")
    return heuristic_grade(lesson, code)


def heuristic_grade(lesson: Lesson, code: str) -> Grade:
    """בדיקה פשוטה: תחביר תקין ומילות המפתח הנדרשות."""
    if not code.strip():
        return Grade(False, "לא קיבלתי קוד.")
    try:
        compile(code, "<exercise>", "exec")
    except SyntaxError as exc:
        return Grade(False, f"יש שגיאת תחביר בשורה {exc.lineno}: {exc.msg}")

    normalized = code.replace(" ", "")
    missing = [
        token
        for token in lesson.exercise.required
        if token.replace(" ", "") not in normalized
    ]
    if missing:
        return Grade(False, f"חסר בקוד: {', '.join(missing)}")
    return Grade(True, "הקוד נראה נכון.")


async def _run_and_report(update: Update, code: str) -> None:
    result = await run_code(code)
    if result.ok:
        await _reply(
            update, f"▶️ <b>פלט:</b>\n{_code_block(result.output or '(אין פלט)')}"
        )
    else:
        await _reply(update, f"❌ <b>שגיאה:</b>\n{_code_block(result.combined)}")


# ------------------------------------------------------------------- helpers
def _strip_fences(text: str) -> str:
    """מסיר עטיפת ```python``` שמשתמשים נוטים להדביק."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _looks_like_code(text: str) -> bool:
    markers = ("print(", "def ", "import ", "for ", "while ", "if ", "=")
    return text.startswith("```") or (
        "\n" in text and any(marker in text for marker in markers)
    )


def _markdown_code_to_html(text: str) -> str:
    """ממיר תשובת מודל (markdown) ל-HTML שטלגרם מקבל."""
    out: list[str] = []
    in_code = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            out.append("<pre><code>" if not in_code else "</code></pre>")
            in_code = not in_code
            continue
        out.append(html.escape(line) if in_code else _inline_markdown(line))
    if in_code:
        out.append("</code></pre>")
    return "\n".join(out)


def _inline_markdown(line: str) -> str:
    """בורח מ-HTML ומתרגם `code`, **bold** ו-*italic*."""
    escaped = html.escape(line)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", escaped)
    return escaped


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("שגיאה בטיפול בעדכון", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "משהו השתבש אצלי 😕 נסו שוב, או /start כדי להתחיל מחדש."
            )
        except Exception:  # noqa: BLE001
            logger.debug("לא הצלחתי לשלוח הודעת שגיאה למשתמש")


def register(application: Application) -> None:
    """רושם את כל ההנדלרים על האפליקציה."""
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler(["lessons", "menu"], lessons_menu))
    application.add_handler(CommandHandler("lesson", lesson_command))
    application.add_handler(CommandHandler("next", next_command))
    application.add_handler(CommandHandler("quiz", quiz_command))
    application.add_handler(CommandHandler(["practice", "exercise"], practice_command))
    application.add_handler(CommandHandler("progress", progress_command))
    application.add_handler(CommandHandler("ask", ask_command))
    application.add_handler(CommandHandler("run", run_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CallbackQueryHandler(on_callback))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, on_text)
    )
    application.add_error_handler(on_error)
