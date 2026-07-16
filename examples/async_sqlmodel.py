import asyncio

from sqlmodel import Field, SQLModel

from ormate import AsyncDatabase, ModelRepository, SQLModelAdapter


class NoteRead(SQLModel):
    id: int
    text: str


class Note(SQLModel, table=True):
    __tablename__ = "notes"

    id: int | None = Field(default=None, primary_key=True)
    text: str


async def main() -> None:
    db = AsyncDatabase.create("sqlite+aiosqlite:///notes.db")
    async with db.engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)
    adapter = SQLModelAdapter(db)
    notes = ModelRepository(adapter, Note, NoteRead)

    async with db:
        await notes.add({"text": "first"})
        await notes.add({"text": "second"})

    print(await notes.find())
    await db.dispose()


if __name__ == "__main__":
    asyncio.run(main())
