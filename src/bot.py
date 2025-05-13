import asyncio
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, BotCommand
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from src.config import BOT_TOKEN, ADMIN_USER_ID
from src.db import AsyncSessionLocal
from src.models import User, Group, GroupMember, GroupCreator, Question, Answer
from src.utils import generate_unique_invite_code
from sqlalchemy import select, insert, and_, or_
import os
import logging
import re
from aiogram.utils.keyboard import InlineKeyboardBuilder

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# FSM состояния
class CreateGroup(StatesGroup):
    name = State()
    description = State()

class Onboarding(StatesGroup):
    nickname = State()
    photo = State()
    location = State()

class JoinGroup(StatesGroup):
    code = State()

# Кнопки
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

def location_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📍 Send location", request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

# Заглушка: получить группы пользователя (реализуем позже)
async def get_user_groups(user_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Group).join(GroupMember).join(User).where(User.telegram_user_id == user_id)
        )
        groups = result.scalars().all()
        logging.info(f"[get_user_groups] user_id={user_id}, groups={[g.name for g in groups]}")
        return [{"id": g.id, "name": g.name} for g in groups]

async def is_onboarded(user_id: int, group_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(GroupMember).join(User).where(
                User.telegram_user_id == user_id,
                GroupMember.group_id == group_id,
                GroupMember.nickname.isnot(None),
                GroupMember.photo_url.isnot(None),
                (GroupMember.geolocation_lat.isnot(None) | GroupMember.city.isnot(None))
            )
        )
        return result.scalar() is not None

async def get_group_balance(user_id: int, group_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(GroupMember.balance).join(User).where(
                User.telegram_user_id == user_id,
                GroupMember.group_id == group_id
            )
        )
        balance = result.scalar()
        return balance if balance is not None else 0

async def create_group(user_id: int, name: str, description: str):
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

async def is_group_creator(user_id: int):
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        if not user:
            return False
        creator = await session.execute(select(GroupCreator).where(GroupCreator.user_id == user.id))
        return creator.scalar() is not None

@dp.startup()
async def on_startup(dispatcher):
    await ensure_admin_in_db()
    commands = [
        BotCommand(command="start", description="Start bot"),
        BotCommand(command="mygroups", description="Show your groups"),
        BotCommand(command="instructions", description="How to use the bot"),
        # Можно добавить другие команды
    ]
    await bot.set_my_commands(commands)

async def show_user_groups(message, user_id, state):
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        if not user:
            await message.answer("You are not registered. Use /start.")
            return
        groups = await session.execute(
            select(Group).join(GroupMember).where(GroupMember.user_id == user.id)
        )
        groups = groups.scalars().all()
        if not groups:
            is_creator = await is_group_creator(user_id)
            if is_creator:
                kb = InlineKeyboardMarkup(inline_keyboard=[[create_group_btn], [join_group_btn]])
            else:
                kb = get_user_keyboard()
            await message.answer("You are not in any groups.", reply_markup=kb)
            return
        current_group = None
        if user.current_group_id:
            current_group = next((g for g in groups if g.id == user.current_group_id), None)
        if not current_group:
            current_group = groups[0]
            user.current_group_id = current_group.id
            await session.commit()
        bot_info = await bot.get_me()
        deeplink = get_group_deeplink(bot_info.username, current_group.invite_code)
        text = f"You are in <b>{current_group.name}</b>\n{current_group.description}\n\nInvite link: {deeplink}\nInvite code: <code>{current_group.invite_code}</code>"
        is_creator = (current_group.creator_user_id == user.id)
        kb = get_group_main_keyboard(user.id, current_group.id, current_group.name, is_creator)
        # Пустая строка-разделитель
        kb.inline_keyboard.append([])
        # Кнопки Switch to <group>
        other_groups = [g for g in groups if g.id != current_group.id]
        for g in other_groups:
            kb.inline_keyboard.append([InlineKeyboardButton(text=f"Switch to {g.name}", callback_data=f"switch_to_group_{g.id}")])
        # Join и Create — в самом низу
        if await is_group_creator(user_id):
            kb.inline_keyboard.append([create_group_btn])
        kb.inline_keyboard.append([join_group_btn])
        sent = await message.answer(text, reply_markup=kb, parse_mode="HTML")
        data = await state.get_data()
        ids = data.get("my_groups_msg_ids", [])
        ids.append(sent.message_id)
        await state.update_data(my_groups_msg_ids=ids)

async def hide_instructions_and_mygroups_by_message(message, state):
    data = await state.get_data()
    msg_id = data.get("instructions_msg_id")
    if msg_id:
        try:
            await message.bot.delete_message(message.chat.id, msg_id)
        except Exception:
            pass
    ids = data.get("my_groups_msg_ids", [])
    for mid in ids:
        try:
            await message.bot.delete_message(message.chat.id, mid)
        except Exception:
            pass
    await state.update_data(instructions_msg_id=None, my_groups_msg_ids=[])

@dp.message(Command("instructions"))
async def instructions(message: types.Message, state: FSMContext):
    await hide_instructions_and_mygroups_by_message(message, state)
    text = (
        "<b>How to use the bot:</b>\n"
        "1. Join a group and get +20💎\n"
        "2. Answer others' questions and get +1💎 for each answer\n"
        "3. Ask your own yes/no questions or statements — +5💎\n"
        "4. Spend points to find your best match in the group —10💎\n"
        "5. Go to Allkinds.Chat and see if you really vibe!"
    )
    msg = await message.answer(text, parse_mode="HTML")
    await state.update_data(instructions_msg_id=msg.message_id)

