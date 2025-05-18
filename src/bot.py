import asyncio
import os
from src.loader import bot, dp
from src.routers import all_routers
import logging

# Регистрация всех роутеров
for router in all_routers:
    dp.include_router(router)

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

async def main():
    logging.basicConfig(level=logging.INFO)
    if WEBHOOK_URL:
        print(f"[INFO] Starting bot in WEBHOOK mode: {WEBHOOK_URL}")
        await bot.set_webhook(WEBHOOK_URL)
        try:
            await dp.start_webhook(
                webhook_path=WEBHOOK_PATH,
                on_startup=None,
                on_shutdown=None,
                skip_updates=True,
                host="0.0.0.0",
                port=int(os.getenv("PORT", 8000)),
            )
        except Exception as e:
            print(f"[ERROR] Bot failed to start in webhook mode: {e}")
            logging.exception(e)
    else:
        print("[INFO] Starting bot in POLLING mode (no WEBHOOK_URL set)...")
        try:
            await dp.start_polling(bot)
        except Exception as e:
            print(f"[ERROR] Bot failed to start in polling mode: {e}")
            logging.exception(e)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"[FATAL] Unhandled exception: {e}")
        logging.exception(e) 