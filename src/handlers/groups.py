import os
import logging
from src.db import AsyncSessionLocal
from sqlalchemy import select, and_, text
from src.models import Group, GroupMember, User, Answer, Question, MatchStatus, Match
# Handlers for group management
# Imports and service calls will be added after extracting business logic 

from aiogram import types, F, Router
from aiogram.fsm.context import FSMContext
from src.loader import bot
from src.keyboards.groups import get_admin_keyboard, get_user_keyboard, go_to_group_keyboard, get_group_main_keyboard, get_confirm_delete_keyboard, get_confirm_leave_keyboard, location_keyboard, get_group_reply_keyboard
from src.fsm.states import CreateGroup, JoinGroup
from src.services.groups import (
    get_user_groups, is_group_creator, get_group_members, create_group_service,
    join_group_by_code_service, leave_group_service, delete_group_service, switch_group_service, find_best_match, set_match_status, get_group_balance
)
from src.constants import WELCOME_BONUS, MIN_ANSWERS_FOR_MATCH, POINTS_FOR_MATCH, POINTS_TO_CONNECT
import asyncio
from src.config import ALLKINDS_CHAT_BOT_USERNAME
from urllib.parse import quote
from src.texts.messages import (
    get_message,
    GROUPS_NOT_IN_ANY, GROUPS_LEAVE_CONFIRM, GROUPS_DELETE_CONFIRM, GROUPS_NAME_EMPTY, GROUPS_DESC_EMPTY, GROUPS_CREATED,
    GROUPS_JOIN_INVALID_CODE, GROUPS_JOIN_NOT_FOUND, GROUPS_JOIN_ONBOARDING, GROUPS_JOINED, GROUPS_NO_NEW_QUESTIONS,
    GROUPS_PROFILE_SETUP, GROUPS_REVIEW_ANSWERED, GROUPS_FIND_MATCH, GROUPS_SELECT, GROUPS_WELCOME_ADMIN, GROUPS_WELCOME,
    GROUPS_SWITCH_TO, GROUPS_INVITE_LINK, BTN_CREATE_GROUP, BTN_JOIN_GROUP, BTN_SWITCH_TO, BTN_DELETE_GROUP, BTN_LEAVE_GROUP,
    BTN_DELETE, BTN_CANCEL, BTN_WHO_IS_VIBING,
    MATCH_FOUND, MATCH_NO_VALID, MATCH_AI_CHEMISTRY, MATCH_SHOW_AGAIN, MATCH_DONT_SHOW, MATCH_PREV, MATCH_NEXT, MATCH_NOT_ENOUGH_POINTS,
    MATCH_REQUEST_SENT, MATCH_INCOMING_REQUEST, MATCH_REQUEST_ACCEPTED, MATCH_REQUEST_REJECTED, MATCH_REQUEST_BLOCKED,
    BTN_ACCEPT_MATCH, BTN_REJECT_MATCH, BTN_BLOCK_MATCH, BTN_GO_TO_CHAT,
    QUESTION_LOAD_ANSWERED, NO_AVAILABLE_ANSWERED_QUESTIONS, BTN_LOAD_UNANSWERED, UNANSWERED_QUESTIONS_MSG,
    MATCH_NO_OTHERS, QUEUE_LOAD_UNANSWERED,
    GROUPS_LEFT_SUCCESS, GROUPS_LEFT_ERROR, GROUPS_DELETED_SUCCESS, GROUPS_DELETED_ERROR
)
from src.utils.redis import get_or_restore_internal_user_id, get_telegram_user_id

router = Router()

ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', 0))

async def ensure_admin_in_db():
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == ADMIN_USER_ID))
        user = user.scalar()
        if not user:
            raise Exception(f"Admin user with id {ADMIN_USER_ID} not found. Use get_or_restore_internal_user_id before calling ensure_admin_in_db.")
        creator = await session.execute(select(GroupCreator).where(GroupCreator.user_id == user.id))
        creator = creator.scalar()
        if not creator:
            session.add(GroupCreator(user_id=user.id))
            await session.commit()

async def get_user_groups(user_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Group).join(GroupMember).join(User).where(User.id == user_id)
        )
        groups = result.scalars().all()
        logging.info(f"[get_user_groups] user_id={user_id}, groups={[g.name for g in groups]}")
        return [{"id": g.id, "name": g.name} for g in groups]

async def create_group(user_id: int, name: str, description: str):
    from src.utils.invite_code import generate_unique_invite_code
    invite_code = await generate_unique_invite_code()
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
        if not user:
            user = User()
            session.add(user)
            await session.flush()
            await session.commit()
            print(f"[DEBUG] User created and committed (create_group): id={user.id}")
        group = Group(name=name, description=description, invite_code=invite_code, creator_user_id=user.id)
        session.add(group)
        await session.flush()
        member = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == group.id))
        member = member.scalar()
        if not member:
            member = GroupMember(user_id=user.id, group_id=group.id)
            session.add(member)
        await session.commit()
        return {"id": group.id, "name": group.name, "invite_code": group.invite_code}

async def join_group_by_code(user_id: int, code: str):
    async with AsyncSessionLocal() as session:
        group = await session.execute(select(Group).where(Group.invite_code == code))
        group = group.scalar()
        if not group:
            return None
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
        if not user:
            raise Exception(f"User with id {user_id} not found in join_group_by_code. Use get_or_restore_internal_user_id before calling this function.")
        member = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == group.id))
        member = member.scalar()
        if not member:
            member = GroupMember(user_id=user.id, group_id=group.id)
            session.add(member)
            await session.commit()
        return {"id": group.id, "name": group.name}

async def show_group_main_flow(message, user_id, group_id):
    """
    After welcome: shows history button, unanswered counter and first unanswered question.
    """
    from src.services.questions import get_next_unanswered_question
    from src.handlers.questions import send_question_to_user
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from src.texts.messages import get_message, QUESTION_LOAD_ANSWERED, GROUPS_REVIEW_ANSWERED
    from src.models import User, Answer, Question
    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
        # No longer creating delivered answers - using dynamic queue
        
        # Count answers for history button
        answers_count = await session.execute(
            select(Answer).where(
                Answer.user_id == user.id,
                Answer.value.isnot(None),
                Answer.question_id.in_(select(Question.id).where(Question.group_id == group_id, Question.is_deleted == 0))
            )
        )
        answers_count = len(answers_count.scalars().all())
        
        # 2. Load answered questions button (if there's something to load)
        if answers_count > 0:
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=get_message(QUESTION_LOAD_ANSWERED, user=user), callback_data="load_answered_questions")]])
            await message.answer(get_message(GROUPS_REVIEW_ANSWERED, user=user), reply_markup=kb)
        
        # 3. Find and show first unanswered question using dynamic queue
        first_question = await get_next_unanswered_question(session, group_id, user.id)
        if first_question:
            await send_question_to_user(message.bot, user, first_question)
        else:
            await message.answer(get_message("GROUPS_NO_NEW_QUESTIONS", user=user))

