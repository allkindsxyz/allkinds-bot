from aiogram import types, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from src.texts.messages import INSTRUCTIONS_TEXT, GROUPS_WELCOME_ADMIN, GROUPS_WELCOME, GROUPS_PROFILE_SETUP, GROUPS_FIND_MATCH, GROUPS_SELECT, get_message, TOKEN_EXTEND, TOKEN_EXTENDED, BTN_SWITCH_TO, BTN_CREATE_GROUP
from src.loader import bot, dp, redis, VERSION
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from src.services.questions import get_next_unanswered_question
from src.handlers.questions import send_question_to_user
from src.services.groups import get_user_groups, is_group_creator, is_onboarded, get_group_balance, join_group_by_code_service, ensure_admin_in_db
from src.services.onboarding import is_onboarding_complete_service
from src.db import AsyncSessionLocal
from sqlalchemy import select, and_
from src.models import User, GroupMember, GroupCreator
from src.keyboards.groups import get_user_keyboard, get_admin_keyboard, get_group_reply_keyboard
from src.utils.redis import get_internal_user_id, set_telegram_mapping, update_ttl, get_or_restore_internal_user_id
import os

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
        data = await state.get_data()
        user_id = data.get('internal_user_id')
        if not user_id:
            await message.answer(get_message("Please start the bot to use this feature.", user=message.from_user))
            return
        async with AsyncSessionLocal() as session:
            user = await session.execute(select(User).where(User.id == user_id))
            user = user.scalar()
        msg = await message.answer(get_message(INSTRUCTIONS_TEXT, user or message.from_user), parse_mode="HTML")
        await state.update_data(instructions_msg_id=msg.message_id)
        # --- Version check ---
        user_data = await state.get_data()
        user_version = user_data.get('bot_version')
        current_version = await redis.get('bot_version')
        if user_version and current_version and user_version != current_version:
            await message.answer("A new version of the bot has been released. Please click /start to update.")
            await state.clear()
            await state.update_data(bot_version=current_version)
            return
    except Exception as e:
        logging.exception(f"Error in /instructions handler: {e}")

@router.message(Command("mygroups"))
async def my_groups(message: types.Message, state: FSMContext):
    import logging
    try:
        print('/mygroups handler triggered')
        await hide_instructions_and_mygroups_by_message(message, state)
        # Get user from DB for current language
        data = await state.get_data()
        user_id = data.get('internal_user_id')
        async with AsyncSessionLocal() as session:
            user = await session.execute(select(User).where(User.id == user_id))
            user = user.scalar()
            is_admin = False
            if user:
                admin = await session.execute(select(GroupCreator).where(GroupCreator.user_id == user.id))
                is_admin = bool(admin.scalar())
        from src.handlers.groups import show_user_groups
        await show_user_groups(message, state, is_admin=is_admin)
    except Exception as e:
        logging.exception(f"Error in /mygroups handler: {e}")

def normalize_lang(lang_code):
    if not lang_code:
        return 'en'
    return lang_code.split('-')[0]

