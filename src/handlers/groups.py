import os
import logging
from src.db import AsyncSessionLocal
from sqlalchemy import select, and_, text
from src.models import Group, GroupMember, User, Answer, Question, MatchStatus, Match
# Хендлеры для управления группами
# Импорты и вызовы сервисов будут добавлены после выноса бизнес-логики 

from aiogram import types, F, Router
from aiogram.fsm.context import FSMContext
from src.loader import bot
from src.keyboards.groups import get_admin_keyboard, get_user_keyboard, go_to_group_keyboard, get_group_main_keyboard, get_confirm_delete_keyboard, location_keyboard, get_group_reply_keyboard
from src.fsm.states import CreateGroup, JoinGroup
from src.services.groups import (
    get_user_groups, is_group_creator, get_group_members, create_group_service,
    join_group_by_code_service, leave_group_service, delete_group_service, switch_group_service, find_best_match, set_match_status
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
    MATCH_FOUND, MATCH_NO_VALID, MATCH_AI_CHEMISTRY, MATCH_SHOW_AGAIN, MATCH_DONT_SHOW,
    QUESTION_LOAD_ANSWERED, NO_AVAILABLE_ANSWERED_QUESTIONS
)

router = Router()

ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', 0))

async def ensure_admin_in_db():
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == ADMIN_USER_ID))
        user = user.scalar()
        if not user:
            user = User(telegram_user_id=ADMIN_USER_ID)
            session.add(user)
            await session.flush()
        creator = await session.execute(select(GroupCreator).where(GroupCreator.user_id == user.id))
        creator = creator.scalar()
        if not creator:
            session.add(GroupCreator(user_id=user.id))
            await session.commit()

async def get_user_groups(user_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Group).join(GroupMember).join(User).where(User.telegram_user_id == user_id)
        )
        groups = result.scalars().all()
        logging.info(f"[get_user_groups] user_id={user_id}, groups={[g.name for g in groups]}")
        return [{"id": g.id, "name": g.name} for g in groups]

async def create_group(user_id: int, name: str, description: str):
    from src.utils import generate_unique_invite_code
    invite_code = await generate_unique_invite_code()
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        if not user:
            user = User(telegram_user_id=user_id)
            session.add(user)
            await session.flush()
        group = Group(name=name, description=description, invite_code=invite_code, creator_user_id=user.id)
        session.add(group)
        await session.flush()
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
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        if not user:
            user = User(telegram_user_id=user_id)
            session.add(user)
            await session.flush()
        member = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == group.id))
        member = member.scalar()
        if not member:
            member = GroupMember(user_id=user.id, group_id=group.id)
            session.add(member)
            await session.commit()
        return {"id": group.id, "name": group.name}

async def show_user_groups(message: types.Message, state: FSMContext) -> None:
    """
    Handler: Показывает пользователю его группы, используя только сервисные методы для получения данных.
    Генерация клавиатур и отправка сообщений — только здесь.
    """
    user_id = message.from_user.id
    groups = await get_user_groups(user_id)
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        if not groups:
            is_creator = await is_group_creator(user_id)
            if is_creator:
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
    if await is_group_creator(user_id):
        kb.inline_keyboard.append([
            types.InlineKeyboardButton(text=get_message(BTN_CREATE_GROUP, user=user), callback_data="create_new_group")
        ])
    kb.inline_keyboard.append([
        types.InlineKeyboardButton(text=get_message(BTN_JOIN_GROUP, user=user), callback_data="join_another_group_with_code")
    ])
    sent = await message.answer(text, reply_markup=kb, parse_mode="HTML")
    # --- Новая логика для кнопки истории ---
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
    user_id = callback.from_user.id
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
    groups = await get_user_groups(user_id)
    group = next((g for g in groups if g["id"] == group_id), None)
    group_name = group["name"] if group else "this group"
    text = get_message(GROUPS_LEAVE_CONFIRM, user=user, group_name=group_name)
    kb = get_confirm_delete_keyboard(group_id, user)
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