@dp.message(Command("mygroups"))
async def my_groups(message: types.Message, state: FSMContext):
    await hide_instructions_and_mygroups_by_message(message, state)
    user_id = message.from_user.id
    await show_user_groups(message, user_id, state)

@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    await hide_instructions_and_mygroups_by_message(message, state)
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) == 2 and len(args[1]) == 5:
        code = args[1].upper()
        group = await join_group_by_code(user_id, code)
        if not group:
            await message.answer("❌ Group not found. Check the invite code.")
            return
        onboarded = await is_onboarded(user_id, group["id"])
        if onboarded:
            balance = await get_group_balance(user_id, group["id"])
            await message.answer(f"Welcome back to {group['name']}. Your balance is {balance} points.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Load answered questions", callback_data="load_answered_questions")]]))
            # Показываем первый неотвеченный вопрос
            async with AsyncSessionLocal() as session:
                user = await session.execute(select(User).where(User.telegram_user_id == user_id))
                user = user.scalar()
                next_q = await get_next_unanswered_question(session, group["id"], user.id)
                if next_q:
                    await send_question_to_user(bot, user, next_q)
            return
        await message.answer(f"Joining '{group['name']}'. Let's set up your profile!\nEnter your nickname:", reply_markup=ReplyKeyboardRemove())
        await state.update_data(group_id=group["id"])
        await state.set_state(Onboarding.nickname)
        return
    groups = await get_user_groups(user_id)
    is_creator = await is_group_creator(user_id)
    logging.info(f"[start] user_id={user_id}, is_creator={is_creator}, groups={groups}")
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        memberships = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id))
        memberships = memberships.scalars().all()
        logging.info(f"[start] user_id={user_id}, group_members: {[m.group_id for m in memberships]}")
    if not groups:
        if is_creator:
            await message.answer("👋 Welcome, admin!", reply_markup=get_admin_keyboard([]))
        else:
            await message.answer(
                "Welcome to Allkinds! Here you can join groups by code.",
                reply_markup=get_user_keyboard()
            )
        return
    if len(groups) == 1:
        group = groups[0]
        onboarded = await is_onboarded(user_id, group["id"])
        if onboarded:
            balance = await get_group_balance(user_id, group["id"])
            await message.answer(f"Welcome back to {group['name']}. Your balance is {balance} points.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Load answered questions", callback_data="load_answered_questions")]]))
            # Показываем первый неотвеченный вопрос
            async with AsyncSessionLocal() as session:
                user = await session.execute(select(User).where(User.telegram_user_id == user_id))
                user = user.scalar()
                next_q = await get_next_unanswered_question(session, group["id"], user.id)
                if next_q:
                    await send_question_to_user(bot, user, next_q)
            return
        await message.answer(f"You have one group. Redirecting to onboarding for '{group['name']}'...", reply_markup=ReplyKeyboardRemove())
        await state.update_data(group_id=group["id"])
        await state.set_state(Onboarding.nickname)
        await message.answer("Enter your nickname:")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Switch to {g['name']}", callback_data=f"switch_to_group_{g['id']}")] for g in groups
    ])
    await message.answer("Select a group:", reply_markup=kb)
    # Показываем первый неотвеченный вопрос для текущей группы
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        group_id = user.current_group_id or (groups[0]["id"] if groups else None)
        if group_id:
            next_q = await get_next_unanswered_question(session, group_id, user.id)
            if next_q:
                await send_question_to_user(bot, user, next_q)

@dp.callback_query(F.data == "create_new_group")
async def cb_create_group(callback: types.CallbackQuery, state: FSMContext):
    is_creator = await is_group_creator(callback.from_user.id)
    if not is_creator:
        await callback.message.answer("You are not allowed to create groups.")
        await callback.answer()
        return
    await callback.message.answer("Enter group name:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(CreateGroup.name)
    await callback.answer()

@dp.message(CreateGroup.name)
async def group_name_step(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("Name can't be empty. Enter group name:")
        return
    await state.update_data(name=name)
    await message.answer("Enter group description:")
    await state.set_state(CreateGroup.description)

@dp.message(CreateGroup.description)
async def group_desc_step(message: types.Message, state: FSMContext):
    desc = message.text.strip()
    if not desc:
        await message.answer("Description can't be empty. Enter group description:")
        return
    data = await state.get_data()
    group = await create_group(message.from_user.id, data["name"], desc)
    bot_info = await bot.get_me()
    deep_link = f"https://t.me/{bot_info.username}?start={group['invite_code']}"
    await message.answer(
        f"✅ Group '{group['name']}' created! Invite code: {group['invite_code']}\nInvite link: {deep_link}",
        reply_markup=go_to_group_keyboard(group["id"], group["name"]))
    await state.clear()

@dp.callback_query(F.data.startswith("switch_to_group_"))
async def cb_switch_to_group(callback: types.CallbackQuery, state: FSMContext):
    await hide_instructions_and_mygroups_by_message(callback.message, state)
    group_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        member = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == group_id))
        member = member.scalar()
        onboarded = member and member.nickname and (member.geolocation_lat or member.city) and member.photo_url
        if onboarded:
            user.current_group_id = group_id
            await session.commit()
            await callback.message.delete()
            # Получаем group_name и all_groups_count заранее
            group_obj = await session.execute(select(Group).where(Group.id == group_id))
            group_obj = group_obj.scalar()
            group_name = group_obj.name if group_obj else None
            memberships = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id))
            memberships = memberships.scalars().all()
            all_groups_count = len(memberships)
            # Сначала Load answered questions, потом первый неотвеченный вопрос
            await callback.message.answer(
                "View your answered questions:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Load answered questions", callback_data="load_answered_questions")]])
            )
            next_q = await get_next_unanswered_question(session, group_id, user.id)
            if next_q:
                await send_question_to_user(callback.bot, user, next_q, group_id=group_id, all_groups_count=all_groups_count, group_name=group_name)
            else:
                await callback.message.answer("No new questions in this group.")
            await callback.answer()
            return
    await callback.message.answer("Let's set up your profile for this group!\nEnter your nickname:", reply_markup=ReplyKeyboardRemove())
    await state.update_data(group_id=group_id)
    await state.set_state(Onboarding.nickname)
    await callback.answer()

