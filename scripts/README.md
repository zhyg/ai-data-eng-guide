## cookie
在极客时间（Geekbang）的 API 请求中，与**用户认证和登录状态（Authentication）**最核心的三个 Cookie 字段是：

  1.  GCESS ：极客时间的核心 Session 凭证（最关键的认证 Token）。
  2.  GCID ：极客时间客户端/用户 ID。
  3.  GRID ：极客时间注册用户 ID（通常与  GCID  保持一致）。

### 建议操作

为了让您的爬取/获取脚本 fetch_article.py 恢复正常访问，您需要将  curl  命令中的  GCESS 、 GCID  和  GRID 对应的值更新到 config.json 的  "cookies"  节点下。

## 下载字幕
使用 @[scripts/fetch_article.py] 获取 https://u.geekbang.org/lesson/857?article=986218 对应的字幕内容，放到 week6/manuscripts/ 下，文件名称：6.资产化数据工厂实践.md