from aiogram import types, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from src.texts.instructions import INSTRUCTIONS_TEXT
from src.loader import bot, dp
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from src.services.questions import get_next_unanswered_question
from src.handlers.questions import send_question_to_user
from src.services.groups import get_user_groups, is_group_creator, is_onboarded, get_group_balance
from src.services.onboarding import is_onboarding_complete_service
from src.db import AsyncSessionLocal
from sqlalchemy import select
from src.models import User, GroupMember
from src.keyboards.groups import get_user_keyboard, get_admin_keyboard

router = Router()
print('System router loaded')

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

@router.message(Command("instructions"))
async def instructions(message: types.Message, state: FSMContext):
    print('/instructions handler triggered')
    await hide_instructions_and_mygroups_by_message(message, state)
    msg = await message.answer(INSTRUCTIONS_TEXT, parse_mode="HTML")
    await state.update_data(instructions_msg_id=msg.message_id)

@router.message(Command("mygroups"))
async def my_groups(message: types.Message, state: FSMContext):
    print('/mygroups handler triggered')
    await hide_instructions_and_mygroups_by_message(message, state)
    from src.handlers.groups import show_user_groups
    await show_user_groups(message, state)

@router.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    print('/start handler triggered')
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
            await message.answer(f"Welcome back to {group['name']}. Your balance is {balance}💎 points.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Load answered questions", callback_data="load_answered_questions")]]))
            async with AsyncSessionLocal() as session:
                user = await session.execute(select(User).where(User.telegram_user_id == user_id))
                user = user.scalar()
                if user is None:
                    print(f"[INFO] Creating new user in DB for telegram_user_id={user_id} in /start handler")
                    user = User(telegram_user_id=user_id)
                    session.add(user)
                    await session.commit()
                    await session.refresh(user)
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
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        if user is None:
            print(f"[INFO] Creating new user in DB for telegram_user_id={user_id} in /start handler (multi-group)")
            user = User(telegram_user_id=user_id)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        memberships = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id))
        memberships = memberships.scalars().all()
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
            await message.answer(f"Welcome back to {group['name']}. Your balance is {balance}💎 points.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Load answered questions", callback_data="load_answered_questions")]]))
            async with AsyncSessionLocal() as session:
                user = await session.execute(select(User).where(User.telegram_user_id == user_id))
                user = user.scalar()
                if user is None:
                    print(f"[INFO] Creating new user in DB for telegram_user_id={user_id} in /start handler (multi-group)")
                    user = User(telegram_user_id=user_id)
                    session.add(user)
                    await session.commit()
                    await session.refresh(user)
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
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        if user is None:
            print(f"[INFO] Creating new user in DB for telegram_user_id={user_id} in /start handler (multi-group)")
            user = User(telegram_user_id=user_id)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        group_id = user.current_group_id or (groups[0]["id"] if groups else None)
        if group_id:
            next_q = await get_next_unanswered_question(session, group_id, user.id)
            if next_q:
                await send_question_to_user(bot, user, next_q) 