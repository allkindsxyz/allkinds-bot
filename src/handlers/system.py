from aiogram import types, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram import F
from src.texts.messages import INSTRUCTIONS_TEXT, GROUPS_WELCOME_ADMIN, GROUPS_WELCOME, GROUPS_PROFILE_SETUP, GROUPS_FIND_MATCH, GROUPS_SELECT, get_message, TOKEN_EXTEND, TOKEN_EXTENDED, BTN_SWITCH_TO, BTN_CREATE_GROUP, BTN_GOT_IT
from src.loader import bot, dp, redis, VERSION
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from src.services.questions import get_next_unanswered_question
from src.handlers.questions import send_question_to_user
from src.services.groups import get_user_groups, is_group_creator, is_onboarded, get_group_balance, join_group_by_code_service, ensure_admin_in_db
from src.services.onboarding import is_onboarding_complete_service
from src.db import AsyncSessionLocal
from sqlalchemy import select, and_
from src.models import User, GroupMember, GroupCreator, Question
from src.keyboards.groups import get_user_keyboard, get_admin_keyboard, get_group_reply_keyboard
from src.utils.redis import get_internal_user_id, set_telegram_mapping, update_ttl, get_or_restore_internal_user_id
from src.constants import WELCOME_BONUS
import os
from src.utils.badges import send_initial_badge_if_needed

router = Router()
print('System router loaded')

async def send_pending_connection_requests(bot, user_id: int):
    """Отправить все пендинг запросы на подключение пользователю при рестарте"""
    from src.models import MatchStatus, GroupMember
    from src.utils.redis import get_telegram_user_id
    from src.services.groups import find_best_match
    
    requests_sent = False
    
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
        if not user or not user.current_group_id:
            return requests_sent
        
        # Найти все входящие пендинг запросы для этого пользователя
        pending_requests = await session.execute(select(MatchStatus).where(
            MatchStatus.match_user_id == user_id,
            MatchStatus.group_id == user.current_group_id,
            MatchStatus.status == "pending"
        ))
        pending_requests = pending_requests.scalars().all()
        
        if not pending_requests:
            return requests_sent
        
        member = await session.execute(select(GroupMember).where(
            GroupMember.user_id == user_id, 
            GroupMember.group_id == user.current_group_id))
        member = member.scalar()
        
        for request in pending_requests:
            initiator_user = await session.execute(select(User).where(User.id == request.user_id))
            initiator_user = initiator_user.scalar()
            initiator_member = await session.execute(select(GroupMember).where(
                GroupMember.user_id == request.user_id, 
                GroupMember.group_id == user.current_group_id))
            initiator_member = initiator_member.scalar()
            
            if not initiator_user or not initiator_member:
                continue
            
            # Получить данные мэтча для отображения
            reverse_match = await find_best_match(user_id, user.current_group_id, exclude_user_ids=[])
            if reverse_match and reverse_match.get('user_id') == initiator_user.id:
                similarity = reverse_match['similarity']
                common_questions = reverse_match['common_questions']
                distance_info = reverse_match['distance_info']
            else:
                # Fallback значения
                similarity = 85
                common_questions = 3
                # Calculate distance manually
                from src.utils.distance import get_match_distance_info
                distance_info = get_match_distance_info(member, initiator_member) if member else "📍 Location not specified"
            
            try:
                # Отправить уведомление о запросе
                request_text = get_message("MATCH_INCOMING_REQUEST", user=user, 
                                         nickname=initiator_member.nickname if initiator_member else "Unknown")
                
                # Карточка мэтча
                intro_text = initiator_member.intro if initiator_member and initiator_member.intro else ""
                match_text = get_message("MATCH_FOUND", user=user, 
                                       nickname=initiator_member.nickname if initiator_member else "Unknown", 
                                       intro=intro_text, similarity=similarity, 
                                       common_questions=common_questions, 
                                       distance_info=distance_info if 'distance_info' in locals() else "📍 Location not specified")
                
                # Кнопки для ответа
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text=get_message("BTN_ACCEPT_MATCH", user=user), 
                                           callback_data=f"accept_match_{initiator_user.id}"),
                        InlineKeyboardButton(text=get_message("BTN_DECLINE_MATCH", user=user), 
                                           callback_data=f"decline_match_{initiator_user.id}")
                    ],
                    [
                        InlineKeyboardButton(text=get_message("BTN_BLOCK_MATCH", user=user), 
                                           callback_data=f"block_match_{initiator_user.id}")
                    ]
                ])
                
                # Получить Telegram ID пользователя
                user_telegram_id = await get_telegram_user_id(user_id)
                if not user_telegram_id:
                    continue
                
                # Отправить уведомление
                await bot.send_message(user_telegram_id, request_text, parse_mode="HTML")
                
                # Отправить карточку мэтча с фото и кнопками
                if initiator_member and initiator_member.photo_url:
                    await bot.send_photo(user_telegram_id, initiator_member.photo_url, 
                                       caption=match_text, reply_markup=kb, parse_mode="HTML")
                else:
                    await bot.send_message(user_telegram_id, match_text, 
                                         reply_markup=kb, parse_mode="HTML")
                
                requests_sent = True
                    
            except Exception as e:
                import logging
                logging.error(f"[send_pending_connection_requests] Failed to send request from user_id={initiator_user.id} to user_id={user_id}: {e}")
    
    return requests_sent

