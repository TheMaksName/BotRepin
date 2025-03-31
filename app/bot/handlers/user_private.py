import asyncio
import logging
from time import time
from typing import Dict, Union, Callable, Awaitable

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.FSM.FSM_user_private import RegistrationUser, User_MainStates
from app.bot.handlers.user_edit_profile import user_view_profile_router
from app.bot.handlers.user_registartion import user_registration_router
from app.kbds.inline import get_callback_btns, create_material_buttons
from app.kbds.reply import get_keyboard
from app.database.orm_query import orm_Get_info_user, orm_get_news_by_id, orm_get_all_news, \
    orm_get_all_themes_by_category_id, orm_get_theme_by_id, orm_Edit_user_profile, orm_get_material_by_id
from app.kbds import reply
from config import settings

logger = logging.getLogger(__name__)

# Создаем роутер для приватных команд пользователя
user_private_router = Router()
user_private_router.include_router(user_registration_router)
user_private_router.include_router(user_view_profile_router)

# Кэш для хранения текущей новости и темы для каждого пользователя
# Кэш с тайм-аутом
CACHE_TIMEOUT = 1800 # 30 минут
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
        if user_id in cache and time() - cache_last_access.get(user_id, 0) > CACHE_TIMEOUT:
            del cache[user_id]

        cache[user_id] = item_id
        cache_last_access[user_id] = time()
        items = await fetch_func(session, item_id)
        if not items:
            await (message.answer if isinstance(message, Message) else message.message.edit_text)("Больше элементов нет.")
            return
        text = format_func(items)
        reply_markup_result = kb_func(items, item_id)
        reply_markup = await reply_markup_result if isinstance(reply_markup_result, Awaitable) else reply_markup_result
        if isinstance(message, Message):
            await message.answer(text, reply_markup=reply_markup)
        else:
            await message.message.edit_text(text, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Ошибка пагинации для user_id={user_id}: {e}")
        await (message.answer if isinstance(message, Message) else message.message.edit_text)("Ошибка загрузки.")


# Команда /menu для открытия меню
# @user_private_router.message(Command('menu'))
# async def menu(message: Message) -> None:
#     """Открывает основное меню пользователя."""
#     logger.info(f"Пользователь {message.from_user.id} открыл меню")
#     await message.answer("Открываю меню...", reply_markup=reply.menu_kb)

# Обработчик для команды "новости"
@user_private_router.message(F.text.lower() == 'новости')
async def news(message: Message, session: AsyncSession) -> None:
    """Отправляет сообщение с ссылкой на Telegram-канал новостей."""
    builder = InlineKeyboardBuilder()
    builder.button(text="Перейти в Телеграм канал", url=settings.news_channel_url)
    await message.answer(
        "Сюда присылаются только важные новости.🤷\nВсе новости вы можете посмотреть в Telegram-канале.⤵",
        reply_markup=builder.as_markup()
    )

    # """Показывает первую новость пользователю."""
    # user_id = message.from_user.id
    #
    # await paginate_items(
    #     message, session, user_id, 1,cache_current_news, orm_get_news_by_id,
    #     lambda n: f"<strong>{n.text}</strong>" if n else "Новостей пока нет(((",
    #     lambda n, _: get_callback_btns(btns={"Далее": "news_next"}) if n else None
    # )




# Обработчик для переключения между новостями
@user_private_router.callback_query(F.data.startswith('news_'))
async def slide_news(callback: CallbackQuery, session: AsyncSession) -> None:
    """Переключает новости вперед или назад."""
    user_id = callback.from_user.id
    action = callback.data.split("_")[1]  # Определяем действие (next или back)
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



# Обработчик для команды "материалы"
@user_private_router.message(F.text.lower() == 'материалы')
async def get_material(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Показывает список материалов с ссылками."""
    user_id = message.from_user.id
    await paginate_items(
        message, session, user_id, 0, cache_current_material,
        orm_get_material_by_id,
        lambda ms: "\n".join(f"{m.id}🟦 {m.title}" for m in ms) if ms else "Материалы отсутствуют",
        lambda ms, _: create_material_buttons(ms) if ms else None
    )




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
        builder = InlineKeyboardBuilder()
        for material in mats:
            if material.link:
                builder.button(text=f"Материал №{material.id}", url=material.link)
            else:
                builder.button(text=f"Материал №{material.id} (нет ссылки)", callback_data=f"no_link_{material.id}")
        if prev_exists:
            builder.button(text="Назад", callback_data="slide_material_back")
        if next_exists:
            builder.button(text="Далее", callback_data="slide_material_next")
        builder.adjust(3, 3, 2)
        return builder.as_markup()

    await paginate_items(
        callback, session, user_id, new_id, cache_current_material,
        orm_get_material_by_id,
        lambda ms: "\n".join(f"{m.id}🟦 {m.title}" for m in ms),
        kb_func
    )


    # user_id = callback.from_user.id
    # action = callback.data.split('_')[2]  # Определяем действие (next или back)
    # current_category_id = cache_current_material.get(user_id, 1)
    #
    # if action == 'next':
    #     current_category_id += 1
    # elif action == 'back':
    #     current_category_id = max(0, current_category_id - 1)  # Не опускаемся ниже первой категории
    #
    # cache_current_theme[user_id] = current_category_id
    # materials = await orm_get_material_by_id(session=session, material_id=current_category_id)
    #
    # if materials:
    #     # Проверяем, есть ли следующая категория
    #     next_materials_exists = await orm_get_material_by_id(session=session, material_id=current_category_id + 1)
    #     # Проверяем, есть ли предыдущая категория
    #     prev_materials_exists = await orm_get_material_by_id(session=session, material_id=current_category_id - 1)
    #
    #     # Создаем кнопки для тем
    #
    #     btns = {f'Материал №{material.id}': f'choice_material_{material.id}' for material in materials}
    #
    #
    #     # Добавляем кнопку "Назад", если это не первая категория
    #     if prev_materials_exists:
    #         btns.update({"Назад": "slide_material_back"})
    #
    #     # Добавляем кнопку "Далее", если это не последняя категория
    #     if next_materials_exists:
    #         btns.update({"Далее": "slide_material_next"})
    #
    #     # Создаем клавиатуру
    #     reply_markup = get_callback_btns(btns=btns, sizes=(3, 3, 2))
    #
    #     # Формируем текст с информацией о темах
    #     result_answer = ""
    #     for material in materials:
    #         result_answer += f'{material.id}🟦 {material.title}\n'
    #
    #     await callback.message.edit_text(f"Вывожу список материалов.\n\n{result_answer}", reply_markup=reply_markup)
    # else:
    #     await callback.answer("Материалы пока отсутствуют")





# Обработчик для команды "выбрать тему"
@user_private_router.message(F.text.lower() == 'посмотреть темы')
async def get_theme(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Показывает список тем."""
    user_id = message.from_user.id
    await paginate_items(
        message, session, user_id, 1, cache_current_theme,
        orm_get_all_themes_by_category_id,
        lambda ts: f"Категория: {ts[0].category.title}\n\n" + "\n".join(
            f"{t.id}🟦 {t.title}\n📌Прием: {t.technique}" for t in ts),
        lambda ts, _: get_callback_btns(
            btns=({f"Тема №{t.id}": f"choice_theme_{t.id}" for t in ts} if settings.prod else {}) | {
                "Далее": "slide_theme_next"},
            sizes=(3, 3, 2)
        )
    )

    # user_id = message.from_user.id
    # cache_current_theme[user_id] = 1  # Устанавливаем начальную тему
    # themes = await orm_get_all_themes_by_category_id(session=session, category_id=1)
    #
    # if themes:
    #     if settings.prod:
    #         btns = {f'Тема №{theme.id}': f'choice_theme_{theme.id}' for theme in themes}
    #     else:
    #         btns = {}
    #     btns.update({"Далее": "slide_theme_next"})
    #     reply_markup = get_callback_btns(btns=btns, sizes=(3, 3, 2))
    #
    #     result_answer = f"Категория: {themes[0].category.title}\n\n"
    #     for theme in themes:
    #         result_answer += (f'{theme.id}🟦 {theme.title}\n'
    #                          f'📌Прием: {theme.technique}\n\n')
    #
    #     await message.answer(f"Вывожу список тем.\n\n{result_answer}", reply_markup=reply_markup)
    # else:
    #     await message.answer("Темы пока отсутствуют")

# Обработчик для переключения между темами
@user_private_router.callback_query(F.data.startswith('slide_theme_'))
async def choice_theme(callback: CallbackQuery, session: AsyncSession) -> None:
    """Переключает категории тем."""
    user_id = callback.from_user.id
    action = callback.data.split("_")[2]
    current_id = cache_current_theme.get(user_id, 1)
    new_id = current_id + 1 if action == 'next' else max(1, current_id - 1)

    async def kb_func(themes, _):
        next_exists = await orm_get_all_themes_by_category_id(session, new_id + 1)
        prev_exists = new_id > 1
        btns = {f"Тема №{t.id}": f"choice_theme_{t.id}" for t in themes} if settings.prod else {}
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
    # user_id = callback.from_user.id
    # action = callback.data.split('_')[2]  # Определяем действие (next или back)
    # current_category_id = cache_current_theme.get(user_id, 1)
    #
    # if action == 'next':
    #     current_category_id += 1
    # elif action == 'back':
    #     current_category_id = max(1, current_category_id - 1)  # Не опускаемся ниже первой категории
    #
    # cache_current_theme[user_id] = current_category_id
    # themes = await orm_get_all_themes_by_category_id(session=session, category_id=current_category_id)
    #
    # if themes:
    #     # Проверяем, есть ли следующая категория
    #     next_category_exists = await orm_get_all_themes_by_category_id(session=session, category_id=current_category_id + 1)
    #     # Проверяем, есть ли предыдущая категория
    #     prev_category_exists = await orm_get_all_themes_by_category_id(session=session, category_id=current_category_id - 1)
    #
    #     # Создаем кнопки для тем
    #     if settings.prod:
    #         btns = {f'Тема №{theme.id}': f'choice_theme_{theme.id}' for theme in themes}
    #     else:
    #         btns = {}
    #
    #     # Добавляем кнопку "Назад", если это не первая категория
    #     if prev_category_exists:
    #         btns.update({"Назад": "slide_theme_back"})
    #
    #     # Добавляем кнопку "Далее", если это не последняя категория
    #     if next_category_exists:
    #         btns.update({"Далее": "slide_theme_next"})
    #
    #     # Создаем клавиатуру
    #     reply_markup = get_callback_btns(btns=btns, sizes=(3, 3, 2))
    #
    #     # Формируем текст с информацией о темах
    #     result_answer = f"Категория: {themes[0].category.title}\n\n"
    #     for theme in themes:
    #         result_answer += (f'{theme.id}🟦 {theme.title}'
    #                          f'📌Прием: {theme.technique}\n\n')
    #
    #     # Редактируем сообщение с новыми данными
    #     await callback.message.edit_text(f"Вывожу список тем.\n\n{result_answer}", reply_markup=reply_markup)
    # else:
    #     await callback.answer("Темы в этой категории отсутствуют")

@user_private_router.callback_query(F.data.startswith('choice_theme_'))
async def choice_theme(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Подтверждение выбора темы."""
    theme_id = int(callback.data.split('_')[2])
    theme = await orm_get_theme_by_id(session, theme_id)
    await state.update_data(prev_message_id=callback.message.message_id)
    await callback.message.answer(
        f"Вы выбираете тему:\n\n🟦 {theme.title}\n📌Прием: {theme.technique}\n\nПодтверждаете выбор?",
        reply_markup=get_callback_btns(
            btns={"Подверждаю✅": f"confirm_theme_{theme_id}", "Я передумал❌": "confirm_theme_"})
    )

    # theme_id = int(callback.data.split('_')[2])
    # current_theme = await orm_get_theme_by_id(session=session, theme_id=theme_id)
    #
    # await state.update_data(prev_message_id=callback.message.message_id)
    #
    # reply_markup = get_callback_btns(
    #     btns={
    #         "Подверждаю✅": f"confirm_theme_{theme_id}",
    #         "Я передумал❌": "confirm_theme_"
    #     }
    # )
    #
    # await callback.message.answer(text=f"Вы выбираете тему:\n\n"
    #                                    f"🟦 {current_theme.title}\n"
    #                                    f"📌Прием: {current_theme.technique}\n\n"
    #                                    f"Подтверждаете выбор?",reply_markup=reply_markup)

@user_private_router.callback_query(F.data.startswith("confirm_theme_"))
async def confirm_theme(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Подтверждение или отмена выбора темы."""
    confirm_theme_id = callback.data.split("_")[2]
    if confirm_theme_id:
        user_id = callback.from_user.id
        theme = await orm_get_theme_by_id(session, int(confirm_theme_id))
        await orm_Edit_user_profile(session, user_id, {'edit_theme': f"{theme.title} {theme.technique}"})
        state_data = await state.get_data()
        await callback.bot.delete_messages(callback.message.chat.id,
                                           [callback.message.message_id, state_data.get("prev_message_id")])
        await callback.message.answer("Тема успешно выбрана📥")
    else:
        await callback.message.delete()

    # confirm_theme_id = callback.data.split("_")[2]
    # if confirm_theme_id:
    #     user_id = callback.from_user.id
    #     current_theme = await orm_get_theme_by_id(session=session, theme_id=int(confirm_theme_id))
    #     data = {'edit_theme': f'{current_theme.title} {current_theme.technique}'}
    #     await orm_Edit_user_profile(session=session, user_id=user_id, data=data)
    #
    #     message_ids_to_delete = []
    #     state_data = await state.get_data()
    #     prev_message_id = state_data.get("prev_message_id")
    #
    #     # Добавляем текущее сообщение в список для удаления
    #     message_ids_to_delete.append(callback.message.message_id)
    #     message_ids_to_delete.append(prev_message_id)
    #
    #     await callback.bot.delete_messages(callback.message.chat.id, message_ids_to_delete)
    #
    #
    #     await callback.message.answer("Тема успешна выбрана📥")
    # else:
    #     await callback.message.delete()

# Обработчик для команды "мой профиль"
@user_private_router.message(User_MainStates.after_registration, F.text.lower() == 'мой профиль')
async def get_user_profile(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Показывает профиль пользователя."""
    data = await orm_Get_info_user(session, message.from_user.id)
    if data:
        await state.set_state(User_MainStates.user_view_profile)
        text = (f"📄ФИО: {data.name}\n🏫Школа: {data.school}\n📱Номер телефона: {data.phone_number}\n"
                f"📧Электронная почта: {data.mail}\n👨‍🏫ФИО наставника: {data.name_mentor}\n"
                f"👪Должность наставника: {data.post_mentor or ''}\n📜Тема: {data.theme}")
        await message.answer("Открываю Ваш профиль")
        await message.answer(text, reply_markup=get_keyboard("Редактировать", "Назад", placeholder="Выберите действие",
                                                             sizes=(2,)))
    else:
        await message.answer("Профиль не найден")

    # await state.set_state(User_MainStates.user_view_profile)
    # data = await orm_Get_info_user(session, message.from_user.id)
    # if data:
    #     result_answer = (f"📄ФИО: {data.name}\n"
    #                     f"🏫Школа: {data.school}\n"
    #                     f"📱Номер телефона: {data.phone_number}\n"
    #                     f"📧Электронная почта: {data.mail}\n"
    #                     f"👨‍🏫ФИО наставника: {data.name_mentor}\n"
    #                     f"👪Должность наставника: {data.post_mentor if data.post_mentor else ''}\n"
    #                     f"📜Тема: {data.theme}")
    #
    #     reply_markup = get_keyboard(
    #         "Редактировать",
    #         "Назад",
    #         placeholder="Выберите действие",
    #         sizes=(2,),
    #     )
    #     await message.answer("Открываю Ваш профиль")
    #     await message.answer(result_answer, reply_markup=reply_markup)
    # else:
    #     await message.answer("Профиль не найден")






# @user_private_router.message(Command('admin'))
# async def admin(message: Message, session: AsyncSession, state: FSMContext):
#     list_admins = list(await orm_get_list_admin(session=session))
#     print(list_admins)
#     if message.from_user.username == settings.USER_ADMIN_NICK or message.from_user.id in list_admins:
#         reply_markup = admin_kb
#         if message.from_user.id not in list_admins:
#             await orm_add_admin(session=session, user_id=message.from_user.id, username=message.from_user.username)
#         if message.from_user.username == settings.USER_ADMIN_NICK:
#             reply_markup = admin_kb
#             reply_markup.keyboard[1].append(KeyboardButton(text="Добавить админа"))
#         await message.answer(text="Вы вошли как админ", reply_markup=reply_markup)
#         await state.set_state(Admin_MainStates.choice_action)
#     else:
#         await message.answer(text="У вас недостаточно прав")


