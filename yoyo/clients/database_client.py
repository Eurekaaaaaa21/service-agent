import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, async_sessionmaker, AsyncSession

from yoyo.conf.config import settings

engine: AsyncEngine | None = None
session_factory: async_sessionmaker[AsyncSession] | None = None


def init_database():
    global engine, session_factory
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def close_database():
    if engine:
        await engine.dispose()


if __name__ == '__main__':
    init_database()


    async def test():
        async with session_factory() as session:
            result = await session.execute(text("select 1"))
            print(result.fetchall())

        await close_database()


    asyncio.run(test())
