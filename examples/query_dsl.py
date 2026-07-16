import asyncio

from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from ormate import (
    AsyncDatabase,
    ModelRepository,
    SQLAlchemyAdapter,
    and_,
    eq,
    gt,
    gte,
    in_,
    ne,
    not_,
    not_in,
    or_,
)


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    category: Mapped[str]
    price: Mapped[int]
    active: Mapped[bool]


class ProductRead(BaseModel):
    id: int
    name: str
    category: str
    price: int
    active: bool


async def main() -> None:
    db = AsyncDatabase.create("sqlite+aiosqlite:///query_dsl.db")
    async with db.engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    products = ModelRepository(SQLAlchemyAdapter(db), Product, ProductRead)
    async with db:
        await products.add_many(
            [
                {"id": 1, "name": "Python Guide", "category": "book", "price": 80, "active": True},
                {"id": 2, "name": "SQL Reference", "category": "book", "price": 120, "active": True},
                {"id": 3, "name": "Legacy Notes", "category": "archive", "price": 20, "active": False},
            ]
        )

    # 比较、集合与嵌套布尔组合。
    visible = and_(
        eq(Product.active, True),
        gte(Product.price, 50),
        or_(in_(Product.category, ["book", "course"]), not_(eq(Product.category, "archive"))),
    )
    print("visible:", await products.find(visible))

    # 同一个 DSL 可以用于 find、count、exists、update 和 remove。
    expensive = gt(Product.price, 100)
    print("expensive count:", await products.count(expensive))
    print("has non-archive:", await products.exists(not_in(Product.category, ["archive"])))
    print("discounted:", await products.update(expensive, {"price": 99}))
    print("removed:", await products.remove(and_(eq(Product.active, False), ne(Product.category, "book"))))

    # 后端原生查询仍可直接传入，但不与 DSL 节点混合。
    print("native query:", await products.find(Product.name.contains("Guide")))
    await db.dispose()


if __name__ == "__main__":
    asyncio.run(main())
