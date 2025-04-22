from aiogram.fsm.state import StatesGroup, State

class User_MainStates(StatesGroup):
    user_edit_profile = State()
    before_registration = State()
    after_registration = State()
    user_view_profile = State()


class EditWorkLink(StatesGroup):
    waiting_link = State()
    confirm_changes = State()

class ChoiceTheme(StatesGroup):
    current_theme = State()
    prev_message_id = State()