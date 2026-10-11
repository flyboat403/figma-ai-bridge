---
name: figma-ai-bridge
description: "让 AI 直接读写 Figma 设计稿的完整能力包（本地插件桥方案，免 Dev Mode、免付费计划）：一键部署、启动/停止中继、连接 Figma 插件（频道号）、读取设计稿结构与内容、修改文字/颜色/位置、导出画板图片验收，以及断连/超时/频道等问题的系统排查。凡涉及 Figma 设计稿的 AI 读写改、插件桥、cursor-talk-to-figma、频道号/Channel ID、「把设计稿读出来/帮我改一下/导出看看」、Figma MCP 被 Dev Mode 门槛挡住、教学场景连接 Figma，都应使用本技能——即使用户没有明说「插件桥」，只要是围绕 Figma 设计稿做读取、修改、导出、排障，就加载本技能。"
metadata:
  version: "1.0.0"
  created_on: "2026-10-11"
  upstream: "grab/cursor-talk-to-figma-mcp v0.3.5（已打本机补丁，见 vendor/PATCHES.md）"
  tested_on: "Windows + Figma Desktop 126.10.7 + Bun 1.4.3；全链路实测：读结构 / 改文字 / 改颜色 / 导出图"
---

# Figma AI 桥接（figma-ai-bridge）

让 AI 直接读写 Figma 设计稿的完整工具箱。一条链路串起四个角色：

```
AI（本技能）──MCP/stdio──> MCP 服务（bun x cursor-talk-to-figma-mcp）
                            └─ WebSocket:3055 ─> 本地中继（socket.ts）
                                                 └─> Figma 插件 ──> 画布
```

**为什么能改稿**：走的是 Figma Plugin API（插件天生拥有设计文件的读写权限），绕开了官方 MCP 的 Dev Mode / 付费门槛。这也是它与「访问令牌（REST API，只读）」的本质区别——改稿只能走插件桥。

> 说明：下文中 `<SKILL_DIR>` 指本技能所在目录——技能加载时会提示 `Base directory for this skill: …`，把它作为 `<SKILL_DIR>` 代入即可。

**三条铁律**（违反一次掉一次线，背后原因见 `references/pitfalls.md`）：
1. **Figma 插件面板必须保持开着**——面板一关，连接立即销毁（实测 close code 1001）。这是最常见的翻车点，也最容易误判成"桥坏了"。
2. **每次重开插件都会生成新的频道号**——让用户把面板上的新频道号发来，不要用旧的。
3. **等用户确认 `Connected to server in channel: xxxxxxxx` 之后再发命令**——连接建立有竞态，先等就绪。

## 用户引导节奏（贯穿全程的沟通层）

这条桥和普通工具最大的不同：**有好几个环节必须用户亲手完成**（导入插件、开面板、发频道号）。所以执行时不要闷头干活——每到涉及用户的节点，主动说清"现在到哪一步、需要你做什么、发什么给我"。脚本本身会输出分步进度，记得把它转述给用户。

| 节点 | 主动提示（要点） |
|---|---|
| 部署 / 体检完成 | 列出接下来要用户做的 2~3 件事，含完整菜单路径 |
| 请用户运行插件 | 「在 Figma 里运行插件：**Plugins → Development → Cursor MCP Plugin → Connect**；然后把面板上的频道号（`Connected to server in channel:` 后面那串）发我」 |
| 收到频道号、开始执行 | 先回一句「正在连接并读取，约 20~40 秒」，再执行 |
| 准备修改 | 一句话预告：「这就把 XX 从 A 改成 B」 |
| 执行完成 | 报结果 + 导出图路径（"可以打开对比"）+ 引导下一步（"还想改什么直接说"） |
| 连接断开 / 命令超时 | 「桥断了（面板被关了）。请重新运行插件，把**新**频道号发我——面板保持开着就不会再断」 |
| 任何多步操作 | 用编号列表告诉用户「你只需要做第 X 步」，降低迷糊概率 |

