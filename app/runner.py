"""הרצת קוד תרגילים בתת-תהליך מוגבל.

התכונה כבויה כברירת מחדל (ENABLE_CODE_RUNNER=false). הפעלה מריצה קוד שנשלח
מטלגרם על השרת שלכם, ולכן הגבלנו זמן CPU, זיכרון, גודל פלט וייבוא מודולים
רגישים. זו הגנה בשכבות, לא בידוד מלא - ראו את הפרק המתאים ב-README.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass

logger = logging.getLogger(__name__)

CPU_SECONDS = 2
MEMORY_BYTES = 128 * 1024 * 1024
WALL_TIMEOUT = 6.0
MAX_OUTPUT_CHARS = 2000
MAX_CODE_CHARS = 4000

BLOCKED_MODULES = {
    "os", "sys", "subprocess", "shutil", "socket", "http", "urllib", "requests",
    "pathlib", "ctypes", "multiprocessing", "threading", "importlib", "pickle",
    "signal", "resource", "glob", "tempfile", "webbrowser", "ftplib", "smtplib",
}
BLOCKED_CALLS = {"open", "eval", "exec", "compile", "__import__", "input", "breakpoint"}

_IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+([A-Za-z_][\w.]*)", re.MULTILINE)


@dataclass(frozen=True)
class RunResult:
    ok: bool
    output: str
    error: str = ""

    @property
    def combined(self) -> str:
        return "\n".join(part for part in (self.output, self.error) if part).strip()


def check_code(code: str) -> str | None:
    """בדיקה סטטית מהירה. מחזיר הודעת שגיאה בעברית, או None אם הקוד עבר."""
    if not code.strip():
        return "לא קיבלתי קוד להרצה."
    if len(code) > MAX_CODE_CHARS:
        return f"הקוד ארוך מדי (מעל {MAX_CODE_CHARS} תווים)."

    for match in _IMPORT_RE.finditer(code):
        root = match.group(1).split(".")[0]
        if root in BLOCKED_MODULES:
            return f"ייבוא המודול <code>{root}</code> חסום בסביבת התרגול."

    for name in BLOCKED_CALLS:
        if re.search(rf"\b{re.escape(name)}\s*\(", code):
            return f"השימוש ב-<code>{name}()</code> חסום בסביבת התרגול."

    try:
        compile(code, "<exercise>", "exec")
    except SyntaxError as exc:
        return f"שגיאת תחביר בשורה {exc.lineno}: {exc.msg}"
    return None


def _apply_limits() -> None:  # pragma: no cover - רץ רק בתת-תהליך
    import resource

    resource.setrlimit(resource.RLIMIT_CPU, (CPU_SECONDS, CPU_SECONDS))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_BYTES, MEMORY_BYTES))
    resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    os.setsid()


def _run_sync(code: str) -> RunResult:
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": "/tmp",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "LANG": "C.UTF-8",
    }
    with tempfile.TemporaryDirectory(prefix="pythonbot-") as workdir:
        try:
            completed = subprocess.run(
                [sys.executable, "-I", "-B", "-c", code],
                capture_output=True,
                text=True,
                timeout=WALL_TIMEOUT,
                cwd=workdir,
                env=env,
                stdin=subprocess.DEVNULL,
                preexec_fn=_apply_limits if hasattr(os, "setsid") else None,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return RunResult(False, "", "הקוד רץ יותר מדי זמן - אולי יש לולאה אינסופית?")
        except OSError as exc:  # pragma: no cover
            logger.exception("הרצת הקוד נכשלה")
            return RunResult(False, "", f"לא הצלחתי להריץ את הקוד: {exc}")

    stdout = completed.stdout[:MAX_OUTPUT_CHARS]
    stderr = completed.stderr[-MAX_OUTPUT_CHARS:]
    if completed.returncode < 0:
        # התהליך נהרג על ידי סיגנל - בדרך כלל חריגה ממגבלת CPU או זיכרון
        return RunResult(
            False,
            stdout.strip(),
            "הקוד חרג ממגבלות הזמן או הזיכרון. בדקו אם יש לולאה שלא נגמרת.",
        )
    if completed.returncode != 0:
        return RunResult(False, stdout.strip(), _short_error(stderr))
    return RunResult(True, stdout.strip())


def _short_error(stderr: str) -> str:
    """מציג לתלמיד את שורת השגיאה המשמעותית בלבד."""
    lines = [line for line in stderr.strip().splitlines() if line.strip()]
    if not lines:
        return "הקוד נעצר עם שגיאה."
    return lines[-1].strip()


async def run_code(code: str) -> RunResult:
    """מריץ קוד ומחזיר את הפלט. אינו חוסם את לולאת האירועים."""
    problem = check_code(code)
    if problem:
        return RunResult(False, "", problem)
    return await asyncio.to_thread(_run_sync, code)
