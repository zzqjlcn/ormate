---
title: 共享 SQLAlchemy 的事务基础
description: SQLModelAdapter 与 SQLAlchemyAdapter 使用相同的 Session、事务和查询实现。
kicker: SQLMODEL
order: 7
---

`SQLModelAdapter` 继承 `SQLAlchemyAdapter`。它是一个明确的语义入口，不干预 SQLModel 业务模型的基础字段定义。

## 安装

```bash
pip install "ormate[sqlmodel]"
```

## 共享事务

绑定到同一个 Database 后，SQLAlchemy 和 SQLModel 的操作可以放在同一个事务中。

```python
from ormate import ModelRepository, SQLAlchemyAdapter, SQLModelAdapter

audit_logs = ModelRepository(SQLAlchemyAdapter(db), AuditLog)
tasks = ModelRepository(SQLModelAdapter(db), Task)

async with db:
    await audit_logs.add({"id": 1, "message": "task created"})
    await tasks.add({"title": "publish package"})
```

任一操作抛出异常时，外层作用域会回滚同一个事务。

## 结构化查询

SQLModel 映射字段可以直接用于 ormate DSL：

```python
active_tasks = await tasks.find(eq(Task.active, True))
```

复杂 SQL 查询仍可以直接传递 SQLAlchemy Select。
