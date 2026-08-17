---
title: 一套紧凑的仓储语义
description: ModelRepository 提供创建、查询、更新、删除、统计和原生执行接口。
kicker: REPOSITORY API
order: 3
---

写入方法接受 Mapping 或实现 `model_dump(exclude_unset=True)` 的对象。读取结果根据是否配置 ReadModel 决定返回类型。

## 方法总览

| 类别 | 方法 | 用途 |
| --- | --- | --- |
| Create | `add`、`add_many` | 创建一项或批量创建 |
| Read | `find`、`find_one`、`get`、`get_many` | 条件与主键读取 |
| Update | `update`、`update_by_id`、`update_many` | 显式条件更新 |
| Delete | `remove`、`remove_by_id`、`remove_many` | 显式条件删除 |
| Inspect | `count`、`exists`、`storage_name` | 统计与存储信息 |
| Native | `execute` | 执行后端原生命令 |

## 查询与分页

```python
users = await repository.find(User.name.contains("Ada"), limit=20)
first = await repository.find_one(User.active.is_(True))
total = await repository.count(User.active.is_(True))
exists = await repository.exists(User.email == email)
```

`limit` 和 `offset` 不能为负数；`limit=0` 固定返回空列表。

## 安全更新与删除

`update()` 和 `remove()` 必须显式提供查询条件，避免遗漏参数时修改全部记录。

```python
from ormate import and_, eq

await repository.update(eq("status", "draft"), {"status": "review"})
await repository.remove(eq("status", "expired"))

# 明确匹配全部记录
await repository.update(and_(), {"status": "archived"})
```

空更新对象和未知存储字段会立即抛出 `ValueError`。

## 原生命令

```python
result = await repository.execute(statement, params={"status": "active"})
```

原生命令不承诺跨 Adapter 可移植，应当只用于明确的后端能力。
