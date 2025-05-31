from aiogram import Bot, Dispatcher
from src.config import BOT_TOKEN
import os
import redis.asyncio as aioredis

VERSION = None
try:
    with open(os.path.join(os.path.dirname(__file__), '../VERSION')) as f:
        VERSION = f.read().strip()
except Exception:
    VERSION = 'dev'

REDIS_URL = os.getenv("REDIS_PUBLIC_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
redis = aioredis.from_url(REDIS_URL, decode_responses=True)

async def set_bot_version():
    if VERSION:
        await redis.set('bot_version', VERSION)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher() 