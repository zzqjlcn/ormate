import asyncio

from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from ormate import AsyncDatabase, ModelRepository, SQLAlchemyAdapter


class Base(DeclarativeBase):
    pass


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str]


class NoteRead(BaseModel):
    id: int
    text: str


async def main() -> None:
    db = AsyncDatabase.create("sqlite+aiosqlite:///notes.db")
    async with db.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    notes = ModelRepository(SQLAlchemyAdapter(db), Note, NoteRead)
    async with db:
        await notes.create_item({"id": 1, "text": "first"})
        await notes.create_item({"id": 2, "text": "second"})

    print(await notes.read_items())
    await db.dispose()


if __name__ == "__main__":
    asyncio.run(main())

