import asyncio
import logging
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from bot.config import BOT_TOKEN
from bot.handlers.users import router as users_router
from bot.handlers.admin import router as admin_router
from database.db import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ai_exam_bot")

async def main():
    if not BOT_TOKEN or BOT_TOKEN.startswith("YOUR_"):
        logger.error("BOT_TOKEN ko'rsatilmagan! .env faylini tekshiring.")
        return

    # Baza sxemasini tekshirish
    init_db(force_recreate=False)

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    dp = Dispatcher()

    # Routerlarni ulash
    dp.include_router(admin_router)
    dp.include_router(users_router)

    logger.info("==================================================")
    logger.info("   🤖 AI EXAM REPORT BOT ISHGA TUSHDI!            ")
    logger.info("==================================================")

    # Eski kutilayotgan yangilanishlarni tashlab yuborish
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
