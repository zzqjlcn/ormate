---
title: 只读取验证真正需要的字段
description: 让 ReadModel 驱动普通读取的字段投影，并正确处理验证与序列化别名。
kicker: READMODEL PROJECTION
order: 5
---

配置 ReadModel 后，`find`、`find_one`、`get` 和 `get_many` 只查询模型验证需要的字段。创建、更新、删除以及未配置 ReadModel 的查询仍读取完整存储对象。

## 验证与序列化别名

```python
from pydantic import BaseModel, Field


class UserRead(BaseModel):
    display_name: str = Field(
        validation_alias="name",
        serialization_alias="displayName",
    )
```

这个模型从底层读取 `name`，执行 `model_dump(by_alias=True)` 时输出 `displayName`。

| 配置 | 行为 |
| --- | --- |
| `validation_alias` | 用于推断底层存储字段 |
| `serialization_alias` | 只控制对外序列化名称 |
| 普通 `alias` | 同时用于验证和序列化 |
| `AliasChoices` | 选择第一个存在的纯字符串候选字段 |
| `AliasPath` | SQL 与 ES 路径语义不同，不自动投影 |

## 自定义转换

存储模型可以提供 `encode_for_storage()`，ReadModel 可以提供 `decode_from_storage()`，用于处理公共 Repository 边界之外的值转换。
