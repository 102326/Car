# 🏗️ CDC 数据同步架构设计说明书 (Architecture Decision Record)

> **状态**: 生产就绪 (Pro Max)
> **最后更新**: 2026-01-21
> **核心组件**: PostgreSQL (Source) -> Debezium -> Kafka -> CDC Consumer (Python) -> Elasticsearch (Sink)

## 1. 核心设计原则 (Core Principles)

### 1.1 唯一事实来源 (Source of Truth)

* **原则**: **数据库 (PostgreSQL) 是唯一的真理。**
* **推论**:
  * ES 中的任何数据都必须能在 DB 中找到对应。
  * **"查不到即删除"策略**: 在同步过程中，如果 Consumer 收到变更信号但反查数据库为空，**必须** 视为该数据已被物理删除，并立即从 ES 中移除。
  * **禁止**: 禁止在 Consumer 中通过 Kafka 消息体直接拼装数据（必须回查 DB），以防止 Kafka 消息乱序导致的数据回滚。

### 1.2 最终一致性 (Eventual Consistency)

* 本系统保证 **At-Least-Once (至少一次)** 投递。
* 利用 ES 的 `Upsert` (覆盖写) 特性实现幂等性。
* 允许在毫秒到秒级的延迟下，ES 数据与 DB 存在短暂不一致。

---

## 2. 关键组件边界 (Component Boundaries)

### 2.1 智能缓冲区 (SmartBuffer)

* **定位**: **业务级 CDC 消费器**，而非通用流处理框架。
* **职责**:
  1. **流量削峰**: 缓冲短时间内的突发变更。
  2. **关联聚合**: 将 Brand/Series 的变更解析为具体的 Car ID 列表。
  3. **流控 (Backpressure)**: 当缓冲池达到 `HARD_LIMIT` (如 5000) 时，主动暂停 Kafka 拉取，防止 OOM。
* **非职责**: 不处理复杂的窗口计算，不处理跨 Topic 的事务。

### 2.2 错误处理与死信 (DLQ)

* **当前实现 (MVP)**:
  * **重试**: 内存级重试队列，最大重试 3 次。
  * **死信**: 超过重试次数后，记录 `ERROR` 级别日志，并丢弃数据。
* **演进路线**:
  * 未来应升级为 **Kafka DLQ Topic** 或 **DB 异常表**，以便进行自动化重放。
  * *目前严禁在无人工介入下无限重试，防止阻塞消费队列。*

---

## 3. 风险与规约 (Risks & Contracts)

### 3.1 关联反查风暴

* **风险**: 修改一个热门品牌（如“大众”），可能关联数万个车型，导致反查 SQL 拖垮主库。
* **防御**: 代码中强制实施了 **Chunking (切片)** 策略，所有 `IN (...)` 查询限制为每批次 500 个 ID。
* **规约**: 严禁移除 `_batch_resolve_events` 中的切片逻辑。

### 3.2 离线兜底

* CDC 系统不是完美的。在发生 Kafka 消息丢失（极低概率）或代码逻辑 Bug 时，数据可能永久不一致。
* **兜底方案**: 必须保留 `app/jobs/full_sync_es.py` 全量同步脚本。建议每周或每月低峰期执行一次全量校准。

---

## 4. 运维操作指南 (Ops Guide)

* **启动**: `python -m app.consumers.cdc_sync`
* **监控**: 重点监控日志中的 `ERROR` (死信) 和 `WARNING` (Buffer 积压/暂停)。
* **紧急停止**: 直接 Kill 进程。重启后会从上次提交的 Offset 继续消费（可能会有少量重复写入，ES 可自动去重）。
