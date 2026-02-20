# Elasticsearch 架构设计文档

> **版本**: 2026-01-29  
> **项目**: CarFast AI OS

## 1. 概述

本项目使用 **Elasticsearch (ES)** 作为主要的搜索引擎，承载车辆库存的全文检索、结构化筛选和聚合统计功能。ES 层设计遵循以下核心原则：

- **Stateless API**: 搜索请求链路完全绕过 PostgreSQL，实现极致低延迟。
- **Write-Through**: 数据变更通过 CDC 或脚本批量同步至 ES，保持最终一致性。
- **Agent 可调用**: 搜索能力已封装为 LangChain Tool，供 AI Agent 直接调用。

---

## 2. 核心架构

```
┌─────────────┐     ┌─────────────┐     ┌───────────────────────┐
│   Frontend  │────►│  FastAPI    │────►│  Elasticsearch        │
│  (Vue.js)   │     │  /search    │     │  (pylab_cars_v1)      │
└─────────────┘     └──────┬──────┘     └───────────────────────┘
                           │                      ▲
                           │                      │
                    ┌──────▼──────┐        ┌──────┴──────┐
                    │ JWT 解析    │        │   CDC Sync  │
                    │ (Stateless) │        │   (Celery)  │
                    └─────────────┘        └─────────────┘
                                                  ▲
                                                  │
                                           ┌──────┴──────┐
                                           │ PostgreSQL  │
                                           │ (car_model) │
                                           └─────────────┘
```

---

## 3. 代码结构

| 文件路径                      | 职责                             |
| ----------------------------- | -------------------------------- |
| `app/core/es.py`              | ES 客户端单例 (Lazy Loading)     |
| `app/services/es_service.py`  | 索引管理 + 批量写入 + Pro 级搜索 |
| `app/api/v1/search.py`        | HTTP 搜索入口 (纯 ES I/O)        |
| `app/schemas/search.py`       | 请求参数 Schema (Pydantic)       |
| `app/utils/search_tool.py`    | LangChain Tool 封装 (Agent 调用) |
| `app/jobs/reset_index_pro.py` | 索引重建脚本 (3 分片集群版)      |
| `app/jobs/clean_sync.py`      | 全量同步脚本 (PG → ES)           |

---

## 4. 索引设计 (`pylab_cars_v1`)

### 4.1 Mapping 定义

```json
{
  "properties": {
    "id": { "type": "integer" },
    "name": {
      "type": "text",
      "analyzer": "ik_max_word",
      "search_analyzer": "ik_smart"
    },
    "brand_name": { "type": "keyword" },
    "series_name": { "type": "keyword" },
    "series_level": { "type": "keyword" },
    "energy_type": { "type": "keyword" },
    "price": { "type": "double" },
    "year": { "type": "keyword" },
    "status": { "type": "integer" },
    "tags_text": { "type": "text", "analyzer": "ik_smart" },
    "updated_at": { "type": "date" }
  }
}
```

### 4.2 设计亮点

| 字段         | 类型      | 用途                             |
| ------------ | --------- | -------------------------------- |
| `name`       | Text + IK | 主搜索字段，支持中文分词         |
| `brand_name` | Keyword   | 精确筛选 + Terms 聚合            |
| `tags_text`  | Text      | 标签模糊匹配 (如 "省油", "家用") |
| `price`      | Double    | Range 区间查询 + 排序            |

### 4.3 集群配置 (生产环境)

```json
{
  "settings": {
    "number_of_shards": 3,
    "number_of_replicas": 0,
    "refresh_interval": "1s"
  }
}
```

- **3 分片**: 激活 `es01`, `es02`, `es03` 节点的并行处理能力。
- **0 副本**: 压测环境追求写入吞吐，生产建议设为 1。

---

## 5. 搜索实现

### 5.1 核心方法: `search_cars_pro()`

**位置**: `app/services/es_service.py`

**功能亮点**:

1. **Bool Query 组合**
   - `must`: Multi-Match 全文检索 (`name^3`, `brand_name^2`, `tags_text`)
   - `filter`: 精确筛选 (品牌/级别/能源/价格区间/上架状态)

2. **智能排序策略**
   - 有关键词: `_score` 相关度优先
   - 无关键词: `id desc` (或可扩展为热度排序)
   - 支持: `price_asc`, `price_desc`, `new`

3. **Facets 聚合**
   - 返回 `brands`, `levels`, `energies` 的 Terms 统计
   - 用于前端侧边栏筛选器渲染

4. **高亮渲染**
   - 使用 Tailwind CSS 兼容的 `<em class='text-red-500'>` 标签

### 5.2 代码片段

