import logging

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from sqlalchemy.ext.asyncio import AsyncSession


from app.bot.FSM.FSM_user_private import RegistrationUser, User_MainStates
from app.bot.common.validation import validate_fio, validate_phone_number, validate_email_format
from app.bot.common.verif_mail import start_verify_mail, \
    check_verify_code
from app.kbds import reply
from app.kbds.inline import role_inline_kb, get_callback_btns
from app.database.orm_query import orm_Change_RegStaus, orm_AddActiveUser


logger = logging.getLogger(__name__)
user_registration_router = Router()

# Обработчик для команды "зарегистрироваться"
@user_registration_router.message(User_MainStates.before_registration, F.text.lower() == 'зарегистрироваться')
async def process_action(message: Message, state: FSMContext) -> None:
    """Начинает процесс регистрации."""
    logger.info(f"Пользователь {message.from_user.id} начал регистрацию")

    reply_markup = get_callback_btns(
        btns={
            "Да": "user_registartion_true",
            "Я передумал": "user_registration_false",
            },
        sizes=(2,)
    )

    await message.answer("Отлично, давай начнем регистрацию.👍", reply_markup=reply.del_kbd ,)
    await message.answer( "Необходимо будет написать:\n"
                         "1️⃣ Фамилия Имя Отчество;\n"
                         "2️⃣ Название школы;\n"
                         "3️⃣ Номер Вашего телефона;\n"
                         "4️⃣ Фамилию Имя Отчество наставника;\n"
                         "5️⃣ Должность наставника;\n"
                         "6️⃣ Адрес Вашей электронной почты.\n\n"
                         "После на Вашу почту будет выслан код подтверждения.\n"
                          "Если Вы допустили ошибку, то отредактировать профиль можно после регистрации.\n"
                          "Готовы начать?", reply_markup=reply_markup)


@user_registration_router.callback_query(User_MainStates.before_registration)
async def confirm_registration(callback: CallbackQuery, state: FSMContext):
    if callback.data == "user_registartion_true":
        await callback.message.delete_reply_markup()
        await callback.message.answer("Введите Ваше ФИО в формате (Фамилия Имя Отчество)", reply_markup=None)
        await state.set_state(RegistrationUser.name_user)
    else:
        await callback.message.delete_reply_markup()
        await callback.message.answer("Очень жаль(")

