from typing import Any

from pydantic import BaseModel
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    secret: Mapped[str] = mapped_column(String(100))

    @classmethod
    def encode_for_storage(cls, values: dict[str, Any]) -> dict[str, Any]:
        values = dict(values)
        if "secret" in values:
            values["secret"] = values["secret"][::-1]
        return values


class UserCreate(BaseModel):
    id: int
    name: str
    secret: str


class UserUpdate(BaseModel):
    name: str | None = None
    secret: str | None = None


class UserRead(BaseModel):
    id: int
    name: str
    secret: str

    @classmethod
    def decode_from_storage(cls, values: dict[str, Any]) -> dict[str, Any]:
        values = dict(values)
        values["secret"] = values["secret"][::-1]
        return values

