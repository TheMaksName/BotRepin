import argparse
import asyncio
import logging
from typing import List

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.bot.handlers.news_channel import news_channel_router
from app.bot.middlewares.db import DataBaseSession

from app.database.engine import create_db, drop_db, session_maker


from app.bot.handlers.user_private import user_private_router

from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BotCommandScopeAllPrivateChats, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.FSM.FSM_user_private import User_MainStates
from app.database.models import User

from config import settings

from app.database.orm_query import orm_Check_avail_user, orm_AddUser, orm_Check_register_user, orm_get_all_user
from app.kbds import reply


from app.bot.common.bot_cmds_list import private
# ALLOWED_UPDATES = ['message', 'callback_query']


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Глобальный кэш для user_ids (заполняется при запуске)
USER_IDS_CACHE: List[int] = []

async def fetch_user_ids(session: AsyncSession) -> List[int]:
    """Получает список всех user_id из таблицы User."""
    query = select(User.user_id)
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
                    "📢 Бот запущен!\n"
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
    dp.include_router(news_channel_router)

    @dp.message(CommandStart())
    async def start(message: Message, state: FSMContext, session: AsyncSession):
        try:
            user_id = message.from_user.id
            if user_id not in USER_IDS_CACHE:
                if not await orm_Check_avail_user(session, user_id):
                    info_user = {
                        "user_id": user_id,
                        "nickname": message.from_user.username or "не установлен"
                    }
                    await orm_AddUser(session, info_user)
                    USER_IDS_CACHE.append(user_id)  # Обновляем кэш

            user_name = await orm_Check_register_user(session, user_id)
            if settings.prod:
                if not user_name:
                    await state.set_state(User_MainStates.before_registration)
                    await message.answer(
                        "Привет.👋"
                        "Для участия в конкурсе нужно зарегистрироваться. Как будешь готов, напиши 'Зарегистрироваться' или нажми на кнопку ниже👇",
                        reply_markup=reply.start_kb_prod
                    )
                else:
                    await state.set_state(User_MainStates.after_registration)
                    await message.answer(
                        f"Привет {user_name.split(' ')[1]}, давно не виделись👋",
                        reply_markup=reply.menu_kb
                    )
                    await message.answer("Выбери действие в меню.")
            else:
                await state.set_state(User_MainStates.before_registration)
                await message.answer(
                    """
📢 Приветствие участникам конкурса «РЕПИН НАШ!»
🔹 Почему вы здесь?
Ты, наверное, слышал про Илью Репина — великого художника, автора «Бурлаков на Волге». Но вот странность: в финском музее «Атенеум» вдруг решили, что Репин — не русский художник, а украинский. Как так? Ведь он сам писал, что его вдохновила русская Волга, что он увидел в бурлаках силу и характер русского народа!
Что мы будем с этим делать? Ответ простой: показать, что Репин – наш!
🔹 Зачем этот конкурс?
Мы не просто будем говорить, а докажем историческую правду через цифровое искусство. Ты сможешь создать виртуальную выставку, где расскажешь о Репине и его связи с Самарой, Волгой, бурлаками, русской культурой. Это твой шанс стать художником, исследователем и рассказчиком одновременно!
🔹 Ты точно справишься!
Мы верим в тебя! У тебя уже есть всё, чтобы создать крутой проект:
✅ Наставники – лучшие эксперты помогут и подскажут.
✅ Материалы – вся нужная информация о Репине, Самаре и истории есть в этом боте.
✅ Пошаговые инструкции – мы будем вести тебя от выбора идеи до создания выставки.
✅ Современные технологии – ты попробуешь 3D-моделирование, нейросети, интерактивные элементы.
🔹 Что делать дальше?
💡 Прочитай условия конкурса.
💡 Выбери свою тему – тебя ждёт 30 идей!
💡 Следи за нашими постами – мы расскажем, как создать выставку шаг за шагом.
📢 Репин наш! Самара – его вдохновение! А ты – тот, кто покажет это миру! 🚀
                    """,
                    reply_markup=reply.start_kb_not_prod
                )
        except SQLAlchemyError as e:
            logger.error(f"Ошибка базы данных для user_id={message.from_user.id}: {e}")
            await message.answer("Ошибка базы данных. Попробуйте позже.")
        except Exception as e:
            logger.error(f"Неизвестная ошибка для user_id={message.from_user.id}: {e}")
            await message.answer("Извините, что-то пошло не так. Попробуйте позже")

    # Установка команд и запуск бота
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands(commands=private, scope=BotCommandScopeAllPrivateChats())
    # await bot.delete_my_commands()
    logger.info("Запуск polling...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())

