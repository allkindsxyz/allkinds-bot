# ---
# Bot versioning for user state compatibility
#
# - VERSION (from VERSION file) — это строка, которую нужно увеличивать ТОЛЬКО при breaking changes (изменения FSM, state, несовместимые обновления).
# - При обычных деплоях (фиксы, UI, тексты, не влияющие на state) НЕ меняй версию — пользователи не увидят уведомление и не будут вынуждены делать /start.
# - Если версия изменилась — пользователи увидят сообщение о необходимости рестарта и не смогут пользоваться ботом, пока не нажмут /start.
# - Механизм полностью под твоим контролем: меняй VERSION только если реально требуется сброс state у всех пользователей.
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