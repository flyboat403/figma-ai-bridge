# vendor 补丁说明（与上游的差异）

上游：`grab/cursor-talk-to-figma-mcp` v0.3.5（本机实测版本）。
本目录中的文件在其基础上加了以下补丁，**升级上游时注意不要被覆盖**。

## 1. socket.ts（中继服务）

| 补丁 | 原因 |
|---|---|
| `websocket.idleTimeout: 0` | Bun 默认会掐断**空闲 120 秒**的 WebSocket —— 插件平时无消息往来，连上约 2 分钟必被断开（实测复现多次）。置 0 禁用空闲断连。 |
| 时间戳日志（本地时间 HH:mm:ss） | 排障时能精确对齐事件时刻 |
| `allClients` 全量客户端追踪 | 日志能显示 `New client connected (sockets: N)` |
| `close` 处理器记录 `code / reason / channels` | **断连取证核心**：1001=页面离开（面板被关）、1006=异常断开 |
| 30s 心跳 `ws.ping()` | 保持链路活跃 + 日志心跳行（探测插件存活） |
| keepalive 消息 → 一行"存活信标"日志 | 识别升级版插件 + 确认插件在线（不打印完整报文） |

**无外部依赖**：socket.ts 只 import Bun 内建模块，`bun run src/socket.ts` 即可运行。

## 2. cursor_mcp_plugin/ui.html（Figma 插件界面）

| 补丁 | 原因 |
|---|---|
| 断线自动重连（2~15s 退避，**沿用同一频道**） | 减少断线后的手工重连；`manualDisconnect` 标志保证手动断开不触发 |
| 面板内诊断区 `#diag` + 存活行 `#alive-line` | 断连代码（❌ CLOSE code=…）直接上屏，肉眼可见 |
| 20s 保活 keepalive | 客户端侧主动保活（配合中继信标） |
| 断线时 `notify` 弹窗 | 用户切到画布也能看到提醒 |

插件其余文件（manifest.json / code.js / setcharacters.js）与上游一致，未改动。

## 3. 升级上游的步骤

1. 从上游重新拉取/复制文件
2. 对照本说明重新打上补丁（socket.ts 的 6 处、ui.html 的 4 处）
3. 用 `figma_e2e_check.py` 做一次端到端自检
4. 更新本文件与 SKILL.md 的 `metadata.upstream` 版本号
