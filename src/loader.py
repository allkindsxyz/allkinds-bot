# ---
# Bot versioning for user state compatibility
#
# - VERSION (from VERSION file) — string that should ONLY be increased for breaking changes (FSM changes, state, incompatible updates).
# - For regular deploys (fixes, UI, texts not affecting state) DON'T change version — users won't see notification and won't be forced to /start.
# - If version changed — users will see restart message and can't use bot until they press /start.
# - Mechanism is fully under your control: change VERSION only if really need state reset for all users.
# ---
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