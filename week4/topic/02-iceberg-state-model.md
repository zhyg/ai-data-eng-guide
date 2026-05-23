# 2. Iceberg 的状态模型

## 核心定义与目标

- **核心理念**：Time travel 不是复制旧表，而是回到旧 snapshot 所代表的状态集合。
- **状态证据链**：由 snapshot、manifest list、manifest files、metadata log 与 data files 构成的完整链路。
- **主要任务**：讲清 Iceberg 靠什么把一组 files 组织成可提交、可回看、可演进的表状态。
- **本课产出**：
  - `docs/blueprints/week04/snapshot_state_model_v1.md`
  - `reports/week04/time_travel_demo_notes.md`

## 关键判断与核心逻辑

### 1. Iceberg 不是目录升级版

Iceberg 不是按日期分目录的升级版，它用 metadata 将提交组织成可追踪对象，从而支持 time travel 和 schema evolution。

### 2. Git 类比与边界

| Git 概念 | Iceberg 概念 | 类比边界 |
| :--- | :--- | :--- |
| commit | snapshot | 记录表状态，不是代码 diff |
| commit history | metadata log / history | 记录状态演进，不是开发分支历史 |
| 文件清单 | manifest / manifest list | 记录 data files 和统计信息 |
| 工作目录文件 | data files | 文件本身不等于表状态 |
| checkout old commit | time travel old snapshot | 回到旧状态集合，不是复制旧表 |

## 状态对象拆分（State Objects）

| 对象 | 工程定义 / 解决问题 |
| :--- | :--- |
| **table metadata file** | 表的状态说明书；存 schema、snapshots、current snapshot 等。 |
| **snapshot** | 一版表状态；让一次提交可命名、可引用、可回看。 |
| **manifest list** | snapshot 的 manifest 索引；优化 scan planning。 |
| **manifest** | 数据文件清单 + 统计；记录 record_count, size, upper/lower bounds。 |
| **data file** | 实际 Parquet 文件；承载数据。 |
| **metadata log** | metadata 文件演进记录；支撑状态证据链。 |
| **history** | 记录谁在何时成为 current；支撑复盘与 baseline。 |

## 关键机制

### 可靠读（Reliable Reads）

- 通过 `current metadata pointer` 和 `atomic swap`（原子交换 metadata 文件路径）实现。
- 读者使用一致的 snapshot，无需持锁。
- 写入失败不会污染读者看到的状态。

### Time Travel 原理

- 依赖稳定的 snapshot id 和未过期的状态证据链。
- 可按 snapshot id 或时间戳定位旧状态。
- 状态由 metadata + manifest + data files 三层共同保证。

### Schema Evolution

- 支持 add/drop/rename/update/reorder。
- 仅为 metadata 变更，无需重写数据文件。
- 旧 snapshot 仍按其当时 schema 读取。
- Week04 范围：仅演示 add-column。

### Hidden Partitioning（隐藏分区）

- 查询者按逻辑字段思考。
- 表格式处理分区转换（transform）与裁剪（pruning）。
- 不依赖具体物理路径，避免目录结构泄漏到查询。

### 并发写入与 Snapshot 保留策略

- 采用乐观并发控制（Optimistic Concurrency）。
- 冲突后进行校验与重试。
- Snapshot 保留是策略问题：保留越久 → time travel 窗口越长，但 metadata 与文件成本越高。

## 观察与排查指南

### Metadata Inspection 观察顺序

```
snapshots → history → files → metadata log → baseline
```

### 常见 Inspection 字段

- `snapshot_id`：标识版本。
- `parent_id`：构成时间线。
- `operation`：解释变更类型（append/overwrite/replace）。
- `record_count / file_size`：核心性能指标。
- `committed_at`：定位提交时间。

### 常见的 5 个误读与修正

1. **误读**：snapshot 是文件。
   **修正**：snapshot 是一版表状态（指向一组文件）。
2. **误读**：manifest 是目录清单。
   **修正**：manifest 记录 data files + stats。
3. **误读**：time travel 复制旧表。
   **修正**：回到旧 snapshot 状态集合。
4. **误读**：schema evolution 随便改。
   **修正**：需考虑兼容性，Week04 仅演示 add-column。
5. **误读**：cleanup 越早越好。
   **修正**：过早清理会缩短 time travel 历史，需先有保留策略。

## 典型坏案例（Incident）

**过早清理 snapshot**：
- 在没有保留策略前，团队执行了 expire snapshots。
- 当 bad case 复盘时旧状态丢失，time travel 失败。
- 团队无法复现旧结果，争论"到底是哪版数据"。
- 教训：保留策略必须先于清理动作。

## 总结

- Iceberg 的本质是**表状态模型**。
- 验收标准不是"用了 Iceberg"，而是建立了"有可复核证据的状态基线"。
- 下一讲衔接：将状态模型落到 Bronze / Silver 最小 4 表设计中。