@router.callback_query(F.data.startswith("confirm_delete_group_"))
async def cb_confirm_delete_group(callback: types.CallbackQuery, state: FSMContext):
    await clear_mygroups_messages(callback.message, state)
    group_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
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
    user_id = callback.from_user.id
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
    # Удаляем группу через сервис
    result = await delete_group_service(group_id)
    if result["ok"]:
        await callback.message.answer(get_message("Группа успешно удалена.", user=user))
        await clear_mygroups_messages(callback.message, state)
        await state.clear()
    else:
        await callback.message.answer(get_message("Ошибка при удалении группы.", user=user))
    await callback.answer()

# --- Group-related handlers ---

@router.callback_query(F.data == "create_new_group")
async def cb_create_group(callback: types.CallbackQuery, state: FSMContext):
    is_creator = await is_group_creator(callback.from_user.id)
    if not is_creator:
        await callback.message.answer(get_message("You are not allowed to create groups.", user=callback.from_user))
        await callback.answer()
        return
    await callback.message.answer(get_message("Enter group name:", user=callback.from_user), reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(CreateGroup.name)
    await callback.answer()

@router.message(CreateGroup.name)
async def group_name_step(message: types.Message, state: FSMContext):
    name = message.text.strip()
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == message.from_user.id))
        user = user.scalar()
    if not name:
        await message.answer(get_message(GROUPS_NAME_EMPTY, user=user))
        return
    await state.update_data(name=name)
    await message.answer(get_message("Enter group description:", user=user))
    await state.set_state(CreateGroup.description)

@router.message(CreateGroup.description)
async def group_desc_step(message: types.Message, state: FSMContext):
    desc = message.text.strip()
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == message.from_user.id))
        user = user.scalar()
    if not desc:
        await message.answer(get_message(GROUPS_DESC_EMPTY, user=user))
        return
    data = await state.get_data()
    group = await create_group_service(message.from_user.id, data["name"], desc)
    bot_info = await bot.get_me()
    deep_link = f"https://t.me/{bot_info.username}?start={group['invite_code']}"
    await message.answer(
        get_message(GROUPS_CREATED, user=user, group_name=group["name"], invite_code=group["invite_code"], deep_link=deep_link),
        reply_markup=go_to_group_keyboard(group["id"], group["name"], user))
    await state.clear()

async def show_group_welcome_and_question(message, user_id, group_id):
    import logging
    try:
        print(f"[DEBUG] show_group_welcome_and_question called: user_id={user_id}, group_id={group_id}")
        from src.services.groups import get_group_balance
        from src.services.groups import is_onboarded
        from src.services.groups import get_user_groups
        from src.services.questions import get_next_unanswered_question
        from src.handlers.questions import send_question_to_user
        from src.loader import bot
        from sqlalchemy import select
        from src.db import AsyncSessionLocal
        from src.models import User
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        async with AsyncSessionLocal() as session:
            user = await session.execute(select(User).where(User.telegram_user_id == user_id))
            user = user.scalar()
            print(f"[DEBUG] loaded user: {user}")
        onboarded = await is_onboarded(user_id, group_id)
        print(f"[DEBUG] onboarded={onboarded}")
        if onboarded:
            async with AsyncSessionLocal() as session:
                print(f"[DEBUG] in onboarded block, user={user}, group_id={group_id}")
                balance = await get_group_balance(user_id, group_id)
                groups = await get_user_groups(user_id)
                print(f"[DEBUG] groups={groups}")
                group = next((g for g in groups if g["id"] == group_id), None)
                print(f"[DEBUG] group={group}")
                group_name = group["name"] if group else "this group"
                # --- Welcome-back с мэтч-кнопкой ---
                await message.answer(
                    get_message(f"Welcome back to {group_name}. Your balance is {balance}💎 points.", user=user),
                    reply_markup=get_group_reply_keyboard(user)
                )
                # --- Кнопка истории ---
                any_answers = await session.execute(
                    select(Answer).where(
                        Answer.user_id == user.id,
                        Answer.question_id.in_(select(Question.id).where(Question.group_id == group_id))
                    )
                )
                any_answers = any_answers.scalars().all()
                valid_answers = await session.execute(
                    select(Answer).where(
                        Answer.user_id == user.id,
                        Answer.value.isnot(None),
                        Answer.question_id.in_(select(Question.id).where(Question.group_id == group_id, Question.is_deleted == 0))
                    )
                )
                valid_answers = valid_answers.scalars().all()
                print(f"[DEBUG] any_answers: {len(any_answers)}, valid_answers: {len(valid_answers)} for user_id={user.id}, group_id={group_id}")
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
                # --- Вопросы ---
                answers_count = await session.execute(
                    select(Answer).where(
                        Answer.user_id == user.id,
                        Answer.value.isnot(None),
                        Answer.question_id.in_(select(Question.id).where(Question.group_id == group_id, Question.is_deleted == 0))
                    )
                )
                answers_count = len(answers_count.scalars().all())
                next_q = await get_next_unanswered_question(session, group_id, user.id)
                if next_q:
                    await send_question_to_user(bot, user, next_q)
                else:
                    await message.answer(get_message(GROUPS_NO_NEW_QUESTIONS, user=user))
            # Клавиатура мэтча уже отправлена с welcome-back
        else:
            await message.answer(get_message(GROUPS_PROFILE_SETUP, user=user), reply_markup=types.ReplyKeyboardRemove())
            from src.fsm.states import Onboarding
            from aiogram.fsm.context import FSMContext
            state = FSMContext(message.bot, message.chat.id, message.from_user.id)
            await state.update_data(group_id=group_id)
            await state.set_state(Onboarding.nickname)
    except Exception as e:
        logging.exception("Ошибка в show_group_welcome_and_question")
        raise

