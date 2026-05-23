# 1. AI 数据工程需要"有记忆的表"，不只是能查的表

## 核心目标与背景

- **定调**：能查到当前数据，不等于能复现当时回答。
- **演进**：从 Week03 的 Ingest Correctness（接入正确性）升级到 Week04 的 Table State Reproducibility（表状态可复现性）。
- **主要任务**：解决 AI 数据工程中"答案变了、评测漂了、坏案例出现时无法定位数据版本"的问题。

## 为什么需要"有记忆的表"

### 真正危险的场景

- **状态不可复现**：有数据、有索引、有答案，但无法对齐到具体的一版数据状态。
- **复盘失败案例**：同一问题在周一和周三得到的回答不同，由于缺乏 Snapshot 锚点，只能猜测数据是否变化。

### 坏案例：Northstar Edge Gateway 答案漂移

同一个工单问题，周一回答 A，周三回答 B：
- Raw 文档是否被更新？没有版本号无法回答。
- Ingest 批次是否变了？日志不全无法回答。
- 索引是否被重建过？只知道"建过"。
- → 团队陷入"猜数据是否变了"的循环。

## 数据对象能力对比（状态账本承担者）

| 对象 | 能查当前？ | 能回看历史状态？ | 适合承担的角色 |
| :--- | :--- | :--- | :--- |
| **Raw Bucket** | 能（靠路径/清单） | 弱（除非手动版本化） | 文件柜：保存原始输入 |
| **PostgreSQL 当前表** | 能 | 弱（仅代表当前视图） | 业务视图：当前事实查询 |
| **pgvector / 向量索引** | 能召回 | 弱（索引不等于账本） | 索引：服务检索，不负责记忆 |
| **Iceberg Table** | **能** | **强（Snapshot/History）** | **数据账本：提交历史与状态锚点** |

## "可查" vs "可回看"

| 场景 | 只可查当前数据 | 可回看表状态 (Iceberg) |
| :--- | :--- | :--- |
| **历史回看** | 靠日志和备份猜 | 绑定 Snapshot / History |
| **评测绑定** | 结论模糊（可能数据变了） | 绑定具体 Table Snapshot |
| **索引重建** | 只知重建过 | 明确消费了哪版文档资产 |
| **Release 复盘** | 数据缺锚点 | 绑定 代码 + Prompt + Table Snapshot |

## 状态记忆的五个核心证据

1. **提交后的表状态**：记录每次 Append/Overwrite。
2. **文件构成**：由 Metadata 组织而非目录猜测。
3. **Snapshot 关系**：清晰的历史与当前关联。
4. **Schema / Partition 演进**：字段与布局变化可解释。
5. **可引用状态锚点**：支持 Time Travel 与 Release 绑定。

## 团队复盘必须问的 8 个问题

1. **Raw 文档版本**：回答基于哪版原始文档？
2. **Ingest Batch**：对应哪次接入批次？
3. **Iceberg Snapshot**：数据状态锚点是什么？
4. **Index Version**：索引消费了哪版数据？
5. **Prompt Version**：提示词是否变化？
6. **Eval Drift Point**：分数变化发生在哪个状态之后？
7. **Business Boundary**：字段或权限是否变化？
8. **Rollback Target**：能否定位到稳定状态？

## 心智模型：四种数据角色

- **文件柜（Raw Bucket）**：负责保真，不负责检索性能。
- **业务视图（PostgreSQL）**：负责服务当前事实，不负责回看历史。
- **索引（pgvector）**：负责召回，不负责"是哪一版"。
- **数据账本（Iceberg）**：负责状态、历史、Snapshot、可引用锚点。

## 工程边界与误区

### Iceberg 不等于自动解决所有问题

- **不自动修数据质量**：只能记住坏数据在哪一版。
- **不自动让 RAG 变准**：仅提供锚点，不替代切分、检索、评测。
- **不替代 Week02 Contract**：准入控制仍需前置。
- **不自动治理回滚**：仍需策略、审批和 Runbook。

### 常见 5 个误解

1. **误以为与 AI/RAG 无关**：实际上索引、评测都需要数据状态。
2. **误以为对象存储 = Lakehouse**：Lakehouse 需要 Metadata/Snapshots。
3. **误以为有向量库就能复现**：向量库不是数据账本。
4. **误以为 Time Travel 是复制表**：它是回到旧 Snapshot 的状态集合。
5. **误以为本周做完就完成治理**：权限和发布治理在后续周次。

## 工程交付物（Handoff）

### 需对齐的 Repo 对象

- `pipelines/lakehouse/iceberg_schemas.py`：最小 4 表 Schema 的 Source of Truth。
- `pipelines/lakehouse/assets.py`：Dagster Asset 入口。
- `infra/docker-compose.yml`：本地基线环境（PG, MinIO, Dagster）。
- `pyproject.toml`：PyIceberg / PyArrow 依赖。

### 本课产出文件

- `docs/blueprints/week04/lakehouse_foundation_v1.md`：说明 Week04 存在意义。
- `docs/blueprints/week04/state_memory_questions_v1.md`：列出复盘必问状态问题。

### 结构化命令占位（Terminal）

```bash
# 创建工件目录
mkdir -p docs/blueprints/week04 reports/week04 runbooks/week04

# 创建设计文档
touch docs/blueprints/week04/lakehouse_foundation_v1.md
touch docs/blueprints/week04/state_memory_questions_v1.md
```

## 核心判断小结（Recap）

- **核心主线**：从 Ingest Baseline 升级为 Lakehouse State Baseline。
- **验收标准**：不是"用了 Iceberg"，而是"拥有第一份可复核的数据状态基线"。
- **下阶段预告**：进入 Iceberg 状态模型（Snapshot, Manifest, Metadata Log）。
