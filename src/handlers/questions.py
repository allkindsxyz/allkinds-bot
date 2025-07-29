# Handlers for questions and answers
# Imports and service calls will be added after extracting business logic 

from aiogram import types, F, Router
from aiogram.fsm.context import FSMContext
from src.loader import bot
from src.keyboards.questions import get_answer_keyboard, get_delete_keyboard, get_load_more_keyboard, ANSWER_VALUE_TO_EMOJI, ANSWER_VALUES
from src.services.questions import (
    get_next_unanswered_question,
    is_duplicate_question,
    moderate_question,
    get_group_members,
    ensure_user_exists,
)
from src.constants import POINTS_FOR_NEW_QUESTION, POINTS_FOR_ANSWER
from src.db import AsyncSessionLocal
from sqlalchemy import select, and_, delete
from src.models import User, GroupMember, Question, Answer, Group, BannedUser, MatchStatus, Match
from src.texts.messages import (
    get_message,
    QUESTION_TOO_SHORT, QUESTION_MUST_JOIN_GROUP, QUESTION_DUPLICATE, QUESTION_REJECTED, QUESTION_ADDED, QUESTION_DELETED,
    QUESTION_ALREADY_DELETED, QUESTION_ONLY_AUTHOR_OR_CREATOR, QUESTION_ANSWER_SAVED, QUESTION_NO_ANSWERED, QUESTION_MORE_ANSWERED,
    QUESTION_NO_MORE_ANSWERED, QUESTION_CAN_CHANGE_ANSWER, QUESTION_INTERNAL_ERROR, QUESTION_LOAD_ANSWERED, QUESTION_LOAD_MORE,
    QUESTION_DELETE, UNANSWERED_QUESTIONS_MSG, BTN_LOAD_UNANSWERED, GROUPS_NO_NEW_QUESTIONS, NEW_QUESTION_NOTIFICATION,
    QUESTION_PENDING_APPROVAL, QUESTION_ADMIN_APPROVAL, QUESTION_APPROVED_ADMIN, QUESTION_REJECTED_ADMIN, 
    QUESTION_APPROVED_AUTHOR, QUESTION_REJECTED_AUTHOR, USER_BANNED_ADMIN, USER_BANNED_NOTIFICATION
)
import logging
from src.utils.redis import get_telegram_user_id, get_or_restore_internal_user_id, set_telegram_mapping

router = Router()

# --- Handlers for questions/answers ---

@router.message(F.text & ~F.text.startswith('/'))
async def handle_new_question(message: types.Message, state: FSMContext):
    """Create new question: save question, award points to author."""
    import asyncio
    text = message.text.strip()
    data = await state.get_data()
    user_id = data.get('internal_user_id')
    if not user_id:
        await message.answer(get_message("Please start the bot to use this feature.", user=message.from_user))
        return
    async with AsyncSessionLocal() as session:
        await ensure_user_exists(session, user_id)
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
    if len(text) < 5:
        await message.answer(get_message(QUESTION_TOO_SHORT, user=user))
        return
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
        if not user or not user.current_group_id:
            await message.answer(get_message(QUESTION_MUST_JOIN_GROUP, user=user))
            return
        # Check for duplicates
        is_dup = await is_duplicate_question(session, user.current_group_id, text)
        if is_dup:
            await message.answer(get_message(QUESTION_DUPLICATE, user=user))
            return
        # Moderation
        ok, reason = await moderate_question(text)
        if not ok:
            await message.answer(reason or get_message(QUESTION_REJECTED, user=user))
            return
        # Save question with pending status (awaiting admin approval)
        q = Question(group_id=user.current_group_id, author_id=user.id, text=text, status="pending")
        session.add(q)
        await session.commit()
        
        # Get group admin/creator
        group = await session.execute(select(Group).where(Group.id == user.current_group_id))
        group = group.scalar()
        admin_user = await session.execute(select(User).where(User.id == group.creator_user_id))
        admin_user = admin_user.scalar()
        
        try:
            await message.delete()
        except Exception:
            pass
        
        # Notify author that question is pending approval
        info_msg = await message.answer(get_message(QUESTION_PENDING_APPROVAL, user=user))
        await asyncio.sleep(2)
        try:
            await info_msg.delete()
        except Exception:
            pass
        
        # Send question to admin for approval
        if admin_user:
            await send_question_for_approval(message.bot, admin_user, q, user)

