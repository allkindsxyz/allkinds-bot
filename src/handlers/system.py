from aiogram import types, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from src.texts.messages import INSTRUCTIONS_TEXT, GROUPS_WELCOME_ADMIN, GROUPS_WELCOME, GROUPS_PROFILE_SETUP, GROUPS_FIND_MATCH, GROUPS_SELECT, get_message
from src.loader import bot, dp
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from src.services.questions import get_next_unanswered_question
from src.handlers.questions import send_question_to_user
from src.services.groups import get_user_groups, is_group_creator, is_onboarded, get_group_balance, join_group_by_code_service
from src.services.onboarding import is_onboarding_complete_service
from src.db import AsyncSessionLocal
from sqlalchemy import select
from src.models import User, GroupMember
from src.keyboards.groups import get_user_keyboard, get_admin_keyboard, get_group_reply_keyboard

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
    import logging
    try:
        print('/instructions handler triggered')
        await hide_instructions_and_mygroups_by_message(message, state)
        # Получаем user из БД для актуального языка
        async with AsyncSessionLocal() as session:
            user = await session.execute(select(User).where(User.telegram_user_id == message.from_user.id))
            user = user.scalar()
        msg = await message.answer(get_message(INSTRUCTIONS_TEXT, user or message.from_user), parse_mode="HTML")
        await state.update_data(instructions_msg_id=msg.message_id)
    except Exception as e:
        logging.exception("Ошибка в хендлере /instructions")
        raise

@router.message(Command("mygroups"))
async def my_groups(message: types.Message, state: FSMContext):
    import logging
    try:
        print('/mygroups handler triggered')
        await hide_instructions_and_mygroups_by_message(message, state)
        # Получаем user из БД для актуального языка
        async with AsyncSessionLocal() as session:
            user = await session.execute(select(User).where(User.telegram_user_id == message.from_user.id))
            user = user.scalar()
        from src.handlers.groups import show_user_groups
        # Передаём user только в get_message и генераторы клавиатур, не патчим message.from_user
        await show_user_groups(message, state)
    except Exception as e:
        logging.exception("Ошибка в хендлере /mygroups")
        raise

def normalize_lang(lang_code):
    if not lang_code:
        return 'en'
    return lang_code.split('-')[0]

@router.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    import logging
    try:
        print('/start handler triggered')
        await hide_instructions_and_mygroups_by_message(message, state)
        user_id = message.from_user.id
        # Получаем user из БД или создаём
        async with AsyncSessionLocal() as session:
            user = await session.execute(select(User).where(User.telegram_user_id == user_id))
            user = user.scalar()
            if user is None:
                user_lang = normalize_lang(getattr(message.from_user, 'language_code', None))
                user = User(telegram_user_id=user_id, language=user_lang)
                session.add(user)
                await session.commit()
                await session.refresh(user)
                print(f"[DEBUG] Created new user: {user}")
        # --- Обработка диплинка для всех пользователей ---
        args = message.text.split()
        if len(args) == 2 and len(args[1]) == 5:
            code = args[1].upper()
            print(f"[DEBUG] Trying join_group_by_code_service with code={code}")
            group = await join_group_by_code_service(user_id, code)
            async with AsyncSessionLocal() as session:
                user = await session.execute(select(User).where(User.telegram_user_id == user_id))
                user = user.scalar()
            if not group:
                await message.answer(get_message("❌ Group not found. Check the invite code.", user), reply_markup=types.ReplyKeyboardRemove())
                return
            if group.get("needs_onboarding"):
                await message.answer(get_message(f"Joining '{group['name']}'. Let's set up your profile!\nEnter your nickname:", user), reply_markup=types.ReplyKeyboardRemove())
                await state.update_data(group_id=group["id"])
                from src.fsm.states import Onboarding
                await state.set_state(Onboarding.nickname)
                return
            print(f"[DEBUG] User joined group via code: {group}")
            from src.handlers.groups import show_group_welcome_and_question
            await show_group_welcome_and_question(message, user_id, group["id"])
            return
        # --- Дальнейшая логика (как было) ---
        groups = await get_user_groups(user_id)
        is_creator = await is_group_creator(user_id)
        async with AsyncSessionLocal() as session:
            user = await session.execute(select(User).where(User.telegram_user_id == user_id))
            user = user.scalar()
            memberships = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id))
            memberships = memberships.scalars().all()
            if memberships and not user.current_group_id:
                user.current_group_id = memberships[0].group_id
                await session.commit()
        if not groups:
            if is_creator:
                await message.answer(get_message(GROUPS_WELCOME_ADMIN, user), reply_markup=get_admin_keyboard([], user))
            else:
                await message.answer(
                    get_message(GROUPS_WELCOME, user),
                    reply_markup=get_user_keyboard(user)
                )
            return
        if len(groups) == 1:
            group = groups[0]
            onboarded = await is_onboarded(user_id, group["id"])
            if not onboarded:
                await message.answer(get_message(GROUPS_PROFILE_SETUP.format(group_name=group["name"]), user), reply_markup=types.ReplyKeyboardRemove())
                await state.update_data(group_id=group["id"])
                from src.fsm.states import Onboarding
                await state.set_state(Onboarding.nickname)
                return
            print(f"[DEBUG] calling show_group_welcome_and_question from /start for group_id={group['id']}")
            from src.handlers.groups import show_group_welcome_and_question
            await show_group_welcome_and_question(message, user_id, group["id"])
            return
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Switch to {g['name']}", callback_data=f"switch_to_group_{g['id']}")] for g in groups
        ])
        await message.answer(get_message(GROUPS_SELECT, user), reply_markup=kb)
    except Exception as e:
        logging.exception("Ошибка в хендлере /start")
        raise

@router.message(Command("language"))
async def language_command(message: types.Message, state: FSMContext):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="English", callback_data="set_lang_en")],
            [InlineKeyboardButton(text="Русский", callback_data="set_lang_ru")],
        ]
    )
    await message.answer("Choose your language / Выберите язык:", reply_markup=kb)

@router.callback_query(F.data.startswith("set_lang_"))
async def set_language(callback: types.CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[-1]
    if lang not in ("en", "ru"):
        lang = "en"
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == callback.from_user.id))
        user = user.scalar()
        if user:
            user.language = lang
            await session.commit()
    # Повторно получаем user с обновлённым языком
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == callback.from_user.id))
        user = user.scalar()
    # Подтверждение на выбранном языке
    await callback.message.answer(get_message("INSTRUCTIONS_TEXT", user), parse_mode="HTML")
    from src.handlers.groups import show_user_groups
    await show_user_groups(callback.message, state)
    await callback.answer() 