@dp.message(Onboarding.nickname)
async def onboarding_nick(message: types.Message, state: FSMContext):
    nickname = message.text.strip()
    if not nickname:
        await message.answer("Nickname can't be empty. Enter your nickname:")
        return
    await state.update_data(nickname=nickname)
    await message.answer("Send a photo for your group profile:")
    await state.set_state(Onboarding.photo)

@dp.message(Onboarding.photo, F.photo)
async def onboarding_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    await message.answer(
        "📍 We need your location to find people nearby.\nSend your location or type your city and country:",
        reply_markup=location_keyboard()
    )
    await state.set_state(Onboarding.location)

@dp.message(Onboarding.photo)
async def onboarding_photo_invalid(message: types.Message):
    await message.answer("Please send a photo (not a file or sticker). Try again:")

@dp.message(Onboarding.location, F.location)
async def onboarding_location_geo(message: types.Message, state: FSMContext):
    lat = message.location.latitude
    lon = message.location.longitude
    data = await state.get_data()
    user_id = message.from_user.id
    group_id = data.get("group_id")
    nickname = data.get("nickname")
    photo_id = data.get("photo_id")
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        member = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == group_id))
        member = member.scalar()
        if member:
            member.nickname = nickname
            member.photo_url = photo_id
            member.geolocation_lat = lat
            member.geolocation_lon = lon
            member.city = None
        user.current_group_id = group_id
        await session.commit()
    await message.answer("🎉 Profile setup complete!", reply_markup=ReplyKeyboardRemove())
    await state.clear()
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == message.from_user.id))
        user = user.scalar()
        group_id = None
        for m in user.memberships:
            if m.nickname and (m.geolocation_lat or m.city):
                group_id = m.group_id
                break
        if group_id:
            next_q = await get_next_unanswered_question(session, group_id, user.id)
            if next_q:
                logging.info(f"[onboarding_location_geo] Showing first unanswered question to user_id={user.id}, group_id={group_id}, question_id={next_q.id}")
                await send_question_to_user(bot, user, next_q)
            else:
                logging.info(f"[onboarding_location_geo] No unanswered questions for user_id={user.id}, group_id={group_id}")

@dp.message(Onboarding.location)
async def onboarding_location_city(message: types.Message, state: FSMContext):
    city = message.text.strip()
    if not city:
        await message.answer("City/country can't be empty. Enter your city and country:")
        return
    data = await state.get_data()
    user_id = message.from_user.id
    group_id = data.get("group_id")
    nickname = data.get("nickname")
    photo_id = data.get("photo_id")
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        member = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == group_id))
        member = member.scalar()
        if member:
            member.nickname = nickname
            member.photo_url = photo_id
            member.geolocation_lat = None
            member.geolocation_lon = None
            member.city = city
        user.current_group_id = group_id
        await session.commit()
    await message.answer("🎉 Profile setup complete!", reply_markup=ReplyKeyboardRemove())
    await state.clear()
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == message.from_user.id))
        user = user.scalar()
        group_id = None
        for m in user.memberships:
            if m.nickname and (m.geolocation_lat or m.city):
                group_id = m.group_id
                break
        if group_id:
            next_q = await get_next_unanswered_question(session, group_id, user.id)
            if next_q:
                logging.info(f"[onboarding_location_city] Showing first unanswered question to user_id={user.id}, group_id={group_id}, question_id={next_q.id}")
                await send_question_to_user(bot, user, next_q)
            else:
                logging.info(f"[onboarding_location_city] No unanswered questions for user_id={user.id}, group_id={group_id}")

@dp.callback_query(F.data == "join_another_group_with_code")
async def cb_join_group(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Enter the 5-character invite code:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(JoinGroup.code)
    await callback.answer()

@dp.message(JoinGroup.code)
async def process_invite_code(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    if len(code) != 5:
        await message.answer("Code must be 5 characters. Try again:")
        return
    user_id = message.from_user.id
    group = await join_group_by_code(user_id, code)
    if not group:
        await message.answer("❌ Group not found. Check the invite code.")
        await state.clear()
        return
    onboarded = await is_onboarded(user_id, group["id"])
    if onboarded:
        balance = await get_group_balance(user_id, group["id"])
        await message.answer(f"Welcome back to {group['name']}. Your balance is {balance} points.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Load answered questions", callback_data="load_answered_questions")]]))
        await state.clear()
        return
    await message.answer(f"Joining '{group['name']}'. Let's set up your profile!\nEnter your nickname:")
    await state.update_data(group_id=group["id"])
    await state.set_state(Onboarding.nickname)

