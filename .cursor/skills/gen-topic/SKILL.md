---
name: gen-topic
description: "从极客时间课程数据生成某一周的 topic 文件。完整流程：获取 class_info.json、生成 index.txt、下载工程实践字幕、将讲义 PDF 整理为 topic markdown。当用户要求生成 topic、整理讲义、准备某一周的内容时使用。"
---

# 生成课程 Topic

从极客时间课程 API 获取课程信息，结合讲义 PDF 生成结构化的 topic markdown 文件。

## 前置条件

1. `scripts/config.json` 存在且 cookies 有效（GCESS、GCID、GRID 未过期）
2. 目标周目录下有讲义 PDF 文件（如 `week8/Week08-RAG服务化.pdf`）
3. `scripts/fetch_article.py` 可用

## 工作流程

### 第一步：获取课程信息

```bash
python scripts/fetch_article.py getinfo > data/class_info.json
```

检查返回的 `code` 字段。如果 `code` 不为 0（如 -1，提示「用户没有大学权限」），说明 cookies 过期，提示用户更新 `scripts/config.json` 中的 GCESS、GCID、GRID。

### 第二步：解析目标章节，生成 index.txt

从 `data/class_info.json` 中的 `data.lessons` 数组定位目标章节。

章节定位规则：
- `lessons` 数组中每个元素有 `chapter_name` 字段，格式为「N：章节标题」（如「八：检索 x 生成的一体化工程闭环」）
- 用户说「第八周」或「week8」对应 `chapter_name` 中带「八」的章节
- 前面的「学习手册」「直播回放」「开学第一课」不是正式章节，正式章节从「一：...」开始

提取文章标题列表，排除「课件下载」和「课后作业」，保存到 `weekN/weekN-index.txt`。每行一个标题，保留原始编号前缀。

### 第三步：获取工程实践字幕

最后一节通常是工程实践课（标题含"实践""实现"等），在讲义 PDF 中没有专门对应的章节，需要通过 API 获取字幕。

从 `data/class_info.json` 中找到该文章的 `article_id`，执行：

```bash
mkdir -p weekN/manuscripts
python scripts/fetch_article.py get --class-id 857 <article_id> > "weekN/manuscripts/<文章标题>.md"
```

文件名与文章标题保持一致。

### 第四步：整理讲义为 topic markdown

读取讲义 PDF 和 index.txt，为每节课生成一个 markdown 文件，保存到 `weekN/topic/` 目录下。

#### 文件命名

文件名与 index.txt 中的标题保持一致，如 `1.纯向量检索为啥在生产里翻车.md`。

#### PDF 与 index 的对应关系

讲义 PDF 通常按 LESSON 划分章节（L01、L02...），每个 LESSON 有明确的开场标记（如「L01 开场」「LESSON 01」）。将 PDF 的 LESSON 按顺序对应 index.txt 中的标题。注意：
- 一个 LESSON 可能跨多页 PDF
- 最后一节（工程实践）在 PDF 中没有专门章节

#### 前 N-1 节：从讲义 PDF 提取

对于讲义中有对应章节的内容，优先提取以下要素（如果讲义中存在）：

1. **核心问题/目标**：本节要解决什么问题
2. **真实场景/案例**：开场的翻车故事或典型问题（用通用描述，保留关键信息）
3. **原理/机制**：技术概念、对比表格、数据
4. **工程实践要点**：代码要点的文字描述（不贴代码）、选型对比表格
5. **行业信号**：Industry Signals 部分的方向性总结
6. **反模式**：Anti-Patterns 表格（如果有的话）

如果讲义中没有上述要素，根据 PDF 实际结构提取关键内容。

保留讲义中的对比表格和数据，这些是核心内容。

#### 最后一节：工程实践

结合讲义全文（了解整体架构和概念）和字幕内容（了解实践细节）生成。

内容要求：
- 描述整体架构和链路（如处理流程图）
- 说明关键模块的职责和关系
- 列出数据模型扩展（新增的表和字段）
- 描述契约测试和健康检测的内容
- 总结本周交付物
- **避免出现代码**，用文字描述代码的逻辑和要点

## 输出规范

### markdown 格式

- 一级标题：`# N. 文章标题`
- 二级标题划分主要章节
- 善用表格呈现对比、选型、指标等结构化信息
- 善用列表呈现步骤、要点
- 流程用文本流程图：`A → B → C → D`

### 内容原则

1. 保留讲义中的关键数据和对比（NDCG 提升、成本对比、精度数据等）
2. 保留反模式（Anti-Patterns）表格，这是实战价值最高的内容
3. 保留行业信号（Industry Signals），帮助理解技术趋势
4. 不贴代码，但保留代码要点的文字描述
5. 参考 `week7/topic/` 下已有文件的风格和结构

## 校验清单

每个 topic 文件完成后检查：

- [ ] 文件名与 index.txt 中的标题一致
- [ ] 核心概念没有遗漏（对照 PDF 对应 LESSON 的所有页面）
- [ ] 表格数据准确（直接从 PDF 提取，不改写数字）
- [ ] 不包含代码块（工程实践节尤其注意）
- [ ] 最后一节结合了字幕内容，覆盖了架构、模块、测试、交付物
