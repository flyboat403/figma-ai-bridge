# figma-ai-bridge

让 AI 直接**读写** Figma 设计稿的一体化技能包 —— 基于本地插件桥（`cursor-talk-to-figma-mcp`），**不需要 Figma Dev Mode，不需要付费计划**。

> 把「安装 → 连接 → 调试 → 运行 → 使用」全流程沉淀为一个可分发技能：学生 / AI 助手照着做即可。
> 已在 Windows + Figma 桌面版 126.10.7 + Bun 1.4.3 全链路实测：读结构 ✓ 改文字 ✓ 改颜色 ✓ 导出图 ✓

## 这是什么

AI 与 Figma 之间的一条本地桥：

```
AI（技能/助手）──MCP/stdio──> MCP 服务（bun x cursor-talk-to-figma-mcp）
                              └─ WebSocket:3055 ─> 本地中继（socket.ts，含加固补丁）
                                                   └─> Figma 插件 ──> 画布
```

走 Figma Plugin API，因此拥有真实的设计文件读写权限（这也是它和「只读的访问令牌」的本质区别——改稿只能走插件桥）。

## 快速开始

1. 把本目录放进技能目录：`C:\Users\<你>\.workbuddy-ai\skills\figma-ai-bridge\`
2. 对 AI 助手（WorkBuddy / Cursor 等）说：**"帮我装 Figma 桥接"**
   → 助手会运行 `scripts/setup_windows.py`：自动装 Bun（如缺）、部署中继与插件、生成启停脚本
3. 按提示在 Figma 导入插件：Plugins → Development → **Import plugin from manifest…**
4. 双击「启动桥接.vbs」→ 在 Figma 里运行插件 → **Connect**
5. 把面板上的**频道号**发给 AI，开始读写设计稿

## 三条铁律（违反必掉线）

- Figma 插件面板**必须保持开着**（关掉 = 连接立即销毁，实测 close code 1001）
- 每次重开插件，**频道号都会变** —— 报最新号
- 等面板显示 `Connected to server in channel: xxxx` 之后再发命令

## 目录结构

| 路径 | 说明 |
|---|---|
| `SKILL.md` | 技能主文件（AI 读取：流程 / 操作配方 / 排障 / 用户引导节奏） |
| `scripts/` | 一键部署（setup_windows.py）、通用调用器（figma_call.py）、自检、探测器 |
| `vendor/` | 打过补丁的中继与 Figma 插件（**自包含**，无需上游仓库在线） |
| `references/` | 全流程手册（.md/.html）、踩坑大全、44 工具速查、教学分发指南 |

## 参考

- 教程原文（插件桥全链路实战）：https://juejin.cn/post/7621026569348513802
- 上游项目：https://github.com/grab/cursor-talk-to-figma-mcp （MIT）
- 本包与上游的差异（加固补丁清单）：见 `vendor/PATCHES.md`

## 许可

MIT（见 LICENSE）。上游 `cursor-talk-to-figma-mcp` 为 MIT 许可，本包在其基础上打包并附加公开补丁。