async def show_group_welcome_and_question(message, user_id, group_id):
    """
    Welcome message when entering group: shows greeting, balance, match button (ReplyKeyboard), then history/questions.
    """
    # Clean up old delivered answers first
    from src.handlers.questions import cleanup_old_delivered_answers
    await cleanup_old_delivered_answers()
    
    from src.keyboards.groups import get_group_reply_keyboard
    from src.services.groups import get_group_balance, get_user_groups
    from src.texts.messages import get_message, GROUPS_FIND_MATCH
    from src.models import User
    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
        groups = await get_user_groups(user_id)
        group = next((g for g in groups if g["id"] == group_id), None)
        group_name = group["name"] if group else "this group"
        balance = await get_group_balance(user_id, group_id)
    # Welcome + match button
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    match_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=get_message(BTN_WHO_IS_VIBING, user=user, points=POINTS_FOR_MATCH))]],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    await message.answer(
        get_message(GROUPS_FIND_MATCH, user=user, group_name=group_name, balance=balance),
        reply_markup=match_kb,
        parse_mode="HTML"
    )
    await show_group_main_flow(message, user_id, group_id)

async def show_user_groups(message, state, is_admin=False):
    """
    Handler: Показывает пользователю его группы, используя только сервисные методы для получения данных.
    Генерация клавиатур и отправка сообщений — только здесь.
    """
    data = await state.get_data()
    user_id = data.get('internal_user_id')
    if not user_id:
        await message.answer(get_message("Please start the bot to use this feature.", user=message.from_user))
        return
    groups = await get_user_groups(user_id)
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
        if not groups:
            if is_admin:
                kb = get_admin_keyboard([], user)
            else:
                kb = get_user_keyboard(user)
            await message.answer(get_message(GROUPS_NOT_IN_ANY, user=user), reply_markup=kb)
            return
        current_group_id = user.current_group_id
        current_group = None
        for g in groups:
            if g["id"] == current_group_id:
                current_group = g
                break
        if not current_group:
            current_group = groups[0]
            user.current_group_id = current_group["id"]
            await session.commit()
            await message.answer("⚠️ Your current group was not found. Switched to: {}".format(current_group["name"]))
        group = await session.execute(select(Group).where(Group.id == current_group["id"]))
        group = group.scalar()
    bot_info = await message.bot.get_me()
    deeplink = f"https://t.me/{bot_info.username}?start={group.invite_code}"
    text = get_message(GROUPS_INVITE_LINK, user=user, group_name=group.name, group_desc=group.description, deeplink=deeplink, invite_code=group.invite_code)
    is_creator = (group.creator_user_id == user.id)
    kb = get_group_main_keyboard(user.id, group.id, group.name, is_creator, user)
    kb.inline_keyboard.append([])
    other_groups = [g for g in groups if g["id"] != group.id]
    for g in other_groups:
        kb.inline_keyboard.append([
            types.InlineKeyboardButton(text=get_message(BTN_SWITCH_TO, user=user, group_name=g['name']), callback_data=f"switch_to_group_{g['id']}")
        ])
    if is_admin:
        kb.inline_keyboard.append([
            types.InlineKeyboardButton(text=get_message(BTN_CREATE_GROUP, user=user), callback_data="create_new_group")
        ])
    kb.inline_keyboard.append([
        types.InlineKeyboardButton(text=get_message(BTN_JOIN_GROUP, user=user), callback_data="join_another_group_with_code")
    ])
    sent = await message.answer(text, reply_markup=kb, parse_mode="HTML")
    # --- New logic for history button ---
    async with AsyncSessionLocal() as session:
        any_answers = await session.execute(
            select(Answer).where(
                Answer.user_id == user.id,
                Answer.question_id.in_(select(Question.id).where(Question.group_id == group.id))
            )
        )
        any_answers = any_answers.scalars().all()
        valid_answers = await session.execute(
            select(Answer).where(
                Answer.user_id == user.id,
                Answer.value.isnot(None),
                Answer.question_id.in_(select(Question.id).where(Question.group_id == group.id, Question.is_deleted == 0))
            )
        )
        valid_answers = valid_answers.scalars().all()
        print(f"[DEBUG] any_answers: {len(any_answers)}, valid_answers: {len(valid_answers)} for user_id={user.id}, group_id={group.id}")
        print(f"[DEBUG] any_answers content: {any_answers}")
        print(f"[DEBUG] valid_answers content: {valid_answers}")
        if len(any_answers) > 0:
            kb_hist = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=get_message(QUESTION_LOAD_ANSWERED, user=user), callback_data="load_answered_questions")]])
            if valid_answers:
                msg = await message.answer(get_message(GROUPS_REVIEW_ANSWERED, user=user), reply_markup=kb_hist)
                print(f"[DEBUG] Sent answered questions msg_id={msg.message_id}")
            else:
                msg = await message.answer(get_message(NO_AVAILABLE_ANSWERED_QUESTIONS, user=user), reply_markup=kb_hist)
                print(f"[DEBUG] Sent no available answered questions msg_id={msg.message_id}")
    data = await state.get_data()
    ids = data.get("my_groups_msg_ids", [])
    ids.append(sent.message_id)
    await state.update_data(my_groups_msg_ids=ids)

async def clear_mygroups_messages(message, state):
    data = await state.get_data()
    ids = data.get("my_groups_msg_ids", [])
    for mid in ids:
        try:
            await message.bot.delete_message(message.chat.id, mid)
        except Exception:
            pass
    await state.update_data(my_groups_msg_ids=[])

@router.callback_query(F.data.startswith("confirm_leave_group_"))
async def cb_confirm_leave_group(callback: types.CallbackQuery, state: FSMContext):
    await clear_mygroups_messages(callback.message, state)
    group_id = int(callback.data.split("_")[-1])
    data = await state.get_data()
    user_id = data.get('internal_user_id')
    if not user_id:
        await callback.message.answer(get_message("Please start the bot to use this feature.", user=callback.from_user))
        await callback.answer()
        return
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
    groups = await get_user_groups(user_id)
    group = next((g for g in groups if g["id"] == group_id), None)
    group_name = group["name"] if group else "this group"
    text = get_message(GROUPS_LEAVE_CONFIRM, user=user, group_name=group_name)
    kb = get_confirm_leave_keyboard(group_id, user)
    msg = await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    data = await state.get_data()
    leave_ids = data.get("leave_msgs", [])
    leave_ids.append(msg.message_id)
    await state.update_data(leave_msgs=leave_ids)
    await callback.answer()

@router.callback_query(F.data.startswith("leave_group_cancel_"))
async def cb_leave_group_cancel(callback: types.CallbackQuery, state: FSMContext):
    await clear_mygroups_messages(callback.message, state)
    await state.clear()
    await callback.answer()

