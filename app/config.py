"""טעינת הגדרות מסביבת ההרצה (משתני סביבה / קובץ .env)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:  # python-dotenv הוא נוחות לפיתוח מקומי בלבד
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - בסביבת הרצה אמיתית המשתנים כבר מוגדרים
    pass


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Config:
    telegram_token: str
    anthropic_api_key: str | None
    claude_model: str
    webhook_url: str | None
    webhook_secret: str | None
    port: int
    data_dir: Path
    enable_code_runner: bool

    @property
    def db_path(self) -> Path:
        return self.data_dir / "pythonbot.sqlite3"

    @property
    def use_webhook(self) -> bool:
        """ברנדר מריצים webhook; מקומית בלי WEBHOOK_URL עוברים ל-polling."""
        return bool(self.webhook_url)

    @property
    def ai_enabled(self) -> bool:
        return bool(self.anthropic_api_key)


def load_config() -> Config:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "חסר TELEGRAM_BOT_TOKEN. צרו בוט אצל @BotFather והגדירו את הטוקן "
            "כמשתנה סביבה (ראו .env.example)."
        )

    # ברנדר מזריק את RENDER_EXTERNAL_URL אוטומטית לשירותי Web.
    webhook_url = (
        os.environ.get("WEBHOOK_URL") or os.environ.get("RENDER_EXTERNAL_URL") or ""
    ).strip().rstrip("/")

    data_dir = Path(os.environ.get("DATA_DIR", "./data")).expanduser()

    return Config(
        telegram_token=token,
        anthropic_api_key=(os.environ.get("ANTHROPIC_API_KEY") or "").strip() or None,
        claude_model=os.environ.get("CLAUDE_MODEL", "claude-opus-5").strip(),
        webhook_url=webhook_url or None,
        webhook_secret=(os.environ.get("WEBHOOK_SECRET") or "").strip() or None,
        port=int(os.environ.get("PORT", "10000")),
        data_dir=data_dir,
        enable_code_runner=_as_bool(os.environ.get("ENABLE_CODE_RUNNER"), False),
    )
