# 踩坑大全（8 条，全部实测）

> 排障总原则：**以中继日志为准**，不要相信界面上显示的文字（它会"过期"）。
>
> 参考：教程原文（可对照排错）https://juejin.cn/post/7621026569348513802
> 本桥 = "教程方案 + 本机加固补丁"（补丁清单见 `vendor/PATCHES.md`）——排错请先按本文档，因为下面 8 条里有一半是原教程未覆盖的坑。

## 诊断三件套

```bash
# ① 端口与连接（Figma 进程连接 = 插件在线）
netstat -ano | findstr 3055

# ② 中继日志关键行（join / close / 心跳 / 信标）
#    日志在 ~/.workbuddy-ai/tools/figma-bridge/socket.log
grep -E "joined channel|Client closed|heartbeat|keepalive" socket.log | tail -20

# ③ 自动狙击命中记录（若启用）
tail -20 _probe_hits.log
```

标准诊断顺序：**插件在不在线**（② 的 join/close + ①）→ **在不在同一频道**（② 的 "No other clients"）→ **工具调用是否超时**（调用输出）→ 才怀疑"桥坏了"。

---

## 坑 1：连上约 2 分钟必断（Bun 空闲断连）

- **现象**：插件 Connected 后约 120 秒被断开，日志无任何异常原因。
- **原因**：Bun 运行时默认掐断空闲 120 秒的 WebSocket；插件平时没有消息往来。
- **解决**：`socket.ts` 的 websocket 配置加 `idleTimeout: 0`（vendor 里已是修复版）。
- **验证**：静默连接 140 秒后仍可正常通信（实测 ✓）。

## 坑 2：面板一关，连接立即销毁（close code 1001）★头号坑

- **现象**：连接活着好好的，突然断开；日志 `Client closed: code=1001`。
- **原因**：1001 = "going away"，只会出现在**页面/面板离开**时——关面板、按 Esc、切插件、切文件、退出 Figma。插件源码本身没有任何自动关闭逻辑（已排查）。
- **实测**：有一次连接只活了 **4 秒**（16:27:30 连上 → 16:27:34 断开，1001）——就是复制完频道号后顺手关了面板。
- **解决**：告知用户"面板就是电话机，必须保持开着"。重开后**频道号会变**，要新号。

## 坑 3：界面显示 Connected，但命令发不到（过期残留）

- **现象**：用户说"显示着 Connected"，但命令全部 `Request to Figma timed out`。
- **原因**：连接其实早已断开，但面板文字（或用户记忆）还停留在上一次成功状态；中继重启也会造成这种"假 Connected"。
- **解决**：永远以中继日志为准（有没有现在的 join/心跳）；先让用户重开插件、报**新**频道号。

## 坑 4：每次重开插件，频道号都会变

- **现象**：用户重开插件后，拿旧频道号发命令永远打空气（日志 `No other clients in channel`）。
- **原因**：插件每次启动随机生成 8 位频道名——设计如此。
- **解决**：每轮对话都让用户报最新频道号；重开插件 = 新号。自动重连（升级版插件）不会变号，只有"重开"才变。

## 坑 5：读不到矢量图形（服务端过滤 VECTOR）

- **现象**：`get_node_info` 返回的 children 不完整，明明画布上有图形却看不到。
- **原因**：MCP 服务端的 `filterFigmaNode` **会把 VECTOR 节点整个剔除**（`return null`）。
- **解决**：用 `scan_nodes_by_types`（插件侧扫描、服务端不过滤）拿矢量清单：
  `figma_call.py <频道> scan_nodes_by_types '{"nodeId":"<画板>","types":["VECTOR","TEXT","FRAME"]}'`

## 坑 6：扫描类工具超时（并发请求互抢）

- **现象**：`scan_text_nodes` 等带分块的扫描工具报超时，但普通读写正常。
- **原因**：分块扫描依赖"当前活动请求"状态，与后台并发轮询（probe_daemon / auto_watcher）互相踩。
- **解决**：做扫描/写操作前，先停掉后台轮询进程；完成后再按需恢复。

## 坑 7："幽灵"进程（node.exe / 残留 MCP 客户端）

- **现象**：杀掉了探测器进程，但端口连接里还挂着一个 node.exe。
- **原因**：`bun x cursor-talk-to-figma-mcp` 实际以 **node.exe** 运行（bunx 临时目录里的 dist/server.js）；父进程被强杀后子进程不退出。
- **解决**：需要时按命令行清理：
  ```powershell
  Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -like '*cursor-talk-to-figma*'} | Select ProcessId,CommandLine
  # 然后 taskkill /PID <pid> /F
  ```

## 坑 8：首次 join 报 "Not connected to Figma"（启动竞态）

- **现象**：刚 Connect 就发命令，join_channel 报错或命令超时。
- **原因**：插件与该频道的连接尚未稳定。
- **解决**：等 2~3 秒再 join；`figma_e2e_check.py` 已内置"等稳定 + 重试"，优先用它。

---

## 附：几个"看起来像故障"的正常行为

| 行为 | 说明 |
|---|---|
| `set_text_content` 后图层名也变了 | 该工具的副作用：图层名同步为新文本 |
| 导出 PNG 里元素被裁 | 元素超出画板边界（如笔尖伸出画板 8px），导出按画板裁剪 |
| `get_document_info` 只有页面/画板名字 | 它只给总览；细节要 `get_node_info` / `scan_*` |
| 日志里 `Client closed: code=1006` | 异常断开（进程被杀/强退），不是面板关闭（那是 1001） |
