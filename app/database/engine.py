from sqlalchemy import QueuePool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from config import settings
from app.database.models import Base


engine = create_async_engine(
    settings.database_url,
    pool_size=20,  # Максимальное количество соединений в пуле
    max_overflow=10,  # Дополнительные соединения при переполнении
    pool_timeout=30,  # Тайм-аут ожидания соединения (в секундах)
    pool_pre_ping=True,  # Проверка соединения перед использованием
    echo=False,  # Отключение логирования SQL-запросов
    query_cache_size = 500
)

session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)




async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)