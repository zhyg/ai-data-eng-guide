# 5. 性能基线不是调优冲动

## 核心理念与目标

- **基本原则**：没有 baseline，就没有真正的优化，只有一堆模糊感受。
- **验收标准**：Week04 的验收不是"用了 Iceberg"，而是"建立了第一份可被复核的数据状态基线"。

## 核心概念区分

| 概念 | 定义 | 本周做不做 |
| :--- | :--- | :--- |
| **Baseline** | 记录当前表、文件、快照、历史及 Schema 演进状态 | ✅ 本周主做 |
| **Benchmark** | 测量吞吐、延迟、并发等性能上限 | ❌ 本周不做 |
| **Tuning** | 执行 Compaction、优化 Partition、Cache 等调优动作 | ❌ 本周不做 |

## 必须记录的 7 项指标

| 指标 | 业务解释 | 异常信号 |
| :--- | :--- | :--- |
| **Row Count** | 当前表总行数 | 与数据源覆盖范围（source coverage）不一致 |
| **Snapshot Count** | 表状态提交次数 | 过多或过少（需结合写入批次解释） |
| **File Count** | 当前引用的 Data Files 数量 | 文件特别碎，碎片化严重 |
| **File Size (avg/min/max)** | 文件大小分布情况 | 小文件过多或分布极端不均 |
| **Partition Distribution** | 分区分布状态 | 极不均匀或不符合后续查询模式 |
| **Latest Snapshot Time** | 最新提交时间 | 与 Ingest / Release 时间点对不上 |
| **Metadata Log Entry Count** | Metadata 演进记录数 | 保留策略（retention）可能不足 |

## 状态证据链的组合解释

| 视图 | 解释什么 |
| :--- | :--- |
| **Snapshots** | 记录了几次提交，每次的操作类型（operation） |
| **History** | 记录哪个 Snapshot 在何时成为当前（current）状态 |
| **Files** | 记录当前 Snapshot 实际引用的文件数量、大小与分区分布 |
| **Metadata Log** | 记录元数据文件的演进轨迹 |

**组合口径**：这次写入产生了哪个 Snapshot？当前引用了哪些文件？是否与源头数据量对得上？

## Baseline Report 模板（iceberg_baseline_report.md）

### 1. 环境与运行说明

- repo commit
- compose profile
- catalog 类型与 uri
- warehouse 根路径
- run timestamp

### 2. 目标表清单

- `bronze.raw_ticket_event`
- `bronze.raw_doc_asset`
- `silver.ticket_fact`
- `silver.knowledge_doc`

### 3. 表状态摘要

| table | row_count | snapshot_count | file_count | latest_snapshot_time |
| :--- | :--- | :--- | :--- | :--- |
| bronze.raw_ticket_event | … | … | … | … |
| bronze.raw_doc_asset | … | … | … | … |
| silver.ticket_fact | … | … | … | … |
| silver.knowledge_doc | … | … | … | … |

### 4. 优秀 Baseline 的标准

- 必须有环境说明。
- 必须覆盖最小闭环 4 表。
- 严禁只有截图。
- 必须有表格与异常解释。
- 必须可被他人在同一 commit 下复现。

## 异常处理：先记，不修

| 现象 | 可能原因 | 处理对策 |
| :--- | :--- | :--- |
| **Snapshot 特别多** | 频繁小批写入或多次 Demo | 记录现象，不急于执行 `expire snapshots` |
| **文件特别小** | 每次 Append 数据量太小 | 记录现象，不急于执行 `compaction` |
| **行数不一致** | Mapping / Dedupe 逻辑问题 | **优先解释并修正逻辑** |
| **Schema ID 变化无记录** | Schema Evolution 未记笔记 | 本周内补齐 `notes` |
| **分区分布极不均匀** | 分区策略与查询模式不匹配 | 记录现状，留待后续演进 |
| **Time Travel 读不到旧状态** | Snapshot 过期或未成功形成 | 解释保留边界（retention boundary） |

## 维护动作边界（Maintenance Boundary）

| 动作 | 本周边界 |
| :--- | :--- |
| **Expire Snapshots** | 仅在历史 Snapshot 过多且已确定保留策略时考虑 |
| **Orphan File Cleanup** | 记录未被 Metadata 引用的遗留文件风险，不作为主线 |
| **Compaction** | 禁止在没有 Baseline 之前盲目优化，需先记录布局 |
| **Metadata Cleanup** | 仅在元数据增长影响维护性能时记录并执行 |

## 典型 Incident

### Incident 1：过早清理 Snapshot

- 团队看到 snapshot 数量"多"，下意识 `expire snapshots`。
- 当 bad case 复盘时旧状态丢失，time travel 失败。
- **教训**：先有保留策略，再做清理动作。

### Incident 2：文件碎急着 compaction

- 看到 file count 很多、avg size 很小，立刻发起 compaction。
- 实际上写入频率本身导致碎片化，compaction 后下一批写入还是碎。
- **教训**：先记录现状、定位根因，再决定是否调优。

## Week04 最终交付物清单

1. `lakehouse_foundation_v1.md`：阐述 Week04 存在意义。
2. `source_to_iceberg_mapping_v1.md`：记录 Source → Iceberg 字段映射。
3. `bronze_silver_table_design_v1.md`：最小 4 表设计方案。
4. `catalog_runtime_plan_v1.md`：配置 Catalog / Warehouse / Location。
5. `runbooks/week04/README.md`：运行与排查路径指南。
6. `iceberg_baseline_report.md`：最终状态基线报告。

## 收官总结

- **核心升级**：Week04 将 Week03 的 Ingest Baseline 升级为了 **Lakehouse State Baseline**。
- **后续衔接**：
  - **Week05（Transform）**：基于稳定的 Bronze / Silver 状态推进语义层。
  - **Week08（Retrieval）**：索引必须绑定特定的文档资产 Snapshot 以保证一致性。
  - **Week11+（Eval / Release）**：评测与发布必须绑定数据状态，而非仅绑定代码。
