# 03 增量与 CDC

> 看起来像增量，不等于已经有稳定增量链路。
> 这节课把 cursor、watermark、checkpoint、乱序、去重和 exactly-once 的边界一次讲清。

**关键词锚点**：cursor · watermark · checkpoint · CDC · dedupe · not exactly-once

---

## 一、这节课先解决什么

> 增量真正难在状态与恢复，不在「少读一点数据」。

### 你会遇到的问题(WHY IT MATTERS)

- 哪个字段配当增量游标？
- updated_at 为什么危险？
- WAL / logical decoding / CDC 解决什么、没解决什么？
- 迟到、重复、乱序怎么处理？
- 为什么不要轻易承诺 exactly-once？

### 本课目标(WHAT YOU CAN DO)

- 拆开 cursor / watermark / checkpoint。
- 区分 dedupe key 与 idempotency key。
- 理解 at-least-once 的现实。
- 能写出 `incremental_ingest_strategy_v1.md`。
- 对 CDC 的边界保持工程诚实。

---

## 二、从 batch baseline 到 incremental / CDC

> 增量不是跳过 batch，而是在 batch 可靠性上继续叠状态。

```diagram
╭───────────╮   ╭───────────────────╮   ╭─────────────────────╮   ╭──────────────╮   ╭──────────────╮
│ W2:       │──▶│ BATCH baseline    │──▶│ STATE incremental / │──▶│ L4 Asset     │──▶│ L5 Recovery  │
│ contract/ │   │ idempotent write/ │   │ CDC semantics       │   │ Flow         │   │ replay /     │
│ manifest/ │   │ reconcile         │   │ cursor / checkpoint │   │ partition /  │   │ backfill /   │
│ gate      │   │                   │   │ / dedupe            │   │ materialize  │   │ runbook      │
╰───────────╯   ╰───────────────────╯   ╰─────────────────────╯   ╰──────┬───────╯   ╰──────┬───────╯
                                                                          │                   │
                                                                          └──W4/6 Lakehouse + Orchestration
```

---

## 三、为什么增量比全量更难

> 全量简单在「边界大但清楚」；增量难在「边界小但持续变化」。

| 风险 | 全量 / Batch | Incremental / CDC |
| :--- | :--- | :--- |
| **重复** | 通常来自重跑 | cursor 粒度、slot 重发、retry 都可能重复 |
| **迟到** | 一次性批次较容易观察 | watermark 之前/之后要有策略 |
| **乱序** | 窗口内排序影响小 | 事件顺序与业务语义可能错位 |
| **恢复** | 重跑整个批次 | 必须知道 checkpoint / LSN / offset |
| **解释** | 一次 run report | 持续状态 + 分区 report |

### 官方信号 · Airbyte：cursor 与 at-least-once 是现实

- **cursor 决定是否复制**：cursor 是用来判断记录是否应该被增量复制的值。
- **append 会保留多版本**：更新记录会被追加，不会原地修改。
- **at-least-once 重复可以发生**：Airbyte 提供 at-least-once 复制保证，重复不是异常。
- **limitation 粒度不足会出事**：日级 cursor、多次修改、`updated_at` 未更新都可能导致重复或漏变更。

> **工程结论**：增量首先是边界声明问题，不是速度问题。

---

## 四、5 个概念必须拆开

> 每个概念回答不同问题。混用这些词，是增量系统最常见的设计味道。

- **cursor**：下一次从哪里继续读
- **watermark**：当前承认处理到哪里
- **checkpoint**：这个边界落在哪里
- **dedupe key**：两条输入是否同一事件
- **idempotency key**：重复写入是否有副作用

### 状态结构图：读取层、状态层、写入层

> 同一条 change stream 要同时走「状态」和「写入」两条逻辑。