async def hide_instructions_and_mygroups_by_message(message, state):
    """Hide previous instructions and mygroups messages by message reference"""
    data = await state.get_data()
    msg_id = data.get("instructions_msg_id")
    if msg_id:
        try:
            await message.bot.delete_message(message.chat.id, msg_id)
        except Exception:
            pass
    group_msg_ids = data.get('my_groups_msg_ids', [])
    for msg_id in group_msg_ids:
        try:
            await message.bot.delete_message(message.chat.id, msg_id)
        except Exception:
            pass
    await state.update_data(instructions_msg_id=None, my_groups_msg_ids=[])

async def show_instructions_with_button(bot, user, chat_id: int) -> int:
    """Show instructions with 'Got it' button. Returns message_id."""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_message(BTN_GOT_IT, user=user), callback_data="got_it_instructions")]
    ])
    msg = await bot.send_message(
        chat_id, 
        get_message(INSTRUCTIONS_TEXT, user=user), 
        parse_mode="HTML", 
        reply_markup=kb
    )
    return msg.message_id

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
        
        # Use new function with button
        msg_id = await show_instructions_with_button(message.bot, user or message.from_user, message.chat.id)
        await state.update_data(instructions_msg_id=msg_id)
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
            from src.services.groups import handle_group_join
            success = await handle_group_join(internal_user_id, code, message, state)
            if success:
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
        from src.handlers.questions import send_question_to_user
        async with AsyncSessionLocal() as session:
            user_obj = await session.execute(select(User).where(User.id == internal_user_id))
            user_obj = user_obj.scalar()
            # Check if user has current group AND is actually a member of that group
            if user_obj and user_obj.current_group_id:
                # Verify user is actually a member of the current group
                member_check = await session.execute(select(GroupMember).where(
                    GroupMember.user_id == user_obj.id,
                    GroupMember.group_id == user_obj.current_group_id
                ))
                if not member_check.scalar():
                    # User has current_group_id but is not a member - reset it
                    user_obj.current_group_id = None
                    await session.commit()
                else:
                    questions = await session.execute(
                        select(Question).where(
                            Question.group_id == user_obj.current_group_id,
                            Question.is_deleted == 0,
                            Question.status == "approved"
                        ).order_by(Question.created_at)
                    )
                    questions = questions.scalars().all()
                    for q in questions:
                        ans = await session.execute(select(Answer).where(and_(Answer.question_id == q.id, Answer.user_id == user_obj.id)))
                        ans = ans.scalar()
                        if not ans:
                            await send_question_to_user(message.bot, user_obj, q)
                            break
        
        # Send initial badge if user has pending questions/matches
        await send_initial_badge_if_needed(message.bot, internal_user_id, user_obj.current_group_id if user_obj else None)
        
        # Send pending connection requests if any
        await send_pending_connection_requests(message.bot, internal_user_id)
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

async def migrate_old_questions_to_approved():
    """
    Temporary function to migrate all pending questions to approved status.
    This is for backward compatibility with questions created before moderation system.
    """
    import logging
    from sqlalchemy import update
    
    async with AsyncSessionLocal() as session:
        # Update all pending questions to approved
        result = await session.execute(
            update(Question).where(Question.status == "pending").values(status="approved")
        )
        await session.commit()
        
        count = result.rowcount
        logging.warning(f"[migrate_old_questions] Updated {count} questions from pending to approved")
        return count 

@router.message(Command("migrate_questions"))
async def cmd_migrate_questions(message: types.Message):
    """Admin command to migrate old pending questions to approved status"""
    # Only allow specific admin user (replace with your admin Telegram ID)
    admin_telegram_ids = [338080957, 485985509]  # Add your admin Telegram IDs here
    
    if message.from_user.id not in admin_telegram_ids:
        await message.answer("❌ Access denied. Admin only command.")
        return
    
    try:
        count = await migrate_old_questions_to_approved()
        await message.answer(f"✅ Migration completed! Updated {count} questions from pending to approved status.")
    except Exception as e:
        import logging
        logging.exception("Error in migrate_questions command")
        await message.answer(f"❌ Error during migration: {str(e)}") 

@router.callback_query(F.data == "got_it_instructions")
async def cb_got_it_instructions(callback: types.CallbackQuery):
    """Handle 'Got it' button for instructions"""
    try:
        await callback.message.delete()
        await callback.answer()
    except Exception as e:
        import logging
        logging.exception(f"Error in cb_got_it_instructions: {e}") 