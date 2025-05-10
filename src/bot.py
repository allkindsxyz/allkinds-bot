import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from src.config import BOT_TOKEN, ADMIN_USER_ID
from src.db import AsyncSessionLocal
from src.models import User, Group, GroupMember, GroupCreator
from src.utils import generate_unique_invite_code
from sqlalchemy import select, insert
import os
import logging

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
    await state.set_state("awaiting_invite_code")
    await callback.answer()

@dp.message(lambda m, state=None: state and state.state == "awaiting_invite_code")
async def process_invite_code(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    if len(code) != 5:
        await message.answer("Code must be 5 characters. Try again:")
        return
    user_id = message.from_user.id
    group = await join_group_by_code(user_id, code)
    if not group:
        await message.answer("❌ Group not found. Check the invite code.")
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

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot)) 