```diagram
╭──────────────────╮   ╭────────────────────────╮   ╭─────────────────────╮
│ SOURCE           │──▶│ STATE                  │──▶│ SINK                │
│ source batch /   │   │ cursor / watermark /   │   │ Bronze / Silver     │
│ change stream    │   │ checkpoint             │   │ write               │
│ (全量/增量/CDC)  │   │ (继续读 + 恢复)        │   │ (dedupe+idempotent) │
╰──────────────────╯   ╰────────────────────────╯   ╰──────────┬──────────╯
                                                                │
                              ┌─────────────────────────────────┼─────────────────────────────┐
                              ▼                                 ▼                             ▼
                       ╭─────────────╮                  ╭──────────────╮               ╭─────────────╮
                       │  REPLAY     │                  │  BACKFILL    │               │  REPORT     │
                       │  同批输入    │                  │  历史窗口    │               │  run        │
                       │  重放       │                  │  补齐        │               │  evidence   │
                       ╰─────────────╯                  ╰──────────────╯               ╰─────────────╯
```

---

## 五、cursor 字段怎么选：每种都有风险

> 字段能当 cursor，前提是它真的表达变化边界。

| 字段 | 适合场景 | 主要风险 |
| :--- | :--- | :--- |
| **updated_at** | 常规数据库表增量 | 被回写、没更新、粒度太粗 |
| **event_time** | 事件发生时间 | 迟到和乱序会打穿窗口 |
| **sequence_id** | 单调递增业务序列 | 需要来源保证单调 |
| **LSN** | 数据库 WAL/CDC | 偏日志位置，不等于业务语义 |
| **offset** | 消息/日志流位置 | 只代表读取位置，不代表数据事实 |

> 不要问「哪个字段好」，先问来源是否保证它的语义。

---

## 六、watermark 和 checkpoint 不要混

> 一个是承认边界，一个是落盘状态。

| 对象 | 回答什么 | 没有它会怎样 |
| :--- | :--- | :--- |
| **watermark** | 系统已经确认处理到哪里 | 迟到/乱序无法判断 |
| **checkpoint** | 这个边界被持久化在哪里 | crash 后不知道从哪恢复 |
| **cursor** | 下一次从哪里继续读 | 增量变成全量或漏读 |
| **report** | 这次处理发生了什么 | state 与事实无法对账 |

> 没有 checkpoint，crash recovery、replay、backfill 都靠记忆。

### dedupe key vs idempotency key

> 输入层和写入层不要混。两个 key 都重要，但保护的边界不同。

| Key | 判断对象 | 例子 |
| :--- | :--- | :--- |
| **dedupe key** | 两条输入是不是同一业务事件 | `event_id` / `ticket_id+updated_at` |
| **idempotency key** | 同一次写入动作重复执行是否有副作用 | `batch_id+primary_key` / `run_id+sink_key` |
| **primary key** | 目标表里一个事实对象如何定位 | `ticket_id` / `doc_id+version` |
| **trace key** | 跨系统如何串联排障 | `trace_id` / `run_id` / `manifest_id` |

> 写入层幂等不能替代输入层去重。

---

## 七、updated_at 为什么危险

> 它很常见，但不是天然可靠。

- **被回写**：批处理或同步任务修改时间戳。
- **没更新**：数据变了，但 cursor 字段没变。
- **粒度太粗**：一天内多次变化无法区分。
- **语义漂移**：从业务更新时间变成 ETL 时间。
- **时区不统一**：窗口边界错位。
- **NULL / default**：默认值导致新旧难分。
- **源端延迟**：变更晚于同步窗口出现。
- **并发写入**：多个更新顺序不可控。

> `updated_at` 可以用，但必须配合窗口、容忍区、dedupe 和 report。

### 迟到、重复、乱序怎么做第一轮决策

> 不要把所有异常都 reject。

| 场景 | 默认动作 | 要记录什么 |
| :--- | :--- | :--- |
| **迟到但在 watermark 容忍窗口内** | accept + mark late | event_time / observed_at / reason |
| **超出 watermark 容忍窗口** | quarantine or backfill review | source_id / window / gap |
| **dedupe key 重复** | skip or merge | original event pointer |
| **idempotency key 重复** | skip write side effect | existing sink key |
| **schema 合法但语义漂移** | quarantine + review | contract / owner / downstream impact |

> 动作背后要有 reason_code，否则后面无法回放。

---

## 八、CDC 解决什么，没解决什么

> WAL/slot/LSN 能提高变化捕获能力，但不会自动消灭重复和恢复边界。

