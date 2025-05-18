import os
import logging
import asyncio
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from src.loader import bot, dp
from src.routers import all_routers

# Регистрация всех роутеров
for router in all_routers:
    dp.include_router(router)

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8000))

async def on_startup(app):
    print(f"[INFO] Setting webhook: {WEBHOOK_URL}")
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(app):
    print("[INFO] Shutting down webhook")
    await bot.delete_webhook()

def create_app():
    app = web.Application()
    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    ).register(app, path=WEBHOOK_PATH)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    setup_application(app, dp, bot=bot)
    return app

async def main():
    logging.basicConfig(level=logging.INFO)
    if WEBHOOK_URL:
        print(f"[INFO] Starting bot in WEBHOOK mode: {WEBHOOK_URL}")
        app = create_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()
        print(f"[INFO] Webhook server started on port {PORT}")
        while True:
            await asyncio.sleep(3600)
    else:
        print("[INFO] Starting bot in POLLING mode (no WEBHOOK_URL set)...")
        await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"[FATAL] Unhandled exception: {e}")
        logging.exception(e) 