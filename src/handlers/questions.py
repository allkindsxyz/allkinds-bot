# Хендлеры для вопросов и ответов
# Импорты и вызовы сервисов будут добавлены после выноса бизнес-логики 

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
from sqlalchemy import select, and_
from src.models import User, GroupMember, Question, Answer, Group
from src.texts.messages import (
    get_message,
    QUESTION_TOO_SHORT, QUESTION_MUST_JOIN_GROUP, QUESTION_DUPLICATE, QUESTION_REJECTED, QUESTION_ADDED, QUESTION_DELETED,
    QUESTION_ALREADY_DELETED, QUESTION_ONLY_AUTHOR_OR_CREATOR, QUESTION_ANSWER_SAVED, QUESTION_NO_ANSWERED, QUESTION_MORE_ANSWERED,
    QUESTION_NO_MORE_ANSWERED, QUESTION_CAN_CHANGE_ANSWER, QUESTION_INTERNAL_ERROR, QUESTION_LOAD_ANSWERED, QUESTION_LOAD_MORE,
    QUESTION_DELETE, UNANSWERED_QUESTIONS_MSG, BTN_LOAD_UNANSWERED, GROUPS_NO_NEW_QUESTIONS, NEW_QUESTION_NOTIFICATION
)
import logging
from src.utils.redis import get_telegram_user_id, get_or_restore_internal_user_id

router = Router()

# --- Handlers for questions/answers ---

@router.message(F.text & ~F.text.startswith('/'))
async def handle_new_question(message: types.Message, state: FSMContext):
    """Создание нового вопроса: сохраняем вопрос, начисляем баллы автору."""
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
        # Проверка на дубликаты
        is_dup = await is_duplicate_question(session, user.current_group_id, text)
        if is_dup:
            await message.answer(get_message(QUESTION_DUPLICATE, user=user))
            return
        # Модерация
        ok, reason = await moderate_question(text)
        if not ok:
            await message.answer(reason or get_message(QUESTION_REJECTED, user=user))
            return
        # Сохраняем вопрос
        q = Question(group_id=user.current_group_id, author_id=user.id, text=text)
        session.add(q)
        # Начисляем баллы автору
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
        from src.handlers.questions import send_question_to_user
        await send_question_to_user(message.bot, user, q)
    # Обновляем бейджи для других участников группы (не рассылаем вопросы)
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
            # Не меняем статус обратно на delivered, просто показываем сообщение
            await show_question_with_all_buttons(callback, question, user, creator_user_id)
            await callback.answer(get_message(QUESTION_CAN_CHANGE_ANSWER, user=user))
            return
        if not ans:
            ans = Answer(question_id=qid, user_id=user.id, status='answered', value=value)
            session.add(ans)
        else:
            ans.value = value
            ans.status = 'answered'
            member = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == question.group_id))
            member = member.scalar()
            if member:
                member.balance += POINTS_FOR_ANSWER
        await session.commit()
        await show_question_with_selected_button(callback, question, user, value, creator_user_id)
        await callback.answer(get_message(QUESTION_ANSWER_SAVED, user=user))
        
        # Показываем следующий неотвеченный вопрос из текущей группы
        next_q_query = select(Answer, Question).join(Question, Answer.question_id == Question.id).where(
            Answer.user_id == user.id,
            Answer.status == 'delivered',
            Answer.value.is_(None),
            Question.group_id == question.group_id,
            Question.is_deleted == 0
        ).order_by(Question.created_at)
        
        next_result = await session.execute(next_q_query)
        next_result = next_result.first()
        
        if next_result:
            next_ans, next_q = next_result
            await send_question_to_user(callback.bot, user, next_q, creator_user_id, question.group_id)
        
        # Обновляем бейдж после ответа (всегда)
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
        # Логируем id всех questions
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
        # Логируем id всех questions
        questions_query = select(Question).where(Question.group_id == group_id, Question.is_deleted == 0)
        questions = await session.execute(questions_query)
        questions = questions.scalars().all()
        print(f"[DEBUG] cb_load_answered_questions_more: questions_ids={[q.id for q in questions]}")
        if total_count > offset:
            # Если после этой страницы ещё останутся вопросы — показываем кнопку
            if offset + ANSWERED_PAGE_SIZE < total_count:
                kb = get_load_more_keyboard(page+1, user)
                print(f"[DEBUG] cb_load_answered_questions_more: sending load more button, reply_markup={kb}")
                await callback.message.answer(get_message(QUESTION_MORE_ANSWERED, user=user), reply_markup=kb)
        else:
            # Все вопросы загружены — удаляем кнопку
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
        unanswered = await session.execute(
            select(Answer).where(
                Answer.user_id == user.id,
                Answer.status == 'delivered',
                Answer.value.is_(None)
            )
        )
        unanswered = unanswered.scalars().all()
        if not unanswered:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.answer()
            return
        # Показываем первый неотвеченный delivered-вопрос
        question = await session.execute(select(Question).where(Question.id == unanswered[0].question_id))
        question = question.scalar()
        from src.handlers.questions import send_question_to_user
        await send_question_to_user(callback.bot, user, question)
        # Если остались ещё — повторно показываем кнопку
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
    # Сравниваем текущую клавиатуру с новой
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
    # Сравниваем текущую клавиатуру с новой
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
    # --- Создаём Answer со статусом delivered, если нет ---
    async with AsyncSessionLocal() as session:
        ans = await session.execute(select(Answer).where(and_(Answer.question_id == question.id, Answer.user_id == user.id)))
        ans = ans.scalar()
        if not ans:
            ans = Answer(question_id=question.id, user_id=user.id, status='delivered')
            session.add(ans)
            await session.commit()
            logging.warning(f"[send_question_to_user] Created new Answer for question_id={question.id}, user_id={user.id}")
        else:
            logging.warning(f"[send_question_to_user] Answer already exists for question_id={question.id}, user_id={user.id}, status={ans.status}, value={ans.value}")
    answer_buttons = [types.InlineKeyboardButton(text=ANSWER_VALUE_TO_EMOJI[val], callback_data=f"answer_{question.id}_{val}") for val, emoji in ANSWER_VALUES]
    keyboard = [answer_buttons]
    if is_author or is_creator:
        keyboard.append([types.InlineKeyboardButton(text="Delete", callback_data=f"delete_question_{question.id}")])
    kb = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    telegram_user_id = await get_telegram_user_id(user.id)
    logging.warning(f"[send_question_to_user] telegram_user_id={telegram_user_id}")
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
    """
    Обновляет бейдж при создании нового вопроса:
    - Если у пользователя 0 неотвеченных → отправить push + показать вопрос + бейдж
    - Если у пользователя >0 неотвеченных → только обновить бейдж (вопрос попадает в очередь)
    """
    from src.utils.redis import get_telegram_user_id
    
    async with AsyncSessionLocal() as session:
        # Сначала считаем сколько было неотвеченных ДО добавления нового вопроса
        old_unanswered_count = await session.execute(
            select(Answer).where(
                Answer.user_id == user.id,
                Answer.status == 'delivered',
                Answer.value.is_(None),
                Answer.question_id.in_(select(Question.id).where(Question.group_id == new_question.group_id, Question.is_deleted == 0))
            )
        )
        old_unanswered_count = len(old_unanswered_count.scalars().all())
        
        # Создаем delivered Answer для нового вопроса
        existing_ans = await session.execute(select(Answer).where(and_(Answer.question_id == new_question.id, Answer.user_id == user.id)))
        existing_ans = existing_ans.scalar()
        if not existing_ans:
            session.add(Answer(question_id=new_question.id, user_id=user.id, status='delivered'))
            await session.commit()
        
        # Считаем количество неотвеченных вопросов в группе ПОСЛЕ добавления
        unanswered_count = await session.execute(
            select(Answer).where(
                Answer.user_id == user.id,
                Answer.status == 'delivered',
                Answer.value.is_(None),
                Answer.question_id.in_(select(Question.id).where(Question.group_id == new_question.group_id, Question.is_deleted == 0))
            )
        )
        unanswered_count = len(unanswered_count.scalars().all())
        
        telegram_user_id = await get_telegram_user_id(user.id)
        if not telegram_user_id:
            return
        
        if old_unanswered_count == 0:
            # У пользователя не было неотвеченных вопросов - показываем новый вопрос сразу
            try:
                await send_question_to_user(bot, user, new_question)
                logging.info(f"[update_badge_for_new_question] Sent new question to user {user.id} (was 0 unanswered)")
            except Exception as e:
                logging.error(f"[update_badge_for_new_question] Failed to send question: {e}")
        else:
            # У пользователя уже были неотвеченные - новый вопрос попадает в очередь
            logging.info(f"[update_badge_for_new_question] Question added to queue for user {user.id} (had {old_unanswered_count} unanswered)")
        
        # Обновляем бейдж (пока только логирование)
        try:
            # badge_text = f"🔔 You have {unanswered_count} unanswered questions"
            # await bot.send_message(telegram_user_id, badge_text)
            logging.info(f"[update_badge_for_new_question] Updated badge for user {user.id}: {unanswered_count} unanswered")
        except Exception as e:
            logging.error(f"[update_badge_for_new_question] Failed to update badge: {e}")

