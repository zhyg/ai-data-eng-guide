# 6. 最小 Iceberg 闭环实验

> 本节作为 Week04 的实操收口，把前 5 节的概念串成一个可被复现的端到端实验：
> 起步环境 → 物化写入 → Snapshot 形成 → Inspect → Schema Evolution → Baseline 报告。

## 实验目标

完成一次可被他人在同一 commit 下复现的最小闭环：

1. 起一套本地 Lakehouse 环境（MinIO + PostgreSQL Catalog）。
2. 创建最小 4 表的 namespace 与 schema。
3. 至少完成 1 个 Bronze + 1 个 Silver 表的 append 写入。
4. 观察到完整的状态证据链（snapshots / history / files / metadata log）。
5. 完成一次 add-column 的 schema evolution 并落到 notes。
6. 输出一份 `iceberg_baseline_report.md`。

## 实验前置

### 环境清单

- `infra/docker-compose.yml`：PostgreSQL + MinIO + Dagster。
- `pipelines/lakehouse/iceberg_schemas.py`：4 表 Schema 的 Source of Truth。
- `pipelines/lakehouse/assets.py`：Dagster Asset 入口。
- `.env`：catalog uri、warehouse root、s3 endpoint、access/secret。

### 依赖

- `pyiceberg`
- `pyarrow`
- `sqlalchemy`（SQL Catalog 后端）
- `boto3` / `minio`（S3 兼容客户端）

## 实验 7 步流程

```diagram
╭──────────────╮   ╭──────────────╮   ╭──────────────╮   ╭──────────────╮
│ 1. 起环境    │──▶│ 2. Ensure    │──▶│ 3. 物化写入  │──▶│ 4. 形成      │
│ compose up   │   │ ns + schema  │   │ append/over  │   │ snapshot     │
╰──────────────╯   ╰──────────────╯   ╰──────────────╯   ╰──────┬───────╯
                                                                 │
   ╭──────────────╮   ╭──────────────╮   ╭──────────────╮        │
   │ 7. 输出      │◀──│ 6. Schema    │◀──│ 5. Inspect   │◀───────╯
   │ baseline 报告│   │ Evolution    │   │ 状态证据链   │
   ╰──────────────╯   ╰──────────────╯   ╰──────────────╯
```

### Step 1：起环境

```bash
docker compose -f infra/docker-compose.yml up -d
# 验证 MinIO 与 PostgreSQL 健康
docker compose ps
```

预期：MinIO console 可打开、PG 可连、bucket 已建。

### Step 2：Ensure Namespace 与 Schema

- `load_catalog()` 读取 env。
- `create_namespace('bronze')`、`create_namespace('silver')`。
- 对最小 4 表执行 `create_table(if_not_exists=True)`，schema 取自 `iceberg_schemas.py`。

验收：`list_tables('bronze')` 与 `list_tables('silver')` 返回 4 张表。

### Step 3：物化写入（Materialize）

按 Section 4 的 10 步动作执行：

1. 读 env / 加载 catalog。
2. Ensure ns / table。
3. 读输入（Week03 ingest 或对象存储 raw 文件）。
4. 按 mapping 转 Arrow。
5. Schema 验证（字段、类型、nullable）。
6. dedupe / idempotency 校验。
7. `table.append(arrow_table)`。
8. 等待 snapshot 生成。
9. 触发 inspect。
10. 写 report。

至少跑 1 个 Bronze 表 + 1 个 Silver 表。

### Step 4：形成 Snapshot

- 每次 append/overwrite 都会形成一个新的 snapshot id。
- 记录：snapshot_id、parent_id、operation、committed_at。

### Step 5：Inspect 状态证据链

按 Section 2 的观察顺序：

```
snapshots → history → files → metadata log → baseline
```

| 视图 | 关键字段 |
| :--- | :--- |
| `inspect.snapshots` | snapshot_id, parent_id, operation, summary |
| `inspect.history` | made_current_at, snapshot_id, is_current_ancestor |
| `inspect.files` | file_path, file_size_in_bytes, record_count, partition |
| `inspect.metadata_log_entries` | timestamp, file |

### Step 6：Schema Evolution 演示

- 选一张 Bronze 表执行 `update_schema().add_column(...)`。
- 再做一次小批量 append，确认旧 snapshot 仍可按旧 schema 读取。
- 记录到 `reports/week04/schema_evolution_demo_notes.md`：
  - 演进前的 schema id。
  - 演进操作（add column 名 / 类型 / nullable）。
  - 演进后的 schema id。
  - 新旧 snapshot 的读取行为差异。

### Step 7：输出 Baseline 报告

使用 Section 5 的报告模板，覆盖：

- 环境与运行说明（commit、profile、catalog、warehouse、timestamp）。
- 最小 4 表的状态摘要（row_count / snapshot_count / file_count / latest_snapshot_time）。
- 异常信号解释（先记录，不急修）。
- Schema Evolution notes 链接。

## 验收 Checklist（Demo Checklist）

- [ ] Catalog 成功加载。
- [ ] Namespace（bronze / silver）成功 ensure。
- [ ] 最小 4 表 Schema 成功 ensure。
- [ ] 至少完成 1 Bronze + 1 Silver 的 append 操作。
- [ ] 能观察到状态证据链（snapshots / history / files）。
- [ ] 完成 add-column schema evolution 演示并记录。
- [ ] 输出 `reports/week04/iceberg_baseline_report.md`。

## 常见踩坑与对策

| 现象 | 排查方向 |
| :--- | :--- |
| Catalog load 失败 | 检查 catalog type / uri / env，打印配置来源 |
| MinIO 连不上 | localhost vs 容器内服务名；endpoint scheme（http/https） |
| Bucket 不存在 | warehouse root 写权限 / 凭证 |
| Schema 不匹配 | 回 `iceberg_schemas.py` 对齐 source of truth |
| 重跑数据重复 | 检查 dedupe key 与 idempotency 策略 |
| Inspect 无 Snapshot | 确认 append/overwrite 是否真正触发提交 |
| Time Travel 读不到旧状态 | 解释 retention boundary，确认未过早 expire |

## 实验产出物

| 工件 | 路径 |
| :--- | :--- |
| 运行手册 | `runbooks/week04/README.md` |
| Schema 演进笔记 | `reports/week04/schema_evolution_demo_notes.md` |
| 基线报告 | `reports/week04/iceberg_baseline_report.md` |
| Time Travel 演示笔记 | `reports/week04/time_travel_demo_notes.md` |

## 总结

- 实验的本质不是"写入成功"，而是**形成可 inspect 的 snapshot + 可复核的 baseline**。
- 这一闭环把 Section 1–5 的所有概念落到一份他人可复现的报告里。
- 完成此实验，即标志 Week04 的核心交付（Lakehouse State Baseline）成立，可进入 Week05 的 Transform 阶段。