@router.callback_query(F.data.startswith("leave_group_yes_"))
async def cb_leave_group_yes(callback: types.CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split("_")[-1])
    data = await state.get_data()
    user_id = data.get('internal_user_id')
    if not user_id:
        await callback.message.answer(get_message("Please start the bot to use this feature.", user=callback.from_user))
        await callback.answer()
        return
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
    # Leave group via service
    result = await leave_group_service(user_id, group_id)
    if result["ok"]:
        await callback.message.answer(get_message(GROUPS_LEFT_SUCCESS, user=user))
        await clear_mygroups_messages(callback.message, state)
        await state.clear()
        await state.update_data(internal_user_id=user_id)
    else:
        await callback.message.answer(get_message(GROUPS_LEFT_ERROR, user=user))
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_delete_group_"))
async def cb_confirm_delete_group(callback: types.CallbackQuery, state: FSMContext):
    await clear_mygroups_messages(callback.message, state)
    group_id = int(callback.data.split("_")[-1])
    data = await state.get_data()
    user_id = data.get('internal_user_id')
    if not user_id:
        await callback.message.answer(get_message("Please start the bot to use this feature.", user=callback.from_user))
        await callback.answer()
        return
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
    from src.services.groups import get_user_groups
    groups = await get_user_groups(user_id)
    group = next((g for g in groups if g["id"] == group_id), None)
    group_name = group["name"] if group else "this group"
    text = get_message(GROUPS_DELETE_CONFIRM, user=user, group_name=group_name)
    kb = get_confirm_delete_keyboard(group_id, user)
    msg = await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    data = await state.get_data()
    leave_ids = data.get("leave_msgs", [])
    leave_ids.append(msg.message_id)
    await state.update_data(leave_msgs=leave_ids)
    await callback.answer()

@router.callback_query(F.data.startswith("delete_group_cancel_"))
async def cb_delete_group_cancel(callback: types.CallbackQuery, state: FSMContext):
    await clear_mygroups_messages(callback.message, state)
    await state.clear()
    await callback.answer()

@router.callback_query(F.data.startswith("delete_group_yes_"))
async def cb_delete_group_yes(callback: types.CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split("_")[-1])
    data = await state.get_data()
    user_id = data.get('internal_user_id')
    if not user_id:
        await callback.message.answer(get_message("Please start the bot to use this feature.", user=callback.from_user))
        await callback.answer()
        return
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
    # Delete group via service
    result = await delete_group_service(group_id)
    if result["ok"]:
        await callback.message.answer(get_message(GROUPS_DELETED_SUCCESS, user=user))
        await clear_mygroups_messages(callback.message, state)
        await state.clear()
        await state.update_data(internal_user_id=user_id)
    else:
        await callback.message.answer(get_message(GROUPS_DELETED_ERROR, user=user))
    await callback.answer()

# --- Group-related handlers ---