#Код ниже для машины состояний (FSM) для регистрации участника
@user_registration_router.message(RegistrationUser.name_user)
async def register_step_name(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод ФИО."""
    fio = message.text.strip()
    if validate_fio(fio):
        logger.info(f"Пользователь {message.from_user.id} ввел ФИО: {fio}")
        await state.update_data(name_user=fio)
        await message.answer('Введите полное название вашей школы')
        await state.set_state(RegistrationUser.school)
    else:
        await message.answer("Пожалуйста, введи ФИО в правильном формате (Фамилия Имя Отчество).")

@user_registration_router.message(RegistrationUser.school)
async def register_step_phone_number(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод школы."""
    logger.info(f"Пользователь {message.from_user.id} ввел школу: {message.text}")
    await state.update_data(school=message.text.strip())
    await message.answer('Введите номер Вашего телефона в формате +7XXXXXXXXXX или 8XXXXXXXXXX.')
    await state.set_state(RegistrationUser.phone_number)


@user_registration_router.message(RegistrationUser.phone_number, F.text)
async def register_step_mail(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод телефона."""
    phone = message.text.strip()
    if validate_phone_number(phone):
        logger.info(f"Пользователь {message.from_user.id} ввел телефон: {phone}")
        await state.update_data(phone_number=phone)
        await message.answer("Введите ФИО вашего наставника в формате (Фамилия Имя Отчество)")
        await state.set_state(RegistrationUser.name_mentor)

    else:
        await message.answer("Пожалуйста, введите номер телефона в формате +7XXXXXXXXXX или 8XXXXXXXXXX.")


@user_registration_router.message(RegistrationUser.mail, F.text)
async def register_step_name_mentor(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод почты и отправляет код верификации."""
    email = message.text.strip()

    if validate_email_format(email=email):
        reply_markup = get_callback_btns(
            btns={
                "Отправить код": "send_email_code",
                "Изменить почту": "edit_email",
            },
            sizes=(2,)
        )
        await state.update_data(mail=email)
        logger.info(f"Пользователь {message.from_user.id} ввел почту: {email}")
        await message.answer(f"Вы ввели почту: {email}\n"
                              f"Если почта введена правильно, нажмите 'Отправить код'", reply_markup=reply_markup)

    else:
        await message.answer(text="Неверный формат электронной почты. Пожалуйста введите почту в правильном формате")


@user_registration_router.callback_query(RegistrationUser.mail)
async def confirm_or_edit_email(callback: CallbackQuery, state: FSMContext):
    if callback.data == "send_email_code":
        await callback.message.delete_reply_markup()
        try:
            email = await state.get_value("mail")
            await start_verify_mail(email, callback.from_user.id)
            print(email, callback.from_user.id)
            await callback.message.answer(text="На вашу почту был отправлен код подтверждения. Пожалуйста введите код")
            await state.set_state(RegistrationUser.verify_mail)
        except Exception as e:
            logger.error(f"Ошибка отправки кода на почту user_id={callback.message.from_user.id}: {e}")
            await callback.message.answer("Ошибка при отправке кода. Проверьте почту и попробуйте снова")
    elif callback.data == "edit_email":
        await callback.message.delete_reply_markup()
        await callback.message.answer('Введите адрес Вашей электронной почты')

@user_registration_router.message(RegistrationUser.verify_mail, F.text)
async def register_step_verify_mail(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Проверяет код верификации почты."""
    if check_verify_code(message.text, message.from_user.id):
        logger.info(f"Пользователь {message.from_user.id} подтвердил почту")
        await message.answer("Подтверждение почты успешно пройдено")
        await register_step_finish(message, state, session, message.from_user.id)
    else:
        await message.answer("Неправильный код. Попробуйте еще раз")

@user_registration_router.message(RegistrationUser.name_mentor, F.text)
async def register_step_status_mentor(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод ФИО наставника."""
    fio = message.text.strip()
    if validate_fio(fio):
        logger.info(f"Пользователь {message.from_user.id} ввел ФИО наставника: {fio}")
        await state.update_data(name_mentor=fio)
        await message.answer("Выберите роль вашего наставника", reply_markup=role_inline_kb)
        await state.set_state(RegistrationUser.status_mentor)
    else:
        await message.answer("Введите ФИО в формате (Фамилия Имя Отчество)")

#Обработка Инлайн при регистрации пользователя
@user_registration_router.callback_query(RegistrationUser.status_mentor)
async def process_callback(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Обрабатывает выбор роли наставника."""
    role = callback.data.split('_')[1]
    await callback.answer()
    if role == 'teacher':
        await callback.message.answer("Введите должность вашего наставника")
        await state.set_state(RegistrationUser.post_mentor)
    elif role == 'other':
        await callback.message.answer("Введите роль вашего наставника")
        await state.set_state(RegistrationUser.input_status_mentor)
    else:
        await state.update_data(post_mentor="Родитель/опекун")
        await callback.message.delete_reply_markup()
        await callback.message.answer('Введите адрес Вашей электронной почты')
        await state.set_state(RegistrationUser.mail)


@user_registration_router.message(RegistrationUser.input_status_mentor)
async def register_input_status_mentor(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Обрабатывает ввод роли наставника."""
    logger.info(f"Пользователь {message.from_user.id} ввел роль наставника: {message.text}")
    await state.update_data(post_mentor=message.text.strip())
    await message.answer('Введите адрес Вашей электронной почты')
    await state.set_state(RegistrationUser.mail)

@user_registration_router.message(RegistrationUser.post_mentor)
async def register_input_post_mentor(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Обрабатывает ввод должности наставника."""
    logger.info(f"Пользователь {message.from_user.id} ввел должность наставника: {message.text}")
    await state.update_data(post_mentor=message.text.strip())
    await message.answer('Введите адрес Вашей электронной почты')
    await state.set_state(RegistrationUser.mail)


# @user_private_router.message(AddUser.input_status_mentor)
# @user_private_router.message(AddUser.post_mentor)
async def register_step_finish(message: Message, state: FSMContext, session: AsyncSession, user_id: int = None) -> None:
    """Завершает регистрацию."""

    try:
        data = await state.get_data()
        data["user_id"] = user_id
        await orm_Change_RegStaus(session, user_id, True)
        await orm_AddActiveUser(session, data)
        logger.info(f"Пользователь {user_id} завершил регистрацию")
        await message.answer('Регистрация успешно пройдена.', reply_markup=reply.menu_kb)
        await message.answer("""
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
""")
        result_answer = (f"📄ФИО: {data['name_user']}\n"
                         f"🏫Школа: {data['school']}\n"
                         f"📱Номер телефона: {data['phone_number']}\n"
                         f"📧электронная почта: {data['mail']}\n"
                         f"👨‍🏫ФИО наставника: {data['name_mentor']}\n"
                         f"{"👪Должность наставника: " + data['post_mentor'] if data['post_mentor'] else ''}")
        await message.answer(result_answer)
        await state.set_state(User_MainStates.after_registration)
        await state.set_data({})

    except Exception as e:
        logger.error(f"Ошибка завершения регистрации user_id={user_id}: {e}")
        await message.answer("Ошибка при регистрации. Попробуйте позже")
        await state.clear()

@user_registration_router.message(F.text.lower() == "отмена", RegistrationUser())
async def cancel_registration(message: Message, state: FSMContext) -> None:
    """Отменяет регистрацию."""
    logger.info(f"Пользователь {message.from_user.id} отменил регистрацию")
    await message.answer("Регистрация отменена.", reply_markup=reply.menu_kb)
    await state.clear()

#     try:
#         if user_id:
#             await state.update_data(user_id=user_id)
#             await orm_Change_RegStaus(session, user_id, True)
#         else:
#             await state.update_data(user_id=message.from_user.id)
#             await orm_Change_RegStaus(session, message.from_user.id, True)
#         data = await state.get_data()
#         await message.answer('Регистрация успешно пройдена.')
#         await message.answer("""
# 📢 Приветствие участникам конкурса «РЕПИН НАШ!»
# 🔹 Почему вы здесь?
# Ты, наверное, слышал про Илью Репина — великого художника, автора «Бурлаков на Волге». Но вот странность: в финском музее «Атенеум» вдруг решили, что Репин — не русский художник, а украинский. Как так? Ведь он сам писал, что его вдохновила русская Волга, что он увидел в бурлаках силу и характер русского народа!
# Что мы будем с этим делать? Ответ простой: показать, что Репин – наш!
# 🔹 Зачем этот конкурс?
# Мы не просто будем говорить, а докажем историческую правду через цифровое искусство. Ты сможешь создать виртуальную выставку, где расскажешь о Репине и его связи с Самарой, Волгой, бурлаками, русской культурой. Это твой шанс стать художником, исследователем и рассказчиком одновременно!
# 🔹 Ты точно справишься!
# Мы верим в тебя! У тебя уже есть всё, чтобы создать крутой проект:
# ✅ Наставники – лучшие эксперты помогут и подскажут.
# ✅ Материалы – вся нужная информация о Репине, Самаре и истории есть в этом боте.
# ✅ Пошаговые инструкции – мы будем вести тебя от выбора идеи до создания выставки.
# ✅ Современные технологии – ты попробуешь 3D-моделирование, нейросети, интерактивные элементы.
# 🔹 Что делать дальше?
# 💡 Прочитай условия конкурса.
# 💡 Выбери свою тему – тебя ждёт 30 идей!
# 💡 Следи за нашими постами – мы расскажем, как создать выставку шаг за шагом.
# 📢 Репин наш! Самара – его вдохновение! А ты – тот, кто покажет это миру! 🚀
# """)
#         await orm_AddActiveUser(session, data)
#         result_answer = (f"📄ФИО: {data['name_user']}\n"
#                          f"🏫Школа: {data['school']}\n"
#                          f"📱Номер телефона: {data['phone_number']}\n"
#                          f"📧электронная почта: {data['mail']}\n"
#                          f"👨‍🏫ФИО наставника: {data['name_mentor']}\n"
#                          f"{"👪Должность наставника: " + data['post_mentor'] if data['post_mentor'] else ''}")
#
#         await message.answer(result_answer)
#         await message.answer('Открываю меню...', reply_markup=reply.menu_kb)
#         await state.set_state(User_MainStates.after_registration)
#         await state.set_data({})
#
#     except Exception as e:
#         await message.answer("Что-то пошло не так... Попробуйте позже")
#         await state.clear()