@router.callback_query(F.data.startswith("answer_"))
async def cb_answer_question(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    qid = int(parts[1])
    user_id = await get_or_restore_internal_user_id(state, callback.from_user.id)
    if not user_id:
        await callback.answer(get_message("Please start the bot to use this feature.", user=callback.from_user), show_alert=True)
        return
    try:
        value = int(parts[2])
    except Exception:
        logging.error(f"[cb_answer_question] Invalid answer value (not int): {parts[2]}")
        async with AsyncSessionLocal() as session:
            user = await session.execute(select(User).where(User.id == user_id))
            user = user.scalar()
        await callback.answer(get_message(QUESTION_INTERNAL_ERROR, user=user, show_alert=True))
        return
    allowed_values = set(ANSWER_VALUE_TO_EMOJI.keys())
    if value not in allowed_values:
        logging.error(f"[cb_answer_question] Invalid answer value: {value}")
        async with AsyncSessionLocal() as session:
            user = await session.execute(select(User).where(User.id == user_id))
            user = user.scalar()
        await callback.answer(get_message(QUESTION_INTERNAL_ERROR, user=user, show_alert=True))
        return
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
        question = await session.execute(select(Question).where(Question.id == qid, Question.is_deleted == 0))
        question = question.scalar()
        if not question:
            await callback.answer(get_message(QUESTION_ALREADY_DELETED, user=user, show_alert=True))
            await callback.message.delete()
            return
        group_obj = await session.execute(select(Group).where(Group.id == question.group_id))
        group_obj = group_obj.scalar()
        creator_user_id = group_obj.creator_user_id if group_obj else None
        ans = await session.execute(select(Answer).where(and_(Answer.question_id == qid, Answer.user_id == user.id)))
        ans = ans.scalar()
        if ans and ans.status == 'answered' and ans.value == value:
            # Don't change status back to delivered, just show message
            await show_question_with_all_buttons(callback, question, user, creator_user_id)
            await callback.answer(get_message(QUESTION_CAN_CHANGE_ANSWER, user=user))
            return
        is_new_answer = not ans
        if not ans:
            ans = Answer(question_id=qid, user_id=user.id, status='answered', value=value)
            session.add(ans)
            # Award points for new answer
            member = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == question.group_id))
            member = member.scalar()
            if member:
                member.balance += POINTS_FOR_ANSWER
        else:
            ans.value = value
            ans.status = 'answered'
        await session.commit()
        
        # Get updated balance
        updated_member = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == question.group_id))
        updated_member = updated_member.scalar()
        balance = updated_member.balance if updated_member else 0
        
        await show_question_with_selected_button(callback, question, user, value, creator_user_id)
        if is_new_answer:
            await callback.answer(f"💎 Balance: {balance} (+{POINTS_FOR_ANSWER})")
        else:
            await callback.answer(f"💎 Balance: {balance} (updated)")
        # Пушим следующий неотвеченный вопрос, если есть (через сервис)
        next_q = await get_next_unanswered_question(session, question.group_id, user.id)
        if next_q:
            logging.warning(f"[cb_answer_question] Push next unanswered: user_id={user.id}, question_id={next_q.id}, text={next_q.text[:50]}...")
            await send_question_to_user(callback.bot, user, next_q)
        else:
            # Debug: check if there are any approved questions at all
            all_questions = await session.execute(
                select(Question).where(
                    Question.group_id == question.group_id,
                    Question.is_deleted == 0,
                    Question.status == "approved"
                )
            )
            all_approved = all_questions.scalars().all()
            
            # Debug: check user's answers
            user_answers = await session.execute(
                select(Answer).where(Answer.user_id == user.id)
            )
            user_answer_count = len(user_answers.scalars().all())
            
            logging.warning(f"[cb_answer_question] No more unanswered for user_id={user.id}. Total approved questions: {len(all_approved)}, User answers: {user_answer_count}")
            for q in all_approved:
                ans = await session.execute(select(Answer).where(and_(Answer.question_id == q.id, Answer.user_id == user.id)))
                has_answer = ans.scalar() is not None
                logging.warning(f"  Question {q.id}: '{q.text[:30]}...' - Has answer: {has_answer}")
        # Update badge after answer (always)
        await update_badge_after_answer(callback.bot, user, question.group_id)