@router.callback_query(F.data == "create_new_group")
async def cb_create_group(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = data.get('internal_user_id')
    if not user_id:
        await callback.message.answer(get_message("Please start the bot to use this feature.", user=callback.from_user))
        await callback.answer()
        return
    is_creator = await is_group_creator(user_id)
    if not is_creator:
        await callback.message.answer(get_message("You are not allowed to create groups.", user=callback.from_user))
        await callback.answer()
        return
    await callback.message.answer(get_message("Enter group name:", user=callback.from_user), reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(CreateGroup.name)
    await callback.answer()

@router.message(CreateGroup.name)
async def group_name_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get('internal_user_id')
    if not user_id:
        await message.answer(get_message("Please start the bot to use this feature.", user=message.from_user))
        return
    name = message.text.strip()
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
    if not name:
        await message.answer(get_message(GROUPS_NAME_EMPTY, user=user))
        return
    await state.update_data(name=name)
    await message.answer(get_message("Enter group description:", user=user))
    await state.set_state(CreateGroup.description)

@router.message(CreateGroup.description)
async def group_desc_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get('internal_user_id')
    if not user_id:
        await message.answer(get_message("Please start the bot to use this feature.", user=message.from_user))
        return
    desc = message.text.strip()
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
    if not desc:
        await message.answer(get_message(GROUPS_DESC_EMPTY, user=user))
        return
    data = await state.get_data()
    group = await create_group_service(user_id, data["name"], desc)
    bot_info = await bot.get_me()
    deep_link = f"https://t.me/{bot_info.username}?start={group['invite_code']}"
    await message.answer(
        get_message(GROUPS_CREATED, user=user, group_name=group["name"], invite_code=group["invite_code"], deep_link=deep_link),
        reply_markup=go_to_group_keyboard(group["id"], group["name"], user))
    await state.clear()
    await state.update_data(internal_user_id=user.id)

@router.callback_query(F.data.startswith("switch_to_group_"))
async def cb_switch_to_group(callback: types.CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split("_")[-1])
    data = await state.get_data()
    user_id = data.get('internal_user_id')
    if not user_id:
        await callback.message.answer(get_message("Please start the bot to use this feature.", user=callback.from_user))
        await callback.answer()
        return
    result = await switch_group_service(user_id, group_id)
    if result["ok"]:
        await callback.message.delete()
        # Show welcome/history/match-button for selected group
        await show_group_welcome_and_question(callback.message, user_id, group_id)
        await callback.answer()
    else:
        async with AsyncSessionLocal() as session:
            user = await session.execute(select(User).where(User.id == user_id))
            user = user.scalar()
        await callback.message.answer(get_message("Let's set up your profile for this group!\nEnter your nickname:", user=user), reply_markup=types.ReplyKeyboardRemove())
        await state.update_data(group_id=group_id)
        from src.fsm.states import Onboarding
        await state.set_state(Onboarding.nickname)
        await callback.answer()

@router.callback_query(F.data == "join_another_group_with_code")
async def cb_join_group(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = data.get('internal_user_id')
    if not user_id:
        await callback.message.answer(get_message("Please start the bot to use this feature.", user=callback.from_user))
        await callback.answer()
        return
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
    await callback.message.answer(get_message("Enter the 5-character invite code:", user=user), reply_markup=types.ReplyKeyboardRemove())
    from src.fsm.states import JoinGroup
    await state.set_state(JoinGroup.code)
    await callback.answer()

@router.message(JoinGroup.code)
async def process_invite_code(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get('internal_user_id')
    if not user_id:
        await message.answer(get_message("Please start the bot to use this feature.", user=message.from_user))
        return
    code = message.text.strip()
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
    if not code or len(code) != 5:
        await message.answer(get_message(GROUPS_JOIN_INVALID_CODE, user=user))
        return
    from src.services.groups import handle_group_join
    success = await handle_group_join(user_id, code, message, state)
    if success:
        # Only clear state if onboarding is not needed (handled by unified function)
        data = await state.get_data()
        current_state = await state.get_state()
        if not current_state:  # No onboarding state set
            await state.clear()
            await state.update_data(internal_user_id=user_id)

@router.callback_query(F.data.startswith("find_match_"))
async def cb_find_match(callback: types.CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split("_")[-1])
    data = await state.get_data()
    user_id = data.get('internal_user_id')
    if not user_id:
        await callback.answer(get_message(MATCH_NO_VALID, user=callback.from_user, show_alert=True))
        return
    from src.models import User, Answer, GroupMember
    from sqlalchemy import select
    from src.db import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
        if not user:
            await callback.answer(get_message(MATCH_NO_VALID, user=callback.from_user, show_alert=True))
            return
        # Count user's answers in group
        answers_count = await session.execute(
            select(Answer).where(
                Answer.user_id == user.id,
                Answer.value.isnot(None),
                Answer.question_id.in_(select(Question.id).where(Question.group_id == group_id, Question.is_deleted == 0))
            )
        )
        answers_count = len(answers_count.scalars().all())
        member = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == group_id))
        member = member.scalar()
        import logging
        logging.warning(f"[cb_find_match] user_id={user.id}, group_id={group_id}, member={member}, balance={getattr(member, 'balance', None)}")
        if not member or member.balance < POINTS_FOR_MATCH:
            await callback.message.answer(get_message(f"Not enough points for match. Your balance: {member.balance if member else 0}.", user=user))
            return
        if answers_count < MIN_ANSWERS_FOR_MATCH:
            await callback.message.answer(get_message(f"You need to answer at least {MIN_ANSWERS_FOR_MATCH} questions to get a match. You have answered: {answers_count}. Keep answering or create new questions!", user=user))
            return
        # Find all matches
        from src.services.groups import find_all_matches
        matches = await find_all_matches(user_id, group_id)
        if not matches:
            await callback.message.answer(get_message(MATCH_NO_OTHERS, user=user))
            await callback.answer(get_message(MATCH_NO_VALID, user=callback.from_user, show_alert=True))
            return
        
        # Deduct points for first match
        member.balance -= POINTS_FOR_MATCH
        await session.commit()
        
        # Show first match with navigation
        await show_match_with_navigation(callback, user, matches, 0)

async def show_match_with_navigation(callback_or_message, user, matches: list, index: int):
    """Display match with navigation buttons"""
    if not matches or index < 0 or index >= len(matches):
        return
    
    match = matches[index]
    
    # Format intro text
    intro_text = ""
    if match.get('intro'):
        intro_text = f"\n{match['intro']}"
    
    text = get_message(MATCH_FOUND, user=user, 
                      nickname=match['nickname'], 
                      intro=intro_text,
                      similarity=match['similarity'], 
                      common_questions=match['common_questions'], 
                      valid_users_count=match['valid_users_count'])
    
    # Build navigation buttons
    nav_buttons = []
    if len(matches) > 1:
        nav_row = []
        if index > 0:
            nav_row.append(types.InlineKeyboardButton(
                text=get_message(MATCH_PREV, user=user), 
                callback_data=f"match_nav_{index-1}"))
        if index < len(matches) - 1:
            nav_row.append(types.InlineKeyboardButton(
                text=get_message(MATCH_NEXT, user=user), 
                callback_data=f"match_nav_{index+1}"))
        if nav_row:
            nav_buttons.append(nav_row)
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        *nav_buttons,
        # [types.InlineKeyboardButton(text=get_message(MATCH_AI_CHEMISTRY, user=user, points=POINTS_TO_CONNECT), callback_data=f"match_chat_{match['user_id']}")],  # Commented out - will return later
        [types.InlineKeyboardButton(text=get_message("BTN_CONNECT", user=user), callback_data=f"connect_{match['user_id']}")],
        [types.InlineKeyboardButton(text=get_message(MATCH_SHOW_AGAIN, user=user), callback_data=f"match_postpone_{match['user_id']}")],
        [types.InlineKeyboardButton(text=get_message(MATCH_DONT_SHOW, user=user), callback_data=f"match_hide_{match['user_id']}")]
    ])
    
    if hasattr(callback_or_message, 'message'):  # It's a callback
        # Store matches in state for navigation
        from src.utils.redis import redis
        import json
        matches_data = json.dumps(matches)
        await redis.set(f"matches_{user.id}", matches_data, ex=300)  # 5 min expiry
        
        if match['photo_url']:
            if callback_or_message.message.photo:
                # Check if it's the same photo URL - if not, delete and send new
                current_photo_file_id = callback_or_message.message.photo[-1].file_id
                
                # For navigation, always delete and send new photo to ensure photo updates
                await callback_or_message.message.delete()
                await callback_or_message.message.answer_photo(match['photo_url'], caption=text, reply_markup=kb, parse_mode="HTML")
            else:
                # Delete text message and send photo
                await callback_or_message.message.delete()
                await callback_or_message.message.answer_photo(match['photo_url'], caption=text, reply_markup=kb, parse_mode="HTML")
        else:
            if callback_or_message.message.photo:
                # Delete photo message and send text
                await callback_or_message.message.delete()
                await callback_or_message.message.answer(text, reply_markup=kb, parse_mode="HTML")
            else:
                # Edit existing text message
                await callback_or_message.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback_or_message.answer()
    else:  # It's a message
        if match['photo_url']:
            await callback_or_message.answer_photo(match['photo_url'], caption=text, reply_markup=kb, parse_mode="HTML")
        else:
            await callback_or_message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("match_nav_"))
async def cb_match_nav(callback: types.CallbackQuery, state: FSMContext):
    """Handle match navigation"""
    from src.utils.redis import get_or_restore_internal_user_id, redis
    import json
    
    internal_user_id = await get_or_restore_internal_user_id(state, callback.from_user.id)
    if not internal_user_id:
        await callback.answer(get_message("Please start the bot to use this feature.", user=callback.from_user))
        return
    
    new_index = int(callback.data.split("_")[-1])
    
    # Get stored matches
    matches_data = await redis.get(f"matches_{internal_user_id}")
    if not matches_data:
        await callback.answer("Session expired. Please search for matches again.")
        return
    
    matches = json.loads(matches_data)
    
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == internal_user_id))
        user = user.scalar()
        if not user:
            await callback.answer("User not found.")
            return
        
        group_id = user.current_group_id
        member = await session.execute(select(GroupMember).where(
            GroupMember.user_id == user.id, 
            GroupMember.group_id == group_id))
        member = member.scalar()
        
        # Check if going forward (need to charge points)
        current_index = 0
        for i, match_data in enumerate(matches):
            if str(match_data['user_id']) in callback.message.reply_markup.inline_keyboard[-1][0].callback_data:
                current_index = i
                break
        
        if new_index > current_index:  # Going forward - charge points
            if member.balance < POINTS_FOR_MATCH:
                await callback.answer(get_message(MATCH_NOT_ENOUGH_POINTS, user=callback.from_user))
                return
            old_balance = member.balance
            member.balance -= POINTS_FOR_MATCH
            await session.commit()
            # Show balance change popup
            await callback.answer(f"💎 Balance: {member.balance} (-{POINTS_FOR_MATCH})", show_alert=False)
        else:
            # Free navigation backwards - just show current balance
            await callback.answer(f"💎 Balance: {member.balance}", show_alert=False)
        
        await show_match_with_navigation(callback, user, matches, new_index)

