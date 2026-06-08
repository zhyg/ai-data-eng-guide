# 04 · 把 Data Contract 做成工程门禁

> Week 02 · Lesson 04 · Contract —— 做门禁
> 把 Data Contract 做成工程门禁 —— Schema 之上还有 5 件事

很多团队提到 Data Contract，第一反应是「写一份 JSON Schema」。JSON Schema 当然要写 —— 但只写 Schema 的契约，是写给评审会看的，不是给生产系统用的。

这一讲讲清楚：**一份能扛得住生产的 Data Contract，Schema 只是它的一层皮，后面还有语义、质量、SLA、兼容性、Owner 五件事必须固化下来。**

---

## 这节课先解决什么

### 为什么它重要
- 为什么 JSON Schema 校验通过了，下游仍然在用错的数据。
- 为什么很多团队的 Data Contract 写完之后没人用，最后变成「文档」。
- 为什么 Schema 改动「向后兼容」这件事，要写进契约。
- 为什么 Data Contract 必须能在 CI 里跑、而不是写在 Confluence 里。

### 学完你能做到
- 说清楚 Schema / Contract / Tests / Gate 这四个对象的区别和协作。
- 用 ODCS（Open Data Contract Standard）的结构写一份能机读的 contract。
- 区分 additive / breaking / coordinated 三类 schema 变更，并制定对应的兼容性策略。
- 把 contract 接入 pytest 和 CI —— 让契约真正成为代码变更的拦截器。

---

## 核心论点：Contract 是 Schema 的生产级超集

**Schema 回答「像不像」，Data Contract 回答「够不够格进入系统」。**

Schema 的范畴只到结构正确 —— `type`、`enum`、`required`、`format`。而 Data Contract 还要回答：

- **语义**对不对（`status=closed` 到底是什么意思）？
- **质量**够不够（completeness / freshness / uniqueness 有没有达标）？
- **SLA** 守住没（延迟、可用性）？
- **兼容性**怎么办（additive / breaking / coordinated）？
- **Owner** 是谁（出问题先找谁）？

> 换句话说 —— Contract 是 Schema 的「生产级超集」。

---

## 行业标准：不是拍脑袋，是已经成型的方向

| 标准 | 形态 | 要点 |
| --- | --- | --- |
| **ODCS v3.1**（Open Data Contract Standard） | 由 Bitol 推动的开源标准 | 把 contract 拆成 8 个 section：description / schema / quality / team / SLA / lifecycle / pricing / custom。 |
| **dbt Model Contracts** | Upfront Guarantees | dbt 1.5+ 把 contract 做成 model 的内建属性 —— 在构建时校验，构建失败 = 上线失败。 |
| **DataHub Assertions** | Contracts via Tests | 把 contract 落地成 assertion —— 发现违反规则的数据质量测试，本身就是 contract 的运行时形态。 |
| **Iceberg Schema Evolution** | Metadata Change | 原生支持 add / drop / rename / update / reorder —— 很多变化是 metadata change，不需要重写数据文件。 |

> Data Contract 不是新概念 —— 是数据工程界已经在走的路。Week2 要做的是把这条路接进 AI 系统的输入端。

---

## 契约 6 层结构：一份生产级 contract 必须包含

### Schema 层（STRUCTURAL）
- `type` / `enum` / `required` / `format`。
- 字段顺序 / null 策略。
- 版本号语义化（semver）。
- 可由 JSON Schema 校验。

### Semantics 层（SEMANTIC）
- `status=closed` 的业务含义。
- 时间字段的口径。
- 枚举的演进规则。
- 业务术语 → 工程字段映射。

### Quality + SLA 层（OPERATIONAL）
- completeness（必填率）。
- freshness（数据时延）。
- uniqueness（去重）。
- compatibility（兼容性策略）。

> 完整的 6 层为：**Schema（结构）、Semantics（语义）、Quality（质量）、SLA（时延/可用性）、Compatibility（兼容性）、Owner（责任人）。**

---

## 真实交付物：`ticket_contract.json`

```json
// contracts/data/ticket_contract.json
{
  "$schema": "https://datacontract.com/odcs-v3.1.json",
  "kind": "DataContract",
  "apiVersion": "v3.0.0",
  "id": "tic.northstar_workspace.support_ticket",
  "info": {
    "title": "Support Ticket",
    "owner": "support-platform",
    "domain": "support_ops",
    "criticality": "P1"
  },
  "schema": {
    "type": "object",
    "required": ["ticket_id", "status", "created_at"],
    "properties": {
      "ticket_id":  {"type": "string", "format": "uuid"},
      "status":     {"type": "string",
                     "enum": ["new", "pending", "in_progress", "resolved", "closed"]},
      "created_at": {"type": "string", "format": "date-time"}
    }
  },
  "semantics": {
    "status_definitions": {
      "in_progress": "已分配且客服已首次响应；非仅已分配"
    }
  },
  "quality": {
    "completeness": {"status": 1.0, "created_at": 1.0},
    "freshness_minutes": 15
  },
  "compatibility": "additive_only_without_review"
}
```