router = Router()

def get_group_deeplink(bot_username, invite_code):
    return f"https://t.me/{bot_username}?start={invite_code}"

def get_group_main_keyboard(user_id, group_id, group_name, is_creator):
    """Return main group keyboard: Delete for creator, Leave for others."""
    if is_creator:
        kb = [[InlineKeyboardButton(text=f"Delete {group_name}", callback_data=f"confirm_delete_group_{group_id}")]]
        logging.info(f"[get_group_main_keyboard] creator, group_id={group_id}, callback_data=confirm_delete_group_{group_id}")
    else:
        kb = [[InlineKeyboardButton(text=f"Leave {group_name}", callback_data=f"confirm_leave_group_{group_id}")]]
        logging.info(f"[get_group_main_keyboard] member, group_id={group_id}, callback_data=confirm_leave_group_{group_id}")
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_confirm_delete_keyboard(group_id):
    """Keyboard for group delete confirmation dialog."""
    kb = [[
        InlineKeyboardButton(text="Delete", callback_data=f"delete_group_yes_{group_id}"),
        InlineKeyboardButton(text="Cancel", callback_data=f"delete_group_cancel_{group_id}")
    ]]
    logging.info(f"[get_confirm_delete_keyboard] group_id={group_id}, yes=delete_group_yes_{group_id}, cancel=delete_group_cancel_{group_id}")
    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.callback_query(F.data.startswith("leave_group_yes_"))
async def cb_leave_group_yes(callback: types.CallbackQuery, state: FSMContext):
    """Handle confirmation of leaving a group: remove user from group_members, update current_group_id, clean up messages."""
    print("cb_leave_group_yes CALLED")
    logging.warning("cb_leave_group_yes CALLED")
    group_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        # Log before deletion
        before = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == group_id))
        logging.info(f"[leave_group_yes] BEFORE DELETE: user_id={user_id}, group_id={group_id}, member_exists={before.scalar() is not None}")
        await session.execute(
            GroupMember.__table__.delete().where(GroupMember.user_id == user.id, GroupMember.group_id == group_id)
        )
        await session.commit()
        # Log after deletion
        after = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == group_id))
        logging.info(f"[leave_group_yes] AFTER DELETE: user_id={user_id}, group_id={group_id}, member_exists={after.scalar() is not None}")
        if user.current_group_id == group_id:
            user.current_group_id = None
            await session.commit()
        groups = await session.execute(
            select(Group).join(GroupMember).where(GroupMember.user_id == user.id)
        )
        groups = groups.scalars().all()
        logging.info(f"[leave_group_yes] user_id={user_id}, remaining groups: {[g.id for g in groups]}")
        if not groups:
            user.current_group_id = None
            await session.commit()
    await clear_leave_and_my_groups(callback, state)
    if not groups:
        await callback.message.answer(
            "Welcome to Allkinds! Here you can join groups by code.",
            reply_markup=get_user_keyboard()
        )
    else:
        await my_groups(callback.message, state)
    await state.clear()
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_leave_group_"))
async def cb_confirm_leave_group(callback: types.CallbackQuery, state: FSMContext):
    """Show confirmation dialog for leaving a group. Clean up previous dialogs/messages."""
    print("cb_confirm_leave_group CALLED")
    logging.warning("cb_confirm_leave_group CALLED")
    await clear_leave_and_my_groups(callback, state)
    group_id = int(callback.data.split("_")[-1])
    async with AsyncSessionLocal() as session:
        group = await session.execute(select(Group).where(Group.id == group_id))
        group = group.scalar()
    text = f"Are you sure you want to leave <b>{group.name}</b>?\nAll your answers in this group will be deleted."
    kb = get_confirm_leave_keyboard(group_id)
    msg = await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    # Save message ids for later cleanup
    data = await state.get_data()
    leave_ids = data.get("leave_msgs", [])
    leave_ids.append(msg.message_id)
    await state.update_data(leave_msgs=leave_ids)
    await callback.answer()

@router.callback_query(F.data.startswith("leave_group_cancel_"))
async def cb_leave_group_cancel(callback: types.CallbackQuery, state: FSMContext):
    """Handle cancel action for leaving a group: clean up all related messages and state, including /mygroups."""
    await clear_leave_and_my_groups(callback, state)
    await state.clear()
    await callback.answer()

async def clear_leave_and_my_groups(callback, state):
    """Delete all leave/cancel/my_groups messages and reset their ids in FSM state."""
    data = await state.get_data()
    all_ids = set(data.get("leave_msgs", [])) | set(data.get("my_groups_msg_ids", []))
    for mid in all_ids:
        try:
            await callback.bot.delete_message(callback.message.chat.id, mid)
        except Exception:
            pass
    await state.update_data(leave_msgs=[], my_groups_msg_ids=[])

