from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from src.texts.messages import get_message

def get_gender_keyboard(user):
    """Keyboard for gender selection."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👨 Мужчина", callback_data="gender_male"),
            InlineKeyboardButton(text="👩 Женщина", callback_data="gender_female")
        ]
    ])

def get_looking_for_keyboard(user):
    """Keyboard for looking_for selection."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👨 Мужчину", callback_data="looking_for_male"),
            InlineKeyboardButton(text="👩 Женщину", callback_data="looking_for_female")
        ],
        [
            InlineKeyboardButton(text="👥 Всех", callback_data="looking_for_all")
        ]
    ]) 