> **讲师解读**
> - `apiVersion` / `id` 让 contract 像代码一样有版本。
> - `schema` 是结构边界 —— JSON Schema 子集，可以被自动校验。
> - `semantics` 把「`in_progress` 到底什么意思」固化下来 —— 这一段就是 Lesson 1 那个事故的解药。
> - `quality` 是 SLA —— 15 分钟内必须到达，否则 freshness 不达标。
> - `compatibility` 是兼容性策略 —— 任何 breaking change 必须先评审。

---

## 兼容性策略：三类 Schema 变更的判断标准

| 变更类型 | 举例 | 兼容性影响 | 处置策略 |
| --- | --- | --- | --- |
| **Additive** | 新增可选字段 / 新增枚举值（且业务上是扩展） | 向后兼容 | 可独立上线，contract 自动升 minor |
| **Breaking** | 删字段 / 改字段类型 / 改枚举语义 | 不向后兼容 | 必须协调下游，contract 升 major |
| **Coordinated** | 改业务口径（如 `status=closed` 加新条件） | 结构兼容但语义变了 | 必须先发 ADR，上下游同步上线 |

> 生产里的事故 80% 来自第三类 —— 结构没坏，但语义变了，所有人以为是 additive，其实是 coordinated。

---

## 门禁动作：Contract 违反时该怎么办

| Gate Action | 什么情况触发 | 系统行为 | 下游影响 |
| --- | --- | --- | --- |
| `accept` | 所有校验通过 | 正常入湖 | 无 |
| `warn` | 可选字段缺失 / 数据质量低于阈值但未失败 | 入湖 + 告警 | 通知 owner，不阻塞流水线 |
| `quarantine` | 部分行数据违反 contract | 违规行进入隔离区，其他行正常 | 触发人工 review，48h 内处理 |
| `reject` | Schema breaking / 关键字段缺失 / PII 违规 | 整批数据拒绝入湖 | 阻塞流水线，触发 P1 告警 |

> Gate 不是 pass / fail 二分 —— 它是工程团队在「数据完美」和「业务永不中断」之间的折中。

---

## Contract 必须能在 CI 里跑 —— pytest 实战

```python
# tests/contract/test_ticket_contract.py
import json, pytest, jsonschema

CONTRACT = json.load(open("contracts/data/ticket_contract.json"))

def test_schema_valid_sample():
    sample = {"ticket_id": "uuid-1", "status": "pending",
              "created_at": "2026-05-18T10:00:00Z"}
    jsonschema.validate(sample, CONTRACT["schema"])

def test_status_enum_drift():
    """Lesson 1 事故的回归测试 —— in_progress 必须显式声明"""
    enums = CONTRACT["schema"]["properties"]["status"]["enum"]
    assert "in_progress" in enums
    assert "in_progress" in CONTRACT["semantics"]["status_definitions"]

def test_freshness_sla_defined():
    assert CONTRACT["quality"]["freshness_minutes"] <= 30

def test_owner_assigned():
    assert CONTRACT["info"]["owner"] != ""
```

```bash
# CI 流水线（GitHub Actions）
pytest tests/contract/ -v
# ↑ 任何一项失败，整个 PR 不能合并。
```

> **讲师解读**：这就是 Contract 从「文档」变成「门禁」的关键一步。`test_status_enum_drift` 是 Lesson 1 那个 `pending → in_progress` 事故的回归测试 —— 上游再想偷偷改语义，这个测试会先 fail。把 pytest 接进 CI，contract 就从「会议纪要」变成了「代码不通过就上不了线」。这是 Data Contract 真正落地的形态。

---

## Contract 的所有权 —— 不写清楚就没人维护

| 对象 | 主 Owner | 协作方 | 什么时候找他 |
| --- | --- | --- | --- |
| Schema 结构 | 上游系统团队 | AI 平台 / Data Platform | 字段变更、新增字段 |
| Semantics 语义 | 业务方 + 上游 | AI 平台 | 业务口径变化（如 status 含义） |
| Quality SLA | Data Platform | 上游 + AI | 延迟、可用性、完整性指标 |
| PII Policy | 合规 / 安全团队 | 全员 | 新增敏感字段、合规变化 |
| Contract Tests | AI Platform | 上游 + QA | 回归测试、Bad case |

> 这张表不是组织架构图 —— 是 contract 出问题时的 routing table，能让 MTTR 从「几小时」降到「几分钟」。

---

## Contract 落地里最容易踩的 5 个坑

1. **把 Contract 写进 Confluence**：一份契约写进 Wiki，所有人都看不见。要么写在 Git 里（`contracts/data/*.json`），要么不要写。
2. **契约校验和 ingest 分离**：契约通过了，但 ingest 不读它 —— 等于没写。必须让 ingest pipeline 在每次入湖前都校验 contract。
3. **所有变更都按 breaking 处理**：过度保守会让团队畏惧变更 —— 只有真正 breaking 才走重协调流程，additive 应该秒级上线。
4. **用 Schema 自动生成 Contract**：反了。Contract 应该指导 Schema，而不是从 Schema 反推。否则永远只有结构、没有语义。
5. **忘记 sunset 旧契约**：V1 / V2 同时存在了 6 个月没人下线 V1 —— 契约的版本也需要生命周期管理。
