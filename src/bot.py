import asyncio
from src.loader import bot, dp
from src.routers import all_routers

# Регистрация всех роутеров
for router in all_routers:
    dp.include_router(router)

async def main():
    import logging
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 