@router.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    import logging
    from src.db import AsyncSessionLocal
    from src.models import User, GroupCreator
    try:
        print('/start handler triggered')
        from src.services.groups import ensure_admin_in_db, join_group_by_code_service
        await ensure_admin_in_db()  # Ensure super-admin exists in GroupCreator
        await hide_instructions_and_mygroups_by_message(message, state)
        telegram_user_id = message.from_user.id
        # --- Get internal_user_id centrally ---
        internal_user_id = await get_or_restore_internal_user_id(state, telegram_user_id)
        await state.update_data(internal_user_id=internal_user_id)
        # --- Version check ---
        user_data = await state.get_data()
        user_version = user_data.get('bot_version')
        current_version = await redis.get('bot_version')
        if user_version and current_version and user_version != current_version:
            await message.answer("A new version of the bot has been released. Please click /start to update.")
            await state.clear()
            await state.update_data(bot_version=current_version)
            return
        # After successful start, update version in state
        await state.update_data(bot_version=current_version)
        # --- Fixed deeplink argument parsing ---
        args = None
        if message.text:
            parts = message.text.strip().split(maxsplit=1)
            if len(parts) == 2:
                args = parts[1]
        if args and len(args) == 5:
            code = args
            group = await join_group_by_code_service(internal_user_id, code)
            if not group:
                await message.answer(get_message("GROUPS_JOIN_NOT_FOUND", user=message.from_user))
                return
            if group.get("needs_onboarding"):
                await message.answer(get_message("GROUPS_JOIN_ONBOARDING", user=message.from_user, group_name=group["name"]), reply_markup=types.ReplyKeyboardRemove())
                await state.update_data(group_id=group["id"])
                from src.fsm.states import Onboarding
                await state.set_state(Onboarding.nickname)
                return
            from src.keyboards.groups import go_to_group_keyboard
            await message.answer(get_message("GROUPS_JOINED", user=message.from_user, group_name=group["name"], bonus=WELCOME_BONUS), reply_markup=go_to_group_keyboard(group["id"], group["name"], message.from_user))
            await state.clear()
            await state.update_data(internal_user_id=internal_user_id)
            return
        async with AsyncSessionLocal() as session:
            user = await session.execute(select(User).where(User.id == internal_user_id))
            user = user.scalar()
            is_admin = False
            if user:
                admin = await session.execute(select(GroupCreator).where(GroupCreator.user_id == user.id))
                is_admin = bool(admin.scalar())
        groups = await get_user_groups(internal_user_id)
        if not groups:
            from src.keyboards.groups import get_admin_keyboard, get_user_keyboard
            if is_admin:
                kb = get_admin_keyboard([], user)
            else:
                kb = get_user_keyboard(user)
            await message.answer(get_message(GROUPS_WELCOME_ADMIN if is_admin else GROUPS_WELCOME, user), reply_markup=kb)
            return
        # If there's at least one group — always show welcome and list of Switch to ... buttons
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_message(BTN_SWITCH_TO, user=user, group_name=g['name']), callback_data=f"switch_to_group_{g['id']}")] for g in groups
        ])
        if is_admin:
            kb.inline_keyboard.append([
                InlineKeyboardButton(text=get_message(BTN_CREATE_GROUP, user=user), callback_data="create_new_group")
            ])
        await message.answer(get_message(GROUPS_SELECT, user), reply_markup=kb)
        # --- PUSH первого неотвеченного вопроса, если есть ---
        from src.db import AsyncSessionLocal
        from src.models import Question, Answer
        from sqlalchemy import select, and_
        from src.handlers.questions import send_question_to_user
        async with AsyncSessionLocal() as session:
            user_obj = await session.execute(select(User).where(User.id == internal_user_id))
            user_obj = user_obj.scalar()
            if user_obj and user_obj.current_group_id:
                questions = await session.execute(
                    select(Question).where(
                        Question.group_id == user_obj.current_group_id,
                        Question.is_deleted == 0
                    ).order_by(Question.created_at)
                )
                questions = questions.scalars().all()
                for q in questions:
                    ans = await session.execute(select(Answer).where(and_(Answer.question_id == q.id, Answer.user_id == user_obj.id)))
                    ans = ans.scalar()
                    if not ans:
                        await send_question_to_user(message.bot, user_obj, q)
                        break
        return
    except Exception as e:
        logging.exception("Error in /start handler")
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
        user = await session.execute(select(User).where(User.id == callback.from_user.id))
        user = user.scalar()
        if user:
            user.language = lang
            await session.commit()
    # Re-get user with updated language
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == callback.from_user.id))
        user = user.scalar()
    # Confirmation in selected language
    await callback.message.answer(get_message("INSTRUCTIONS_TEXT", user), parse_mode="HTML")
    from src.handlers.groups import show_user_groups
    await show_user_groups(callback.message, state)
    await callback.answer()

