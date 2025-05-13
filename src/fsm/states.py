from aiogram.fsm.state import State, StatesGroup

class CreateGroup(StatesGroup):
    name = State()
    description = State()

class Onboarding(StatesGroup):
    nickname = State()
    photo = State()
    location = State()

class JoinGroup(StatesGroup):
    code = State() 