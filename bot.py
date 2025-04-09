import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import TOKEN
from handlers import register_handlers
from detector import SpamDetector
from warnings_ import WarningManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    detector = SpamDetector("RUSpam/spam_deberta_v4")
    warn_mgr = WarningManager('warnings.json')

    register_handlers(dp, bot, detector, warn_mgr)

    logger.info("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Ошибка запуска: {e}")
