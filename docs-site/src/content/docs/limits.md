---
title: 清楚知道边界，才能放心采用
description: 了解 ormate 0.1.x Alpha 的当前限制、测试覆盖和后续演进方向。
kicker: STATUS & ROADMAP
order: 11
---

ormate 当前处于 `0.1.x Alpha`，API 在 1.0 前仍可能调整。

## 当前限制

1. PostgreSQL、MySQL 和真实 Elasticsearch 集群尚未加入自动化集成测试。
2. Elasticsearch 条件批量更新和删除受 `default_size` 限制，默认最多处理 1000 个匹配文档。
3. ES mapping 迁移、PIT/search_after 和乐观并发控制尚未实现。
4. 不提供 SQL 与 Elasticsearch 之间的分布式事务。

## 0.2

完善 Elasticsearch：

- PIT/search_after 深分页；
- 索引 mapping 管理；
- 并发冲突处理；
- 真实 Elasticsearch 集群测试。

## 0.3

完善关系型数据库：

- PostgreSQL/MySQL 测试矩阵；
- 分页结果类型；
- 显式 savepoint API；
- 批量性能优化。

## 走向 1.0

在 1.0 前冻结公共 API，补齐迁移指南、Adapter 契约测试工具和性能基准。路线图表示开发方向，不承诺具体发布日期。