```python
body = {
    "query": {
        "bool": {
            "must": [{"multi_match": {"query": q, "fields": ["name^3", "brand_name^2"]}}],
            "filter": [{"term": {"status": 1}}, {"range": {"price": {"gte": 10, "lte": 50}}}]
        }
    },
    "aggs": {
        "brands": {"terms": {"field": "brand_name", "size": 20}}
    },
    "highlight": {"fields": {"name": {}}}
}
```

---

## 6. API 接口

### `POST /api/v1/search/cars`

**特点**: 零 PostgreSQL 压力，纯 ES I/O。

**请求参数** (`SearchParams`):

| 参数                  | 类型   | 说明                                   |
| --------------------- | ------ | -------------------------------------- |
| q                     | string | 搜索关键词                             |
| brand                 | string | 品牌筛选                               |
| min_price / max_price | float  | 价格区间 (万)                          |
| sort_by               | string | default / price_asc / price_desc / new |
| page / size           | int    | 分页参数                               |

**响应结构**:

```json
{
  "code": 200,
  "data": {
    "total": 156,
    "list": [...],
    "facets": {"brands": ["宝马", "奥迪"], "levels": ["SUV"]}
  },
  "meta": {"latency_source": "Elasticsearch Only"}
}
```

---

## 7. Agent 集成

### 7.1 VehicleSearchTool

**位置**: `app/utils/search_tool.py`

**职责**: 将 ES 搜索能力暴露给 LangGraph Agent。

**输入 Schema** (`VehicleSearchInput`):

```python
class VehicleSearchInput(BaseModel):
    query: Optional[str]
    min_price: Optional[int]
    max_price: Optional[int]
    brand: Optional[str]
    tags: Optional[List[str]]
    sort_strategy: Literal["default", "price_lowest", "price_highest", "newest"]
```

**输出格式**: 元认知报告 (Agent 友好)

```
[库存摘要]
共找到 23 辆符合条件的车辆。(仅展示 Top 5)

[精选车源]
- ID:101 | 宝马X3 | 32.5万 | 2024款 中型SUV
- ID:102 | 奥迪Q5L | 38.8万 | 2023款 中型SUV

[交互建议]
当前结果包含多个品牌: 宝马, 奥迪, 奔驰。如果用户未指定品牌，可询问其品牌偏好。
```

---

## 8. 数据同步

### 8.1 全量同步 (`clean_sync.py`)

**流程**:

1. 从 PostgreSQL 分页读取所有 `CarModel.id`
2. 每批 100 条调用 `fetch_and_assemble_car_docs()` 组装文档
3. 使用 `async_bulk()` 批量写入 ES

**性能指标** (参考):

- 速度: ~500 docs/s (取决于网络和 ES 集群)

### 8.2 增量同步 (CDC)

- 基于 Debezium 或自定义 Binlog 监听
- 变更事件触发 `CarESService.sync_car_doc()` 或 `bulk_sync_cars()`
- 详见 `files/CDC_ARCHITECTURE.md`

### 8.3 索引重建 (`reset_index_pro.py`)

**用途**: 修改 Mapping 或清空脏数据时执行。

```bash
python app/jobs/reset_index_pro.py
```

---

## 9. 优化策略

### 9.1 已实现 ✅

| 优化项         | 说明                           |
| -------------- | ------------------------------ |
| Filter Context | 精确筛选不计算评分，性能更优   |
| Keyword 字段   | 品牌/级别使用 Keyword 加速聚合 |
| Bulk API       | 批量写入减少网络开销           |
| Lazy Client    | 单例模式避免重复创建连接       |
| 404 容错       | 删除不存在的文档不报错         |

### 9.2 待优化 📌

| 优化项      | 预期收益                   |
| ----------- | -------------------------- |
| 热词缓存    | 高频搜索词结果 Redis 缓存  |
| Scroll API  | 超大分页场景替代 from/size |
| 向量搜索    | 语义相似度匹配 (需 ES 8.x) |
| Index Alias | 零停机索引切换             |

---

## 10. 监控与运维

### 10.1 健康检查

```bash
curl http://localhost:9200/_cluster/health?pretty
```

### 10.2 索引状态

```bash
curl http://localhost:9200/pylab_cars_v1/_stats?pretty
```

### 10.3 日志关键词

| 关键词               | 含义                     |
| -------------------- | ------------------------ |
| `✅ ES 索引创建成功` | 索引初始化完成           |
| `❌ [ES] Bulk 失败`  | 批量写入部分失败，需排查 |
| `💥 [ES] 系统级崩溃` | 网络或集群故障           |

---

## 11. 总结

CarFast 的 ES 层实现了从 **被动查询** 到 **主动推荐** 的完整能力闭环：

1. **高性能查询**: 纯 ES I/O 的 Stateless API
2. **电商级筛选**: 多维度 Filter + Facets 聚合
3. **AI 原生集成**: LangChain Tool 无缝对接 Agent

该架构已在压测中验证稳定性，可作为后续扩展（如语义搜索、个性化排序）的坚实基础。