三条表达原则：
- 说「去哪里点」必须给**完整菜单路径**（Plugins → Development → …），不要说"运行一下插件"这种让新手发懵的话；
- 纪律提醒（面板保持开着）只在**首次连接**和**断线时**各说一次，不重复唠叨；
- 在支持中途发消息的客户端，每个节点发一条简短进度；在不支持中途发言的客户端，把「下一步需要你做什么」放在回复最上方。

## 一、环境体检（先做）

```bash
python "<SKILL_DIR>/scripts/setup_windows.py" --check
```

| 检查项 | 判定 | 处理 |
|---|---|---|
| Bun 运行时 | `~/.bun/bin/bun.exe` 存在，或 PATH 中有 bun | 缺失 → 跑部署（自动装） |
| 桥接目录 | `~/.workbuddy-ai/tools/figma-bridge/` | 缺失 → 跑部署 |
| 中继服务 | `netstat -ano | findstr 3055` 有 LISTENING | 未跑 → 启动「启动桥接.vbs」 |
| 插件连接 | 查询中继日志出现 `Client joined channel` | 无 → 引导用户在 Figma 里运行插件 |

## 二、部署（新机器一次性）

```bash
python "<SKILL_DIR>/scripts/setup_windows.py"
```

把 vendor 下的**中继 + 已打补丁的 Figma 插件**部署到 `~/.workbuddy-ai/tools/figma-bridge/`，并生成「启动桥接.vbs / 停止桥接.bat / 使用说明.txt」。缺 Bun 时自动从 npmmirror 下载官方二进制安装。

部署后引导用户完成**插件导入（一次性）**：
Figma 桌面版 → 菜单 Figma → Plugins → Development → **Import plugin from manifest…** → 选择
`~/.workbuddy-ai/tools/figma-bridge/repo/src/cursor_mcp_plugin/manifest.json`

## 三、连接（每次使用）

1. 启动中继：用户双击「启动桥接.vbs」；
   AI 环境里直接后台运行 `bun run src/socket.ts`（cwd = bridge/repo）也可以。
2. 用户在 Figma 运行插件：Plugins → Development → **Cursor MCP Plugin** → Connect。
3. 用户把面板上的频道号发给 AI（8 位随机串，如 `wpr59n03`）。
4. 强调**面板保持开着**（不要按 Esc、不要关面板、不要切插件/文件）。

## 四、使用（核心配方）

调用器：
```bash
python "<SKILL_DIR>/scripts/figma_call.py" <频道> <工具名> '<参数JSON>'
python "<SKILL_DIR>/scripts/figma_call.py" <频道> --batch '[{"tool":…,"args":…}, …]'
```
导出图片自动保存为 `~/.workbuddy-ai/tools/figma-bridge/_export_*.png`；每次调用的完整输出存 `_last_<工具>.txt`。

| 需求 | 工具 | 示例参数 |
|---|---|---|
| 读文档结构 | get_document_info | `{}` |
| 读图层详情 | get_node_info | `{"nodeId":"2:3"}` |
| 读当前选择 | get_selection | `{}` |
| 全量图层清单（**含矢量**） | scan_nodes_by_types | `{"nodeId":"2:3","types":["VECTOR","TEXT","FRAME","RECTANGLE"]}` |
| 改文字 | set_text_content | `{"nodeId":"2:7","text":"2.000"}` |
| 改填充色 | set_fill_color | `{"nodeId":"2:9","r":0.118,"g":0.565,"b":1.0}`（0-1 浮点） |
| 移动 | move_node | `{"nodeId":"…","x":100,"y":200}` |
| 重命名 | rename_node | `{"nodeId":"…","name":"新名字"}` |
| 导出图片（验收必用） | export_node_as_image | `{"nodeId":"2:3","format":"PNG","scale":2}` |