@router.callback_query(F.data.startswith("match_hide_"))
async def cb_match_hide(callback: types.CallbackQuery, state: FSMContext):
    from src.utils.redis import get_or_restore_internal_user_id
    user_id = await get_or_restore_internal_user_id(state, callback.from_user.id)
    if not user_id or user_id > 2_147_483_647:
        import logging
        logging.error(f"[cb_match_hide] Invalid user_id: {user_id}")
        await callback.answer("Internal error: invalid user id.", show_alert=True)
        return
    data = callback.data.split("_")
    match_user_id = int(data[-1])
    # Get group_id from user's current group
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
        group_id = user.current_group_id if user else None
    if group_id:
        await set_match_status(user_id, group_id, match_user_id, "hidden")
        # Delete match messages (photo/text)
        try:
            await callback.message.delete()
        except Exception:
            pass
        # Send notification and delete it after 5 seconds
        notif = await callback.message.answer(get_message("This user will no longer be shown to you.", user=callback.from_user))
        await asyncio.sleep(5)
        try:
            await notif.delete()
        except Exception:
            pass
    await callback.answer()

@router.callback_query(F.data.startswith("match_postpone_"))
async def cb_match_postpone(callback: types.CallbackQuery, state: FSMContext):
    from src.utils.redis import get_or_restore_internal_user_id
    user_id = await get_or_restore_internal_user_id(state, callback.from_user.id)
    if not user_id or user_id > 2_147_483_647:
        import logging
        logging.error(f"[cb_match_postpone] Invalid user_id: {user_id}")
        await callback.answer("Internal error: invalid user id.", show_alert=True)
        return
    data = callback.data.split("_")
    match_user_id = int(data[-1])
    # Get group_id from user's current group
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
        group_id = user.current_group_id if user else None
        if group_id:
            # Remove postponed/hidden status for this match (return to pool)
            await session.execute(
                text("DELETE FROM match_statuses WHERE user_id = :user_id AND group_id = :group_id AND match_user_id = :match_user_id"),
                {"user_id": user.id, "group_id": group_id, "match_user_id": match_user_id}
            )
            await session.commit()
    # Delete only two last messages (match and button)
    for offset in range(0, 2):
        try:
            await callback.bot.delete_message(callback.message.chat.id, callback.message.message_id - offset)
        except Exception:
            pass
    await callback.answer()

@router.message(F.text.func(lambda t: t and ("vibing" in t.lower() or "совпадает" in t.lower())))
async def handle_vibing_button(message: types.Message, state: FSMContext):
    import logging
    try:
        await state.update_data(vibing_msg_id=message.message_id)
        data = await state.get_data()
        user_id = data.get('internal_user_id')
        if not user_id:
            await message.answer(get_message("Please start the bot to use this feature.", user=message.from_user))
            return
        from src.services.groups import get_user_groups
        async with AsyncSessionLocal() as session:
            user = await session.execute(select(User).where(User.id == user_id))
            user = user.scalar()
            group_id = user.current_group_id
        from src.handlers.groups import cb_find_match
        class DummyCallback:
            def __init__(self, message, user_id, group_id):
                self.message = message
                self.from_user = type('User', (), {'id': user_id})()
                self.data = f"find_match_{group_id}"
                self.bot = message.bot
            async def answer(self, *args, **kwargs):
                pass
        callback = DummyCallback(message, message.from_user.id, group_id)
        await cb_find_match(callback, state)
    except Exception as e:
        logging.exception("Ошибка в handle_vibing_button")
        raise

