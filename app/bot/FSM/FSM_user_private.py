from aiogram.fsm.state import StatesGroup, State

class User_MainStates(StatesGroup):
    user_edit_profile = State()
    before_registration = State()
    after_registration = State()
    user_view_profile = State()


class RegistrationUser(StatesGroup):
    name_user = State()
    user_id = State()
    school = State()
    phone_number = State()
    mail = State()
    verify_mail = State()
    name_mentor = State()
    status_mentor = State()
    post_mentor = State()
    input_status_mentor = State()

class EditProfile(StatesGroup):
    edit_name = State()
    edit_school = State()
    edit_phone_number = State()
    edit_mail = State()
    edit_name_mentor = State()
    edit_post_mentor = State()
    confirm_changes = State()
    verify_mail = State()

class ChoiceTheme(StatesGroup):
    current_theme = State()
    prev_message_id = State()