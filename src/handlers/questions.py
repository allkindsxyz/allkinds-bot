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
    QUESTION_DELETE, UNANSWERED_QUESTIONS_MSG, BTN_LOAD_UNANSWERED
)
import logging

router = Router()

# --- Handlers for questions/answers ---

@router.message(F.text & ~F.text.startswith('/'))
async def handle_new_question(message: types.Message, state: FSMContext):
    """Создание нового вопроса: сохраняем вопрос, начисляем баллы автору."""
    import asyncio
    text = message.text.strip()
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == message.from_user.id))
        user = user.scalar()
    if len(text) < 5:
        await message.answer(get_message(QUESTION_TOO_SHORT, user=user))
        return
    user_id = message.from_user.id
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
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
        # Удаляем исходное сообщение пользователя (вопрос без кнопок)
        try:
            await message.delete()
        except Exception:
            pass
        # Отправляем сообщение о добавлении вопроса и удаляем его через 1 секунду
        info_msg = await message.answer(get_message(QUESTION_ADDED, user=user, points=POINTS_FOR_NEW_QUESTION))
        await asyncio.sleep(1)
        try:
            await info_msg.delete()
        except Exception:
            pass
        # Сразу показываем вопрос автору с кнопками ответов
        from src.handlers.questions import send_question_to_user
        await send_question_to_user(message.bot, user, q)
        # Пуш-уведомления всем участникам группы (кроме автора)
        group_members = await session.execute(select(GroupMember, User).join(User).where(GroupMember.group_id == user.current_group_id))
        group_members = group_members.all()
        for gm, u in group_members:
            if u.id == user.id:
                continue  # не отправляем автору
            try:
                await send_question_to_user(message.bot, u, q)
            except Exception:
                pass

@router.callback_query(F.data.startswith("answer_"))
async def cb_answer_question(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    qid = int(parts[1])
    try:
        value = int(parts[2])
    except Exception:
        logging.error(f"[cb_answer_question] Invalid answer value (not int): {parts[2]}")
        async with AsyncSessionLocal() as session:
            user = await session.execute(select(User).where(User.telegram_user_id == callback.from_user.id))
            user = user.scalar()
        await callback.answer(get_message(QUESTION_INTERNAL_ERROR, user=user, show_alert=True))
        return
    user_id = callback.from_user.id
    allowed_values = set(ANSWER_VALUE_TO_EMOJI.keys())
    if value not in allowed_values:
        logging.error(f"[cb_answer_question] Invalid answer value: {value}")
        async with AsyncSessionLocal() as session:
            user = await session.execute(select(User).where(User.telegram_user_id == callback.from_user.id))
            user = user.scalar()
        await callback.answer(get_message(QUESTION_INTERNAL_ERROR, user=user, show_alert=True))
        return
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
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
        # --- Новый UX: двухшаговый переответ ---
        if ans and ans.status == 'answered' and ans.value == value:
            # Первый клик по уже выбранному ответу — переводим в delivered, показываем все кнопки
            ans.status = 'delivered'
            await session.commit()
            await show_question_with_all_buttons(callback, question, user, creator_user_id)
            await callback.answer(get_message(QUESTION_CAN_CHANGE_ANSWER, user=user))
            return
        # Любой другой клик (или delivered) — сохраняем ответ и скрываем остальные кнопки
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
        # --- Следующий вопрос из очереди ---
        next_q = await get_next_unanswered_question(session, question.group_id, user.id)
        if next_q:
            await send_question_to_user(bot, user, next_q, creator_user_id)
        else:
            unanswered = await session.execute(
                select(Answer).where(
                    Answer.user_id == user.id,
                    Answer.status == 'delivered',
                    Answer.value.is_(None)
                )
            )
            unanswered = unanswered.scalars().all()
            if unanswered:
                count = len(unanswered)
                msg = get_message(UNANSWERED_QUESTIONS_MSG, user=user, count=count)
                kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=get_message(BTN_LOAD_UNANSWERED, user=user), callback_data="load_unanswered")]])
                await callback.message.answer(msg, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("delete_question_"))
async def cb_delete_question(callback: types.CallbackQuery, state: FSMContext):
    qid = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
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
            allowed_telegram_ids.add(author.telegram_user_id)
        if creator:
            allowed_telegram_ids.add(creator.telegram_user_id)
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
    user_id = callback.from_user.id
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
            ).order_by(Answer.created_at).limit(ANSWERED_PAGE_SIZE)
        )
        answers = answers.scalars().all()
        if not answers:
            await callback.answer(get_message(QUESTION_NO_ANSWERED, user=user, show_alert=True))
            return
        for ans in answers:
            question = await session.execute(select(Question).where(Question.id == ans.question_id))
            question = question.scalar()
            await send_answered_question_to_user(callback.bot, user, question, ans.value, group_name=group_name, all_groups_count=all_groups_count)
        total_count = await session.execute(
            select(Answer).where(
                Answer.user_id == user.id,
                Answer.value.isnot(None),
                Answer.question_id.in_(select(Question.id).where(Question.group_id == group_id, Question.is_deleted == 0))
            )
        )
        total_count = len(total_count.scalars().all())
        if total_count > ANSWERED_PAGE_SIZE:
            kb = get_load_more_keyboard(1)
            await callback.message.answer(get_message(QUESTION_MORE_ANSWERED, user=user, reply_markup=kb))
    await callback.answer()

@router.callback_query(F.data.startswith("load_answered_questions_more_"))
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
            await callback.answer(get_message(QUESTION_NO_MORE_ANSWERED, user=user, show_alert=True))
            return
        for ans in answers:
            question = await session.execute(select(Question).where(Question.id == ans.question_id))
            question = question.scalar()
            await send_answered_question_to_user(callback.bot, user, question, ans.value, group_name=group_name, all_groups_count=all_groups_count)
        total_count = await session.execute(
            select(Answer).where(
                Answer.user_id == user.id,
                Answer.value.isnot(None),
                Answer.question_id.in_(select(Question.id).where(Question.group_id == group_id, Question.is_deleted == 0))
            )
        )
        total_count = len(total_count.scalars().all())
        if total_count > offset + ANSWERED_PAGE_SIZE:
            kb = get_load_more_keyboard(page+1)
            await callback.message.answer(get_message(QUESTION_MORE_ANSWERED, user=user, reply_markup=kb))
    await callback.answer()

@router.callback_query(F.data == "load_unanswered")
async def cb_load_unanswered(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
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
    answer_buttons = [types.InlineKeyboardButton(text=ANSWER_VALUE_TO_EMOJI[val], callback_data=f"answer_{question.id}_{val}") for val, emoji in ANSWER_VALUES]
    keyboard = [answer_buttons]
    if is_author or is_creator:
        keyboard.append([types.InlineKeyboardButton(text="Delete", callback_data=f"delete_question_{question.id}")])
    kb = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    await bot.send_message(user.telegram_user_id, text, reply_markup=kb, parse_mode="HTML")

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
    await bot.send_message(user.telegram_user_id, text, reply_markup=kb, parse_mode="HTML") 