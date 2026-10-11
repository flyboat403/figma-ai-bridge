# 教学分发指南（给老师）

面向"把 Figma AI 桥接教给学生"的场景。目标：学生拿到技能包后，能在自己的电脑上独立完成安装、连接、使用。

## 一、分发什么

| 材料 | 说明 | 位置 |
|---|---|---|
| **技能包**（整个文件夹） | 核心：交给学生的 AI 用 | `C:\Users\fly04\.workbuddy-ai\skills\figma-ai-bridge\` |
| 全流程手册 | 学生自查 / 打印 | 技能包内 `references/全流程手册.md`（另有 HTML 精排版） |
| 示例导出图 | 展示效果（改前/改后对照） | 桥接目录 `万用表画板导出*.png` |

**分发方式（三选一）**：
1. **压缩包**：把 `figma-ai-bridge` 文件夹打包为 zip 发给学生（最稳，含所有脚本与补丁文件）。
2. **GitHub 仓库**：把技能文件夹放进老师自己的仓库（如 `flyboat403`），学生 `git clone`。
3. **SkillHub 类平台**：注意平台的**扩展名白名单**——.js/.html 等非文本类型可能被过滤，走压缩包更稳。

## 二、学生操作流程（可原样分发给学生）

1. 把 `figma-ai-bridge` 文件夹放到：
   `C:\Users\<你的用户名>\.workbuddy-ai\skills\figma-ai-bridge\`
   （没有 skills 目录就新建一个）
2. 对 AI 说：**"帮我装 Figma 桥接"**（或"体检一下 Figma 桥"）
   ——AI 会自动运行体检 / 部署脚本，缺什么补什么
3. 按 AI 提示完成 **Figma 插件导入**（一次性）：
   Figma 桌面版 → 菜单 Figma → Plugins → Development → Import plugin from manifest… →
   选择 `C:\Users\<你>\.workbuddy-ai\tools\figma-bridge\repo\src\cursor_mcp_plugin\manifest.json`
4. 双击 `启动桥接.vbs`，在 Figma 里运行插件并 Connect
5. 把面板上的**频道号**发给 AI，然后直接说需求（读稿 / 改稿 / 导出）

## 三、学生常见问题（预判）

| 学生问 | 回答 |
|---|---|
| "AI 说连不上 / Request timed out" | 插件面板是不是关了？重开插件，把**新**频道号发 AI |
| "频道号在哪里？" | 插件面板上 `Connected to server in channel: xxxxxxxx` 那一行 |
| "为什么每次都要发频道号？" | 插件每次重开都会换个随机号，属正常 |
| "改完怎么确认？" | 让 AI 导出画板图片（export），自己对照 |
| "我的 Figma 是网页版行不行？" | 理论上可以（本地 ws 连接），但实测环境是桌面版；网页版需自行验证浏览器对 localhost WebSocket 的放行 |
| "Bun 装不上" | 技能里 setup 脚本会走 npmmirror 自动装；再不行参考手册第四节 |

## 四、教师备课建议

- **先在教师机全流程走通一遍**（本手册就是实测产物），再批量发给学生。
- 每人**各自跑本机中继**（localhost:3055），互不干扰，不需要局域网/服务器。
- 建议的课堂练习（难度递增）：
  1. 让 AI 读出文件里有哪些图层（观察"读"）
  2. 改一个读数 / 一个颜色（观察"写"）
  3. 导出画板图验收（观察"闭环"）
  4. 自由题：移动表笔、加一个新档位文字、批量改色
- 强调纪律：**面板保持开着**——这一条能省掉 90% 的求助。

## 五、环境要求

- Windows + Figma 桌面版（实测 126.10.7）
- 能访问 npmmirror（Bun 下载与 bunx 拉包）
- 学生机器无需 GitHub（技能自带全部补丁文件；不依赖上游仓库在线）
