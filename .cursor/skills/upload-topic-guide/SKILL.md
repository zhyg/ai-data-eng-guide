---
name: upload-topic-guide
description: "把本地 topic-guide 目录下的导学 Markdown 文件批量上传到飞书知识库。当用户要求上传导学、发布导学到飞书、同步 topic-guide 到知识库时使用。"
disable-model-invocation: true
---

# 上传导学到飞书知识库

把指定周的 `topic-guide/` 目录下的 Markdown 导学文件，批量上传到飞书知识库 `ai-data-eng-guide` 下对应的子目录节点中。

## 前置条件

1. **lark-cli 已安装**：确认 `lark-cli` 可用。
2. **用户已授权**：需要 `wiki:space:retrieve`、`wiki:node:retrieve`、`wiki:node:create` 三个 scope。如未授权，按下方"认证流程"操作。
3. **导学文件已生成**：目标 `weekN/topic-guide/` 目录下有待上传的 `.md` 文件。

## 输入

用户需提供（或从上下文推断）：

- **周编号**：如 `week6`、`week7`，用于定位本地目录和知识库子目录名称。
- **知识库目录名**（可选）：默认为 `weekNN`（两位数，如 `week06`、`week07`）。

## 工作流程

### 1. 认证检查

```bash
lark-cli wiki +space-list --as user --format json
```

如果返回 `need_user_authorization` 或 `token_missing`，执行认证流程：

```bash
lark-cli auth login \
  --scopes "wiki:space:retrieve wiki:node:retrieve wiki:node:create" \
  --no-wait --json
```

从输出中提取 `verification_url` 和 `device_code`，生成二维码并展示给用户：

```bash
lark-cli auth qrcode --url "<verification_url>" --output auth-qr.png
```

将二维码图片和 URL 展示给用户，等用户确认授权后：

```bash
lark-cli auth login --device-code "<device_code>"
```

### 2. 定位知识库根节点

在个人文档库中找到 `ai-data-eng-guide` 节点：

```bash
lark-cli wiki +node-list --space-id my_library --as user --format json
```

从返回的节点列表中找到 `title` 为 `ai-data-eng-guide` 的节点，记录其 `node_token`（下称 `ROOT_TOKEN`）。

### 3. 检查或创建周目录节点

先列出 `ai-data-eng-guide` 下已有的子节点：

```bash
lark-cli wiki +node-list --parent-node-token <ROOT_TOKEN> --as user --format json
```

- 如果目标周目录（如 `week06`）已存在，记录其 `node_token`（下称 `WEEK_TOKEN`）。
- 如果不存在，创建新节点：

```bash
lark-cli wiki +node-create \
  --parent-node-token <ROOT_TOKEN> \
  --title "week06" \
  --as user --format json
```

从返回结果中获取 `WEEK_TOKEN`。

### 4. 批量上传文档

列出本地 `weekN/topic-guide/` 目录下的所有 `.md` 文件，按文件名顺序逐个上传：

```bash
lark-cli docs +create \
  --api-version v1 \
  --title "<文件名去掉.md后缀>" \
  --markdown "@weekN/topic-guide/<文件名>" \
  --wiki-node <WEEK_TOKEN> \
  --as user --format json
```

可并行上传多个文件以提高效率（同时发起多个 Shell 调用）。

### 5. 验证与汇总

上传完成后，列出周目录下的所有节点确认：

```bash
lark-cli wiki +node-list --parent-node-token <WEEK_TOKEN> --as user --format json
```

以表格形式汇总所有文档的标题和链接。

## 注意事项

- `--wiki-node` 和 `--wiki-space` 互斥，创建文档时只传 `--wiki-node`。
- `--markdown` 参数用 `@` 前缀指定本地文件路径（相对于当前工作目录）。
- 需要先 `cd` 到项目根目录，确保 `@weekN/topic-guide/xxx.md` 路径正确。
- 如果目标周目录下已有同名文档，会创建新文档而非覆盖，需要人工确认是否清理旧文档。

## 校验清单

- [ ] lark-cli 用户授权有效
- [ ] `ai-data-eng-guide` 根节点存在
- [ ] 目标周目录节点已创建
- [ ] 所有 `.md` 文件上传成功（返回 `"ok": true`）
- [ ] 汇总表格包含每篇文档的标题和可访问链接
