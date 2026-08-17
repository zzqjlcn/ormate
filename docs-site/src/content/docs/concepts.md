---
title: 三层职责，保持边界清晰
description: 理解 ModelRepository、StorageAdapter 和 Database 如何协作而不隐藏后端能力。
kicker: CONCEPTS
order: 2
---

ormate 将仓储操作拆成三层，每层只处理一个明确问题。

## ModelRepository

Repository 是业务代码使用的公共入口，负责：

- 统一常用 CRUD 语义；
- 将 Mapping 或 Pydantic/SQLModel 输入转换为存储值；
- 调用 `encode_for_storage()` 与 `decode_from_storage()`；
- 根据 ReadModel 构建字段投影和返回对象。

## StorageAdapter

Adapter 负责把公共操作落实到具体存储：

- 编译结构化查询 DSL；
- 创建、读取、更新和删除底层对象；
- 解析主键条件与存储名称；
- 保留后端原生查询和执行入口。

## Database 或原生客户端

SQLAlchemy Adapter 通过 `Database` 或 `AsyncDatabase` 管理 Session 与事务。Elasticsearch Adapter 使用官方异步客户端，并保持 ES 自身的一致性语义。

## 可移植边界

结构化 DSL 使用存储字段名作为跨后端边界，适合常见过滤、统计、更新和删除。

原生能力不会被抽象隐藏：

- SQL JOIN 和复杂 Select 使用 SQLAlchemy 表达式；
- Elasticsearch 全文评分、nested、geo 和聚合使用原生 Query DSL；
- 自定义命令通过 `execute()` 进入底层实现。
