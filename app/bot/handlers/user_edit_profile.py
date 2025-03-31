from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.FSM.FSM_user_private import User_MainStates, EditProfile
from app.bot.common.validation import validate_fio, validate_phone_number, validate_email_format
from app.bot.common.verif_mail import start_verify_mail, check_verify_code

from app.kbds.reply import get_keyboard, menu_kb
from app.database.orm_query import orm_Edit_user_profile, orm_Get_info_user

user_view_profile_router = Router()

@user_view_profile_router.message(User_MainStates.user_view_profile, F.text)
async def change_edit_profile(message: Message, state: FSMContext):
    if message.text.lower() == 'редактировать':
        reply_markup = get_keyboard(
            "ФИО",
            "Название школы",
            "Номер телефона",
            "Электронную почту",
            "ФИО наставника",
            "Должность наставника",
            "Назад",
            placeholder="Выберите:",
            sizes=(2,),
        )
        await message.answer(text="Открываю меню редактирования профиля.\nВыберите в меню что хотите изменить.\nВывожу меню...", reply_markup=reply_markup)
        await state.set_state(User_MainStates.user_edit_profile)
    elif message.text.lower() == 'назад':
        reply_markup = menu_kb
        await message.answer(
            text="Открываю основное меню...",
            reply_markup=reply_markup)
        await state.set_state(User_MainStates.after_registration)

@user_view_profile_router.message(User_MainStates.user_edit_profile, F.text)
async def edit_profile(message: Message, state: FSMContext):
    if message.text.lower() == "фио":
        await state.set_state(EditProfile.edit_name)
        reply_markup = get_keyboard("Отменить")
        await message.answer("Введи новое ФИО", reply_markup=reply_markup)

    elif message.text.lower() == "название школы":
        await state.set_state(EditProfile.edit_school)
        reply_markup = get_keyboard("Отменить")
        await message.answer("Введи новое название школы", reply_markup=reply_markup)

    elif message.text.lower() == "электронную почту":
        await state.set_state(EditProfile.edit_mail)
        reply_markup = get_keyboard("Отменить")
        await message.answer("При редактировании почты нужно заново пройти подтверждение.\n\nВведи новый адрес почты", reply_markup=reply_markup)

    elif message.text.lower() == "фио наставника":
        await state.set_state(EditProfile.edit_name_mentor)
        reply_markup = get_keyboard("Отменить")
        await message.answer("Введи новое ФИО наставника", reply_markup=reply_markup)

    elif message.text.lower() == "должность наставника":
        await state.set_state(EditProfile.edit_post_mentor)
        reply_markup = get_keyboard("Отменить")
        await message.answer("Введи новое должность наставника", reply_markup=reply_markup)

    elif message.text.lower() == "номер телефона":
        await state.set_state(EditProfile.edit_phone_number)
        reply_markup = get_keyboard("Отменить")
        await message.answer("Введи новый номер телефона", reply_markup=reply_markup)
    elif message.text.lower() == "назад":
        await state.set_state(User_MainStates.user_view_profile)
        reply_markup = get_keyboard(
            "Редактировать",
            "Назад",
            placeholder="Выберите действие",
            sizes=(2,),
        )
        await message.answer(text="Вы вернулись в меню профиля.", reply_markup=reply_markup)
    else:
        await message.answer(text="Пожалуйста выберите действие")


@user_view_profile_router.message(StateFilter(EditProfile.edit_name, EditProfile.edit_school,
                                          EditProfile.edit_mail, EditProfile.edit_name_mentor,
                                          EditProfile.edit_post_mentor, EditProfile.edit_phone_number,), F.text)