@router.callback_query(F.data.startswith("delete_question_"))
async def cb_delete_question(callback: types.CallbackQuery, state: FSMContext):
    qid = int(callback.data.split("_")[-1])
    user_id = await get_or_restore_internal_user_id(state, callback.from_user.id)
    if not user_id:
        await callback.answer(get_message("Please start the bot to use this feature.", user=callback.from_user), show_alert=True)
        return
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
        question = await session.execute(select(Question).where(Question.id == qid, Question.is_deleted == 0))
        question = question.scalar()
        if not question:
            await callback.answer(get_message(QUESTION_ALREADY_DELETED, user=user, show_alert=True))
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
            allowed_telegram_ids.add(author.id)
        if creator:
            allowed_telegram_ids.add(creator.id)
        if user_id not in allowed_telegram_ids:
            await callback.answer(get_message(QUESTION_ONLY_AUTHOR_OR_CREATOR, user=user, show_alert=True))
            return
        question.is_deleted = 1
        await session.execute(Answer.__table__.delete().where(Answer.question_id == qid))
        await session.commit()
        try:
            await callback.message.delete()
        except Exception as e:
            logging.error(f"[cb_delete_question] Failed to delete message: {e}")
        await callback.answer(get_message(QUESTION_DELETED, user=user))

ANSWERED_PAGE_SIZE = 10

@router.callback_query(F.data == "load_answered_questions")
async def cb_load_answered_questions(callback: types.CallbackQuery, state: FSMContext):
    user_id = await get_or_restore_internal_user_id(state, callback.from_user.id)
    if not user_id:
        await callback.answer(get_message("Please start the bot to use this feature.", user=callback.from_user), show_alert=True)
        return
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
        group_id = user.current_group_id
        print(f"[DEBUG] cb_load_answered_questions: user_id={user_id}, group_id={group_id}, user={user}")
        group_obj = await session.execute(select(Group).where(Group.id == group_id))
        group_obj = group_obj.scalar()
        group_name = group_obj.name if group_obj else None
        memberships = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id))
        memberships = memberships.scalars().all()
        all_groups_count = len(memberships)
        answers_query = select(Answer).where(
                Answer.user_id == user.id,
                Answer.value.isnot(None),
                Answer.question_id.in_(select(Question.id).where(Question.group_id == group_id, Question.is_deleted == 0, Question.status == "approved"))
        ).order_by(Answer.created_at)
        answers = await session.execute(answers_query.limit(ANSWERED_PAGE_SIZE))
        answers = answers.scalars().all()
        print(f"[DEBUG] cb_load_answered_questions: answers_ids={[a.id for a in answers]}")
        if not answers:
            await callback.answer(get_message(QUESTION_NO_ANSWERED, user=user, show_alert=True))
            return
        for ans in answers:
            question = await session.execute(select(Question).where(Question.id == ans.question_id))
            question = question.scalar()
            await send_answered_question_to_user(callback.bot, user, question, ans.value, group_name=group_name, all_groups_count=all_groups_count)
        total_count_query = select(Answer).where(
                Answer.user_id == user.id,
                Answer.value.isnot(None),
                Answer.question_id.in_(select(Question.id).where(Question.group_id == group_id, Question.is_deleted == 0, Question.status == "approved"))
            )
        total_count = await session.execute(total_count_query)
        total_count = len(total_count.scalars().all())
        print(f"[DEBUG] cb_load_answered_questions: total_count={total_count}, page=0, offset={ANSWERED_PAGE_SIZE}")
        # Log all questions
        questions_query = select(Question).where(Question.group_id == group_id, Question.is_deleted == 0, Question.status == "approved")
        questions = await session.execute(questions_query)
        questions = questions.scalars().all()
        print(f"[DEBUG] cb_load_answered_questions: questions_ids={[q.id for q in questions]}")
        if total_count > ANSWERED_PAGE_SIZE:
            kb = get_load_more_keyboard(1, user)
            print(f"[DEBUG] cb_load_answered_questions: sending load more button, reply_markup={kb}")
            await callback.message.answer(get_message(QUESTION_MORE_ANSWERED, user=user), reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("load_answered_questions_more_"))
