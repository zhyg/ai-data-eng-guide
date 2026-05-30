# 4. PyIceberg 本地最小闭环

## 核心目标

先让核心机制可见，再谈更复杂的平台接入。通过 **PyIceberg + PostgreSQL-backed SQL Catalog + MinIO warehouse** 跑出可演示、可验收的最小闭环。

## 关键技术栈选择

- **路线**：PyIceberg + PostgreSQL SQL Catalog + MinIO（推荐，中等复杂度，覆盖所有目标）。
- **排除重型设施**：本周不引入 Spark / Hive / Nessie / Trino / REST Catalog，避免分布式计算、元数据服务排错及分支语义分散注意力。

## 配置与环境（Config Layers）

### 1. 三层配置拆解

- **Catalog**：记录表在哪里、metadata 在哪里。
- **Warehouse**：Iceberg metadata 和 data files 的存储根路径。
- **Table Location**：某张表在 warehouse 里的具体物理位置。

### 2. 环境变量（Env Config）

必须通过 env 配置，严禁硬编码：

| 变量 | 作用 |
| :--- | :--- |
| `catalog type` | 告知 PyIceberg 加载类（sql / rest / hive 等） |
| `catalog uri` | PostgreSQL SQL Catalog 连接串 |
| `warehouse root` | Iceberg 默认存储根（s3://bucket/warehouse） |
| `s3 endpoint` | MinIO / S3 兼容端点 |
| `access key / secret` | Warehouse 访问凭证 |
| `namespace` | bronze / silver 逻辑空间 |

## 工程实现与流程

### 1. Materialize（物化）10 步动作

1. 读取 env 与配置（catalog / warehouse / endpoint）。
2. 加载 SQL Catalog。
3. Ensure namespace（bronze / silver）。
4. Ensure table schema（以 source of truth 为准）。
5. 读取输入（Week03 源表或对象存储）。
6. 按 mapping 转换（Arrow / writable data）。
7. Append / Overwrite（形成新状态）。
8. 产生 snapshot（进入历史）。
9. Inspect（查看 history / files / snapshots）。
10. 输出 report（写入可验收证据）。

### 2. 最小防御线（Minimum Defenses）

- **dry-run**：展示计划，不污染表状态。
- **materialization plan**：明确映射关系，防止 Agent 乱猜。
- **schema validation**：写入前确认字段 / 类型 / nullable。
- **deterministic dedupe**：结果可预测，处理重复输入。
- **idempotency**：重跑无副作用。

### 3. PyIceberg API 常用动作

| API | 作用 |
| :--- | :--- |
| `load_catalog()` | 加载配置 |
| `create_namespace()` / `list_namespaces()` | 确保逻辑空间 |
| `catalog.create_table()` | 确保最小 4 表 Schema |
| `catalog.load_table()` | 定位已有表 |
| `table.append()` / `table.overwrite()` | 形成新 Snapshot |
| `table.scan().to_arrow()` | 验证数据可读 |
| `inspect.history / snapshots / files` | 产出报告数据 |
| `update_schema().add_column()` | Schema 演进演示 |

## 工程工件与交付（Engineering Handoff）

### 1. 结构化占位

```bash
# Week04 输出工件准备
touch docs/blueprints/week04/catalog_runtime_plan_v1.md
touch runbooks/week04/README.md
touch reports/week04/schema_evolution_demo_notes.md
```

### 2. 运行手册主干（runbooks/week04/README.md）

- **环境启动**：compose / devbox / env 文件。
- **Catalog 检查**：加载、namespace、table。
- **Materialize 执行**：目标表、dry-run、写入边界。
- **Inspect**：snapshots / history / files。
- **异常处理**：按错误层级排查。
- **Report 输出**：结果写入 `reports/week04`。

## 错误排查清单（Troubleshooting）

| 现象 | 排查方向 |
| :--- | :--- |
| **Catalog load 失败** | 检查 catalog type / uri / env，打印配置来源 |
| **MinIO 连不上** | 区分 localhost 与容器内服务名 |
| **Bucket 不存在** | 检查 warehouse root 是否可写及凭证 |
| **Schema 不匹配** | 回到 `iceberg_schemas.py` 检查 source of truth |
| **重跑重复** | 检查 dedupe / idempotency 策略及 key |
| **Inspect 无 Snapshot** | 确认 append / overwrite 是否真正发生 |

## 验收标准（Demo Checklist）

1. Catalog 成功加载。
2. Namespace（bronze / silver）成功 ensure。
3. 最小 4 表 Schema 成功 ensure。
4. 至少完成 1 Bronze + 1 Silver 的 append 操作。
5. 能观察到状态证据链（snapshots / history / files）。
6. 完成 add-column schema evolution 演示并记录。

## 核心避坑指南（Anti-Patterns）

- **禁止硬编码**：endpoint / secret 必须走环境。
- **禁止空表验收**：必须有数据写入产生的 snapshot 证据。
- **禁止盲目过度封装**：Dagster 本周仅作 thin wrapper，重点在 PyIceberg 状态而非调度。
- **禁止伪造输出**：PPT 必须与落地代码一致，确保学生可复现。

## 总结判断

- Week04 不是重型基础设施秀。
- Materialization 不只是写入成功，而是形成可 inspect 的 snapshot。
- 没有 baseline，就没有真正优化。下一讲将基于这些 inspect 结果建立性能基线。