async def edit_profile(message: Message, state: FSMContext):
    if message.text.lower() == "отменить":
        reply_markup = get_keyboard(
            "ФИО",
            "Название школы",
            "Номер телефона",
            "Электронную почту",
            "ФИО наставника",
            "Должность наставника",
            "Назад",
            placeholder="Выберите:",
            sizes=(2,),
        )
        await state.set_state(User_MainStates.user_edit_profile)
        await message.answer(text="Изменение отменено.\n"
                                  "Открываю меню редактирования профиля.\n"
                                  "Выберите в меню что хотите изменить.", reply_markup=reply_markup)
    else:

        current_state = str(await state.get_state()).lstrip("EditProfile")
        reply_markup = get_keyboard(
            "Да, подтверждаю",
            "Я передумал",
            placeholder="Выберите:",
            sizes=(2,),
        )
        if current_state == ':edit_name':
            fio = message.text.strip()
            if validate_fio(fio):
                await state.update_data(edit_name=fio)
                await message.answer(f"Вы изменяете имя на: {message.text}\n\n"
                                     f"Подтверждаете изменения?", reply_markup=reply_markup)
                await state.set_state(EditProfile.confirm_changes)
            else:
                await message.answer("Пожалуйста, введи ФИО в правильном формате (Фамилия Имя Отчество).")


        elif current_state == ':edit_school':
            await state.update_data(edit_school=message.text)
            await message.answer(f"Вы изменяете название школы на: {message.text}\n\n"
                                 f"Подтверждаете изменения?", reply_markup=reply_markup)
            await state.set_state(EditProfile.confirm_changes)

        elif current_state == ':edit_phone_number':
            phone_number = message.text
            if validate_phone_number(phone_number):
                await state.update_data(edit_phone_number=message.text)
                await message.answer(f"Вы изменяете номер телефона на: {message.text}\n\n"
                                     f"Подтверждаете изменения?", reply_markup=reply_markup)
                await state.set_state(EditProfile.confirm_changes)
            else:
                await message.answer("Пожалуйста, введите номер телефона в формате +7XXXXXXXXXX или 8XXXXXXXXXX.")

        elif current_state == ':edit_mail':
            email = message.text
            if validate_email_format(email):
                await state.update_data(edit_mail=message.text)
                await message.answer(f"Вы изменяете адрес электронной почты на: {message.text}\n\n"
                                     f"Подтверждаете изменения?", reply_markup=reply_markup)
                await state.set_state(EditProfile.confirm_changes)
            else:
                await message.answer(
                    text="Неверный формат электронной почты. Пожалуйста введите почту в правильном формате")

        elif current_state == ':edit_name_mentor':
            fio = message.text.strip()
            if validate_fio(fio):
                await state.update_data(edit_name_mentor=fio)
                await message.answer(f"Вы изменяете ФИО наставника на: {message.text}\n\n"
                                     f"Подтверждаете изменения?", reply_markup=reply_markup)
                await state.set_state(EditProfile.confirm_changes)
            else:
                await message.answer("Пожалуйста, введите ФИО в правильном формате (Фамилия Имя Отчество).")
        elif current_state == ':edit_post_mentor':
            await state.update_data(edit_post_mentor=message.text)
            await message.answer(f"Вы изменяете должность наставника на: {message.text}\n\n"
                                 f"Подтверждаете изменения?", reply_markup=reply_markup)
            await state.set_state(EditProfile.confirm_changes)

@user_view_profile_router.message(EditProfile.verify_mail)
async def verify_mail(message: Message, state: FSMContext, session: AsyncSession):
    if message.text.lower() == 'я передумал':

        reply_markup = get_keyboard(
            "ФИО",
            "Название школы",
            "Номер телефона",
            "Электронную почту",
            "ФИО наставника",
            "Должность наставника",
            "Назад",
            placeholder="Выберите:",
            sizes=(2,),
        )
        await state.set_state(User_MainStates.user_edit_profile)
        await message.answer(text='Хорошо. Возвращаю вас в меню вашего профиля', reply_markup=reply_markup)
        await state.set_data({})
        return
    if check_verify_code(message.text, message.from_user.id):
        data = await state.get_data()
        print("После подвтверждения", data)
        await message.answer(text="Подтверждение почты успешно пройдено")
        await orm_Edit_user_profile(session=session, user_id=message.from_user.id, data=data)

        data = await orm_Get_info_user(session, message.from_user.id)
        await message.answer(text="Данные успешно изменены.\nПеревожу Вас в меню Вашего профиля...")
        result_answer = f"""
                                    ФИО: {data.name}
                                    Школа: {data.school}
                                    Номер телефона: {data.phone_number}
                                    электронная почта: {data.mail}
                                    ФИО наставника: {data.name_mentor}
                                    {"Должность наставника: " + data.post_mentor if data.post_mentor else ''}"""
        reply_markup = get_keyboard(
            "Редактировать",
            "Назад",
            placeholder="Выберите действие",
            sizes=(2,),
        )

        await message.answer(result_answer, reply_markup=reply_markup)
        await state.set_data({})
        await state.set_state(User_MainStates.user_view_profile)

    else:
        await message.answer(text="Введен неправильный код. Попробуйте еще раз")

@user_view_profile_router.message(EditProfile.confirm_changes)
async def confirm_changes(message: Message, state: FSMContext, session: AsyncSession):
    if message.text.lower() == 'да, подтверждаю':
        data = await state.get_data()
        print("При верификации", data)
        if list(data.keys())[0] == 'edit_mail':
            try:
                # await state.update_data(mail=data['edit_mail'])
                await start_verify_mail(data['edit_mail'], message.from_user.id)
                await state.set_state(EditProfile.verify_mail)
            except Exception as e:
                pass
            finally:
                reply_markup = get_keyboard(
                    "Я передумал",
                    placeholder="Выберите:",
                    sizes=(2,),
                )
                await message.answer(text="На вашу почту был отправлен код подтверждения. Пожалуйста введите код", reply_markup=reply_markup)
        else:
            try:
                await orm_Edit_user_profile(session=session, user_id=message.from_user.id, data=data)

                data = await orm_Get_info_user(session, message.from_user.id)
                await message.answer(text="Данные успешно изменены.\nПеревожу Вас в меню Вашего профиля...")
                result_answer = f"""
                                ФИО: {data.name}
                                Школа: {data.school}
                                Номер телефона: {data.phone_number}
                                электронная почта: {data.mail}
                                ФИО наставника: {data.name_mentor}
                                {"Должность наставника: " + data.post_mentor if data.post_mentor else ''}"""
                reply_markup = get_keyboard(
                    "Редактировать",
                    "Назад",
                    placeholder="Выберите действие",
                    sizes=(2,),
                )

                await message.answer(result_answer, reply_markup=reply_markup)
                await state.set_data({})
                await state.set_state(User_MainStates.user_view_profile)
            except Exception as e:
                await message.answer(text= "При редактировании что-то пошло не так... Попробуйте позже")

    elif message.text.lower() == 'я передумал':
        reply_markup = get_keyboard(
            "ФИО",
            "Название школы",
            "Номер телефона",
            "Электронную почту",
            "ФИО наставника",
            "Должность наставника",
            "Назад",
            placeholder="Выберите:",
            sizes=(2,),
        )
        await state.set_state(User_MainStates.user_edit_profile)
        await message.answer(text="Изменения не были подтверждены.\n"
                                  "Открываю меню редактирования профиля.\n"
                                  "Выберите в меню что хотите изменить.", reply_markup=reply_markup)
        await state.set_data({})
    else:
        await message.answer(text="Пожалуйста, подтвердите изменения")

