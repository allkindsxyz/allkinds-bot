import redis.asyncio as aioredis
import os
from src.db import AsyncSessionLocal
from src.models import User
from sqlalchemy import select
import logging

REDIS_URL = os.getenv("REDIS_PUBLIC_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))

redis = aioredis.from_url(REDIS_URL, decode_responses=True)

TTL_DAYS = 30
TTL_SECONDS = TTL_DAYS * 24 * 60 * 60

async def set_telegram_mapping(telegram_user_id: int, internal_user_id: int, ttl: int = TTL_SECONDS):
    key = f"tg2int:{telegram_user_id}"
    await redis.setex(key, ttl, internal_user_id)
    # Двунаправленный маппинг
    key2 = f"int2tg:{internal_user_id}"
    await redis.setex(key2, ttl, telegram_user_id)

async def get_internal_user_id(telegram_user_id: int):
    key = f"tg2int:{telegram_user_id}"
    val = await redis.get(key)
    return int(val) if val else None

async def get_telegram_user_id(internal_user_id: int):
    key = f"int2tg:{internal_user_id}"
    val = await redis.get(key)
    return int(val) if val else None

async def update_ttl(telegram_user_id: int, ttl: int = TTL_SECONDS):
    key = f"tg2int:{telegram_user_id}"
    await redis.expire(key, ttl)

async def get_or_restore_internal_user_id(state, telegram_user_id):
    data = await state.get_data()
    user_id = data.get('internal_user_id')
    if user_id:
        logging.info(f"[get_or_restore_internal_user_id] Found user_id in state: {user_id}")
        return user_id
    # Пробуем восстановить из Redis
    user_id = await get_internal_user_id(telegram_user_id)
    if user_id:
        # Проверяем, есть ли такой пользователь в БД
        async with AsyncSessionLocal() as session:
            user = await session.execute(select(User).where(User.id == user_id))
            user = user.scalar()
            if user:
                logging.info(f"[get_or_restore_internal_user_id] Found user_id in Redis and DB: {user_id}")
                await state.update_data(internal_user_id=user_id)
                return user_id
            else:
                logging.warning(f"[get_or_restore_internal_user_id] user_id from Redis not found in DB: {user_id}")
                # Удаляем устаревшие mapping-и
                await redis.delete(f"tg2int:{telegram_user_id}")
                await redis.delete(f"int2tg:{user_id}")
    # Если не найден — создать нового пользователя и обновить Redis
    async with AsyncSessionLocal() as session:
        user = User()
        session.add(user)
        await session.flush()
        await session.commit()
        logging.info(f"[get_or_restore_internal_user_id] Created new user: id={user.id}")
        user_id = user.id
        await set_telegram_mapping(telegram_user_id, user_id)
        await state.update_data(internal_user_id=user_id)
        return user_id 