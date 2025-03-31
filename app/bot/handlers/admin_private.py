import asyncio
import logging
from time import time
from typing import Dict, Union, Callable, Awaitable
from asyncio import gather

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.filters import Command, StateFilter
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.FSM.FSM_user_private import RegistrationUser, User_MainStates
from app.bot.handlers.user_edit_profile import user_view_profile_router
from app.bot.handlers.user_registartion import user_registration_router
from app.kbds.inline import get_callback_btns
from app.kbds.reply import get_keyboard, menu_kb
from app.database.orm_query import (
    orm_Get_info_user, orm_get_news_by_id, orm_get_all_news,
    orm_get_all_themes_by_category_id, orm_get_theme_by_id,
    orm_Edit_user_profile, orm_get_material_by_id
)
from config import settings

logger = logging.getLogger(__name__)

# Создаем роутер для приватных команд пользователя
user_private_router = Router()
user_private_router.include_router(user_registration_router)
user_private_router.include_router(user_view_profile_router)

# Кэш с тайм-аутом (30 минут)
CACHE_TIMEOUT = 1800
cache_current_news: Dict[int, int] = {}
cache_current_theme: Dict[int, int] = {}
cache_current_material: Dict[int, int] = {}
cache_last_access: Dict[int, float] = {}

async def paginate_items(
    message: Union[Message, CallbackQuery],
    session: AsyncSession,
    user_id: int,
    item_id: int,
    cache: Dict[int, int],
    fetch_func: Callable,
    format_func: Callable,
    kb_func: Callable[[list, int], Union[InlineKeyboardMarkup, Awaitable[InlineKeyboardMarkup]]]
) -> None:
    """Универсальная функция для пагинации элементов."""
    try:
        # Очистка устаревшего кэша
        if user_id in cache and time() - cache_last_access.get(user_id, 0) > CACHE_TIMEOUT:
            del cache[user_id]
            cache_last_access.pop(user_id, None)

        cache[user_id] = item_id
        cache_last_access[user_id] = time()

        # Выполняем запрос
        items = await fetch_func(session, item_id)
        if not items:
            text = "Больше элементов нет."
            await (message.answer if isinstance(message, Message) else message.message.edit_text)(text)
            return

        # Форматируем текст и клавиатуру параллельно
        text_task = asyncio.create_task(asyncio.to_thread(format_func, items))
        kb_task = asyncio.create_task(kb_func(items, item_id))
        text, reply_markup_result = await gather(text_task, kb_task)
        reply_markup = await reply_markup_result if isinstance(reply_markup_result, Awaitable) else reply_markup_result

        # Отправляем или редактируем сообщение
        if isinstance(message, Message):
            await message.answer(text, reply_markup=reply_markup)
        else:
            await message.message.edit_text(text, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Ошибка пагинации для user_id={user_id}, item_id={item_id}: {e}")
        await (message.answer if isinstance(message, Message) else message.message.edit_text)("Ошибка загрузки.")

# Команда /menu
@user_private_router.message(Command('menu'))
async def menu(message: Message) -> None:
    """Открывает основное меню пользователя."""
    await message.answer("Открываю меню...", reply_markup=menu_kb)
    logger.debug(f"Пользователь {message.from_user.id} открыл меню")

# Команда "новости"
@user_private_router.message(F.text.lower() == 'новости')
async def news(message: Message, session: AsyncSession) -> None:
    """Показывает первую новость пользователю."""
    user_id = message.from_user.id
    await paginate_items(
        message, session, user_id, 1, cache_current_news,
        orm_get_news_by_id,
        lambda n: f"<strong>{n.text}</strong>" if n else "Новостей пока нет(((",
        lambda n, _: get_callback_btns(btns={"Далее": "news_next"}) if n else None
    )

# Переключение новостей
@user_private_router.callback_query(F.data.startswith('news_'))
async def slide_news(callback: CallbackQuery, session: AsyncSession) -> None:
    """Переключает новости вперед или назад."""
    user_id = callback.from_user.id
    action = callback.data.split("_")[1]
    current_news_id = cache_current_news.get(user_id, 1)
    new_id = current_news_id + 1 if action == 'next' else max(1, current_news_id - 1)

    async def kb_func(news, _):
        next_exists = await orm_get_news_by_id(session, new_id + 1)
        return get_callback_btns(btns={"Назад": "news_back", "Далее": "news_next" if next_exists else None})

    await paginate_items(
        callback, session, user_id, new_id, cache_current_news,
        orm_get_news_by_id,
        lambda n: f"<strong>{n.text}</strong>",
        kb_func
    )
    await callback.answer()

# Команда "материалы"
@user_private_router.message(F.text.lower() == 'материалы')
async def get_material(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Показывает список материалов."""
    user_id = message.from_user.id
    await paginate_items(
        message, session, user_id, 0, cache_current_material,
        orm_get_material_by_id,
        lambda ms: "\n".join(f"{m.id}🟦 {m.title}" for m in ms) if ms else "Материалы отсутствуют",
        lambda ms, _: get_callback_btns(
            btns={f"Материал №{m.id}": f"choice_material_{m.id}" for m in ms} | {"Далее": "slide_material_next"},
            sizes=(3, 3, 2)
        ) if ms else None
    )

# Переключение материалов
@user_private_router.callback_query(F.data.startswith('slide_material_'))
async def slide_material(callback: CallbackQuery, session: AsyncSession) -> None:
    """Переключает материалы вперед или назад."""
    user_id = callback.from_user.id
    action = callback.data.split("_")[2]
    current_id = cache_current_material.get(user_id, 0)
    new_id = current_id + 1 if action == 'next' else max(0, current_id - 1)

    async def kb_func(mats, _):
        next_exists_task = asyncio.create_task(orm_get_material_by_id(session, new_id + 1))
        prev_exists = new_id > 0
        next_exists = await next_exists_task
        btns = {f"Материал №{m.id}": f"choice_material_{m.id}" for m in mats}
        if prev_exists:
            btns["Назад"] = "slide_material_back"
        if next_exists:
            btns["Далее"] = "slide_material_next"
        return get_callback_btns(btns=btns, sizes=(3, 3, 2))

    await paginate_items(
        callback, session, user_id, new_id, cache_current_material,
        orm_get_material_by_id,
        lambda ms: "\n".join(f"{m.id}🟦 {m.title}" for m in ms),
        kb_func
    )

# Команда "посмотреть темы"
@user_private_router.message(F.text.lower() == 'посмотреть темы')
async def get_themes(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Показывает список тем."""
    user_id = message.from_user.id
    await paginate_items(
        message, session, user_id, 1, cache_current_theme,
        orm_get_all_themes_by_category_id,
        lambda ts: f"Категория: {ts[0].category.title}\n\n" + "\n".join(
            f"{t.id}🟦 {t.title}\n📌Прием: {t.technique}" for t in ts),
        lambda ts, _: get_callback_btns(
            btns=({"Тема №{t.id}": f"choice_theme_{t.id}" for t in ts} if settings.prod else {}) | {
                "Далее": "slide_theme_next"},
            sizes=(3, 3, 2)
        )
    )

# Переключение тем
@user_private_router.callback_query(F.data.startswith('slide_theme_'))
async def slide_theme(callback: CallbackQuery, session: AsyncSession) -> None:
    """Переключает категории тем."""
    user_id = callback.from_user.id
    action = callback.data.split("_")[2]
    current_id = cache_current_theme.get(user_id, 1)
    new_id = current_id + 1 if action == 'next' else max(1, current_id - 1)

    async def kb_func(themes, _):
        next_exists_task = asyncio.create_task(orm_get_all_themes_by_category_id(session, new_id + 1))
        prev_exists = new_id > 1
        next_exists = await next_exists_task
        btns = {"Тема №{t.id}": f"choice_theme_{t.id}" for t in themes} if settings.prod else {}
        if prev_exists:
            btns["Назад"] = "slide_theme_back"
        if next_exists:
            btns["Далее"] = "slide_theme_next"
        return get_callback_btns(btns=btns, sizes=(3, 3, 2))

    await paginate_items(
        callback, session, user_id, new_id, cache_current_theme,
        orm_get_all_themes_by_category_id,
        lambda ts: f"Категория: {ts[0].category.title}\n\n" + "\n".join(
            f"{t.id}🟦 {t.title}\n📌Прием: {t.technique}" for t in ts),
        kb_func
    )

# Выбор темы
@user_private_router.callback_query(F.data.startswith('choice_theme_'))
async def choice_theme(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Подтверждение выбора темы."""
    theme_id = int(callback.data.split('_')[2])
    theme = await orm_get_theme_by_id(session, theme_id)
    if not theme:
        await callback.answer("Тема не найдена.")
        return
    await state.update_data(prev_message_id=callback.message.message_id)
    await callback.message.answer(
        f"Вы выбираете тему:\n\n🟦 {theme.title}\n📌Прием: {theme.technique}\n\nПодтверждаете выбор?",
        reply_markup=get_callback_btns(
            btns={"Подтверждаю✅": f"confirm_theme_{theme_id}", "Я передумал❌": "confirm_theme_"}
        )
    )

# Подтверждение выбора темы
@user_private_router.callback_query(F.data.startswith("confirm_theme_"))
async def confirm_theme(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Подтверждение или отмена выбора темы."""
    confirm_theme_id = callback.data.split("_")[2]
    user_id = callback.from_user.id
    state_data = await state.get_data()
    prev_message_id = state_data.get("prev_message_id")

    if confirm_theme_id:
        theme = await orm_get_theme_by_id(session, int(confirm_theme_id))
        if theme and await orm_Edit_user_profile(session, user_id, {'edit_theme': f"{theme.title} {theme.technique}"}):
            await callback.bot.delete_messages(callback.message.chat.id, [callback.message.message_id, prev_message_id])
            await callback.message.answer("Тема успешно выбрана📥")
        else:
            await callback.message.edit_text("Ошибка при сохранении темы.")
    else:
        await callback.message.delete()

# Профиль пользователя
@user_private_router.message(User_MainStates.after_registration, F.text.lower() == 'мой профиль')
async def get_user_profile(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Показывает профиль пользователя."""
    data = await orm_Get_info_user(session, message.from_user.id)
    if data:
        await state.set_state(User_MainStates.user_view_profile)
        text = (
            f"📄ФИО: {data.name}\n🏫Школа: {data.school}\n📱Номер телефона: {data.phone_number}\n"
            f"📧Электронная почта: {data.mail}\n👨‍🏫ФИО наставника: {data.name_mentor}\n"
            f"👪Должность наставника: {data.post_mentor or ''}\n📜Тема: {data.theme}"
        )
        await message.answer(text, reply_markup=get_keyboard("Редактировать", "Назад", sizes=(2,)))
    else:
        await message.answer("Профиль не найден")