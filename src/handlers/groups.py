import os
import logging
from src.db import AsyncSessionLocal
from sqlalchemy import select
from src.models import Group, GroupMember, User
# Хендлеры для управления группами
# Импорты и вызовы сервисов будут добавлены после выноса бизнес-логики 

from aiogram import types, F, Router
from aiogram.fsm.context import FSMContext
from src.loader import bot
from src.keyboards.groups import get_admin_keyboard, get_user_keyboard, go_to_group_keyboard, get_group_main_keyboard, get_confirm_delete_keyboard, location_keyboard
from src.fsm.states import CreateGroup, JoinGroup
from src.services.groups import (
    get_user_groups, is_group_creator, get_group_members, create_group_service,
    join_group_by_code_service, leave_group_service, delete_group_service, switch_group_service
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
    if not groups:
        is_creator = await is_group_creator(user_id)
        if is_creator:
            kb = get_admin_keyboard([])
        else:
            kb = get_user_keyboard()
        await message.answer("You are not in any groups.", reply_markup=kb)
        return
    # Получаем текущую группу пользователя
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
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
        # Получаем данные о группе
        group = await session.execute(select(Group).where(Group.id == current_group["id"]))
        group = group.scalar()
    bot_info = await message.bot.get_me()
    deeplink = f"https://t.me/{bot_info.username}?start={group.invite_code}"
    text = f"You are in <b>{group.name}</b>\n{group.description}\n\nInvite link: {deeplink}\nInvite code: <code>{group.invite_code}</code>"
    is_creator = (group.creator_user_id == user.id)
    kb = get_group_main_keyboard(user.id, group.id, group.name, is_creator)
    kb.inline_keyboard.append([])
    other_groups = [g for g in groups if g["id"] != group.id]
    for g in other_groups:
        kb.inline_keyboard.append([
            types.InlineKeyboardButton(text=f"Switch to {g['name']}", callback_data=f"switch_to_group_{g['id']}")
        ])
    if await is_group_creator(user_id):
        kb.inline_keyboard.append([
            types.InlineKeyboardButton(text="Create a new group", callback_data="create_new_group")
        ])
    kb.inline_keyboard.append([
        types.InlineKeyboardButton(text="Join another group with code", callback_data="join_another_group_with_code")
    ])
    sent = await message.answer(text, reply_markup=kb, parse_mode="HTML")
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
    # Получаем только данные для UI
    user_id = callback.from_user.id
    groups = await get_user_groups(user_id)
    group = next((g for g in groups if g["id"] == group_id), None)
    group_name = group["name"] if group else "this group"
    text = f"Are you sure you want to leave <b>{group_name}</b>?\nAll your answers in this group will be deleted."
    kb = get_confirm_delete_keyboard(group_id)
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
    from src.services.groups import get_user_groups
    user_id = callback.from_user.id
    groups = await get_user_groups(user_id)
    group = next((g for g in groups if g["id"] == group_id), None)
    group_name = group["name"] if group else "this group"
    text = f"Are you sure you want to delete <b>{group_name}</b>?\nAll questions and users will be deleted from this group. This action cannot be undone."
    kb = get_confirm_delete_keyboard(group_id)
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

# --- Group-related handlers ---

@router.callback_query(F.data == "create_new_group")
async def cb_create_group(callback: types.CallbackQuery, state: FSMContext):
    is_creator = await is_group_creator(callback.from_user.id)
    if not is_creator:
        await callback.message.answer("You are not allowed to create groups.")
        await callback.answer()
        return
    await callback.message.answer("Enter group name:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(CreateGroup.name)
    await callback.answer()

@router.message(CreateGroup.name)
async def group_name_step(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("Name can't be empty. Enter group name:")
        return
    await state.update_data(name=name)
    await message.answer("Enter group description:")
    await state.set_state(CreateGroup.description)

@router.message(CreateGroup.description)
async def group_desc_step(message: types.Message, state: FSMContext):
    desc = message.text.strip()
    if not desc:
        await message.answer("Description can't be empty. Enter group description:")
        return
    data = await state.get_data()
    group = await create_group_service(message.from_user.id, data["name"], desc)
    bot_info = await bot.get_me()
    deep_link = f"https://t.me/{bot_info.username}?start={group['invite_code']}"
    await message.answer(
        f"✅ Group '{group['name']}' created! Invite code: {group['invite_code']}\nInvite link: {deep_link}",
        reply_markup=go_to_group_keyboard(group["id"], group["name"]))
    await state.clear()

async def show_group_welcome_and_question(message, user_id, group_id):
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

    onboarded = await is_onboarded(user_id, group_id)
    if onboarded:
        balance = await get_group_balance(user_id, group_id)
        groups = await get_user_groups(user_id)
        group = next((g for g in groups if g["id"] == group_id), None)
        group_name = group["name"] if group else "this group"
        await message.answer(
            f"Welcome back to {group_name}. Your balance is {balance} points.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="Load answered questions", callback_data="load_answered_questions")]]
            )
        )
        async with AsyncSessionLocal() as session:
            user = await session.execute(select(User).where(User.telegram_user_id == user_id))
            user = user.scalar()
            next_q = await get_next_unanswered_question(session, group_id, user.id)
            if next_q:
                await send_question_to_user(bot, user, next_q)
            else:
                await message.answer("No new questions in this group yet.")
    else:
        await message.answer("Let's set up your profile for this group!\nEnter your nickname:", reply_markup=types.ReplyKeyboardRemove())
        from src.fsm.states import Onboarding
        from aiogram.fsm.context import FSMContext
        state = FSMContext(message.bot, message.chat.id, message.from_user.id)
        await state.update_data(group_id=group_id)
        await state.set_state(Onboarding.nickname)

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
        await callback.message.answer("Let's set up your profile for this group!\nEnter your nickname:", reply_markup=types.ReplyKeyboardRemove())
        await state.update_data(group_id=group_id)
        from src.fsm.states import Onboarding
        await state.set_state(Onboarding.nickname)
        await callback.answer()

@router.callback_query(F.data == "join_another_group_with_code")
async def cb_join_group(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Enter the 5-character invite code:", reply_markup=types.ReplyKeyboardRemove())
    from src.fsm.states import JoinGroup
    await state.set_state(JoinGroup.code)
    await callback.answer()

@router.message(JoinGroup.code)
async def process_invite_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    if not code or len(code) != 5:
        await message.answer("Invalid code. Enter the 5-character invite code:")
        return
    group = await join_group_by_code_service(message.from_user.id, code)
    if not group:
        await message.answer("Group not found. Check the code and try again.")
        return
    await message.answer(f"You joined group '{group['name']}'!", reply_markup=go_to_group_keyboard(group["id"], group["name"]))
    await state.clear()

# TODO: Перенести сюда все group-related хендлеры (create, join, switch, delete, leave, confirm/cancel) 