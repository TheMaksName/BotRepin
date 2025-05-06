import argparse
import asyncio
import logging
from typing import List

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from sqlalchemy import select

from app.bot.handlers.user_private import user_private_router
from app.bot.handlers.user_registartion import user_registration_router
from app.bot.middlewares.db import DataBaseSession

from app.database.engine import create_db, drop_db, session_maker




from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import BotCommandScopeAllPrivateChats, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.FSM.FSM_user_private import User_MainStates
from app.database.models import UserCode

from config import settings

from app.database.orm_query import get_verified_user_by_chat_id
from app.kbds import reply


from app.bot.common.bot_cmds_list import private
# ALLOWED_UPDATES = ['message', 'callback_query']


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Глобальный кэш для user_ids (заполняется при запуске)
USER_IDS_CACHE: List[int] = []

async def fetch_user_ids(session: AsyncSession) -> List[int]:
     """Получает список всех user_id из таблицы User."""
     query = select(UserCode.telegram_chat_id)
     result = await session.execute(query)
     return result.scalars().all()

async def send_message_batch(bot: Bot, user_ids: List[int], message_text: str, batch_size: int = 30) -> None:
     """Отправляет сообщения партиями с учетом лимитов Telegram."""
     for i in range(0, len(user_ids), batch_size):
         batch = user_ids[i:i + batch_size]
         tasks = [bot.send_message(chat_id=user_id, text=message_text, reply_markup=ReplyKeyboardRemove()) for user_id in batch]
         results = await asyncio.gather(*tasks, return_exceptions=True)
         for user_id, result in zip(batch, results):
             if isinstance(result, Exception):
                 logger.warning(f"Не удалось отправить сообщение user_id={user_id}: {result}")
             else:
                 logger.debug(f"Сообщение отправлено user_id={user_id}")
         await asyncio.sleep(1)  # Пауза 1 секунда между партиями (30 сообщений/сек)

async def send_message_to_all_users(bot: Bot, session: AsyncSession, message_text: str) -> None:
     """Отправляет сообщение всем пользователям из кэша или базы."""
     global USER_IDS_CACHE
     try:
         if not USER_IDS_CACHE:
             USER_IDS_CACHE = await fetch_user_ids(session)
         await send_message_batch(bot, USER_IDS_CACHE, message_text)
         logger.info(f"Сообщения отправлены {len(USER_IDS_CACHE)} пользователям")
     except Exception as e:
         logger.error(f"Ошибка при отправке сообщений всем пользователям: {e}")
         raise

def get_startup_handler(reset_db: bool):
    async def startup(bot: Bot) -> None:
        """Выполняется при запуске бота: инициализация БД и отправка сообщений."""
        try:
            if reset_db:
                await drop_db()
                logger.info("База данных сброшена")
            await create_db()
            logger.info("База данных инициализирована")

            # Отправка сообщения всем пользователям
            async with session_maker() as session:
                welcome_message = (
                    "📢 Бот перезапущен!\n"
                    "Напишите команду /start для продолжения работы.✏"
                )
                await send_message_to_all_users(bot, session, welcome_message)
        except Exception as e:
            logger.error(f"Ошибка при запуске бота: {e}")
            raise
    return startup


async def on_shutdown(bot):
    logger.info("Бот остановлен")

async def main():
    parser = argparse.ArgumentParser(description="Запуск бота конкурса «РЕПИН НАШ!»")
    parser.add_argument("--reset-db", action="store_true", help="Сбросить базу данных при запуске")
    args = parser.parse_args()

    # Оптимизация пула соединений для высокой нагрузки
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()

    # Регистрация обработчиков запуска и остановки
    dp.startup.register(get_startup_handler(args.reset_db))
    dp.shutdown.register(on_shutdown)

    # Middleware для сессии базы данных
    dp.update.middleware(DataBaseSession(session_pool=session_maker))

    # Подключение роутеров
    dp.include_router(user_private_router)
    # dp.include_router(news_channel_router)
    dp.include_router(user_registration_router)

    @dp.message(CommandStart())
    async def start(message: Message, state: FSMContext, session: AsyncSession):
            chat_id = message.chat.id
            user_code = await get_verified_user_by_chat_id(session, chat_id)
            if user_code:
                await state.set_state(User_MainStates.after_registration)
                await message.answer("C вовращением.", reply_markup=reply.menu_kb)
            else:
                await state.set_state(User_MainStates.before_registration)
                await message.answer("Приветсвую, дорогой участник. Для доступа к боту введи код.")

    # Установка команд и запуск бота
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands(commands=private, scope=BotCommandScopeAllPrivateChats())
    # await bot.delete_my_commands()
    logger.info("Запуск polling...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())

