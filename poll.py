"""Точка входа: запуск бота."""

import asyncio
import logging

from dotenv import load_dotenv

from bot import create_bot, create_dispatcher


async def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    bot = create_bot()
    dp = create_dispatcher()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
