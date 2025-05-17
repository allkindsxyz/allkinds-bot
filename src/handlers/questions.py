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

router = Router()

# --- Handlers for questions/answers ---

@router.message(F.text & ~F.text.startswith('/'))
async def handle_new_question(message: types.Message, state: FSMContext):
    """Создание нового вопроса: сохраняем вопрос, начисляем баллы автору."""
    text = message.text.strip()
    if len(text) < 5:
        await message.answer("Question too short. Please enter a more detailed question.")
        return
    user_id = message.from_user.id
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        if not user or not user.current_group_id:
            await message.answer("You must join a group before asking questions.")
            return
        # Проверка на дубликаты
        is_dup = await is_duplicate_question(session, user.current_group_id, text)
        if is_dup:
            await message.answer("This question already exists in the group.")
            return
        # Модерация
        ok, reason = await moderate_question(text)
        if not ok:
            await message.answer(reason or "Question rejected by moderation.")
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
        await message.answer(f"✅ Question added! You received +{POINTS_FOR_NEW_QUESTION}💎 points.")
        # Сразу показываем вопрос автору с кнопками ответов
        from src.handlers.questions import send_question_to_user
        await send_question_to_user(message.bot, user, q)

@router.callback_query(F.data.startswith("answer_"))
async def cb_answer_question(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    qid = int(parts[1])
    try:
        value = int(parts[2])
    except Exception:
        logging.error(f"[cb_answer_question] Invalid answer value (not int): {parts[2]}")
        await callback.answer("Internal error: invalid answer value.", show_alert=True)
        return
    user_id = callback.from_user.id
    allowed_values = set(ANSWER_VALUE_TO_EMOJI.keys())
    if value not in allowed_values:
        logging.error(f"[cb_answer_question] Invalid answer value: {value}")
        await callback.answer("Internal error: invalid answer value.", show_alert=True)
        return
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == user_id))
        user = user.scalar()
        question = await session.execute(select(Question).where(Question.id == qid, Question.is_deleted == 0))
        question = question.scalar()
        if not question:
            await callback.answer("Question was deleted.", show_alert=True)
            await callback.message.delete()
            return
        group_obj = await session.execute(select(Group).where(Group.id == question.group_id))
        group_obj = group_obj.scalar()
        creator_user_id = group_obj.creator_user_id if group_obj else None
        ans = await session.execute(select(Answer).where(and_(Answer.question_id == qid, Answer.user_id == user.id)))
        ans = ans.scalar()
        if ans and ans.value == value:
            await show_question_with_all_buttons(callback, question, user, creator_user_id)
            await callback.answer("You can change your answer.")
            return
        if not ans:
            ans = Answer(question_id=qid, user_id=user.id)
            session.add(ans)
            member = await session.execute(select(GroupMember).where(GroupMember.user_id == user.id, GroupMember.group_id == question.group_id))
            member = member.scalar()
            if member:
                member.balance += POINTS_FOR_ANSWER
        ans.value = value
        ans.is_skipped = int(value == 0)
        await session.commit()
        await show_question_with_selected_button(callback, question, user, value, creator_user_id)
        await callback.answer("Answer saved.")
        next_q = await get_next_unanswered_question(session, question.group_id, user.id)
        if next_q:
            await send_question_to_user(bot, user, next_q, creator_user_id)

@router.callback_query(F.data.startswith("delete_question_"))
async def cb_delete_question(callback: types.CallbackQuery, state: FSMContext):
    qid = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    async with AsyncSessionLocal() as session:
        question = await session.execute(select(Question).where(Question.id == qid, Question.is_deleted == 0))
        question = question.scalar()
        if not question:
            await callback.answer("Question already deleted.", show_alert=True)
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
            await callback.answer("Only the author or group creator can delete this question.", show_alert=True)
            return
        question.is_deleted = 1
        await session.execute(Answer.__table__.delete().where(Answer.question_id == qid))
        await session.commit()
        try:
            await callback.message.delete()
        except Exception as e:
            logging.error(f"[cb_delete_question] Failed to delete message: {e}")
        await callback.answer("Question deleted.")

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
            await callback.answer("No answered questions yet.", show_alert=True)
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
            await callback.message.answer("More answered questions available:", reply_markup=kb)
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
            await callback.answer("No more answered questions.", show_alert=True)
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
            await callback.message.answer("More answered questions available:", reply_markup=kb)
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
        await callback.answer("Internal error: unknown answer value.", show_alert=True)
        return
    row = [types.InlineKeyboardButton(text=ANSWER_VALUE_TO_EMOJI[value], callback_data=f"answer_{question.id}_{value}")]
    if is_author or is_creator:
        row.append(types.InlineKeyboardButton(text="Delete", callback_data=f"delete_question_{question.id}"))
    kb = types.InlineKeyboardMarkup(inline_keyboard=[row])
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
    try:
        await callback.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        pass

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