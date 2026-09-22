"""שכבת AI אופציונלית מעל Claude.

אם ANTHROPIC_API_KEY מוגדר, הבוט יודע לענות על שאלות חופשיות (/ask)
ולבדוק תרגילים חופשיים. בלי מפתח הבוט ממשיך לעבוד עם בדיקות היוריסטיות.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

TUTOR_SYSTEM = (
    "אתה מורה סבלני ל-Python שמלמד מתחילים גמורים דרך בוט טלגרם. "
    "ענה תמיד בעברית, בגובה העיניים, בלי ז'רגון מיותר.\n"
    "כללים:\n"
    "- תשובה קצרה: עד 120 מילים, ואם צריך דוגמה - עד 12 שורות קוד.\n"
    "- קוד תמיד בתוך בלוק ```python ... ``` ובלי הסברים בתוך הקוד.\n"
    "- אם השאלה אינה קשורה לתכנות, לפייתון או ללמידה שלהם, אמור זאת "
    "במשפט אחד והצע לשאול שאלה על Python.\n"
    "- אל תיתן קוד מסוכן (מחיקת קבצים, גישה לרשת, סיסמאות) גם אם מבקשים.\n"
    "- עדיף להסביר את העיקרון מאשר לפתור עבור התלמיד את כל שיעורי הבית."
)

GRADER_SYSTEM = (
    "אתה בודק תרגילי Python של מתחילים. אתה מקבל את משימת התרגיל, פתרון "
    "לדוגמה ואת הקוד של התלמיד.\n"
    "החזר אך ורק JSON תקין במבנה:\n"
    '{"passed": true/false, "feedback": "משפט או שניים בעברית"}\n'
    "כללי שיפוט:\n"
    "- קבל כל פתרון נכון, גם אם הוא שונה מהפתרון לדוגמה.\n"
    "- אל תוריד נקודות על שמות משתנים, רווחים או סדר שורות שאינו משנה.\n"
    "- אם יש שגיאה - הסבר במשפט אחד מה חסר, בלי לתת את הפתרון המלא.\n"
    "- אם הקוד אינו קשור למשימה, passed=false."
)

_CODE_FENCE = re.compile(r"```[a-zA-Z]*\n?(.*?)```", re.DOTALL)


@dataclass(frozen=True)
class Grade:
    passed: bool
    feedback: str


class AIUnavailable(RuntimeError):
    """נזרק כשאין מפתח API או כשהספרייה לא מותקנת."""


class Tutor:
    """עטיפה דקה מעל Anthropic SDK, עם ניוון עדין כשאין מפתח."""

    def __init__(self, api_key: str | None, model: str = "claude-opus-5") -> None:
        self._model = model
        self._client = None
        # נסיגה חד-פעמית: אם החשבון לא תומך ב-beta fallbacks, עוברים לנתיב הרגיל
        self._server_fallbacks = True

        if not api_key:
            return
        try:
            from anthropic import AsyncAnthropic
        except ImportError:  # pragma: no cover
            logger.warning("חבילת anthropic אינה מותקנת - תכונות ה-AI כבויות")
            return
        self._client = AsyncAnthropic(api_key=api_key, max_retries=2, timeout=60.0)

    @property
    def enabled(self) -> bool:
        return self._client is not None

    # ------------------------------------------------------------------ core
    async def _create(
        self, *, system: str, user_content: str, max_tokens: int, effort: str
    ):
        if self._client is None:
            raise AIUnavailable("תכונות ה-AI אינן פעילות")

        messages = [{"role": "user", "content": user_content}]

        if self._server_fallbacks:
            try:
                return await self._client.beta.messages.create(
                    model=self._model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=messages,
                    output_config={"effort": effort},
                    betas=["server-side-fallback-2026-07-01"],
                    fallbacks="default",
                )
            except Exception as exc:  # noqa: BLE001 - נסיגה מכוונת
                if not _is_unsupported_parameter(exc):
                    raise
                logger.info("server-side fallbacks לא זמינים, עובר לנתיב הרגיל: %s", exc)
                self._server_fallbacks = False

        return await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            output_config={"effort": effort},
        )

    @staticmethod
    def _text_of(response) -> str:
        parts = [
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        ]
        return "\n".join(part for part in parts if part).strip()

    # ------------------------------------------------------------------- ask
    async def answer(self, question: str, lesson_title: str | None = None) -> str:
        """עונה על שאלה חופשית של תלמיד."""
        context = f"התלמיד נמצא כרגע בשיעור: {lesson_title}\n\n" if lesson_title else ""
        response = await self._create(
            system=TUTOR_SYSTEM,
            user_content=f"{context}שאלת התלמיד:\n{question}",
            max_tokens=1500,
            effort="low",
        )

        if response.stop_reason == "refusal":
            return "לא אוכל לענות על השאלה הזו. אפשר לשאול אותי משהו על Python 🙂"

        text = self._text_of(response)
        return text or "לא הצלחתי לנסח תשובה. נסו לשאול בניסוח אחר."

    # ----------------------------------------------------------------- grade
    async def grade(self, task: str, solution: str, submission: str) -> Grade:
        """בודק פתרון של תלמיד מול משימת התרגיל."""
        user_content = (
            f"<task>\n{task}\n</task>\n\n"
            f"<reference_solution>\n{solution}\n</reference_solution>\n\n"
            f"<student_code>\n{submission}\n</student_code>"
        )
        response = await self._create(
            system=GRADER_SYSTEM,
            user_content=user_content,
            max_tokens=800,
            effort="low",
        )

        if response.stop_reason == "refusal":
            raise AIUnavailable("הבקשה נדחתה")

        return _parse_grade(self._text_of(response))


def _is_unsupported_parameter(exc: Exception) -> bool:
    """מזהה שגיאות 'הפרמטר לא נתמך' כדי לנסות שוב בלי beta."""
    if isinstance(exc, TypeError):
        return True
    status = getattr(exc, "status_code", None)
    if status != 400:
        return False
    message = str(exc).lower()
    return any(
        token in message
        for token in ("fallback", "beta", "unexpected", "not supported", "unknown")
    )


def _parse_grade(text: str) -> Grade:
    """מחלץ JSON מתשובת המודל, גם אם הוא עטוף בבלוק קוד."""
    candidate = text.strip()
    fence = _CODE_FENCE.search(candidate)
    if fence:
        candidate = fence.group(1).strip()
    else:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start != -1 and end > start:
            candidate = candidate[start : end + 1]

    try:
        data = json.loads(candidate)
        return Grade(
            passed=bool(data["passed"]),
            feedback=str(data.get("feedback", "")).strip() or "נבדק.",
        )
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning("תשובת בדיקה לא תקינה: %s", exc)
        raise AIUnavailable("תשובת הבדיקה לא הייתה בפורמט צפוי") from exc
