# Changelog

## 0.1.2a1 - 2026-08-13

- 提供同步和异步 SQLAlchemy 会话作用域。
- 提供基于 `StorageAdapter` 的统一 `ModelRepository`。
- 提供 `SQLAlchemyAdapter`，SQLAlchemy 与 SQLModel 表模型共享同一套接口。
- 提供直接继承 `SQLAlchemyAdapter` 的 `SQLModelAdapter` 语义入口，不干预业务模型的基础字段定义。
- 通过 Adapter 的 `storage_name()` 统一解析 SQL 表名与 Elasticsearch 索引名。
- 提供可选 `ElasticsearchAdapter` 与 `ElasticsearchDocument`，支持原生 Query DSL、全文检索入口和聚合。
- Elasticsearch 写入使用异步 streaming bulk，支持分块、大小限制、429 指数退避重试和批次后 refresh。
- 支持独立 Create、Update、Read 模型、批量主键操作、复合主键、计数和存在性检查。
- Repository 使用 `add`、`find`、`get`、`update`、`remove` 等仓储语义 API。
- ReadModel 普通读取按字段和 `validation_alias` 自动投影，并区分 `serialization_alias`。
- 提供可编译到 SQLAlchemy、SQLModel 和 Elasticsearch 的结构化过滤 DSL，同时保留原生查询。
- 增加结构化查询 DSL 的完整可运行示例。
- 会话作用域在不同线程和 `asyncio.Task` 之间自动隔离，同时支持显式 `reuse_session()`、`new_session()` 和 `detached()`。
- ASGI 中间件只管理 HTTP 请求，并在最终响应体发送后、后台任务运行前结束请求事务。
- 更新和删除要求显式查询条件，更新字段、空更新对象及分页参数会被严格校验。
- 增加 Windows/Linux CI、构建和发行元数据检查。
- 提供数据库驱动 extras。