> **工程诚实**：CDC 是 snapshot + change stream 的组合，不是 exactly-once 魔法。

### PostgreSQL logical replication：先 snapshot，再持续 changes

> CDC 不完全取代 snapshot，而是把初始状态与后续变化接起来。

- **publication / subscription**：发布者声明变化，订阅者消费变化。
- **initial snapshot**：先复制已有数据，建立起点。
- **continuous changes**：之后持续发送 INSERT/UPDATE/DELETE。
- **transaction order**：同一 subscription 内按发布顺序应用。

### logical decoding 与 slot：能重放，也可能重发

> 官方文档明确说：crash 后最近 changes 可能再次发送。

- **logical decoding**：从 WAL 中抽取持久化变化。
- **replication slot**：代表可重放的 change stream。
- **crash-safe but…**：位置只在 checkpoint 持久化。
- **client responsibility**：客户端要避免重复处理副作用。

> 这就是为什么 CDC 客户端仍要 dedupe + idempotent write。

### Debezium 信号：exactly-once 不要轻易承诺

- **默认 at-least-once**：不漏 change，但 record 可能多次 delivery。
- **没有内部 dedup layer**：Debezium 自身不实现内部去重层。
- **可利用 Kafka Connect EOS**：需要 distributed mode、Kafka Connect 版本和配置前置条件。
- **仍有边界**：官方文档提示 exactly-once 的正确性仍需谨慎看待。

---

## 九、工程诚实：不要轻易承诺 exactly-once

> 工程上更诚实的目标，是可复现、可定位、可补数、可回放。

> 「at-least-once + 幂等写入 + 去重 + 可回放恢复」比空喊 exactly-once 更可靠。

在真实系统里，重复、重发、迟到、crash recovery 都不是罕见异常，而是运行语义。

- **能复现**：同一批次能重放
- **能定位**：run / state / source 可追踪
- **能补数**：backfill 有边界
- **能解释**：为什么重复、为什么不会漏

---

## 十、当前 repo 的增量主线

> 本周不要求本地搭完整 CDC 平台，但要把对象认清。

- **CONTRACT**：`contracts/data/*.json`（字段与边界规则）
- **MANIFEST**：`data/seed_manifests/*.json`（`load_mode` / window / source）
- **LOADER**：`pipelines/ingestion/seed_loader.py`（manifest dry-run）
- **TICKET**：`pipelines/ingestion/ticket_ingest.py`（batch + cursor 思维）
- **DOC**：`pipelines/ingestion/doc_ingest.py`（document source ingest）
- **TESTS**：`tests/contract/test_json_schemas.py`（最小门禁）

### 进阶对象认知边界：知道意义，不急着全搭

- **logical decoding**：变化从 WAL 来
- **replication slot / LSN**：日志流位置与恢复边界
- **Debezium snapshot + stream**：初始状态 + 后续变化
- **Kafka Connect EOS**：有条件支持 exactly-once
- **streaming observability**：持续状态与延迟观察

---

## 十一、动手实践：把增量策略写进文档

> 这节课更多是设计与观察，不是搭重型 CDC。

```bash
mkdir -p docs/blueprints/week03
touch docs/blueprints/week03/incremental_ingest_strategy_v1.md
touch docs/blueprints/week03/checkpoint_state_v1.md
touch docs/blueprints/week03/late_arrival_decision_table.csv
```

**建议先读**：

- `contracts/data/*.json`
- `data/seed_manifests/*.json`
- `pipelines/ingestion/seed_loader.py`
- `pipelines/ingestion/ticket_ingest.py`

**任务**：

1. **策略说明**：cursor / watermark / checkpoint 怎么定义
2. **状态结构**：state 落在哪，谁更新
3. **决策表**：迟到、重复、乱序如何处理

### late arrival / duplicate / disorder 决策表

> 建议直接照这个骨架写 CSV。决策表就是 runbook 的前身。

| case | condition | action | evidence |
| :--- | :--- | :--- | :--- |
| **late_in_window** | `event_time < watermark` but within tolerance | accept + mark late | event_time / observed_at |
| **late_out_of_window** | beyond tolerance | quarantine / backfill review | window / reason_code |
| **duplicate_input** | same dedupe key | skip / merge | original_event_id |
| **duplicate_write** | same idempotency key | skip write | sink_key |
| **semantic_drift** | schema ok, meaning changed | quarantine + owner review | contract version |