@router.callback_query(F.data.startswith("confirm_delete_group_"))
async def cb_confirm_delete_group(callback: types.CallbackQuery, state: FSMContext):
    """Show confirmation dialog for group deletion (for creator)."""
    print("cb_confirm_delete_group CALLED")
    logging.warning("cb_confirm_delete_group CALLED")
    await clear_leave_and_my_groups(callback, state)
    group_id = int(callback.data.split("_")[-1])
    async with AsyncSessionLocal() as session:
        group = await session.execute(select(Group).where(Group.id == group_id))
        group = group.scalar()
    text = f"Are you sure you want to delete <b>{group.name}</b>?\nAll questions and users will be deleted from this group. This action cannot be undone."
    kb = get_confirm_delete_keyboard(group_id)
    msg = await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    data = await state.get_data()
    leave_ids = data.get("leave_msgs", [])
    leave_ids.append(msg.message_id)
    await state.update_data(leave_msgs=leave_ids)
    await callback.answer()

@router.callback_query(F.data.startswith("delete_group_yes_"))
async def cb_delete_group_yes(callback: types.CallbackQuery, state: FSMContext):
    """Delete group and all related data (for creator). Notify all members and reset their state."""
    print("cb_delete_group_yes CALLED")
    logging.warning("cb_delete_group_yes CALLED")
    group_id = int(callback.data.split("_")[-1])
    async with AsyncSessionLocal() as session:
        # Получаем всех участников группы (кроме создателя)
        group = await session.execute(select(Group).where(Group.id == group_id))
        group = group.scalar()
        members = await session.execute(select(GroupMember).where(GroupMember.group_id == group_id))
        members = members.scalars().all()
        # Сбрасываем current_group_id у всех пользователей, у кого оно указывает на эту группу
        users_to_update = await session.execute(select(User).where(User.current_group_id == group_id))
        users_to_update = users_to_update.scalars().all()
        for user in users_to_update:
            user.current_group_id = None
        await session.commit()
        # Оповещаем участников (кроме создателя)
        for member in members:
            user = await session.execute(select(User).where(User.id == member.user_id))
            user = user.scalar()
            if user and user.id != group.creator_user_id:
                try:
                    await callback.bot.send_message(user.telegram_user_id, f"The group '{group.name}' was deleted by the admin. You have been removed from this group.")
                except Exception as e:
                    logging.warning(f"[delete_group_yes] Failed to notify user {user.telegram_user_id}: {e}")
        await session.commit()
        # Удаляем всех участников и саму группу (каскадно)
        await session.execute(GroupMember.__table__.delete().where(GroupMember.group_id == group_id))
        await session.execute(Group.__table__.delete().where(Group.id == group_id))
        await session.commit()
    await clear_leave_and_my_groups(callback, state)
    await callback.message.answer("Group deleted. All users have been removed and notified.")
    await state.clear()
    await callback.answer()

@router.callback_query(F.data.startswith("delete_group_cancel_"))
async def cb_delete_group_cancel(callback: types.CallbackQuery, state: FSMContext):
    """Cancel group deletion dialog (for creator)."""
    await clear_leave_and_my_groups(callback, state)
    await state.clear()
    await callback.answer()

# --- Question/Answer logic ---

ANSWER_VALUES = [(-2, "👎👎"), (-1, "👎"), (0, "⏭️"), (1, "👍"), (2, "👍👍")]
ANSWER_VALUE_TO_EMOJI = dict(ANSWER_VALUES)

async def moderate_question(text: str) -> (bool, str):
    banned = ["drugs", "violence", "hate", "sex"]
    for word in banned:
        if word in text.lower():
            return False, f"Question contains banned topic: {word}"
    # Если есть кириллица — отключаем модерацию (разрешаем всё)
    if re.search(r'[а-яА-ЯёЁ]', text):
        return True, ""
    # Для английского — старая эвристика
    t = text.strip().lower()
    t = re.sub(r'^[\s\.,!?-]+', '', t)
    yesno_patterns = [
        r"^(do|does|is|are|was|were|have|has|will|can|should|could|would|may|might|am|did|doesn't|isn't|aren't|won't|can't|didn't|haven't|hasn't)\b",
    ]
    if text.strip().endswith("?"):
        for pat in yesno_patterns:
            if re.match(pat, t, re.IGNORECASE):
                break
        else:
            return False, "Question must be a yes/no statement (e.g. 'Do you...?', 'Is it...?')."
    if len(text.strip()) < 5:
        return False, "Question is too short."
    return True, ""

async def is_duplicate_question(session, group_id, text):
    """Check if question already exists in group (case-insensitive, not deleted)."""
    q = await session.execute(
        select(Question).where(
            and_(Question.group_id == group_id, Question.is_deleted == 0, Question.text.ilike(text.strip()))
        )
    )
    return q.scalar() is not None

async def get_group_members(session, group_id):
    """Return all user_ids in group."""
    members = await session.execute(select(GroupMember).where(GroupMember.group_id == group_id))
    return [m.user_id for m in members.scalars().all()]

@dp.message()
async def log_and_handle(message: types.Message, state: FSMContext):
    if message.text:
        logging.info(f"[USER_MESSAGE] user_id={message.from_user.id}, text={message.text}")
    # Проксируем в handle_new_question, если это не команда и не FSM
    if not message.text.startswith("/") and not await state.get_state():
        await handle_new_question(message, state)

async def clear_mygroups_messages(message, state):
    data = await state.get_data()
    ids = data.get("my_groups_msg_ids", [])
    for mid in ids:
        try:
            await message.bot.delete_message(message.chat.id, mid)
        except Exception:
            pass
    await state.update_data(my_groups_msg_ids=[])