@router.callback_query(F.data.startswith("match_chat_"))
async def cb_match_chat(callback: types.CallbackQuery, state: FSMContext):
    """Инициировать запрос на подключение к матчу (новая двухэтапная логика)"""
    internal_user_id = await get_or_restore_internal_user_id(state, callback.from_user.id)
    if not internal_user_id:
        await callback.message.answer(get_message("Please start the bot to use this feature.", user=callback.from_user))
        await callback.answer()
        return
    match_user_id = int(callback.data.split("_")[-1])
    from src.models import MatchStatus, GroupMember
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == internal_user_id))
        user = user.scalar()
        group_id = user.current_group_id if user else None
        if not user or not group_id:
            await callback.message.answer(get_message("Please start the bot to use this feature.", user=callback.from_user))
            await callback.answer()
            return
        member = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == group_id))
        member = member.scalar()
        match_user = await session.execute(select(User).where(User.id == match_user_id))
        match_user = match_user.scalar()
        match_member = await session.execute(select(GroupMember).where(GroupMember.user_id == match_user_id, GroupMember.group_id == group_id))
        match_member = match_member.scalar()
        
        # Check if request already exists
        existing_request = await session.execute(select(MatchStatus).where(
            MatchStatus.user_id == user.id,
            MatchStatus.group_id == group_id,
            MatchStatus.match_user_id == match_user.id
        ))
        existing_request = existing_request.scalar()
        
        # Create "pending approval" status for initiator
        if existing_request:
            existing_request.status = "pending_approval"
        else:
            new_request = MatchStatus(user_id=user.id, group_id=group_id, match_user_id=match_user.id, status="pending_approval")
            session.add(new_request)
        await session.commit()
    
    # Delete match card
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    # Delete "vibing" message
    data = await state.get_data()
    vibing_msg_id = data.get("vibing_msg_id")
    if vibing_msg_id:
        try:
            await callback.message.bot.delete_message(callback.message.chat.id, vibing_msg_id)
        except Exception:
            pass
        await state.update_data(vibing_msg_id=None)
    
    # Notify initiator that request was sent
    notif = await callback.message.answer(
        get_message(MATCH_REQUEST_SENT, user=user, nickname=match_member.nickname if match_member else "Unknown")
    )
    
    # Send notification to second user
    match_telegram_user_id = await get_telegram_user_id(match_user.id)
    if match_telegram_user_id:
        # Get data for match display
        reverse_match = await find_best_match(match_user_id, group_id, exclude_user_ids=[])
        if reverse_match and reverse_match.get('user_id') == user.id:
            similarity = reverse_match['similarity']
            common_questions = reverse_match['common_questions']
            valid_users_count = reverse_match['valid_users_count']
        else:
            # If couldn't get reverse match, use basic data
            similarity = 85  # fallback
            common_questions = 3  # fallback
            valid_users_count = 2  # fallback
        
        # First message about connection request
        request_text = get_message(MATCH_INCOMING_REQUEST, user=match_user, nickname=member.nickname if member else "Unknown")
        
        # Then match card
        intro_text = f"\n{member.intro}" if member and member.intro else ""
        match_text = get_message(MATCH_FOUND, user=match_user, nickname=member.nickname if member else "Unknown", 
                               intro=intro_text, similarity=similarity, common_questions=common_questions, valid_users_count=valid_users_count)
        
        # Buttons for accept/decline/block
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text=get_message(BTN_ACCEPT_MATCH, user=match_user), 
                                         callback_data=f"accept_match_{user.id}"),
                types.InlineKeyboardButton(text=get_message(BTN_REJECT_MATCH, user=match_user), 
                                         callback_data=f"reject_match_{user.id}")
            ],
            [
                types.InlineKeyboardButton(text=get_message(BTN_BLOCK_MATCH, user=match_user), 
                                         callback_data=f"block_match_{user.id}")
            ]
        ])
        
        try:
            # Send notification to second user
            await callback.bot.send_message(match_telegram_user_id, request_text, parse_mode="HTML")
            
            # Send match card with photo and buttons
            if member and member.photo_url:
                await callback.bot.send_photo(match_telegram_user_id, member.photo_url, 
                                            caption=match_text, reply_markup=kb, parse_mode="HTML")
            else:
                await callback.bot.send_message(match_telegram_user_id, match_text, 
                                              reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            import logging
            logging.error(f"[cb_match_chat] Failed to send match request to user_id={match_user.id}: {e}")
    else:
        import logging
        logging.error(f"[cb_match_chat] No telegram_user_id in Redis for user_id={match_user.id}")
    
    await callback.answer()

@router.callback_query(F.data.startswith("connect_"))
async def cb_connect(callback: types.CallbackQuery, state: FSMContext):
    """Инициировать запрос на подключение к матчу (новая упрощенная логика)"""
    from src.utils.redis import get_or_restore_internal_user_id, get_telegram_user_id
    from src.services.groups import find_best_match
    
    internal_user_id = await get_or_restore_internal_user_id(state, callback.from_user.id)
    if not internal_user_id:
        await callback.message.answer(get_message("Please start the bot to use this feature.", user=callback.from_user))
        await callback.answer()
        return
    
    match_user_id = int(callback.data.split("_")[-1])
    from src.models import MatchStatus, GroupMember, Match
    
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == internal_user_id))
        user = user.scalar()
        group_id = user.current_group_id if user else None
        
        if not user or not group_id:
            await callback.message.answer(get_message("Please start the bot to use this feature.", user=callback.from_user))
            await callback.answer()
            return
        
        member = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == group_id))
        member = member.scalar()
        match_user = await session.execute(select(User).where(User.id == match_user_id))
        match_user = match_user.scalar()
        match_member = await session.execute(select(GroupMember).where(GroupMember.user_id == match_user_id, GroupMember.group_id == group_id))
        match_member = match_member.scalar()
        
        if not match_user or not match_member:
            await callback.answer("User not found")
            return
        
        # Check if there's already a reverse pending request (mutual initiative logic)
        reverse_request = await session.execute(select(MatchStatus).where(
            MatchStatus.user_id == match_user.id,
            MatchStatus.group_id == group_id,
            MatchStatus.match_user_id == user.id,
            MatchStatus.status == "pending"
        ))
        reverse_request = reverse_request.scalar()
        
        if reverse_request:
            # Mutual initiative - automatic match!
            # Update reverse request to accepted
            reverse_request.status = "accepted"
            
            # Create Match record with exchanged_contacts status
            # Use consistent user ordering (smaller id first)
            user1_id = min(user.id, match_user.id)
            user2_id = max(user.id, match_user.id)
            
            existing_match = await session.execute(select(Match).where(
                Match.user1_id == user1_id,
                Match.user2_id == user2_id,
                Match.group_id == group_id
            ))
            existing_match = existing_match.scalar()
            
            if not existing_match:
                new_match = Match(user1_id=user1_id, user2_id=user2_id, group_id=group_id, status="contacts")
                session.add(new_match)
            else:
                existing_match.status = "contacts"
            
            await session.commit()
            
            # Delete match cards
            try:
                await callback.message.delete()
            except Exception:
                pass
            
            # Notify both users about successful match and exchange contacts
            await notify_successful_match_and_exchange_contacts(callback.bot, user, match_user, member, match_member)
            await callback.answer()
            return
        
        # Check if request already exists from this user
        existing_request = await session.execute(select(MatchStatus).where(
            MatchStatus.user_id == user.id,
            MatchStatus.group_id == group_id,
            MatchStatus.match_user_id == match_user.id
        ))
        existing_request = existing_request.scalar()
        
        # Create or update "pending" status for initiator
        if existing_request:
            if existing_request.status == "blocked":
                await callback.answer("You cannot connect with this user")
                return
            existing_request.status = "pending"
        else:
            new_request = MatchStatus(user_id=user.id, group_id=group_id, match_user_id=match_user.id, status="pending")
            session.add(new_request)
        
        await session.commit()
    
    # Delete match card
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    # Delete "vibing" message
    data = await state.get_data()
    vibing_msg_id = data.get("vibing_msg_id")
    if vibing_msg_id:
        try:
            await callback.message.bot.delete_message(callback.message.chat.id, vibing_msg_id)
        except Exception:
            pass
        await state.update_data(vibing_msg_id=None)
    
    # Notify initiator that request was sent
    await callback.message.answer(
        get_message("MATCH_REQUEST_SENT", user=user, nickname=match_member.nickname if match_member else "Unknown")
    )
    
    # Send notification to second user
    await send_connection_request_to_user(callback.bot, user, match_user, member, match_member, group_id)
    
    await callback.answer()

async def send_connection_request_to_user(bot, initiator_user, target_user, initiator_member, target_member, group_id):
    """Отправить уведомление о запросе на подключение"""
    from src.utils.redis import get_telegram_user_id
    from src.services.groups import find_best_match
    
    target_telegram_user_id = await get_telegram_user_id(target_user.id)
    if not target_telegram_user_id:
        import logging
        logging.error(f"[send_connection_request] No telegram_user_id in Redis for user_id={target_user.id}")
        return
    
    try:
        # Get match data for display
        reverse_match = await find_best_match(target_user.id, group_id, exclude_user_ids=[])
        if reverse_match and reverse_match.get('user_id') == initiator_user.id:
            similarity = reverse_match['similarity']
            common_questions = reverse_match['common_questions']
            valid_users_count = reverse_match['valid_users_count']
        else:
            # Fallback values
            similarity = 85
            common_questions = 3
            valid_users_count = 2
        
        # First message about connection request
        request_text = get_message("MATCH_INCOMING_REQUEST", user=target_user, 
                                 nickname=initiator_member.nickname if initiator_member else "Unknown")
        
        # Then match card
        intro_text = f"\n{initiator_member.intro}" if initiator_member and initiator_member.intro else ""
        match_text = get_message("MATCH_FOUND", user=target_user, 
                               nickname=initiator_member.nickname if initiator_member else "Unknown", 
                               intro=intro_text, similarity=similarity, 
                               common_questions=common_questions, valid_users_count=valid_users_count)
        
        # Buttons for accept/decline/block
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text=get_message("BTN_ACCEPT_MATCH", user=target_user), 
                                         callback_data=f"accept_match_{initiator_user.id}"),
                types.InlineKeyboardButton(text=get_message("BTN_DECLINE_MATCH", user=target_user), 
                                         callback_data=f"decline_match_{initiator_user.id}")
            ],
            [
                types.InlineKeyboardButton(text=get_message("BTN_BLOCK_MATCH", user=target_user), 
                                         callback_data=f"block_match_{initiator_user.id}")
            ]
        ])
        
        # Send notification to target user
        await bot.send_message(target_telegram_user_id, request_text, parse_mode="HTML")
        
        # Send match card with photo and buttons
        if initiator_member and initiator_member.photo_url:
            await bot.send_photo(target_telegram_user_id, initiator_member.photo_url, 
                               caption=match_text, reply_markup=kb, parse_mode="HTML")
        else:
            await bot.send_message(target_telegram_user_id, match_text, 
                                 reply_markup=kb, parse_mode="HTML")
            
    except Exception as e:
        import logging
        logging.error(f"[send_connection_request] Failed to send request to user_id={target_user.id}: {e}")