@router.message(Command("addadmin"))
async def add_admin_command(message: types.Message, state: FSMContext):
    args = message.text.strip().split()
    if len(args) != 2 or not args[1].isdigit():
        await message.answer("Usage: /addadmin <user_id>")
        return
    target_user_id = int(args[1])
    data = await state.get_data()
    user_id = data.get('internal_user_id')
    if not user_id:
        await message.answer(get_message("Please start the bot to use this feature.", user=message.from_user))
        return
    async with AsyncSessionLocal() as session:
        admin = await session.execute(select(GroupCreator).where(GroupCreator.user_id == user_id))
        if not admin.scalar():
            await message.answer("You are not an admin.")
            return
        user = await session.execute(select(User).where(User.id == target_user_id))
        user = user.scalar()
        if not user:
            await message.answer(f"User with id {target_user_id} does not exist.")
            return
        exists = await session.execute(select(GroupCreator).where(GroupCreator.user_id == target_user_id))
        if exists.scalar():
            await message.answer(f"User {target_user_id} is already an admin.")
            return
        session.add(GroupCreator(user_id=target_user_id))
        await session.commit()
        await message.answer(f"User {target_user_id} is now an admin.")

@router.message(Command("removeadmin"))
async def remove_admin_command(message: types.Message, state: FSMContext):
    args = message.text.strip().split()
    if len(args) != 2 or not args[1].isdigit():
        await message.answer("Usage: /removeadmin <user_id>")
        return
    target_user_id = int(args[1])
    data = await state.get_data()
    user_id = data.get('internal_user_id')
    if not user_id:
        await message.answer(get_message("Please start the bot to use this feature.", user=message.from_user))
        return
    async with AsyncSessionLocal() as session:
        admin = await session.execute(select(GroupCreator).where(GroupCreator.user_id == user_id))
        if not admin.scalar():
            await message.answer("You are not an admin.")
            return
        user = await session.execute(select(User).where(User.id == target_user_id))
        user = user.scalar()
        if not user:
            await message.answer(f"User with id {target_user_id} does not exist.")
            return
        exists = await session.execute(select(GroupCreator).where(GroupCreator.user_id == target_user_id))
        exists = exists.scalar()
        if not exists:
            await message.answer(f"User {target_user_id} is not an admin.")
            return
        await session.delete(exists)
        await session.commit()
        await message.answer(f"User {target_user_id} is no longer an admin.")

@router.callback_query(F.data == "extend_token")
async def extend_token_callback(callback: types.CallbackQuery, state: FSMContext):
    from src.utils.redis import update_ttl
    telegram_user_id = callback.from_user.id
    await update_ttl(telegram_user_id)
    # Get user for localization
    async with AsyncSessionLocal() as session:
        data = await state.get_data()
        user_id = data.get('internal_user_id')
        user = None
        if user_id:
            user = await session.execute(select(User).where(User.id == user_id))
            user = user.scalar()
    await callback.message.answer(get_message(TOKEN_EXTENDED, user or callback.from_user))
    await callback.answer()

@router.message(Command("myid"))
async def myid_command(message: types.Message, state: FSMContext):
    from src.utils.redis import get_or_restore_internal_user_id
    user_id = await get_or_restore_internal_user_id(state, message.from_user.id)
    if not user_id:
        await message.answer("User not found. Please use /start first.")
        return
    await message.answer(f"Your user.id: {user_id}")

@router.message(Command("addcreator"))
async def add_creator_command(message: types.Message, state: FSMContext):
    args = message.text.strip().split()
    if len(args) != 2 or not args[1].isdigit():
        await message.answer("Usage: /addcreator <telegram_id>")
        return
    admin_telegram_id = os.getenv("ADMIN_USER_ID")
    if not admin_telegram_id or str(message.from_user.id) != str(admin_telegram_id):
        await message.answer("You are not authorized to use this command.")
        return
    telegram_id = int(args[1])
    from src.utils.redis import get_or_restore_internal_user_id
    internal_user_id = await get_or_restore_internal_user_id(state, telegram_id)
    from src.models import GroupCreator, User
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == internal_user_id))
        user = user.scalar()
        if not user:
            await message.answer(f"Internal error: user not found after mapping (id: {internal_user_id})")
            return
        exists = await session.execute(select(GroupCreator).where(GroupCreator.user_id == user.id))
        if exists.scalar():
            await message.answer(f"User {telegram_id} (internal id: {user.id}) is already a group creator.")
            return
        session.add(GroupCreator(user_id=user.id))
        await session.commit()
        await message.answer(f"User {telegram_id} added to group_creators (internal id: {user.id}).") 