@dp.message()
async def handle_new_question(message: types.Message, state: FSMContext):
    await hide_instructions_and_mygroups_by_message(message, state)
    """Handle new question/statement from user (not a command or FSM step)."""
    # Очищаем меню /mygroups, если оно есть
    await clear_mygroups_messages(message, state)
    if message.text.startswith("/"):
        return  # Ignore commands
    user_id = message.from_user.id
    try:
        async with AsyncSessionLocal() as session:
            user = await session.execute(select(User).where(User.telegram_user_id == user_id))
            user = user.scalar()
            if not user or not user.current_group_id:
                await message.answer("You must join a group first.")
                return
            group_id = user.current_group_id
            checking_msg = await message.answer("Checking your question...")
            ok, reason = await moderate_question(message.text)
            if not ok:
                await checking_msg.edit_text(f"❌ {reason}")
                await asyncio.sleep(2)
                await checking_msg.delete()
                # Удаляем исходное сообщение пользователя, если не прошёл модерацию
                try:
                    await message.delete()
                except Exception as e:
                    logging.warning(f"[handle_new_question] Failed to delete user message after moderation fail: {e}")
                return
            if await is_duplicate_question(session, group_id, message.text):
                await checking_msg.edit_text("❌ This question already exists in this group.")
                await asyncio.sleep(2)
                await checking_msg.delete()
                return
            q = Question(group_id=group_id, author_id=user.id, text=message.text.strip())
            session.add(q)
            member = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == group_id))
            member = member.scalar()
            if member:
                member.balance += 5
            await session.commit()
            await session.refresh(q)
            group_obj = await session.execute(select(Group).where(Group.id == group_id))
            group_obj = group_obj.scalar()
            creator_user_id = group_obj.creator_user_id if group_obj else None
            member_ids = await get_group_members(session, group_id)
            for uid in member_ids:
                is_author = (uid == user.id)
                u = await session.execute(select(User).where(User.id == uid))
                u = u.scalar()
                is_creator = (u.id == creator_user_id)
                answer_buttons = [types.InlineKeyboardButton(text=emoji, callback_data=f"answer_{q.id}_{val}") for val, emoji in ANSWER_VALUES]
                keyboard = [answer_buttons]
                if is_author or is_creator:
                    keyboard.append([types.InlineKeyboardButton(text="Delete", callback_data=f"delete_question_{q.id}")])
                kb = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
                try:
                    sent = await bot.send_message(u.telegram_user_id, message.text.strip(), reply_markup=kb)
                except Exception as e:
                    logging.error(f"[handle_new_question] Failed to send question to user_id={u.telegram_user_id}: {e}")
            await checking_msg.delete()
            # Удаляем исходное сообщение пользователя (если не команда)
            try:
                await message.delete()
            except Exception as e:
                logging.warning(f"[handle_new_question] Failed to delete user message: {e}")
    except Exception as e:
        logging.exception(f"[handle_new_question] Unexpected error: {e}")
        try:
            await message.answer(f"❌ Internal error: {e}")
        except Exception:
            pass

async def get_next_unanswered_question(session, group_id, user_id):
    """Return the next unanswered question for user in group (skip считается ответом)."""
    q = await session.execute(
        select(Question).where(
            and_(Question.group_id == group_id, Question.is_deleted == 0)
        ).order_by(Question.created_at)
    )
    questions = q.scalars().all()
    for question in questions:
        ans = await session.execute(select(Answer).where(and_(Answer.question_id == question.id, Answer.user_id == user_id)))
        ans = ans.scalar()
        if not ans or ans.value is None:
            return question
    return None

@router.callback_query(F.data.startswith("answer_"))
async def cb_answer_question(callback: types.CallbackQuery, state: FSMContext):
    await hide_instructions_and_mygroups_by_message(callback.message, state)
    parts = callback.data.split("_")
    qid = int(parts[1])
    try:
        value = int(parts[2])
    except Exception:
        logging.error(f"[cb_answer_question] Invalid answer value (not int): {parts[2]}")
        await callback.answer("Internal error: invalid answer value.", show_alert=True)
        return
    user_id = callback.from_user.id
    logging.info(f"[cb_answer_question] user_id={user_id}, qid={qid}, value={value}")
    allowed_values = set(ANSWER_VALUE_TO_EMOJI.keys())
    if value not in allowed_values:
        logging.error(f"[cb_answer_question] Invalid answer value: {value}")
        await callback.answer("Internal error: invalid answer value.", show_alert=True)
        return
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        question = await session.execute(select(Question).where(Question.id == qid, Question.is_deleted == 0))
        question = question.scalar()
        if not question:
            await callback.answer("Question was deleted.", show_alert=True)
            await callback.message.delete()
            return
        group_obj = await session.execute(select(Group).where(Group.id == question.group_id))
        group_obj = group_obj.scalar()
        creator_user_id = group_obj.creator_user_id if group_obj else None
        logging.info(f"[cb_answer_question] creator_user_id={creator_user_id}")
        ans = await session.execute(select(Answer).where(and_(Answer.question_id == qid, Answer.user_id == user.id)))
        ans = ans.scalar()
        if ans and ans.value == value:
            await show_question_with_all_buttons(callback, question, user, creator_user_id)
            await callback.answer("You can change your answer.")
            return
        if not ans:
            ans = Answer(question_id=qid, user_id=user.id)
            session.add(ans)
            member = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == question.group_id))
            member = member.scalar()
            if member:
                member.balance += 1
        ans.value = value
        ans.is_skipped = int(value == 0)
        await session.commit()
        await show_question_with_selected_button(callback, question, user, value, creator_user_id)
        await callback.answer("Answer saved.")
        next_q = await get_next_unanswered_question(session, question.group_id, user.id)
        if next_q:
            await send_question_to_user(bot, user, next_q, creator_user_id)