async def notify_successful_match_and_exchange_contacts(bot, user1, user2, member1, member2):
    """Уведомить об успешном мэтче и обменяться контактами"""
    from src.utils.redis import get_telegram_user_id
    
    # Get telegram user IDs
    user1_telegram_id = await get_telegram_user_id(user1.id)
    user2_telegram_id = await get_telegram_user_id(user2.id)
    
    if not user1_telegram_id or not user2_telegram_id:
        import logging
        logging.error(f"[notify_successful_match] Missing telegram IDs: user1={user1_telegram_id}, user2={user2_telegram_id}")
        return
    
    try:
        # Notify both users about successful match
        success_msg1 = get_message("MATCH_REQUEST_ACCEPTED", user=user1, 
                                 nickname=member2.nickname if member2 else "Unknown")
        success_msg2 = get_message("MATCH_REQUEST_ACCEPTED", user=user2, 
                                 nickname=member1.nickname if member1 else "Unknown")
        
        await bot.send_message(user1_telegram_id, success_msg1, parse_mode="HTML")
        await bot.send_message(user2_telegram_id, success_msg2, parse_mode="HTML")
        
        # Note: Real contact exchange would require actual phone numbers
        # For now, we'll just send the Telegram usernames/IDs as contact info
        contact_msg1 = f"📞 Контакт: @{user2_telegram_id} ({member2.nickname if member2 else 'Unknown'})"
        contact_msg2 = f"📞 Контакт: @{user1_telegram_id} ({member1.nickname if member1 else 'Unknown'})"
        
        await bot.send_message(user1_telegram_id, contact_msg1, parse_mode="HTML")
        await bot.send_message(user2_telegram_id, contact_msg2, parse_mode="HTML")
                                 
    except Exception as e:
        import logging
        logging.error(f"[notify_successful_match] Failed to exchange contacts: {e}")

@router.callback_query(F.data.startswith("accept_match_"))
async def cb_accept_match(callback: types.CallbackQuery, state: FSMContext):
    """Принять запрос на подключение к матчу (новая упрощенная логика)"""
    from src.utils.redis import get_or_restore_internal_user_id
    
    user_id = await get_or_restore_internal_user_id(state, callback.from_user.id)
    if not user_id:
        await callback.answer("Please start the bot to use this feature.", show_alert=True)
        return
    
    initiator_user_id = int(callback.data.split("_")[-1])
    
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
        group_id = user.current_group_id if user else None
        
        if not user or not group_id:
            await callback.answer("Please start the bot to use this feature.", show_alert=True)
            return
        
        initiator = await session.execute(select(User).where(User.id == initiator_user_id))
        initiator = initiator.scalar()
        
        member = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == group_id))
        member = member.scalar()
        initiator_member = await session.execute(select(GroupMember).where(GroupMember.user_id == initiator_user_id, GroupMember.group_id == group_id))
        initiator_member = initiator_member.scalar()
        
        if not initiator or not member or not initiator_member:
            await callback.answer("User not found", show_alert=True)
            return
        
        # Update status to "accepted" and create Match with exchanged_contacts
        match_status = await session.execute(select(MatchStatus).where(
            MatchStatus.user_id == initiator_user_id,
            MatchStatus.group_id == group_id,
            MatchStatus.match_user_id == user.id,
            MatchStatus.status == "pending"
        ))
        match_status = match_status.scalar()
        
        if match_status:
            match_status.status = "accepted"
        
        # Create Match record with exchanged_contacts status
        user1_id = min(user.id, initiator.id)
        user2_id = max(user.id, initiator.id)
        
        existing_match = await session.execute(select(Match).where(
            Match.user1_id == user1_id,
            Match.user2_id == user2_id,
            Match.group_id == group_id
        ))
        existing_match = existing_match.scalar()
        
        if not existing_match:
            new_match = Match(user1_id=user1_id, user2_id=user2_id, group_id=group_id, status="contacts")
            session.add(new_match)
        else:
            existing_match.status = "contacts"
        
        await session.commit()
    
    # Delete request messages
    try:
        await callback.message.delete()
        # Try to delete previous message (request text)
        await callback.bot.delete_message(callback.message.chat.id, callback.message.message_id - 1)
    except Exception:
        pass
    
    # Notify both users about successful match and exchange contacts
    await notify_successful_match_and_exchange_contacts(callback.bot, initiator, user, initiator_member, member)
    
    await callback.answer()

@router.callback_query(F.data.startswith("decline_match_"))
async def cb_decline_match(callback: types.CallbackQuery, state: FSMContext):
    """Отклонить запрос на подключение к матчу"""
    from src.utils.redis import get_or_restore_internal_user_id, get_telegram_user_id
    
    user_id = await get_or_restore_internal_user_id(state, callback.from_user.id)
    if not user_id:
        await callback.answer("Please start the bot to use this feature.", show_alert=True)
        return
    
    initiator_user_id = int(callback.data.split("_")[-1])
    
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
        group_id = user.current_group_id if user else None
        
        if not user or not group_id:
            await callback.answer("Please start the bot to use this feature.", show_alert=True)
            return
        
        initiator = await session.execute(select(User).where(User.id == initiator_user_id))
        initiator = initiator.scalar()
        
        member = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == group_id))
        member = member.scalar()
        initiator_member = await session.execute(select(GroupMember).where(GroupMember.user_id == initiator_user_id, GroupMember.group_id == group_id))
        initiator_member = initiator_member.scalar()
        
        if not initiator or not member or not initiator_member:
            await callback.answer("User not found", show_alert=True)
            return
        
        # Update status to "declined"
        match_status = await session.execute(select(MatchStatus).where(
            MatchStatus.user_id == initiator_user_id,
            MatchStatus.group_id == group_id,
            MatchStatus.match_user_id == user.id,
            MatchStatus.status == "pending"
        ))
        match_status = match_status.scalar()
        
        if match_status:
            match_status.status = "declined"
        
        await session.commit()
    
    # Delete request messages
    try:
        await callback.message.delete()
        # Try to delete previous message (request text)
        await callback.bot.delete_message(callback.message.chat.id, callback.message.message_id - 1)
    except Exception:
        pass
    
    # Notify initiator about rejection
    initiator_telegram_id = await get_telegram_user_id(initiator.id)
    if initiator_telegram_id:
        try:
            await callback.bot.send_message(
                initiator_telegram_id,
                get_message("MATCH_REQUEST_REJECTED", user=initiator, nickname=member.nickname if member else "Unknown")
            )
        except Exception as e:
            import logging
            logging.error(f"[cb_decline_match] Failed to notify initiator: {e}")
    
    await callback.answer()