async def update_badge_after_answer(bot, user, group_id):
    """
    Обновляет бейдж после ответа на вопрос:
    - Считает оставшиеся неотвеченные вопросы
    - Если стало 0 → убирает бейдж
    - Если >0 → обновляет бейдж с новым количеством
    """
    from src.utils.redis import get_telegram_user_id
    
    async with AsyncSessionLocal() as session:
        # Считаем количество оставшихся неотвеченных вопросов в группе
        unanswered_count = await session.execute(
            select(Answer).where(
                Answer.user_id == user.id,
                Answer.status == 'delivered',
                Answer.value.is_(None),
                Answer.question_id.in_(select(Question.id).where(Question.group_id == group_id, Question.is_deleted == 0))
            )
        )
        unanswered_count = len(unanswered_count.scalars().all())
        
        telegram_user_id = await get_telegram_user_id(user.id)
        if not telegram_user_id:
            return
        
        try:
            if unanswered_count == 0:
                # Убираем бейдж - больше нет неотвеченных вопросов
                # badge_text = "✅ All questions answered!"
                # await bot.send_message(telegram_user_id, badge_text)
                logging.info(f"[update_badge_after_answer] Removed badge for user {user.id}: no more unanswered questions")
            else:
                # Обновляем бейдж с новым количеством
                # badge_text = f"🔔 You have {unanswered_count} unanswered questions"
                # await bot.send_message(telegram_user_id, badge_text)
                logging.info(f"[update_badge_after_answer] Updated badge for user {user.id}: {unanswered_count} unanswered")
        except Exception as e:
            logging.error(f"[update_badge_after_answer] Failed to update badge: {e}") 