import asyncio

from aiogram import Bot, Dispatcher

from app.bot.handlers import router
from app.core.config import settings


async def main() -> None:
    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = Dispatcher()

    dispatcher.include_router(router)

    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