**交付习惯**：每次改完设计，`export_node_as_image` 导出画板图并描述变化——AI 能直接"看图"确认结果，用户也能一眼验收。
完整 44 工具清单与更多配方 → `references/usage-tools.md`

**两个已知特性**（先知道，别误判为故障）：
- `get_node_info` 会**过滤掉 VECTOR 节点**（服务端行为）→ 要矢量清单用 `scan_nodes_by_types`。
- `set_text_content` 会**同步把图层名改成新文本**。

## 五、故障排查（速查）

| 症状 | 先查 | 处置 |
|---|---|---|
| `Request to Figma timed out` | 插件是否还在线（中继日志尾部 / netstat） | 多半面板被关了 → 请用户重开插件，发新频道号 |
| 命令发出去没人接 | 中继日志是否出现 `No other clients in channel` | 插件不在该频道 → 核对频道号是否最新 |
| 连上几秒/几分钟就断 | 中继日志 `Client closed: code=1001` | 面板被关/切走 → 告知用户保持面板打开 |
| 连上约 2 分钟必断（旧版） | socket.ts 是否含 `idleTimeout: 0` | 用 vendor 里的新版重新部署 |
| 读不到矢量图形 | —— | 改用 `scan_nodes_by_types` |
| 扫描类工具（scan_text_nodes）超时 | 是否有轮询在抢请求 | 先停 probe_daemon / auto_watcher 再操作 |

仍然不清晰时：对照**教程原文**（https://juejin.cn/post/7621026569348513802）与上游仓库 README / Issues 自查（链接见文末「参考链接」）。

逐条诊断命令 → `references/pitfalls.md`

## 六、进阶（可选）：自动狙击

插件频繁重开/断连时启用：插件一上线，系统 1 秒内发现、8 秒内自动读取文档信息。

```bash
python "<SKILL_DIR>/scripts/auto_watcher.py"     # 常驻；跟随中继日志自动接应
```
命中记录：`~/.workbuddy-ai/tools/figma-bridge/_probe_hits.log`

⚠️ 它会自动拉起 `probe_daemon.py` 轮询——**做写操作或扫描类操作前先停掉它**，避免请求互抢（这一坑实测过）。

## 七、脚本清单

| 脚本 | 用途 |
|---|---|
| scripts/setup_windows.py | 一键部署 / 体检（--check） |
| scripts/figma_call.py | 通用调用器（单次 / --batch 批量） |
| scripts/figma_e2e_check.py | 端到端自检（加入频道→读文档→附中继日志证据） |
| scripts/probe_daemon.py | 秒级文档探测器（常驻轮询，配合 watcher） |
| scripts/auto_watcher.py | 自动狙击（监听日志，自动探测新频道） |

## 八、合规

只操作用户本人有权访问的 Figma 文件；不要用它读取或修改不属于用户的设计稿。

## 参考文件

- `references/全流程手册.md` / `全流程手册.html` — 人类可读的完整历程与操作手册（html 可直接打印/发给学生）
- `references/pitfalls.md` — 踩坑大全（8 条，含命令级诊断）
- `references/usage-tools.md` — 44 工具速查 + 命令配方
- `references/teaching.md` — 教学分发指南（给老师）
- `vendor/PATCHES.md` — 本机补丁说明（与上游差异，升级时防覆盖）

## 参考链接（用户自行排错用）

- **教程原文（插件桥全链路实战，本桥的出发点）**：
  https://juejin.cn/post/7621026569348513802
  —— 安装、连接、报错处理的完整场景讲解；排错时可对照阅读
- 官方 MCP 背景文章（「方案二」的由来，解释 Dev Mode 门槛）：
  https://juejin.cn/post/7572390974458953728
- 上游开源仓库（源码与最新说明）：
  https://github.com/grab/cursor-talk-to-figma-mcp

自查顺序建议：**先按 `references/pitfalls.md` 的「诊断三件套」定位**（一切以中继日志为准）；仍不清晰时，再对照教程原文与上游仓库的 README / Issues。