@router.callback_query(F.data.startswith("switch_to_group_"))
async def cb_switch_to_group(callback: types.CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    result = await switch_group_service(user_id, group_id)
    if result["ok"]:
        await callback.message.delete()
        await show_group_welcome_and_question(callback.message, user_id, group_id)
        await callback.answer()
    else:
        async with AsyncSessionLocal() as session:
            user = await session.execute(select(User).where(User.telegram_user_id == user_id))
            user = user.scalar()
        await callback.message.answer(get_message("Let's set up your profile for this group!\nEnter your nickname:", user=user), reply_markup=types.ReplyKeyboardRemove())
        await state.update_data(group_id=group_id)
        from src.fsm.states import Onboarding
        await state.set_state(Onboarding.nickname)
        await callback.answer()

@router.callback_query(F.data == "join_another_group_with_code")
async def cb_join_group(callback: types.CallbackQuery, state: FSMContext):
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == callback.from_user.id))
        user = user.scalar()
    await callback.message.answer(get_message("Enter the 5-character invite code:", user=user), reply_markup=types.ReplyKeyboardRemove())
    from src.fsm.states import JoinGroup
    await state.set_state(JoinGroup.code)
    await callback.answer()

@router.message(JoinGroup.code)
async def process_invite_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == message.from_user.id))
        user = user.scalar()
    if not code or len(code) != 5:
        await message.answer(get_message(GROUPS_JOIN_INVALID_CODE, user=user))
        return
    group = await join_group_by_code_service(message.from_user.id, code)
    if not group:
        await message.answer(get_message(GROUPS_JOIN_NOT_FOUND, user=user))
        return
    if group.get("needs_onboarding"):
        await message.answer(get_message(GROUPS_JOIN_ONBOARDING, user=user, group_name=group["name"]), reply_markup=types.ReplyKeyboardRemove())
        await state.update_data(group_id=group["id"])
        from src.fsm.states import Onboarding
        await state.set_state(Onboarding.nickname)
        return
    await message.answer(get_message(GROUPS_JOINED, user=user, group_name=group["name"], bonus=WELCOME_BONUS), reply_markup=go_to_group_keyboard(group["id"], group["name"], user))
    # Клавиатура мэтча будет показана после входа в группу
    await state.clear()

