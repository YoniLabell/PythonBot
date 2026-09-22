"""נקודת הכניסה של הבוט.

ברנדר (Web Service) מוגדר RENDER_EXTERNAL_URL, ולכן הבוט עולה במצב webhook
ומאזין על PORT. מקומית, בלי WEBHOOK_URL, הוא עובר אוטומטית ל-polling.
"""

from __future__ import annotations

import logging
import sys

from telegram import BotCommand
from telegram.ext import Application, ApplicationBuilder

from app import handlers
from app.ai import Tutor
from app.config import Config, load_config
from app.storage import Storage

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("pythonbot")

COMMANDS = [
    BotCommand("start", "התחלה"),
    BotCommand("lessons", "תפריט השיעורים"),
    BotCommand("next", "השיעור הבא"),
    BotCommand("practice", "תרגיל"),
    BotCommand("quiz", "חידון"),
    BotCommand("ask", "שאלה חופשית על Python"),
    BotCommand("progress", "ההתקדמות שלי"),
    BotCommand("help", "עזרה"),
]

WEBHOOK_PATH = "telegram"


def build_application(config: Config) -> Application:
    storage = Storage(config.db_path)
    tutor = Tutor(config.anthropic_api_key, config.claude_model)

    async def on_startup(app: Application) -> None:
        await storage.init()
        await app.bot.set_my_commands(COMMANDS)
        logger.info(
            "הבוט מוכן | AI: %s | הרצת קוד: %s | מצב: %s",
            "פעיל" if tutor.enabled else "כבוי",
            "פעילה" if config.enable_code_runner else "כבויה",
            "webhook" if config.use_webhook else "polling",
        )

    application = (
        ApplicationBuilder()
        .token(config.telegram_token)
        .post_init(on_startup)
        .build()
    )
    application.bot_data["storage"] = storage
    application.bot_data["tutor"] = tutor
    application.bot_data["enable_code_runner"] = config.enable_code_runner

    handlers.register(application)
    return application


def main() -> int:
    try:
        config = load_config()
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1

    application = build_application(config)

    if config.use_webhook:
        url = f"{config.webhook_url}/{WEBHOOK_PATH}"
        logger.info("מאזין ב-webhook על פורט %s", config.port)
        application.run_webhook(
            listen="0.0.0.0",
            port=config.port,
            url_path=WEBHOOK_PATH,
            webhook_url=url,
            secret_token=config.webhook_secret,
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"],
        )
    else:
        logger.info("מצב polling (פיתוח מקומי)")
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"],
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
