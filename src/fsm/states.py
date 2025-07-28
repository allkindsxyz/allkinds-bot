from aiogram.fsm.state import State, StatesGroup

class CreateGroup(StatesGroup):
    name = State()
    description = State()

class Onboarding(StatesGroup):
    nickname = State()
    photo = State()
    intro = State()
    gender = State()
    looking_for = State()
    location = State()

class JoinGroup(StatesGroup):
    code = State() 