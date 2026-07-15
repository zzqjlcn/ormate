from typing import TYPE_CHECKING, Any

from .database import AsyncDatabase, Database

if TYPE_CHECKING:
    from ormate.adapters.sqlalchemy import SQLAlchemyAdapter

__all__ = ["AsyncDatabase", "Database", "SQLAlchemyAdapter"]


def __getattr__(name: str) -> Any:
    if name == "SQLAlchemyAdapter":
        from ormate.adapters.sqlalchemy import SQLAlchemyAdapter

        return SQLAlchemyAdapter
    raise AttributeError(name)