@router.callback_query(F.data.startswith("block_match_"))
async def cb_block_match(callback: types.CallbackQuery, state: FSMContext):
    """Заблокировать пользователя"""
    from src.utils.redis import get_or_restore_internal_user_id, get_telegram_user_id
    
    user_id = await get_or_restore_internal_user_id(state, callback.from_user.id)
    if not user_id:
        await callback.answer("Please start the bot to use this feature.", show_alert=True)
        return
    
    initiator_user_id = int(callback.data.split("_")[-1])
    
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
        group_id = user.current_group_id if user else None
        
        if not user or not group_id:
            await callback.answer("Please start the bot to use this feature.", show_alert=True)
            return
        
        initiator = await session.execute(select(User).where(User.id == initiator_user_id))
        initiator = initiator.scalar()
        
        member = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == group_id))
        member = member.scalar()
        
        # Update status to "rejected"
        match_status = await session.execute(select(MatchStatus).where(
            MatchStatus.user_id == initiator_user_id,
            MatchStatus.group_id == group_id,
            MatchStatus.match_user_id == user.id,
            MatchStatus.status == "pending_approval"
        ))
        match_status = match_status.scalar()
        
        if match_status:
            match_status.status = "rejected"
        await session.commit()
    
    # Delete request messages
    try:
        await callback.message.delete()
        # Try to delete previous message (request text)
        await callback.bot.delete_message(callback.message.chat.id, callback.message.message_id - 1)
    except Exception:
        pass
    
    # Notify initiator about rejection
    initiator_telegram_id = await get_telegram_user_id(initiator.id)
    if initiator_telegram_id:
        try:
            await callback.bot.send_message(
                initiator_telegram_id,
                get_message(MATCH_REQUEST_REJECTED, user=initiator, nickname=member.nickname if member else "Unknown")
            )
        except Exception as e:
            import logging
            logging.error(f"[cb_reject_match] Failed to notify initiator: {e}")
    
    await callback.answer()

@router.callback_query(F.data.startswith("block_match_"))
async def cb_block_match(callback: types.CallbackQuery, state: FSMContext):
    """Заблокировать пользователя (больше не показывать матчи)"""
    from src.utils.redis import get_or_restore_internal_user_id, get_telegram_user_id
    
    user_id = await get_or_restore_internal_user_id(state, callback.from_user.id)
    if not user_id:
        await callback.answer("Please start the bot to use this feature.", show_alert=True)
        return
    
    initiator_user_id = int(callback.data.split("_")[-1])
    
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
        group_id = user.current_group_id if user else None
        
        if not user or not group_id:
            await callback.answer("Please start the bot to use this feature.", show_alert=True)
            return
        
        initiator = await session.execute(select(User).where(User.id == initiator_user_id))
        initiator = initiator.scalar()
        
        member = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == group_id))
        member = member.scalar()
        
        # Set status to "blocked" for request
        match_status = await session.execute(select(MatchStatus).where(
            MatchStatus.user_id == initiator_user_id,
            MatchStatus.group_id == group_id,
            MatchStatus.match_user_id == user.id,
            MatchStatus.status == "pending_approval"
        ))
        match_status = match_status.scalar()
        
        if match_status:
            match_status.status = "blocked"
        
        # Create reverse record for blocking (to exclude this user from future matches)
        reverse_status = await session.execute(select(MatchStatus).where(
            MatchStatus.user_id == user.id,
            MatchStatus.group_id == group_id,
            MatchStatus.match_user_id == initiator_user_id
        ))
        reverse_status = reverse_status.scalar()
        
        if reverse_status:
            reverse_status.status = "hidden"
        else:
            new_reverse_status = MatchStatus(user_id=user.id, group_id=group_id, 
                                           match_user_id=initiator_user_id, status="hidden")
            session.add(new_reverse_status)
        
        await session.commit()
    
    # Delete request messages
    try:
        await callback.message.delete()
        # Try to delete previous message (request text)
        await callback.bot.delete_message(callback.message.chat.id, callback.message.message_id - 1)
    except Exception:
        pass
    
    # Notify initiator about blocking
    initiator_telegram_id = await get_telegram_user_id(initiator.id)
    if initiator_telegram_id:
        try:
            await callback.bot.send_message(
                initiator_telegram_id,
                get_message(MATCH_REQUEST_BLOCKED, user=initiator, nickname=member.nickname if member else "Unknown")
            )
        except Exception as e:
            import logging
            logging.error(f"[cb_block_match] Failed to notify initiator: {e}")
    
    await callback.answer()

@router.callback_query(F.data.startswith("go_to_chat_"))
async def cb_go_to_chat(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик нажатия на кнопку 'Go to Allkinds Chat Bot' - удаляет уведомление и перенаправляет в чат-бот."""
    # Extract parameter for link
    param = callback.data.replace("go_to_chat_", "")
    link = f"https://t.me/{ALLKINDS_CHAT_BOT_USERNAME}?start={param}"
    
    # Delete notification message
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    # Send new message with URL button
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🚀 Open Allkinds Chat Bot", url=link)]
    ])
    await callback.message.answer("Ready to chat? Click the button below:", reply_markup=kb)
    await callback.answer()

async def switch_group_service(user_id: int, group_id: int) -> dict:
    """Сменить текущую группу пользователя. Вернуть статус и данные группы."""
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
        member = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == group_id))
        member = member.scalar()
        onboarded = member and member.nickname and (member.geolocation_lat or member.city) and member.photo_url
        if not onboarded:
            return {"ok": False, "reason": "not_onboarded", "group": {"id": group_id}}
        user.current_group_id = group_id
        await session.commit()
        group = await session.execute(select(Group).where(Group.id == group_id))
        group = group.scalar()
        return {"ok": True, "group": {"id": group.id, "name": group.name}}

# TODO: Move all group-related handlers here (create, join, switch, delete, leave, confirm/cancel) 