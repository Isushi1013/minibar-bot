import logging
from datetime import time

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from bot.config import get_token
from bot.handlers import handle_callback, handle_room_text, start

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def _daily_reset_job(context) -> None:
    """Запускается каждый день в 08:00.
    Данные хранятся вечно и разделяются по полю 'date',
    поэтому физического удаления не нужно — просто логируем смену дня."""
    logger.info("Новый день начался — база готова к записи.")


def main() -> None:
    app = Application.builder().token(get_token()).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_room_text))

    # Ежедневный сброс в 08:00 (UTC+0 — поменяй timezone при необходимости)
    job_queue = app.job_queue
    if job_queue is not None:
        job_queue.run_daily(
            _daily_reset_job,
            time=time(hour=8, minute=0, second=0),
        )
        logger.info("Задание ежедневного сброса зарегистрировано на 08:00 UTC")
    else:
        logger.warning(
            "JobQueue недоступен. Установи 'python-telegram-bot[job-queue]' "
            "для поддержки ежедневного сброса."
        )

    logger.info("Бот запущен")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
