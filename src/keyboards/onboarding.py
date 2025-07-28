from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from src.texts.messages import get_message

def get_gender_keyboard(user):
    """Keyboard for gender selection."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=get_message("BTN_GENDER_MALE", user=user), callback_data="gender_male"),
            InlineKeyboardButton(text=get_message("BTN_GENDER_FEMALE", user=user), callback_data="gender_female")
        ]
    ])

def get_looking_for_keyboard(user):
    """Keyboard for looking_for selection."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=get_message("BTN_LOOKING_FOR_MALE", user=user), callback_data="looking_for_male"),
            InlineKeyboardButton(text=get_message("BTN_LOOKING_FOR_FEMALE", user=user), callback_data="looking_for_female")
        ],
        [
            InlineKeyboardButton(text=get_message("BTN_LOOKING_FOR_ALL", user=user), callback_data="looking_for_all")
        ]
    ]) 