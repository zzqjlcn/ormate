import pytest_asyncio

from ormate import AsyncDatabase, Database, SQLAlchemyAdapter
from tests.models import Base


@pytest_asyncio.fixture
async def async_db(tmp_path):
    db = AsyncDatabase.create(f"sqlite+aiosqlite:///{tmp_path / 'async.db'}")
    async with db.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield db
    await db.dispose()


@pytest_asyncio.fixture
async def async_adapter(async_db):
    return SQLAlchemyAdapter(async_db)


@pytest_asyncio.fixture
async def sync_db(tmp_path):
    db = Database.create(f"sqlite:///{tmp_path / 'sync.db'}")
    Base.metadata.create_all(db.engine)
    yield db
    await db.dispose()


@pytest_asyncio.fixture
async def sync_adapter(sync_db):
    return SQLAlchemyAdapter(sync_db)
