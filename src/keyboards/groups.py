# Генерация клавиатур для групп 
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from src.constants import POINTS_FOR_MATCH

create_group_btn = InlineKeyboardButton(text="Create a new group", callback_data="create_new_group")
join_group_btn = InlineKeyboardButton(text="Join another group with code", callback_data="join_another_group_with_code")

def get_admin_keyboard(groups):
    kb = [[create_group_btn, join_group_btn]]
    for g in groups:
        kb.append([InlineKeyboardButton(text=f"Switch to {g['name']}", callback_data=f"switch_to_group_{g['id']}" )])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_user_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[join_group_btn]])

def go_to_group_keyboard(group_id, group_name):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"Switch to {group_name}", callback_data=f"switch_to_group_{group_id}")]])

def get_group_main_keyboard(user_id, group_id, group_name, is_creator):
    rows = []
    if is_creator:
        rows.append([InlineKeyboardButton(text=f"Delete {group_name}", callback_data=f"confirm_delete_group_{group_id}")])
    else:
        rows.append([InlineKeyboardButton(text=f"Leave {group_name}", callback_data=f"confirm_leave_group_{group_id}")])
    # Кнопка мэтча убрана из inline-клавиатуры
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_confirm_delete_keyboard(group_id):
    kb = [[
        InlineKeyboardButton(text="Delete", callback_data=f"delete_group_yes_{group_id}"),
        InlineKeyboardButton(text="Cancel", callback_data=f"delete_group_cancel_{group_id}")
    ]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def location_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[InlineKeyboardButton(text="📍 Send location", request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_group_reply_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=f"Who is vibing the most right now ({POINTS_FOR_MATCH}💎)")]],
        resize_keyboard=True,
        one_time_keyboard=False
    ) 