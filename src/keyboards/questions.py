# Генерация клавиатур для вопросов и ответов 
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from src.texts.messages import QUESTION_DELETE, QUESTION_LOAD_MORE

ANSWER_VALUES = [(-2, "👎👎"), (-1, "👎"), (0, "⏭️"), (1, "👍"), (2, "👍👍")]
ANSWER_VALUE_TO_EMOJI = dict(ANSWER_VALUES)

def get_answer_keyboard(question_id, is_author=False, is_creator=False):
    answer_buttons = [InlineKeyboardButton(text=emoji, callback_data=f"answer_{question_id}_{val}") for val, emoji in ANSWER_VALUES]
    keyboard = [answer_buttons]
    if is_author or is_creator:
        keyboard.append([InlineKeyboardButton(text="Delete", callback_data=f"delete_question_{question_id}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_delete_keyboard(question_id):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=QUESTION_DELETE, callback_data=f"delete_question_{question_id}")]])

def get_load_more_keyboard(page):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=QUESTION_LOAD_MORE, callback_data=f"load_answered_questions_more_{page}")]]) 