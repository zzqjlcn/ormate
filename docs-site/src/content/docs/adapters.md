---
title: 通过一个协议接入新存储
description: 实现 StorageAdapter，复用 Repository 的转换、投影和公共仓储语义。
kicker: CUSTOM ADAPTERS
order: 10
---

`StorageAdapter` 是 `ModelRepository` 与具体存储后端之间的运行时协议。

## 协议方法

实现需要提供：

- `storage_name`
- `add`
- `find`
- `update`
- `remove`
- `count`
- `exists`
- `primary_key_query`
- `primary_keys_query`
- `execute`

```python
repository = ModelRepository(
    custom_adapter,
    CustomStorageModel,
    CustomReadModel,
)
```

## 职责边界

Adapter 应负责：

- 执行具体存储操作；
- 编译该后端支持的查询语法；
- 处理主键条件；
- 提供底层存储名称；
- 执行后端原生命令。

Repository 会继续负责输入转换、ReadModel 构造和字段投影。

## 不要伪造可移植性

新 Adapter 只需要实现公共协议，不需要模拟不适合该存储的能力。例如 Elasticsearch 不应模拟 SQL JOIN，SQL Adapter 也不应模拟全文评分语义。