async def cb_load_answered_questions_more(callback: types.CallbackQuery, state: FSMContext):
    print(f"[DEBUG] cb_load_answered_questions_more: callback.data={callback.data}")
    user_id = await get_or_restore_internal_user_id(state, callback.from_user.id)
    if not user_id:
        await callback.answer(get_message("Please start the bot to use this feature.", user=callback.from_user), show_alert=True)
        return
    try:
        page = int(callback.data.split("_")[-1])
    except Exception as e:
        print(f"[ERROR] Failed to parse page from callback.data: {callback.data}, error: {e}")
        await callback.answer("Internal error: invalid page.", show_alert=True)
        return
    offset = page * ANSWERED_PAGE_SIZE
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
        group_id = user.current_group_id
        print(f"[DEBUG] cb_load_answered_questions_more: user_id={user_id}, group_id={group_id}, user={user}")
        group_obj = await session.execute(select(Group).where(Group.id == group_id))
        group_obj = group_obj.scalar()
        group_name = group_obj.name if group_obj else None
        memberships = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id))
        memberships = memberships.scalars().all()
        all_groups_count = len(memberships)
        answers_query = select(Answer).where(
                Answer.user_id == user.id,
                Answer.value.isnot(None),
                Answer.question_id.in_(select(Question.id).where(Question.group_id == group_id, Question.is_deleted == 0, Question.status == "approved"))
            ).order_by(Answer.created_at).offset(offset).limit(ANSWERED_PAGE_SIZE)
        answers = await session.execute(answers_query)
        answers = answers.scalars().all()
        print(f"[DEBUG] cb_load_answered_questions_more: answers_ids={[a.id for a in answers]}, offset={offset}")
        if not answers:
            print(f"[DEBUG] No more answers to load for user_id={user_id}, group_id={group_id}")
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except Exception as e:
                print(f"[ERROR] Failed to remove inline keyboard: {e}")
            await callback.answer(get_message(QUESTION_NO_MORE_ANSWERED, user=user, show_alert=True))
            return
        for ans in answers:
            question = await session.execute(select(Question).where(Question.id == ans.question_id))
            question = question.scalar()
            await send_answered_question_to_user(callback.bot, user, question, ans.value, group_name=group_name, all_groups_count=all_groups_count)
        total_count_query = select(Answer).where(
            Answer.user_id == user.id,
            Answer.value.isnot(None),
            Answer.question_id.in_(select(Question.id).where(Question.group_id == group_id, Question.is_deleted == 0, Question.status == "approved"))
        )
        total_count = await session.execute(total_count_query)
        total_count = len(total_count.scalars().all())
        print(f"[DEBUG] cb_load_answered_questions_more: total_count={total_count}, page={page}, offset={offset}")
        # Log all questions
        questions_query = select(Question).where(Question.group_id == group_id, Question.is_deleted == 0, Question.status == "approved")
        questions = await session.execute(questions_query)
        questions = questions.scalars().all()
        print(f"[DEBUG] cb_load_answered_questions_more: questions_ids={[q.id for q in questions]}")
        if total_count > offset:
            # If there are more questions after this page — show button
            if offset + ANSWERED_PAGE_SIZE < total_count:
                kb = get_load_more_keyboard(page+1, user)
                print(f"[DEBUG] cb_load_answered_questions_more: sending load more button, reply_markup={kb}")
                await callback.message.answer(get_message(QUESTION_MORE_ANSWERED, user=user), reply_markup=kb)
        else:
            # All questions loaded — remove button
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except Exception as e:
                print(f"[ERROR] Failed to remove inline keyboard (final): {e}")
            await callback.message.answer(get_message(QUESTION_NO_MORE_ANSWERED, user=user))
    await callback.answer()

