# Generate keyboards for groups 
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from src.constants import POINTS_FOR_MATCH
from src.texts.messages import get_message, BTN_CREATE_GROUP, BTN_JOIN_GROUP, BTN_SWITCH_TO, BTN_DELETE_GROUP, BTN_LEAVE_GROUP, BTN_DELETE, BTN_CANCEL, BTN_SEND_LOCATION, BTN_WHO_IS_VIBING

def get_admin_keyboard(groups, user):
    kb = [[
        InlineKeyboardButton(text=get_message(BTN_CREATE_GROUP, user=user), callback_data="create_new_group"),
        InlineKeyboardButton(text=get_message(BTN_JOIN_GROUP, user=user), callback_data="join_another_group_with_code")
    ]]
    for g in groups:
        kb.append([
            InlineKeyboardButton(text=get_message(BTN_SWITCH_TO, user=user, group_name=g['name']), callback_data=f"switch_to_group_{g['id']}")
        ])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_user_keyboard(user):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=get_message(BTN_JOIN_GROUP, user=user), callback_data="join_another_group_with_code")]])

def go_to_group_keyboard(group_id, group_name, user):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=get_message(BTN_SWITCH_TO, user=user, group_name=group_name), callback_data=f"switch_to_group_{group_id}")]])

def get_group_main_keyboard(user_id, group_id, group_name, is_creator, user):
    rows = []
    if is_creator:
        rows.append([InlineKeyboardButton(text=get_message(BTN_DELETE_GROUP, user=user, group_name=group_name), callback_data=f"confirm_delete_group_{group_id}")])
    else:
        rows.append([InlineKeyboardButton(text=get_message(BTN_LEAVE_GROUP, user=user, group_name=group_name), callback_data=f"confirm_leave_group_{group_id}")])
    # Match button removed from inline keyboard
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_confirm_delete_keyboard(group_id, user):
    kb = [[
        InlineKeyboardButton(text=get_message(BTN_DELETE, user=user), callback_data=f"delete_group_yes_{group_id}"),
        InlineKeyboardButton(text=get_message(BTN_CANCEL, user=user), callback_data=f"delete_group_cancel_{group_id}")
    ]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_confirm_leave_keyboard(group_id, user):
    kb = [[
        InlineKeyboardButton(text="✅ Yes, leave", callback_data=f"leave_group_yes_{group_id}"),
        InlineKeyboardButton(text=get_message(BTN_CANCEL, user=user), callback_data=f"leave_group_cancel_{group_id}")
    ]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def location_keyboard(user):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=get_message(BTN_SEND_LOCATION, user=user), request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_group_reply_keyboard(user):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=get_message(BTN_WHO_IS_VIBING, user=user, points=POINTS_FOR_MATCH))]],
        resize_keyboard=True,
        one_time_keyboard=False
    ) 