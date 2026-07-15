from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from ormate import Database


class Base(DeclarativeBase):
    pass


class Note(Base):
    __tablename__ = "notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str]


db = Database.create("sqlite:///notes.db")
Base.metadata.create_all(db.engine)
with db as session:
    # Database 同时适用于原生 SQLAlchemy 和 SQLModel 表模型。
    session.add(Note(id=1, text="hello"))
db.close()