@router.callback_query(F.data == "load_unanswered")
async def cb_load_unanswered(callback: types.CallbackQuery, state: FSMContext):
    user_id = await get_or_restore_internal_user_id(state, callback.from_user.id)
    if not user_id:
        await callback.answer(get_message("Please start the bot to use this feature.", user=callback.from_user), show_alert=True)
        return
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar()
        # Новый динамический запрос: все вопросы группы, на которые нет Answer
        questions = await session.execute(
            select(Question).where(
                Question.group_id == user.current_group_id,
                Question.is_deleted == 0,
                Question.status == "approved"
            ).order_by(Question.created_at)
        )
        questions = questions.scalars().all()
        unanswered = []
        for q in questions:
            ans = await session.execute(select(Answer).where(and_(Answer.question_id == q.id, Answer.user_id == user.id)))
            ans = ans.scalar()
            if not ans:
                unanswered.append(q)
        if not unanswered:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.answer()
            return
        # Показываем первый неотвеченный вопрос
        from src.handlers.questions import send_question_to_user
        await send_question_to_user(callback.bot, user, unanswered[0])
        # Если есть ещё — показываем кнопку снова
        if len(unanswered) > 1:
            msg = get_message(UNANSWERED_QUESTIONS_MSG, user=user, count=len(unanswered)-1)
            kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=get_message(BTN_LOAD_UNANSWERED, user=user), callback_data="load_unanswered")]])
            await callback.message.answer(msg, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# --- Helper functions ---

async def show_question_with_selected_button(callback, question, user, value, creator_user_id=None):
    if creator_user_id is None:
        async with AsyncSessionLocal() as session:
            group_obj = await session.execute(select(Group).where(Group.id == question.group_id))
            group_obj = group_obj.scalar()
            creator_user_id = group_obj.creator_user_id if group_obj else None
    is_author = (user.id == question.author_id)
    is_creator = (user.id == creator_user_id)
    if value not in ANSWER_VALUE_TO_EMOJI:
        logging.error(f"[show_question_with_selected_button] Unknown value: {value}")
        await callback.answer(get_message(QUESTION_INTERNAL_ERROR, user=user, show_alert=True))
        return
    row = [types.InlineKeyboardButton(text=ANSWER_VALUE_TO_EMOJI[value], callback_data=f"answer_{question.id}_{value}")]
    if is_author or is_creator:
        row.append(types.InlineKeyboardButton(text="Delete", callback_data=f"delete_question_{question.id}"))
    kb = types.InlineKeyboardMarkup(inline_keyboard=[row])
    # Compare current keyboard with new
    current = callback.message.reply_markup
    if current and current.inline_keyboard == kb.inline_keyboard:
        return
    try:
        await callback.message.edit_reply_markup(reply_markup=kb)
    except Exception as e:
        logging.error(f"[show_question_with_selected_button] Failed to edit reply markup: {e}")

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
    # Compare current keyboard with new
    current = callback.message.reply_markup
    if current and current.inline_keyboard == kb.inline_keyboard:
        return
    try:
        await callback.message.edit_reply_markup(reply_markup=kb)
    except Exception as e:
        logging.error(f"[show_question_with_all_buttons] Failed to edit reply markup: {e}")

async def send_question_to_user(bot, user, question, creator_user_id=None, group_id=None, all_groups_count=None, group_name=None):
    import logging
    logging.warning(f"[send_question_to_user] user.id={user.id}, question.id={question.id}, user.current_group_id={getattr(user, 'current_group_id', None)}")
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
    # Не создаём Answer заранее!
    answer_buttons = [types.InlineKeyboardButton(text=ANSWER_VALUE_TO_EMOJI[val], callback_data=f"answer_{question.id}_{val}") for val, emoji in ANSWER_VALUES]
    keyboard = [answer_buttons]
    if is_author or is_creator:
        keyboard.append([types.InlineKeyboardButton(text="Delete", callback_data=f"delete_question_{question.id}")])
    kb = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    telegram_user_id = await get_telegram_user_id(user.id)
    logging.warning(f"[send_question_to_user] telegram_user_id={telegram_user_id}")
    if not telegram_user_id:
        tg_id = getattr(user, 'telegram_user_id', None)
        if tg_id:
            await set_telegram_mapping(tg_id, user.id)
            telegram_user_id = tg_id
            logging.info(f"[send_question_to_user] Restored mapping for user.id={user.id} <-> telegram_user_id={tg_id}")
    if telegram_user_id:
        await bot.send_message(telegram_user_id, text, reply_markup=kb, parse_mode="HTML")
        logging.warning(f"[send_question_to_user] sent to {telegram_user_id}")
    else:
        logging.error(f"[send_question_to_user] telegram_user_id not found for user.id={user.id}")

async def send_answered_question_to_user(bot, user, question, value, group_name=None, all_groups_count=None):
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
    row = [types.InlineKeyboardButton(text=ANSWER_VALUE_TO_EMOJI[value], callback_data=f"answer_{question.id}_{value}")]
    if is_author or is_creator:
        row.append(types.InlineKeyboardButton(text="Delete", callback_data=f"delete_question_{question.id}"))
    kb = types.InlineKeyboardMarkup(inline_keyboard=[row])
    telegram_user_id = await get_telegram_user_id(user.id)
    if telegram_user_id:
        await bot.send_message(telegram_user_id, text, reply_markup=kb, parse_mode="HTML")

async def update_badge_for_new_question(bot, user, new_question):
    from src.utils.redis import get_telegram_user_id
    async with AsyncSessionLocal() as session:
        questions = await session.execute(
            select(Question).where(
                Question.group_id == new_question.group_id,
                Question.is_deleted == 0,
                Question.status == "approved"
            )
        )
        questions = questions.scalars().all()
        unanswered = 0
        for q in questions:
            ans = await session.execute(select(Answer).where(and_(Answer.question_id == q.id, Answer.user_id == user.id)))
            ans = ans.scalar()
            if not ans:
                unanswered += 1
        telegram_user_id = await get_telegram_user_id(user.id)
        if not telegram_user_id:
            return
        try:
            if unanswered == 1:
                # Это был первый неотвеченный — пушим новый вопрос
                await send_question_to_user(bot, user, new_question)
                logging.info(f"[update_badge_for_new_question] Sent new question to user {user.id} (was 0 unanswered)")
            # badge_text = f"🔔 You have {unanswered} unanswered questions"
            # await bot.send_message(telegram_user_id, badge_text)
            logging.info(f"[update_badge_for_new_question] Updated badge for user {user.id}: {unanswered} unanswered")
        except Exception as e:
            logging.error(f"[update_badge_for_new_question] Failed to update badge: {e}")

async def update_badge_after_answer(bot, user, group_id):
    from src.utils.redis import get_telegram_user_id
    async with AsyncSessionLocal() as session:
        questions = await session.execute(
            select(Question).where(
                Question.group_id == group_id,
                Question.is_deleted == 0,
                Question.status == "approved"
            )
        )
        questions = questions.scalars().all()
        unanswered = 0
        for q in questions:
            ans = await session.execute(select(Answer).where(and_(Answer.question_id == q.id, Answer.user_id == user.id)))
            ans = ans.scalar()
            if not ans:
                unanswered += 1
        telegram_user_id = await get_telegram_user_id(user.id)
        if not telegram_user_id:
            return
        try:
            if unanswered == 0:
                # badge_text = "✅ All questions answered!"
                # await bot.send_message(telegram_user_id, badge_text)
                logging.info(f"[update_badge_after_answer] Removed badge for user {user.id}: no more unanswered questions")
            else:
                # badge_text = f"🔔 You have {unanswered} unanswered questions"
                # await bot.send_message(telegram_user_id, badge_text)
                logging.info(f"[update_badge_after_answer] Updated badge for user {user.id}: {unanswered} unanswered")
        except Exception as e:
            logging.error(f"[update_badge_after_answer] Failed to update badge: {e}") 

async def cleanup_old_delivered_answers():
    """Удалить все старые delivered Answer без value (устаревшие очереди)."""
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Answer).where(Answer.status == 'delivered', Answer.value.is_(None))
        )
        await session.commit()

