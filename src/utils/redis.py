import redis.asyncio as aioredis
import os

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
        return user_id
    # Пробуем восстановить из Redis
    user_id = await get_internal_user_id(telegram_user_id)
    if user_id:
        await state.update_data(internal_user_id=user_id)
        return user_id
    return None 