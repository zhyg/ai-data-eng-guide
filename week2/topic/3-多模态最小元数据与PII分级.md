# 03 · 多模态最小元数据与 PII 分级

> Week 02 · Lesson 03 · Metadata —— 建接口
> Metadata 是运行时接口，PII 是动作矩阵

上一讲我们把数据建模成了「对象」。今天进一步 —— 把对象的属性从「给人看的备注」升级成「系统真正在运行时消费的接口」。同时把 PII 从 `true / false` 这种粗暴的二分，升级成一个「分级 × 动作」的动作矩阵。

> 这两件事做好了，后面的 Contract 和 Manifest 才有可能落地。

---

## 这节课先解决什么

### 为什么它重要
- 为什么 metadata 看起来「都差不多」，但生产里有的能撑住、有的撑不住。
- 为什么 PII 写成 boolean（是 / 否）会在合规审查时被一票否决。
- 为什么文档、音频、视频共用一套 metadata 框架但又必须有专属字段。
- 为什么大厂的 metadata 越做越简单，反而是新团队总想做很复杂。

### 学完你能做到
- 画出 metadata 的 runtime 消费图 —— RAG / Tool / Audit / Access 怎么读它。
- 区分「最小元数据集」和「扩展元数据集」—— 别一上来就贪多。
- 用 PII Action Matrix 把每一级敏感度对应到 mask / redact / route / block 的具体动作。
- 在 OmniSupport 仓库里读懂 `metadata_minimums.md` 和 `pii_policy_matrix.csv`。

---

## 核心论点：Metadata 是运行时接口

Metadata 不是「备注字段」—— 是 RAG / Tool / Audit / Access 共用的运行时接口。

很多团队把 metadata 当 Excel 里的「备注列」对待 —— 能填就填，不能填也无所谓。生产级 AI 系统里完全反过来：**metadata 是被四个不同服务在每次请求里都要读取的合同。**

- 检索要靠它过滤候选；
- 引用要靠它回指来源；
- 审计要靠它定位现场；
- 权限要靠它前置拦截。

> 所以 metadata 设计的核心问题不是「字段多不多」，而是「字段能不能被这四个服务稳定消费」。

### Metadata 的四个消费方

| 服务 | 作用 | 依赖字段 |
| --- | --- | --- |
| **Retrieval** | 过滤候选 | 按 tenant / role / 时间窗 |
| **Citation** | 回指来源 | `page_no` / `bbox` / 时间戳 |
| **Audit** | 定位现场 | `source_fingerprint` / version |
| **Access** | 前置拦截 | PII / role / lifecycle |

> 把 metadata 设计当成 API 设计：它有调用方，有契约，有版本，有变更影响范围 —— 而不是「我们存一下，将来万一用得上」。

---

## 共享核心字段：所有模态都必须有的 5 个 metadata

| 字段 | 含义 | 哪个服务依赖它 | 出错时表现 |
| --- | --- | --- | --- |
| `asset_id` | 资产稳定唯一标识 | 全部 | 无法做 bad case 回退、无法版本对齐 |
| `source_fingerprint` | 内容指纹（hash） | Audit / Lineage | 同一份内容多次入湖不去重 |
| `source_version` | 资产版本号 | RAG / Audit | 回答可能引用已废弃版本 |
| `ingest_batch_id` | 入湖批次号 | Audit / Replay | 出问题无法定位是哪批数据 |
| `license_tag` | 许可类型 | Access / 合规 | 输出引用了不可分发内容 |

> 这 5 个字段是「最小集」—— 少一个，下游某一层就会有运行时盲区。

---

## 模态专属字段：共享核心之外的扩展

### Document
- `page_no`：精准回页。
- `bbox`：图表 / 表格定位。
- `section_path`：结构化上下文。
- `doc_version`：版本对齐。
- `lang`：多语种 RAG 路由。

### Audio
- `call_id`：通话维度聚合。
- `speaker_role`：客户 / 客服。
- `start_ts` / `end_ts`：时间窗。
- `confidence`：ASR 降级信号。
- `pii_redaction_flag`：是否已脱敏。

### Video
- `video_id`：视频维度。
- `segment_ts`：片段时间。
- `frame_ts`：关键帧时间。
- `transcript_ref`：音轨外键。
- `image_caption` / `ocr_text`：多模态文本。

---

## PII 不是 true / false，是一张动作矩阵

合规审查一定会问的一个问题是：你的系统对 PII 做了什么？回答「我们标记了 `is_pii = true`」一定会被打回。

