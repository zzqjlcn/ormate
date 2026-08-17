---
title: 从安装到第一次查询
description: 安装 ormate，定义 SQLAlchemy 模型，并完成第一次异步 Repository 查询。
kicker: QUICKSTART
order: 1
---

核心包只依赖 SQLAlchemy。SQLite、SQLModel、PostgreSQL、MySQL、Elasticsearch 和 Web 集成通过 extras 按需安装。

```bash
pip install ormate
pip install "ormate[sqlite]"
pip install "ormate[sqlmodel]"
pip install "ormate[postgresql]"
pip install "ormate[mysql]"
pip install "ormate[elasticsearch]"
pip install "ormate[web]"
```

## 定义模型

存储模型继续使用标准 SQLAlchemy 声明。ReadModel 可以使用 Pydantic，并且需要提供 `model_validate()`。

```python
from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]


class UserRead(BaseModel):
    id: int
    name: str
```

## 创建 Repository

```python
from ormate import AsyncDatabase, ModelRepository, SQLAlchemyAdapter

db = AsyncDatabase.create("sqlite+aiosqlite:///app.db")
users = ModelRepository(SQLAlchemyAdapter(db), User, UserRead)

async with db.engine.begin() as connection:
    await connection.run_sync(Base.metadata.create_all)

created = await users.add({"id": 1, "name": "Ada"})
loaded = await users.get(1)
updated = await users.update_by_id(1, {"name": "Grace"})
deleted = await users.remove_by_id(1)
```

> 配置 ReadModel 时返回 ReadModel；不配置时直接返回底层存储模型。

## 输入对象

Create 和 Update 参数可以是普通字典，也可以是实现了 `model_dump(exclude_unset=True)` 的 Pydantic 或 SQLModel 对象。

```python
class UserCreate(BaseModel):
    id: int
    name: str


created = await users.add(UserCreate(id=1, name="Ada"))
```