@router.callback_query(F.data.startswith("find_match_"))
async def cb_find_match(callback: types.CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    from src.models import User, Answer, GroupMember
    from sqlalchemy import select
    from src.db import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        if not user:
            await callback.answer(get_message(MATCH_NO_VALID, user=user, show_alert=True))
            return
        # Считаем количество ответов пользователя в группе
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
        if not member or member.balance < POINTS_FOR_MATCH:
            await callback.message.answer(get_message(f"Not enough points for match. Your balance: {member.balance if member else 0}.", user=user))
            return
        if answers_count < MIN_ANSWERS_FOR_MATCH:
            await callback.message.answer(get_message(f"You need to answer at least {MIN_ANSWERS_FOR_MATCH} questions to get a match. You have answered: {answers_count}. Keep answering or create new questions!", user=user))
            return
        # Поиск мэтча
        match = await find_best_match(user_id, group_id)
        if not match or not match.get('telegram_user_id'):
            await callback.answer(get_message(MATCH_NO_VALID, user=user, show_alert=True))
            return
        # Списываем баллы
        member.balance -= POINTS_FOR_MATCH
        await session.commit()
        # Показываем UX мэтча
        text = get_message(MATCH_FOUND, user=user, nickname=match['nickname'], similarity=match['similarity'], common_questions=match['common_questions'], valid_users_count=match['valid_users_count'])
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text=get_message(MATCH_AI_CHEMISTRY, user=user, points=POINTS_TO_CONNECT), callback_data=f"match_chat_{match['user_id']}")],
            [types.InlineKeyboardButton(text=get_message(MATCH_SHOW_AGAIN, user=user), callback_data=f"match_postpone_{match['user_id']}")],
            [types.InlineKeyboardButton(text=get_message(MATCH_DONT_SHOW, user=user), callback_data=f"match_hide_{match['user_id']}")]
        ])
        if match['photo_url']:
            await callback.message.answer_photo(match['photo_url'], caption=text, reply_markup=kb, parse_mode="HTML")
        else:
            await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()