async def send_question_for_approval(bot, admin_user, question, author_user):
    """Send question to admin for approval"""
    from src.utils.redis import get_telegram_user_id
    
    admin_telegram_id = await get_telegram_user_id(admin_user.id)
    if not admin_telegram_id:
        return
    
    # Get author nickname for the admin message
    async with AsyncSessionLocal() as session:
        author_member = await session.execute(select(GroupMember).where(
            GroupMember.user_id == author_user.id, 
            GroupMember.group_id == question.group_id))
        author_member = author_member.scalar()
        author_name = author_member.nickname if author_member and author_member.nickname else f"User {author_user.id}"
    
    # Send admin notification
    admin_text = get_message(QUESTION_ADMIN_APPROVAL, user=admin_user, 
                           author_name=author_name,
                           question_text=question.text)
    
    # Admin approval buttons
    keyboard = [
        [
            types.InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_question_{question.id}"),
            types.InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_question_{question.id}")
        ],
        [
            types.InlineKeyboardButton(text="🚫 Ban User", callback_data=f"ban_user_{question.id}")
        ]
    ]
    kb = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    try:
        await bot.send_message(admin_telegram_id, admin_text, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        logging.error(f"[send_question_for_approval] Failed to send to admin: {e}")

@router.callback_query(F.data.startswith("approve_question_"))
async def cb_approve_question(callback: types.CallbackQuery, state: FSMContext):
    """Handle question approval by admin"""
    question_id = int(callback.data.split("_")[-1])
    
    data = await state.get_data()
    admin_user_id = data.get('internal_user_id')
    if not admin_user_id:
        await callback.answer("Please start the bot to use this feature.")
        return
    
    async with AsyncSessionLocal() as session:
        # Verify admin privileges
        admin_user = await session.execute(select(User).where(User.id == admin_user_id))
        admin_user = admin_user.scalar()
        
        question = await session.execute(select(Question).where(Question.id == question_id))
        question = question.scalar()
        if not question:
            await callback.answer("Question not found.")
            return
            
        group = await session.execute(select(Group).where(Group.id == question.group_id))
        group = group.scalar()
        if not group or group.creator_user_id != admin_user_id:
            await callback.answer("You are not authorized to approve this question.")
            return
        
        # Update question status to approved
        question.status = "approved"
        
        # Award points to author
        author = await session.execute(select(User).where(User.id == question.author_id))
        author = author.scalar()
        author_member = await session.execute(select(GroupMember).where(
            GroupMember.user_id == question.author_id, 
            GroupMember.group_id == question.group_id))
        author_member = author_member.scalar()
        
        if author_member:
            author_member.balance += POINTS_FOR_NEW_QUESTION
        
        await session.commit()
        
        # Delete admin approval message
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        # Notify admin of approval
        await callback.message.answer(get_message(QUESTION_APPROVED_ADMIN, user=admin_user))
        
        # Notify author of approval
        if author:
            author_telegram_id = await get_telegram_user_id(author.id)
            if author_telegram_id:
                try:
                    await callback.bot.send_message(author_telegram_id, 
                        get_message(QUESTION_APPROVED_AUTHOR, user=author, points=POINTS_FOR_NEW_QUESTION))
                except Exception:
                    pass
        
        # Send question to author first
        if author:
            await send_question_to_user(callback.bot, author, question)
        
        # Send to all other group members
        group_members = await session.execute(select(GroupMember, User).join(User).where(
            GroupMember.group_id == question.group_id))
        group_members = group_members.all()
        
        for gm, u in group_members:
            if u.id == question.author_id:  # Skip author, already sent
                continue
            try:
                await update_badge_for_new_question(callback.bot, u, question)
            except Exception as e:
                logging.error(f"[cb_approve_question] Failed to update badge for user_id={u.id}: {e}")

@router.callback_query(F.data.startswith("reject_question_"))  
async def cb_reject_question(callback: types.CallbackQuery, state: FSMContext):
    """Handle question rejection by admin"""
    question_id = int(callback.data.split("_")[-1])
    
    data = await state.get_data()
    admin_user_id = data.get('internal_user_id')
    if not admin_user_id:
        await callback.answer("Please start the bot to use this feature.")
        return
    
    async with AsyncSessionLocal() as session:
        # Verify admin privileges
        admin_user = await session.execute(select(User).where(User.id == admin_user_id))
        admin_user = admin_user.scalar()
        
        question = await session.execute(select(Question).where(Question.id == question_id))
        question = question.scalar()
        if not question:
            await callback.answer("Question not found.")
            return
            
        group = await session.execute(select(Group).where(Group.id == question.group_id))
        group = group.scalar()
        if not group or group.creator_user_id != admin_user_id:
            await callback.answer("You are not authorized to reject this question.")
            return
        
        # Update question status to rejected
        question.status = "rejected"
        await session.commit()
        
        # Delete admin approval message
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        # Notify admin of rejection
        await callback.message.answer(get_message(QUESTION_REJECTED_ADMIN, user=admin_user))
        
        # Notify author of rejection
        author = await session.execute(select(User).where(User.id == question.author_id))
        author = author.scalar()
        if author:
            author_telegram_id = await get_telegram_user_id(author.id)
            if author_telegram_id:
                try:
                    await callback.bot.send_message(author_telegram_id,
                        get_message(QUESTION_REJECTED_AUTHOR, user=author))
                except Exception:
                    pass

@router.callback_query(F.data.startswith("ban_user_"))
async def cb_ban_user(callback: types.CallbackQuery, state: FSMContext):
    """Handle user ban by admin"""
    question_id = int(callback.data.split("_")[-1])
    
    data = await state.get_data()
    admin_user_id = data.get('internal_user_id')
    if not admin_user_id:
        await callback.answer("Please start the bot to use this feature.")
        return
    
    async with AsyncSessionLocal() as session:
        # Verify admin privileges
        admin_user = await session.execute(select(User).where(User.id == admin_user_id))
        admin_user = admin_user.scalar()
        
        question = await session.execute(select(Question).where(Question.id == question_id))
        question = question.scalar()
        if not question:
            await callback.answer("Question not found.")
            return
            
        group = await session.execute(select(Group).where(Group.id == question.group_id))
        group = group.scalar()
        if not group or group.creator_user_id != admin_user_id:
            await callback.answer("You are not authorized to ban users.")
            return
        
        banned_user_id = question.author_id
        
        # Check if user is already banned
        existing_ban = await session.execute(select(BannedUser).where(
            BannedUser.user_id == banned_user_id,
            BannedUser.group_id == question.group_id
        ))
        if existing_ban.scalar():
            await callback.answer("User is already banned.")
            return
        
        # Get banned user info for notification
        banned_user = await session.execute(select(User).where(User.id == banned_user_id))
        banned_user = banned_user.scalar()
        
        # Get banned user's nickname before deleting membership
        banned_member = await session.execute(select(GroupMember).where(
            GroupMember.user_id == banned_user_id, 
            GroupMember.group_id == question.group_id))
        banned_member = banned_member.scalar()
        banned_nickname = banned_member.nickname if banned_member and banned_member.nickname else f"User {banned_user_id}"
        
        # 1. Add to banned_users table
        ban_record = BannedUser(
            user_id=banned_user_id,
            group_id=question.group_id,
            banned_by=admin_user_id,
            reason="Spam questions"
        )
        session.add(ban_record)
        
        # 2. Reject current question
        question.status = "rejected"
        
        # 3. Delete ALL questions from this user in this group
        await session.execute(
            delete(Question).where(
                Question.author_id == banned_user_id,
                Question.group_id == question.group_id
            )
        )
        
        # 4. Delete ALL answers from this user in this group
        await session.execute(
            delete(Answer).where(
                Answer.user_id == banned_user_id,
                Answer.question_id.in_(
                    select(Question.id).where(Question.group_id == question.group_id)
                )
            )
        )
        
        # 5. Delete match statuses and matches involving this user
        await session.execute(
            delete(MatchStatus).where(
                MatchStatus.group_id == question.group_id,
                (MatchStatus.user_id == banned_user_id) | (MatchStatus.match_user_id == banned_user_id)
            )
        )
        
        await session.execute(
            delete(Match).where(
                Match.group_id == question.group_id,
                (Match.user1_id == banned_user_id) | (Match.user2_id == banned_user_id)
            )
        )
        
        # 6. Remove from group membership
        await session.execute(
            delete(GroupMember).where(
                GroupMember.user_id == banned_user_id,
                GroupMember.group_id == question.group_id
            )
        )
        
        # 7. Reset current_group_id if this was their current group
        if banned_user and banned_user.current_group_id == question.group_id:
            banned_user.current_group_id = None
        
        await session.commit()
        
        # Delete admin moderation message
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        # Notify admin of ban
        await callback.message.answer(get_message(USER_BANNED_ADMIN, user=admin_user, banned_nickname=banned_nickname))
        
        # Notify banned user
        if banned_user:
            banned_telegram_id = await get_telegram_user_id(banned_user.id)
            if banned_telegram_id:
                try:
                    await callback.bot.send_message(banned_telegram_id,
                        get_message(USER_BANNED_NOTIFICATION, user=banned_user, group_name=group.name))
                except Exception:
                    pass