from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

role_inline_kb = InlineKeyboardMarkup(
    inline_keyboard= [
        [InlineKeyboardButton(text="Учитель", callback_data="role_teacher"),
         InlineKeyboardButton(text="Родитель/Опекун", callback_data="role_parent"),
         InlineKeyboardButton(text="Иное", callback_data="role_other"),
         ],
    ]
)

def get_callback_btns(
        *,
        btns: dict[str, str],
        sizes: tuple[int] = (2,)):

        keyboard = InlineKeyboardBuilder()

        for text, data in btns.items():
            keyboard.add(InlineKeyboardButton(text=text, callback_data=data))
        return keyboard.adjust(*sizes).as_markup()


news_kbd = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Далее", callback_data='1'),
        InlineKeyboardButton(text='Назад', callback_data='2'),
         ],
    ]
)

def create_material_buttons(materials: list) -> InlineKeyboardMarkup:
    """Создает инлайн-кнопки с URL из таблицы Material."""
    builder = InlineKeyboardBuilder()
    for material in materials:
        # Проверяем наличие ссылки и добавляем кнопку
        if material.link:
            builder.button(text=f"Материал №{material.id}", url=material.link)
        else:
            builder.button(text=f"Материал №{material.id} (нет ссылки)", callback_data=f"no_link_{material.id}")
    builder.button(text="Далее", callback_data="slide_material_next")
    builder.adjust(3, 3, 2)  # Аналог sizes=(3, 3, 2)
    return builder.as_markup()
