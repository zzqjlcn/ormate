---
title: 让常用过滤跨越存储
description: 使用不可变查询节点表达通用条件，并编译到 SQLAlchemy、SQLModel 与 Elasticsearch。
kicker: QUERY DSL
order: 4
---

结构化查询 DSL 覆盖常见比较、集合与布尔组合，同时允许 Repository 继续接受完整的后端原生查询。

## 操作符

`eq` · `ne` · `gt` · `gte` · `lt` · `lte` · `in_` · `not_in` · `and_` · `or_` · `not_`

```python
from ormate import and_, eq, gte, in_, not_, or_

query = and_(
    eq(Product.status, "published"),
    gte(Product.created_at, start_time),
    or_(
        in_(Product.category, ["guide", "reference"]),
        not_(eq(Product.hidden, True)),
    ),
)

items = await products.find(query, limit=20)
total = await products.count(query)
```

## 字段写法

字段可以写成底层存储字段名，也可以使用 SQLAlchemy/SQLModel 映射字段。

```python
eq("active", True)
eq(Product.active, True)
```

映射字段会在构造表达式时归一化为存储字段名，因此 DSL AST 不持有 SQLAlchemy 对象。

## 空组合语义

| 表达式 | 固定语义 |
| --- | --- |
| `and_()` | 恒真 |
| `or_()` | 恒假 |
| `in_("id", [])` | 恒假 |
| `not_in("id", [])` | 恒真 |

`and_`、`or_` 和 `not_` 只接受 ormate DSL 节点。不要在同一个 DSL 节点内混入 SQLAlchemy 表达式或 ES 字典。
