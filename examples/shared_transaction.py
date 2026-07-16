import asyncio

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlmodel import Field, SQLModel

from ormate import AsyncDatabase, ModelRepository, SQLAlchemyAdapter, SQLModelAdapter


class Base(DeclarativeBase):
    pass


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    message: Mapped[str]


class Task(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str


async def main() -> None:
    db = AsyncDatabase.create("sqlite+aiosqlite:///shared.db")
    async with db.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.run_sync(SQLModel.metadata.create_all)

    audit_logs = ModelRepository(SQLAlchemyAdapter(db), AuditLog)
    tasks = ModelRepository(SQLModelAdapter(db), Task)

    # 两种表模型共享同一个 AsyncSession：全部成功时一起提交，任一异常时全部回滚。
    async with db:
        await tasks.add({"title": "publish package"})
        await audit_logs.add({"id": 1, "message": "task created"})

    await db.dispose()


if __name__ == "__main__":
    asyncio.run(main())