@router.callback_query(F.data.startswith("match_hide_"))
async def cb_match_hide(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = callback.data.split("_")
    match_user_id = int(data[-1])
    # Получаем group_id из текущей группы пользователя
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        group_id = user.current_group_id if user else None
    if group_id:
        await set_match_status(user_id, group_id, match_user_id, "hidden")
        # Удаляем сообщения мэтча (фото/текст)
        try:
            await callback.message.delete()
        except Exception:
            pass
        # Отправляем уведомление и удаляем его через 5 секунд
        notif = await callback.message.answer(get_message("This user will no longer be shown to you.", user=callback.from_user))
        await asyncio.sleep(5)
        try:
            await notif.delete()
        except Exception:
            pass
    await callback.answer()

@router.callback_query(F.data.startswith("match_postpone_"))
async def cb_match_postpone(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = callback.data.split("_")
    match_user_id = int(data[-1])
    # Получаем group_id из текущей группы пользователя
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        group_id = user.current_group_id if user else None
        if group_id:
            # Удаляем статус postponed/hidden для этого мэтча (возвращаем в пул)
            await session.execute(
                text("DELETE FROM match_statuses WHERE user_id = :user_id AND group_id = :group_id AND match_user_id = :match_user_id"),
                {"user_id": user.id, "group_id": group_id, "match_user_id": match_user_id}
            )
            await session.commit()
            # Удаляем сообщения мэтча (фото/текст)
            try:
                await callback.message.delete()
            except Exception:
                pass
            # Удаляем исходное сообщение с кнопкой мэтча, если оно есть
            data = await state.get_data()
            vibing_msg_id = data.get("vibing_msg_id")
            if vibing_msg_id:
                try:
                    await callback.message.bot.delete_message(callback.message.chat.id, vibing_msg_id)
                except Exception:
                    pass
                await state.update_data(vibing_msg_id=None)
            # Отправляем уведомление и удаляем его через 5 секунд
            notif = await callback.message.answer(get_message("This match will be shown to you again.", user=callback.from_user))
            await asyncio.sleep(5)
            try:
                await notif.delete()
            except Exception:
                pass
    await callback.answer()

@router.message(F.text.func(lambda t: t and ("vibing" in t.lower() or "совпадает" in t.lower())))
async def handle_vibing_button(message: types.Message, state: FSMContext):
    import logging
    try:
        await state.update_data(vibing_msg_id=message.message_id)
        async with AsyncSessionLocal() as session:
            user = await session.execute(select(User).where(User.telegram_user_id == message.from_user.id))
            user = user.scalar()
            group_id = user.current_group_id if user else None
        if not group_id:
            await message.answer(get_message("You are not in a group.", user=user))
            return
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
    user_id = callback.from_user.id
    match_user_id = int(callback.data.split("_")[-1])
    from src.models import MatchStatus
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        group_id = user.current_group_id if user else None
        member = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == group_id))
        member = member.scalar()
        print(f"[DEBUG] cb_match_chat: user_id={user_id}, match_user_id={match_user_id}, group_id={group_id}")
        match_user = await session.execute(select(User).where(User.id == match_user_id))
        match_user = match_user.scalar()
        print(f"[DEBUG] cb_match_chat: match_user={match_user}")
        if not match_user:
            await callback.message.answer(get_message("Match user not found.", user=user))
            await callback.answer()
            return
        obj1 = await session.execute(select(MatchStatus).where(
            MatchStatus.user_id == user.id,
            MatchStatus.group_id == group_id,
            MatchStatus.match_user_id == match_user.id
        ))
        obj1 = obj1.scalar()
        if not obj1:
            obj1 = MatchStatus(user_id=user.id, group_id=group_id, match_user_id=match_user.id, status="matched")
            session.add(obj1)
        else:
            obj1.status = "matched"
        obj2 = await session.execute(select(MatchStatus).where(
            MatchStatus.user_id == match_user.id,
            MatchStatus.group_id == group_id,
            MatchStatus.match_user_id == user.id
        ))
        obj2 = obj2.scalar()
        if not obj2:
            obj2 = MatchStatus(user_id=match_user.id, group_id=group_id, match_user_id=user.id, status="matched")
            session.add(obj2)
        else:
            obj2.status = "matched"
        user1_id = min(user.id, match_user.id)
        user2_id = max(user.id, match_user.id)
        match_obj = await session.execute(select(Match).where(
            Match.user1_id == user1_id,
            Match.user2_id == user2_id,
            Match.group_id == group_id
        ))
        match_obj = match_obj.scalar()
        if not match_obj:
            from datetime import datetime, UTC
            match_obj = Match(user1_id=user1_id, user2_id=user2_id, group_id=group_id, created_at=datetime.now(UTC), status="active")
            session.add(match_obj)
        await session.commit()
    try:
        await callback.message.delete()
    except Exception:
        pass
    data = await state.get_data()
    vibing_msg_id = data.get("vibing_msg_id")
    if vibing_msg_id:
        try:
            await callback.message.bot.delete_message(callback.message.chat.id, vibing_msg_id)
        except Exception:
            pass
        await state.update_data(vibing_msg_id=None)
    param = quote(f"match_{user_id}_{match_user_id}")
    link = f"https://t.me/{ALLKINDS_CHAT_BOT_USERNAME}?start={param}"
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=get_message("Go to Allkinds Chat Bot", user=user), url=link)]
    ])
    notif = await callback.message.answer(get_message("Click the button below to start your private chat:", user=user), reply_markup=kb)
    async with AsyncSessionLocal() as session:
        match_user = await session.execute(select(User).where(User.id == match_user_id))
        match_user = match_user.scalar()
        if match_user:
            param2 = quote(f"match_{match_user_id}_{user_id}")
            link2 = f"https://t.me/{ALLKINDS_CHAT_BOT_USERNAME}?start={param2}"
            kb2 = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text=get_message("Go to Allkinds Chat Bot", user=match_user), url=link2)]
            ])
            try:
                await callback.bot.send_message(match_user.telegram_user_id, get_message("You have a new match! Click below to start your private chat:", user=match_user), reply_markup=kb2)
            except Exception:
                pass
    await asyncio.sleep(5)
    try:
        await notif.delete()
    except Exception:
        pass
    await callback.answer()

async def switch_group_service(user_id: int, group_id: int) -> dict:
    """Сменить текущую группу пользователя. Вернуть статус и данные группы."""
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
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

# TODO: Перенести сюда все group-related хендлеры (create, join, switch, delete, leave, confirm/cancel) 