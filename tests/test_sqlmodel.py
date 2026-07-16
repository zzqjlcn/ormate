from sqlmodel import Field, SQLModel

from ormate import ModelRepository, SQLAlchemyAdapter, SQLModelAdapter, eq
from tests.models import User


class ItemRead(SQLModel):
    id: int
    name: str


class Item(SQLModel, table=True):
    __tablename__ = "items"

    id: int | None = Field(default=None, primary_key=True)
    name: str


def test_sqlmodel_adapter_inherits_sqlalchemy_adapter():
    assert issubclass(SQLModelAdapter, SQLAlchemyAdapter)


async def test_sqlmodel_table_uses_unified_repository(async_db):
    async with async_db.engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)
    repository = ModelRepository(SQLModelAdapter(async_db), Item, ItemRead)
    assert repository.storage_name == "items"
    created = await repository.add({"name": "SQLModel"})
    assert created.name == "SQLModel"
    assert (await repository.get(created.id)).name == "SQLModel"
    assert (await repository.find(eq("name", "SQLModel")))[0].id == created.id


async def test_sqlmodel_and_sqlalchemy_share_one_transaction(async_db, async_adapter):
    async with async_db.engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)
    items = ModelRepository(SQLModelAdapter(async_db), Item)
    users = ModelRepository(async_adapter, User)

    try:
        async with async_db:
            await items.add({"name": "SQLModel"})
            await users.add({"id": 1, "name": "SQLAlchemy", "secret": "x"})
            raise RuntimeError("rollback both")
    except RuntimeError:
        pass

    assert await items.count() == 0
    assert await users.count() == 0
