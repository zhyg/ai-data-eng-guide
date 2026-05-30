# 3. 从入湖到湖仓：Bronze / Silver 最小表设计

## 核心理念

- **表越多不代表越生产级**：第一版 Lakehouse 的核心能力是状态型表的**真实可写**与**可回看**。
- **最小 4 表配置**：
  - `bronze.raw_ticket_event`
  - `bronze.raw_doc_asset`
  - `silver.ticket_fact`
  - `silver.knowledge_doc`

## 课程目标与产出

- **解决问题**：明确当前项目必须存在的表，防止层数堆砌导致的复杂度膨胀。
- **关键技能**：
  - 区分 Bronze、Silver、Gold 的角色。
  - 编写 Source-to-Iceberg mapping 最小字段。
  - 解释 Hidden Partitioning 与 Partition Evolution 的边界。
- **本课产出**：
  - `docs/blueprints/week04/source_to_iceberg_mapping_v1.md`
  - `docs/blueprints/week04/bronze_silver_table_design_v1.md`

## 数据流向图

### 工单流（Ticket Flow）

```diagram
╭─────────────────────╮      ╭──────────────────────────╮      ╭────────────────────╮      ╭──────────────╮
│ Week03 ticket       │─────▶│ bronze.raw_ticket_event  │─────▶│ silver.ticket_fact │─────▶│ Week05       │
│ ingest baseline     │      │ (保真事件 / replay 入口) │      │ (统一工单事实)     │      │ Transform    │
╰─────────────────────╯      ╰──────────────────────────╯      ╰────────────────────╯      ╰──────────────╯
```

### 文档流（Document Flow）

```diagram
╭─────────────────────╮      ╭──────────────────────────╮      ╭────────────────────────╮      ╭──────────────────╮
│ MinIO raw inputs    │─────▶│ bronze.raw_doc_asset     │─────▶│ silver.knowledge_doc   │─────▶│ Week08           │
│ (文档/PDF/文本)     │      │ (文档资产状态)           │      │ (统一文档事实)         │      │ Retrieval / RAG  │
╰─────────────────────╯      ╰──────────────────────────╯      ╰────────────────────────╯      ╰──────────────────╯
```

## 最小 4 表设计地图

| 表名 | 层级 | 来源 | 解决问题 | 后续消费 |
| :--- | :--- | :--- | :--- | :--- |
| `bronze.raw_ticket_event` | Bronze | Week03 ticket ingest | 保留原始事件和 replay 入口 | `silver.ticket_fact` / Week05 |
| `bronze.raw_doc_asset` | Bronze | MinIO raw docs | 保留文档资产与版本状态 | `silver.knowledge_doc` / Week08 |
| `silver.ticket_fact` | Silver | `raw_ticket_event` | 统一工单事实与状态 | Week05 semantic layer |
| `silver.knowledge_doc` | Silver | `raw_doc_asset` | 统一知识文档资产状态 | Week08 retrieval consistency |

## 层级角色定义

- **Bronze（保真）**：尽量保真的入湖记录，保留输入状态与 replay 入口；不做业务解释。
- **Silver（稳定事实）**：稳定可消费的业务对象，统一事实和资产状态；做去重、清洗、关键事实归一。
- **Gold（语义层）**：指标层、服务层（Week 05+ 展开），本周不展开。

## Source-to-Iceberg Mapping 规范

在编写代码前必须明确映射关系，防止 Coding Agent 在字段名、类型和去重逻辑上出错。

| 字段 | 回答什么 | 缺失风险 |
| :--- | :--- | :--- |
| **source object** | 来自哪个源对象 | Agent 随意猜源 |
| **source field** | 源字段名是什么 | 字段名误写 |
| **target table / field** | 进入哪张表哪个字段 | 目标表混乱 |
| **transform** | 是否派生 / cast / normalize | 时间语义被误改 |
| **required** | 缺失是否允许 | nullable 随意扩散 |
| **dedupe key** | 如何识别同一业务事件 | 重复写入 |
| **idempotency strategy** | 重跑是否有副作用 | 不可解释重复 |

## Hidden Partitioning（隐藏分区）

### 原理

- 查询者按逻辑字段思考。
- 表格式处理 Partition Transform 与 Pruning。
- 物理目录由 Iceberg 管理，查询不依赖目录约定。

### 对比手工目录分区

| 维度 | 手工目录分区 | Hidden Partitioning |
| :--- | :--- | :--- |
| **查询写法** | 必须 `WHERE dt='2025-05-23'` 配合路径 | 写逻辑字段，Iceberg 自动 prune |
| **布局演进** | 改分区需迁表与改查询 | Partition Evolution，新旧布局共存 |
| **回放边界** | 靠路径约定 | 绑定 Metadata / Partition Spec |

## 避坑指南：常见设计错误

1. **Bronze 过早业务解释**：导致保真入口丢失，后期 replay 失真。
2. **Silver Blind Append**：事实表变成历史垃圾堆，导致 KPI 漂移，应使用 upsert 语义。
3. **分区字段与查询无关**：对 scan 和回放边界无帮助。
4. **技术字段替代业务键**：导致业务 dedupe / idempotency 不稳。

## 本周判准（RECAP）

1. 先站住最小 4 表，不抢跑 Gold 层。
2. **Bronze 保真，Silver 统一**。
3. Mapping 必须先于表创建和物化。
4. 字段以 Repo Schema / Contract / Ingest 输出为准。
5. Hidden Partitioning 并非手工目录分区，Evolution 是工程判断而非炫技。