async def show_question_with_selected_button(callback, question, user, value, creator_user_id=None):
    logging.info(f"[show_question_with_selected_button] user_id={user.id}, question_id={question.id}, value={value}, creator_user_id={creator_user_id}")
    if creator_user_id is None:
        async with AsyncSessionLocal() as session:
            group_obj = await session.execute(select(Group).where(Group.id == question.group_id))
            group_obj = group_obj.scalar()
            creator_user_id = group_obj.creator_user_id if group_obj else None
    is_author = (user.id == question.author_id)
    is_creator = (user.id == creator_user_id)
    if value not in ANSWER_VALUE_TO_EMOJI:
        logging.error(f"[show_question_with_selected_button] Unknown value: {value}")
        await callback.answer("Internal error: unknown answer value.", show_alert=True)
        return
    # Одна строка: [ответ, Delete] если доступно, иначе только ответ
    row = [types.InlineKeyboardButton(text=ANSWER_VALUE_TO_EMOJI[value], callback_data=f"answer_{question.id}_{value}")]
    if is_author or is_creator:
        row.append(types.InlineKeyboardButton(text="Delete", callback_data=f"delete_question_{question.id}"))
    kb = types.InlineKeyboardMarkup(inline_keyboard=[row])
    try:
        await callback.message.edit_reply_markup(reply_markup=kb)
    except Exception as e:
        logging.error(f"[show_question_with_selected_button] Failed to edit reply markup: {e}")
        pass

async def show_question_with_all_buttons(callback, question, user, creator_user_id=None):
    if creator_user_id is None:
        async with AsyncSessionLocal() as session:
            group_obj = await session.execute(select(Group).where(Group.id == question.group_id))
            group_obj = group_obj.scalar()
            creator_user_id = group_obj.creator_user_id if group_obj else None
    is_author = (user.id == question.author_id)
    is_creator = (user.id == creator_user_id)
    answer_buttons = [types.InlineKeyboardButton(text=ANSWER_VALUE_TO_EMOJI[val], callback_data=f"answer_{question.id}_{val}") for val, emoji in ANSWER_VALUES]
    keyboard = [answer_buttons]
    if is_author or is_creator:
        keyboard.append([types.InlineKeyboardButton(text="Delete", callback_data=f"delete_question_{question.id}")])
    kb = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    try:
        await callback.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        pass

async def send_question_to_user(bot, user, question, creator_user_id=None, group_id=None, all_groups_count=None, group_name=None):
    # Получаем creator_user_id, group_id, group_name, all_groups_count если не переданы
    if creator_user_id is None or group_id is None or group_name is None or all_groups_count is None:
        async with AsyncSessionLocal() as session:
            group_obj = await session.execute(select(Group).where(Group.id == question.group_id))
            group_obj = group_obj.scalar()
            creator_user_id = group_obj.creator_user_id if group_obj else None
            group_id = group_obj.id if group_obj else None
            group_name = group_obj.name if group_obj else None
            memberships = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id))
            memberships = memberships.scalars().all()
            all_groups_count = len(memberships)
    is_author = (user.id == question.author_id)
    is_creator = (user.id == creator_user_id)
    if all_groups_count > 1:
        text = f"<b>{group_name}</b>: {question.text}"
    else:
        text = question.text
    # Все кнопки в одну строку
    answer_buttons = [types.InlineKeyboardButton(text=ANSWER_VALUE_TO_EMOJI[val], callback_data=f"answer_{question.id}_{val}") for val, emoji in ANSWER_VALUES]
    keyboard = [answer_buttons]
    if is_author or is_creator:
        keyboard.append([types.InlineKeyboardButton(text="Delete", callback_data=f"delete_question_{question.id}")])
    kb = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    await bot.send_message(user.telegram_user_id, text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("delete_question_"))
async def cb_delete_question(callback: types.CallbackQuery, state: FSMContext):
    qid = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    logging.info(f"[cb_delete_question] user_id={user_id}, qid={qid}")
    async with AsyncSessionLocal() as session:
        question = await session.execute(select(Question).where(Question.id == qid, Question.is_deleted == 0))
        question = question.scalar()
        if not question:
            await callback.answer("Question already deleted.", show_alert=True)
            await callback.message.delete()
            return
        author = await session.execute(select(User).where(User.id == question.author_id))
        author = author.scalar()
        group_obj = await session.execute(select(Group).where(Group.id == question.group_id))
        group_obj = group_obj.scalar()
        creator = await session.execute(select(User).where(User.id == group_obj.creator_user_id)) if group_obj else None
        creator = creator.scalar() if creator else None
        allowed_telegram_ids = set()
        if author:
            allowed_telegram_ids.add(author.telegram_user_id)
        if creator:
            allowed_telegram_ids.add(creator.telegram_user_id)
        logging.info(f"[cb_delete_question] allowed_telegram_ids={allowed_telegram_ids}")
        if user_id not in allowed_telegram_ids:
            await callback.answer("Only the author or group creator can delete this question.", show_alert=True)
            return
        question.is_deleted = 1
        await session.execute(Answer.__table__.delete().where(Answer.question_id == qid))
        await session.commit()
        try:
            await callback.message.delete()
        except Exception as e:
            logging.error(f"[cb_delete_question] Failed to delete message: {e}")
        await callback.answer("Question deleted.")