# @user_edit_profile_router.callback_query(MainStates.after_registration)
# @user_edit_profile_router.callback_query(F.data.startswith("edit_"))
# async def change_edit_profile_callback(callback_query: types.CallbackQuery, session: AsyncSession, state: FSMContext):
#     if callback_query.data.lstrip('edit_') == 'profile':
#         reply_markup = get_callback_btns(
#             btns={
#                 "Редактировать ФИО": f"edit_profile_name",
#                 "Редактировать название школы": f"edit_profile_school",
#                 "Редактировать номер телефона": f"edit_profile_phone_number",
#                 "Редактировать электронную почту": f"edit_profile_email",
#                 "Редактировать ФИО наставника": f"edit_profile_name_mentor",
#                 "Редактировать должность наставника": f"edit_profile_post_mentor",
#                 "Назад": f"edit_back"
#
#             }
#             )
#         await callback_query.message.edit_reply_markup(reply_markup=reply_markup)
#     elif callback_query.data.lstrip('edit_') == 'profile_name':
#         await state.set_state(EditProfile.edit_name)
#         await callback_query.message.answer("Введи новое ФИО")
#     elif callback_query.data.lstrip('edit_') == 'profile_school':
#         await state.set_state(EditProfile.edit_school)
#         await callback_query.message.answer("Введи новое название школы")
#     elif callback_query.data.lstrip('edit_') == 'profile_phone_number':
#         await state.set_state(EditProfile.edit_phone_number)
#         await callback_query.message.answer("Введи новый номер телефона")
#     elif callback_query.data.lstrip('edit_') == 'profile_email':
#         await state.set_state(EditProfile.edite_mail)
#         await callback_query.message.answer("Введи новую почту")
#     elif callback_query.data.lstrip('edit_') == 'profile_name_mentor':
#         await state.set_state(EditProfile.edit_name_mentor)
#         await callback_query.message.answer("Введи новое ФИО наставника")
#     elif callback_query.data.lstrip('edit_') == 'profile_post_mentor':
#         await state.set_state(EditProfile.edit_post_mentor)
#         await callback_query.message.answer("Введи новую должность наставника")
#     elif callback_query.data.lstrip('edit_') == 'back':
#         reply_markup = get_callback_btns(
#             btns={
#                 "Редактировать": f"edit_profile"
#             }
#         )
#         await state.set_state(MainStates.after_registration)
#         await callback_query.message.edit_reply_markup(reply_markup=reply_markup)
#
# @user_edit_profile_router.message(StateFilter(EditProfile.edit_name, EditProfile.edit_school,
#                                          EditProfile.edite_mail, EditProfile.edit_name_mentor,
#                                          EditProfile.edit_post_mentor, EditProfile.edit_phone_number,))
# async def edit_profile(message: Message, session: AsyncSession, state: FSMContext):
#     current_state = str(await state.get_state()).lstrip("EditProfile")
#     if current_state == ':edit_name':
#         await message.answer(f"Вы изменили имя на: {message.text}")
#         await state.set_state(MainStates.after_registration)
#     elif current_state == ':edit_school':
#         await message.answer(f"Вы изменили навзвание школы на: {message.text}")
#         await state.set_state(MainStates.after_registration)
#     elif current_state == ':edit_phone_number':
#         await message.answer(f"Вы изменили номер телефона на: {message.text}")
#         await state.set_state(MainStates.after_registration)
#     elif current_state == ':edit_mail':
#         await message.answer(f"Вы изменили адрес электронной почты на: {message.text}")
#         await state.set_state(MainStates.after_registration)
#     elif current_state == ':edit_name_mentor':
#         await message.answer(f"Вы изменили имя наставника на: {message.text}")
#         await state.set_state(MainStates.after_registration)
#     elif current_state == ':edit_post_mentor':
#         await message.answer(f"Вы изменили должность наставника на: {message.text}")
#         await state.set_state(MainStates.user_edit_profile_router)