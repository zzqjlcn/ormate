# Changelog

## 0.1.0 - Unreleased

- 提供同步和异步 SQLAlchemy 会话作用域。
- 提供基于 `StorageAdapter` 的统一 `ModelRepository`。
- 提供 `SQLAlchemyAdapter`，SQLAlchemy 与 SQLModel 表模型共享同一套接口。
- 提供直接继承 `SQLAlchemyAdapter` 的 `SQLModelAdapter` 语义入口，不干预业务模型的基础字段定义。
- 通过 Adapter 的 `storage_name()` 统一解析 SQL 表名与 Elasticsearch 索引名。
- 提供可选 `ElasticsearchAdapter` 与 `ElasticsearchDocument`，支持原生 Query DSL、全文检索入口和聚合。
- 支持独立 Create、Update、Read 模型、批量主键操作、复合主键、计数和存在性检查。
- 提供并发安全的会话作用域、ASGI 中间件和数据库驱动 extras。
