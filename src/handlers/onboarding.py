# Хендлеры для онбординга
# Импорты и вызовы сервисов будут добавлены после выноса бизнес-логики 

from aiogram import types, F, Router
from aiogram.fsm.context import FSMContext
from src.loader import bot
from src.services.onboarding import save_nickname_service, save_photo_service, save_location_service, is_onboarding_complete_service
from src.fsm.states import Onboarding
from src.db import AsyncSessionLocal
from src.models import User, Answer, Question
from src.services.questions import get_next_unanswered_question
from src.handlers.questions import send_question_to_user
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from src.texts.messages import (
    ONBOARDING_NICKNAME_TOO_SHORT, ONBOARDING_INTERNAL_ERROR, ONBOARDING_SEND_PHOTO, ONBOARDING_PHOTO_REQUIRED,
    ONBOARDING_SEND_LOCATION, ONBOARDING_LOCATION_REQUIRED, ONBOARDING_LOCATION_SAVED, ONBOARDING_SOMETHING_WRONG,
    get_message
)

router = Router()

# --- Onboarding Handlers ---

@router.message(Onboarding.nickname)
async def onboarding_nickname(message: types.Message, state: FSMContext):
    nickname = message.text.strip()
    data = await state.get_data()
    group_id = data.get("group_id")
    telegram_user_id = message.from_user.id
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == telegram_user_id))
        user = user.scalar()
        if len(nickname) < 2:
            await message.answer(get_message("ONBOARDING_NICKNAME_TOO_SHORT", user or message.from_user))
            return
        if not group_id:
            await message.answer(get_message("ONBOARDING_INTERNAL_ERROR", user or message.from_user))
            await state.clear()
            return
        await save_nickname_service(telegram_user_id, group_id, nickname)
        await state.set_state(Onboarding.photo)
        await message.answer(get_message("ONBOARDING_SEND_PHOTO", user or message.from_user), reply_markup=types.ReplyKeyboardRemove())

@router.message(Onboarding.photo)
async def onboarding_photo(message: types.Message, state: FSMContext):
    if not message.photo:
        await message.answer(get_message("ONBOARDING_PHOTO_REQUIRED", message.from_user))
        return
    file_id = message.photo[-1].file_id
    data = await state.get_data()
    group_id = data.get("group_id")
    telegram_user_id = message.from_user.id
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == telegram_user_id))
        user = user.scalar()
        if not group_id:
            await message.answer(get_message("ONBOARDING_INTERNAL_ERROR", user or message.from_user))
            await state.clear()
            return
        await save_photo_service(telegram_user_id, group_id, file_id)
        await state.set_state(Onboarding.location)
        await message.answer(get_message("ONBOARDING_SEND_LOCATION", user or message.from_user), reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text=get_message("BTN_SEND_LOCATION", user or message.from_user), request_location=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        ))

@router.message(Onboarding.location)
async def onboarding_location(message: types.Message, state: FSMContext):
    data = await state.get_data()
    group_id = data.get("group_id")
    telegram_user_id = message.from_user.id
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == telegram_user_id))
        user = user.scalar()
        if not group_id:
            await message.answer(get_message("ONBOARDING_INTERNAL_ERROR", user or message.from_user))
            await state.clear()
            return
        if message.location:
            lat = message.location.latitude
            lon = message.location.longitude
            await save_location_service(telegram_user_id, group_id, lat, lon)
        elif message.text and len(message.text.strip()) > 2:
            city_raw = message.text.strip()
            city, country = await normalize_city_country(city_raw)
            await save_location_service(telegram_user_id, group_id, None, None, city=city, country=country)
        else:
            await message.answer(get_message("ONBOARDING_LOCATION_REQUIRED", user or message.from_user))
            return
        complete = await is_onboarding_complete_service(telegram_user_id, group_id)
        if complete:
            await state.clear()
            await message.answer(get_message("ONBOARDING_LOCATION_SAVED", user or message.from_user), reply_markup=types.ReplyKeyboardRemove())
            from src.handlers.groups import show_group_welcome_and_question
            await show_group_welcome_and_question(message, telegram_user_id, group_id)
        else:
            await message.answer(get_message("ONBOARDING_SOMETHING_WRONG", user or message.from_user))
            await state.clear()

# Заглушка для нормализации города/страны через OpenAI
async def normalize_city_country(text: str):
    # Без OpenAI: просто делим по запятой, если есть
    if "," in text:
        parts = [p.strip() for p in text.split(",", 1)]
        city = parts[0]
        country = parts[1] if len(parts) > 1 else None
    else:
        city = text
        country = None
    print("Parsed city:", city, "country:", country)
    return city, country

async def show_group_main_flow_after_onboarding(message, telegram_user_id, group_id):
    """После онбординга: показать первый вопрос или сообщение, а также кнопку Load answered questions только если есть ответы."""
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_user_id == telegram_user_id))
        user = user.scalar()
        if not user:
            await message.answer(get_message("ONBOARDING_INTERNAL_ERROR", message.from_user))
            return
        # Проверяем, есть ли хотя бы один ответ в этой группе
        answers_count = await session.execute(
            select(Answer).where(
                Answer.user_id == user.id,
                Answer.value.isnot(None),
                Answer.question_id.in_(select(Question.id).where(Question.group_id == group_id, Question.is_deleted == 0))
            )
        )
        answers_count = len(answers_count.scalars().all())
        # Ищем первый неотвеченный вопрос
        next_q = await get_next_unanswered_question(session, group_id, user.id)
        if next_q:
            await send_question_to_user(message.bot, user, next_q)
        else:
            await message.answer("No new questions in this group yet.")
        # Кнопка Load answered questions — только если есть хотя бы один ответ
        if answers_count > 0:
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Load answered questions", callback_data="load_answered_questions")]])
            await message.answer("You can review your answered questions:", reply_markup=kb) 