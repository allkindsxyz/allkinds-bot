import asyncio
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, BotCommand
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from src.config import BOT_TOKEN, ADMIN_USER_ID
from src.db import AsyncSessionLocal
from src.models import User, Group, GroupMember, GroupCreator
from src.utils import generate_unique_invite_code
from sqlalchemy import select, insert
import os
import logging

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
create_group_btn = InlineKeyboardButton(text="Create a group", callback_data="create_group")
join_group_btn = InlineKeyboardButton(text="Join group with code", callback_data="join_group")

def get_admin_keyboard(groups):
    kb = [[create_group_btn, join_group_btn]]
    for g in groups:
        kb.append([InlineKeyboardButton(text=f"Go to {g['name']}", callback_data=f"go_group_{g['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_user_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[join_group_btn]])

def go_to_group_keyboard(group_id, group_name):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"Go to {group_name}", callback_data=f"go_group_{group_id}")]])

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
        # Можно добавить другие команды
    ]
    await bot.set_my_commands(commands)

@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
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
            await message.answer(f"Welcome back to {group['name']}. Your balance is {balance} points.")
            return
        await message.answer(f"Joining '{group['name']}'. Let's set up your profile!\nEnter your nickname:", reply_markup=ReplyKeyboardRemove())
        await state.update_data(group_id=group["id"])
        await state.set_state(Onboarding.nickname)
        return
    groups = await get_user_groups(user_id)
    is_creator = await is_group_creator(user_id)
    logging.info(f"[start] user_id={user_id}, is_creator={is_creator}, groups={groups}")
    # Логируем подробную информацию о членстве
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
            await message.answer(f"Welcome back to {group['name']}. Your balance is {balance} points.")
            return
        await message.answer(f"You have one group. Redirecting to onboarding for '{group['name']}'...", reply_markup=ReplyKeyboardRemove())
        await state.update_data(group_id=group["id"])
        await state.set_state(Onboarding.nickname)
        await message.answer("Enter your nickname:")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Go to {g['name']}", callback_data=f"go_group_{g['id']}")] for g in groups
    ])
    await message.answer("Select a group:", reply_markup=kb)

@dp.callback_query(F.data == "create_group")
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

@dp.callback_query(F.data.startswith("go_group_"))
async def cb_go_group(callback: types.CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split("_")[-1])
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
            await session.commit()
    await message.answer("🎉 Profile setup complete!", reply_markup=ReplyKeyboardRemove())
    await state.clear()

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
            await session.commit()
    await message.answer("🎉 Profile setup complete!", reply_markup=ReplyKeyboardRemove())
    await state.clear()

@dp.callback_query(F.data == "join_group")
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
        await message.answer(f"Welcome back to {group['name']}. Your balance is {balance} points.")
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
        kb = [[InlineKeyboardButton(text=f"Delete {group_name}", callback_data=f"confirm_delete_group_{group_id}")], [join_group_btn]]
        logging.info(f"[get_group_main_keyboard] creator, group_id={group_id}, callback_data=confirm_delete_group_{group_id}")
    else:
        kb = [[InlineKeyboardButton(text=f"Leave {group_name}", callback_data=f"confirm_leave_group_{group_id}")], [join_group_btn]]
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

@router.message(Command("mygroups"))
async def my_groups(message: types.Message, state: FSMContext):
    """Show user's groups and main group menu."""
    user_id = message.from_user.id
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
            # Если админ — показываем кнопку создания группы
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
        # Проверяем, является ли пользователь создателем этой группы
        is_creator = (current_group.creator_user_id == user.id)
        kb = get_group_main_keyboard(user.id, current_group.id, current_group.name, is_creator)
        # Добавляем кнопку создания группы для админа
        if await is_group_creator(user_id):
            kb.inline_keyboard.append([create_group_btn])
        sent = await message.answer(text, reply_markup=kb, parse_mode="HTML")
        data = await state.get_data()
        ids = data.get("my_groups_msg_ids", [])
        ids.append(sent.message_id)
        await state.update_data(my_groups_msg_ids=ids)

@router.callback_query(F.data.startswith("goto_group_"))
async def cb_goto_group(callback: types.CallbackQuery):
    group_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        user.current_group_id = group_id
        await session.commit()
    await callback.message.delete()
    await my_groups(callback.message, state=None)
    await callback.answer()

def get_leave_group_keyboard(group_id, group_name):
    """Keyboard for main group screen: leave and join buttons."""
    kb = [
        [InlineKeyboardButton(text=f"Leave {group_name}", callback_data=f"confirm_leave_group_{group_id}")],
        [join_group_btn]
    ]
    logging.info(f"[get_leave_group_keyboard] group_id={group_id}, callback_data=confirm_leave_group_{group_id}")
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_confirm_leave_keyboard(group_id):
    """Keyboard for confirmation dialog: leave/cancel buttons."""
    kb = [[
        InlineKeyboardButton(text="Leave", callback_data=f"leave_group_yes_{group_id}"),
        InlineKeyboardButton(text="Cancel", callback_data=f"leave_group_cancel_{group_id}")
    ]]
    logging.info(f"[get_confirm_leave_keyboard] group_id={group_id}, yes=leave_group_yes_{group_id}, cancel=leave_group_cancel_{group_id}")
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

dp.include_router(router)

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot)) 