正确的答案是 —— 我们对每一级 PII，在每一种使用场景下，都有明确的 mask / redact / route / block 动作。

### PII 分级矩阵：从 P0 到 P3

| 等级 | 示例 | 存储动作 | 检索动作 | 输出动作 |
| --- | --- | --- | --- | --- |
| **P0 · 公开** | 产品文档 / 公开 FAQ | 原样存储 | 开放检索 | 允许引用 |
| **P1 · 内部** | 工单标题 / 客服日志摘要 | 原样存储 + tenant 标记 | tenant 内可检索 | 允许（带 tenant 范围） |
| **P2 · 敏感** | 客户姓名 / 邮箱 / 公司名 | mask 化存储 | role-based 召回 | 默认 mask，需提权 |
| **P3 · 高敏** | 电话 / 地址 / 银行卡 / 身份证 | redact 后存储 | 不参与召回 | block，永不输出 |

> 这张表不是为了好看 —— 它是 contract 里能机器读取的策略源，也是 access boundary 的判断依据。

### 四个动作的工程定义

| 动作 | 工程定义 | 什么时候用 |
| --- | --- | --- |
| **Mask** | 保留长度和位置，字符替换为 `*` | 展示给授权用户，但需要隐藏明文（如客服界面） |
| **Redact** | 完整移除该字段或片段 | 存入索引前永久去除（如电话进入向量库前） |
| **Route** | 走更严格的链路：人工审、加审计 | P2 以上字段进入 Agent 工具调用前的兜底 |
| **Block** | 直接拒绝该请求 / 输出 | 低权用户访问 P3 内容；模型输出包含 P3 字段时 |

> Mask 和 Redact 的差别不是术语之争 —— 是「数据进入索引前」和「数据展示给前端」的两个不同位置。

---

## 真实交付物：`pii_policy_matrix.csv`

```csv
# data/policies/pii_policy_matrix.csv
field_name,asset_type,pii_level,storage_action,retrieval_action,output_action
customer_name,ticket,P2,mask,role_based,mask_default
customer_phone,ticket,P3,redact,exclude,block
customer_email,ticket,P2,mask,role_based,mask_default
agent_id,ticket,P1,plain,tenant_scoped,allow
doc_author,document,P0,plain,public,allow
speaker_id,audio,P2,mask,role_based,mask_default
frame_ocr_text,video,P1,plain,tenant_scoped,allow
# 注：这份文件会被 ingest pipeline 和 RAG service 同时读取
#     —— 任何字段调整都必须走 contract change 流程。
```

> **讲师解读**：这就是「PII 不是布尔」的工程化形态。一行 = 一个字段 × 一个模态 × 三个位置的动作。Storage 决定数据怎么落地；Retrieval 决定召回时怎么过滤；Output 决定最终展示的形态。这份 CSV 是机器可读的 —— 可以直接被 contract test 用来验证 ingest 是否合规。生产团队不应该用文档讨论 PII，应该用这张表。

---

## 为什么这件事重要 —— 行业里已经发生的事

| 来源 | 主张 | 含义 |
| --- | --- | --- |
| **GDPR / CCPA** | 可解释 + 可追溯 | 一次合规审计要求你能回答：这条客户信息在 6 个月内被哪些系统读取过？metadata 不完整 = 罚款。 |
| **NIST AI RMF** | Trustworthy AI | 把数据来源、隐私、可追溯作为四大支柱之一 —— 没有 metadata 框架完全做不到。 |
| **Anthropic** | Provenance over capability | 客户更愿意相信「能解释来源」的 AI，而不是「答得更准」的 AI。 |
| **OpenAI** | Trace + Audit | Structured Outputs + Function Calling 的最新版本里，trace 和 audit 字段是默认必选的。 |

> Metadata 不是工程细节 —— 它是合规、信任、可演进的根基。

---

## Metadata 设计里 3 个最常见的坑

| 坑 | 为什么会犯 | 正确做法 |
| --- | --- | --- |
| 字段一上来就 50 个 | 想做得完整 | 先定最小集 5 个 + 模态扩展 5 个，剩下的按需扩展 |
| 用业务术语命名（如 `doc_type`） | 看起来直观 | 用工程语义命名（如 `asset_subtype`）—— 业务语义会变，工程语义不会 |
| Metadata 跟正文一起存 | 懒，方便 | 正文 vs metadata 分开 —— metadata 必须能独立查询、独立索引 |

> 记一个原则：metadata 越简单越好 —— 但每一个保留下来的字段，都必须有明确的下游消费方。
