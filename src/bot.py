import asyncio
from src.loader import bot, dp
from src.routers import all_routers
import logging

# Регистрация всех роутеров
for router in all_routers:
    dp.include_router(router)

async def main():
    logging.basicConfig(level=logging.INFO)
    print("[INFO] Bot is starting...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"[ERROR] Bot failed to start: {e}")
        logging.exception(e)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"[FATAL] Unhandled exception: {e}")
        logging.exception(e) 