---

## 十二、Crash 后为什么可能重发：slot 位置只在 checkpoint 持久化

> 用 PostgreSQL 官方语义解释「重复不是异常」。

**故障过程**：

1. **client consumes**：读取 WAL changes
2. **sink writes**：写入目标表
3. **server crash**：slot position rollback
4. **recent changes resent**：同一 change 再来
5. **client handles**：dedupe / idempotent

**屏幕上看起来像什么**：CDC 看起来「多发了一次」，下游多了一些重复记录。

**实际已经坏在哪**：这是 documented behavior，客户端需要记录 LSN / dedupe，写入层必须幂等。

### 状态写错，补数和回放都会失真

> 增量系统最怕 state 先于事实前进。

1. **读取一半**：部分 source 失败
2. **checkpoint 更新**：状态被推进
3. **下次继续**：跳过未写入记录
4. **下游缺口**：gap 被固化
5. **backfill 困难**：不知道缺哪段

**屏幕上看起来像什么**：每次同步都成功，只是某些天少数据。

**实际已经坏在哪**：checkpoint 与写入事实不一致，report 没有 source coverage。

---

## 十三、行业信号：生产级增量拼的是边界、状态和恢复

- **Airbyte**：cursor + at-least-once（避免重复或漏变更）。
- **PostgreSQL**：WAL / slot（crash 后可能重发最近 changes）。
- **Debezium**：EOS with boundaries（exactly-once 需要严格条件）。
- **OpenLineage**：run evidence（facets 可以把运行上下文对象化）。

> 工具越复杂，越不能省掉状态和证据。

### 不是 streaming 工具秀

> 不要让工具名掩盖工程边界。高级不是工具多，而是边界诚实。

- **不是**：一上来堆 Kafka / Debezium 配置 → **而是**：写清 cursor / watermark / checkpoint
- **不是**：宣称「已经 exactly-once」 → **而是**：接受 at-least-once + idempotency
- **不是**：把 `updated_at` 当银弹 → **而是**：为 replay/backfill 留证据
- **不是**：只看消费 offset → **而是**：能解释重复和缺口

### 增量链路最常见的假动作

> 看起来工程化，实际上没有可恢复边界。共同点：把恢复问题推给未来。

| 假动作 | 为什么危险 | 修正 |
| :--- | :--- | :--- |
| **只存 `last_updated_at`** | 不知道状态来自哪次 run | checkpoint 带 run_id / source / report |
| **只看 offset** | offset 不是业务事实 | offset + dedupe + 业务 key |
| **遇到重复就删** | 可能删除真实多版本 | 保留证据并定义 dedupe 规则 |
| **承诺 exactly-once** | 忽略系统边界和 crash 现实 | 讲清 at-least-once + 幂等 |
| **没有容忍窗口** | 迟到数据被静默丢弃 | watermark + late policy |

---

## 十四、自检：你能不能讲清这 6 个问题

1. **cursor 是什么**：下一次从哪里继续读
2. **watermark 是什么**：已经确认处理到哪里
3. **checkpoint 落在哪里**：状态被谁持久化
4. **dedupe key 怎么定**：输入是否同一事件
5. **idempotency key 怎么定**：写入是否重复副作用
6. **exactly-once 能否承诺**：当前课程不承诺，边界要讲清

> 能讲清边界，就已经比很多「工具配置课」更接近生产。

---

## 十五、RECAP & NEXT

### 本课最重要的判断

- 增量不是天然可靠。
- cursor / watermark / checkpoint 不可混用。
- dedupe key / idempotency key 不可混用。
- CDC 不替代 snapshot，而是 snapshot + change stream。

### 继续向前

- 有 slot 不等于不重不漏。
- 不要轻易承诺 exactly-once。
- 当前目标是 at-least-once + idempotent write + dedupe + replayable recovery。
- 下节课把 ingest 组织成资产流。

### 下一讲

Lesson 04 会把 manifest、ingest、state、metadata 组织到 Dagster asset / materialization / partition / backfill 视角。
