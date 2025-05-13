import sys
import os
# Добавляем src и корень проекта в sys.path для универсального импорта
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC_PATH = os.path.join(PROJECT_ROOT, 'src')
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# Это гарантирует, что тесты можно запускать из любой директории, без необходимости выставлять PYTHONPATH вручную

import pytest
import pytest_asyncio
import asyncio
from testcontainers.postgres import PostgresContainer
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.models import Base

@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Создаёт новый event loop для сессии тестов (совместимо с pytest-asyncio >= 0.21)."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def pg_url():
    with PostgresContainer("postgres:15") as pg:
        url = pg.get_connection_url()
        url = url.replace('postgresql://', 'postgresql+asyncpg://')
        url = url.replace('postgresql+psycopg2://', 'postgresql+asyncpg://')
        print("TEST DB URL:", url)  # для отладки
        yield url

@pytest_asyncio.fixture(scope="function")
async def async_session(pg_url):
    engine = create_async_engine(pg_url, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose() 