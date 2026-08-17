---
title: 事务跟随执行上下文
description: 在同步线程和 asyncio.Task 中安全地复用、隔离或显式绑定 Session。
kicker: TRANSACTIONS
order: 6
---

作用域正常退出时提交，发生异常时回滚。同步代码使用 `Database` 与 `with db:`，异步代码使用 `AsyncDatabase` 与 `async with db:`。

## 普通作用域

同一线程或 `asyncio.Task` 内的嵌套作用域复用当前 Session。新的 Task 即使继承了 ContextVar，也会自动创建独立 Session。

```python
async def worker(item):
    async with db:
        await tasks.add(item)


await asyncio.gather(worker(item1), worker(item2))
```

每个 worker 独立提交或回滚，不会并发操作同一个 AsyncSession。

## 强制新事务

`new_session()` 用于在同一个 Task 内创建独立短事务。

```python
async with db as parent:
    async with db.new_session() as independent:
        assert independent is not parent
```

## 显式复用

`reuse_session(session)` 绑定一个已有 Session，但 ormate 不提交或关闭它。

```python
async with db as session:
    async with db.reuse_session(session):
        await tasks.add({"title": "same transaction"})
```

> 跨 Task 并发复用同一个 AsyncSession 不受 SQLAlchemy 支持。

## 切断上下文继承

手动创建并跨生命周期传递的后台任务可以在入口使用 `detached()`。

```python
async def run_background_job(job):
    async with db.detached():
        await process(job)
```

`detached()` 只临时隐藏并恢复当前 Session，不负责创建、提交或关闭 Session。
