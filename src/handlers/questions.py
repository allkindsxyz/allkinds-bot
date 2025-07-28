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
from src.models import User, GroupMember, Question, Answer, Group
from src.texts.messages import (
    get_message,
    QUESTION_TOO_SHORT, QUESTION_MUST_JOIN_GROUP, QUESTION_DUPLICATE, QUESTION_REJECTED, QUESTION_ADDED, QUESTION_DELETED,
    QUESTION_ALREADY_DELETED, QUESTION_ONLY_AUTHOR_OR_CREATOR, QUESTION_ANSWER_SAVED, QUESTION_NO_ANSWERED, QUESTION_MORE_ANSWERED,
    QUESTION_NO_MORE_ANSWERED, QUESTION_CAN_CHANGE_ANSWER, QUESTION_INTERNAL_ERROR, QUESTION_LOAD_ANSWERED, QUESTION_LOAD_MORE,
    QUESTION_DELETE, UNANSWERED_QUESTIONS_MSG, BTN_LOAD_UNANSWERED, GROUPS_NO_NEW_QUESTIONS, NEW_QUESTION_NOTIFICATION
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
        # Save question
        q = Question(group_id=user.current_group_id, author_id=user.id, text=text)
        session.add(q)
        # Award points to author
        member = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == user.current_group_id))
        member = member.scalar()
        if member:
            member.balance += POINTS_FOR_NEW_QUESTION
        await session.commit()
        try:
            await message.delete()
        except Exception:
            pass
        info_msg = await message.answer(get_message(QUESTION_ADDED, user=user, points=POINTS_FOR_NEW_QUESTION))
        await asyncio.sleep(1)
        try:
            await info_msg.delete()
        except Exception:
            pass
        # Показываем вопрос автору сразу (push)
        from src.handlers.questions import send_question_to_user
        await send_question_to_user(message.bot, user, q)
    # Для остальных участников — обновляем бейджи и пушим только если нет очереди
    async with AsyncSessionLocal() as session:
        group_members = await session.execute(select(GroupMember, User).join(User).where(GroupMember.group_id == user.current_group_id))
        group_members = group_members.all()
        for gm, u in group_members:
            if u.id == user.id:
                continue
            try:
                await update_badge_for_new_question(message.bot, u, q)
            except Exception as e:
                logging.error(f"[handle_new_question] Failed to update badge for user_id={u.id}: {e}")

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
            logging.warning(f"[cb_answer_question] Push next unanswered: user_id={user.id}, question_id={next_q.id}")
            await send_question_to_user(callback.bot, user, next_q)
        else:
            logging.warning(f"[cb_answer_question] No more unanswered for user_id={user.id}")
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
                Answer.question_id.in_(select(Question.id).where(Question.group_id == group_id, Question.is_deleted == 0))
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
                Answer.question_id.in_(select(Question.id).where(Question.group_id == group_id, Question.is_deleted == 0))
            )
        total_count = await session.execute(total_count_query)
        total_count = len(total_count.scalars().all())
        print(f"[DEBUG] cb_load_answered_questions: total_count={total_count}, page=0, offset={ANSWERED_PAGE_SIZE}")
        # Log all questions
        questions_query = select(Question).where(Question.group_id == group_id, Question.is_deleted == 0)
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
                Answer.question_id.in_(select(Question.id).where(Question.group_id == group_id, Question.is_deleted == 0))
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
            Answer.question_id.in_(select(Question.id).where(Question.group_id == group_id, Question.is_deleted == 0))
        )
        total_count = await session.execute(total_count_query)
        total_count = len(total_count.scalars().all())
        print(f"[DEBUG] cb_load_answered_questions_more: total_count={total_count}, page={page}, offset={offset}")
        # Log all questions
        questions_query = select(Question).where(Question.group_id == group_id, Question.is_deleted == 0)
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
                Question.is_deleted == 0
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
                Question.is_deleted == 0
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
                Question.is_deleted == 0
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