# --- Load answered questions logic ---
ANSWERED_PAGE_SIZE = 10

@dp.callback_query(F.data == "load_answered_questions")
async def cb_load_answered_questions(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        group_id = user.current_group_id
        # Получаем group_name и all_groups_count заранее
        group_obj = await session.execute(select(Group).where(Group.id == group_id))
        group_obj = group_obj.scalar()
        group_name = group_obj.name if group_obj else None
        memberships = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id))
        memberships = memberships.scalars().all()
        all_groups_count = len(memberships)
        # Получаем первые N отвеченных вопросов
        answers = await session.execute(
            select(Answer).where(
                Answer.user_id == user.id,
                Answer.value.isnot(None),
                Answer.question_id.in_(select(Question.id).where(Question.group_id == group_id, Question.is_deleted == 0))
            ).order_by(Answer.created_at).limit(ANSWERED_PAGE_SIZE)
        )
        answers = answers.scalars().all()
        if not answers:
            await callback.answer("No answered questions yet.", show_alert=True)
            return
        for ans in answers:
            question = await session.execute(select(Question).where(Question.id == ans.question_id))
            question = question.scalar()
            await send_answered_question_to_user(callback.bot, user, question, ans.value, group_name=group_name, all_groups_count=all_groups_count)
        # Проверяем, есть ли ещё
        total_count = await session.execute(
            select(Answer).where(
                Answer.user_id == user.id,
                Answer.value.isnot(None),
                Answer.question_id.in_(select(Question.id).where(Question.group_id == group_id, Question.is_deleted == 0))
            )
        )
        total_count = len(total_count.scalars().all())
        if total_count > ANSWERED_PAGE_SIZE:
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Load more", callback_data="load_answered_questions_more_1")]])
            await callback.message.answer("More answered questions available:", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("load_answered_questions_more_"))
async def cb_load_answered_questions_more(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    page = int(callback.data.split("_")[-1])
    offset = (page + 1) * ANSWERED_PAGE_SIZE
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        group_id = user.current_group_id
        group_obj = await session.execute(select(Group).where(Group.id == group_id))
        group_obj = group_obj.scalar()
        group_name = group_obj.name if group_obj else None
        memberships = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id))
        memberships = memberships.scalars().all()
        all_groups_count = len(memberships)
        answers = await session.execute(
            select(Answer).where(
                Answer.user_id == user.id,
                Answer.value.isnot(None),
                Answer.question_id.in_(select(Question.id).where(Question.group_id == group_id, Question.is_deleted == 0))
            ).order_by(Answer.created_at).offset(offset).limit(ANSWERED_PAGE_SIZE)
        )
        answers = answers.scalars().all()
        if not answers:
            await callback.answer("No more answered questions.", show_alert=True)
            return
        for ans in answers:
            question = await session.execute(select(Question).where(Question.id == ans.question_id))
            question = question.scalar()
            await send_answered_question_to_user(callback.bot, user, question, ans.value, group_name=group_name, all_groups_count=all_groups_count)
        # Проверяем, есть ли ещё
        total_count = await session.execute(
            select(Answer).where(
                Answer.user_id == user.id,
                Answer.value.isnot(None),
                Answer.question_id.in_(select(Question.id).where(Question.group_id == group_id, Question.is_deleted == 0))
            )
        )
        total_count = len(total_count.scalars().all())
        if total_count > offset + ANSWERED_PAGE_SIZE:
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Load more", callback_data=f"load_answered_questions_more_{page+1}")]])
            await callback.message.answer("More answered questions available:", reply_markup=kb)
    await callback.answer()

async def send_answered_question_to_user(bot, user, question, value, group_name=None, all_groups_count=None):
    # Получаем group_name и all_groups_count если не переданы
    if group_name is None or all_groups_count is None:
        async with AsyncSessionLocal() as session:
            group_obj = await session.execute(select(Group).where(Group.id == question.group_id))
            group_obj = group_obj.scalar()
            group_name = group_obj.name if group_obj else None
            memberships = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id))
            memberships = memberships.scalars().all()
            all_groups_count = len(memberships)
    is_author = (user.id == question.author_id)
    async with AsyncSessionLocal() as session:
        group_obj = await session.execute(select(Group).where(Group.id == question.group_id))
        group_obj = group_obj.scalar()
        creator_user_id = group_obj.creator_user_id if group_obj else None
    is_creator = (user.id == creator_user_id)
    if all_groups_count > 1:
        text = f"<b>{group_name}</b>: {question.text}"
    else:
        text = question.text
    # Все кнопки в одну строку
    row = [types.InlineKeyboardButton(text=ANSWER_VALUE_TO_EMOJI[value], callback_data=f"answer_{question.id}_{value}")]
    if is_author or is_creator:
        row.append(types.InlineKeyboardButton(text="Delete", callback_data=f"delete_question_{question.id}"))
    kb = types.InlineKeyboardMarkup(inline_keyboard=[row])
    await bot.send_message(user.telegram_user_id, text, reply_markup=kb, parse_mode="HTML")

dp.include_router(router)

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot)) 