from aiogram.fsm.state import StatesGroup, State


class Admin_MainStates(StatesGroup):
    choice_action = State()
    add_admin = State()

class AddNews(StatesGroup):
    add_title = State()
    add_description = State()
    add_image = State()
    confirm_add = State()

