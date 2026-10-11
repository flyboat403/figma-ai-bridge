# 44 工具速查 + 命令配方

调用方式（本技能自带调用器）：

```bash
python "<SKILL_DIR>/scripts/figma_call.py" <频道> <工具名> '<参数JSON>'
python "<SKILL_DIR>/scripts/figma_call.py" <频道> --batch '[{"tool":"…","args":{…}}, …]'
```

- 导出图片 → 自动保存 `~/.workbuddy-ai/tools/figma-bridge/_export_<工具名>.png`
- 每次输出全文 → `~/.workbuddy-ai/tools/figma-bridge/_last_<工具名>.txt`
- 参数不确定时：先空参数调一次，工具会返回参数说明/报错提示，据此修正。

## 工具分组（44 个）

**连接与总览**：`join_channel` `get_document_info` `get_selection` `read_my_design`

**读取**：`get_node_info` `get_nodes_info` `get_styles` `get_local_components` `get_annotations` `get_reactions` `get_instance_overrides` `scan_text_nodes`（扫全部文字）`scan_nodes_by_types`（按类型扫，**含矢量**）

**修改·内容与样式**：`set_text_content` `set_multiple_text_contents` `rename_node` `set_fill_color` `set_stroke_color` `set_image_fill` `set_corner_radius` `set_annotation` `set_multiple_annotations`

**修改·位置与组织**：`move_node` `resize_node` `set_parent` `set_selections` `set_focus`

**创建与增删**：`create_rectangle` `create_frame` `create_text` `create_component_instance` `create_section` `clone_node` `delete_node` `delete_multiple_nodes` `set_instance_overrides`

**自动布局**：`set_layout_mode` `set_padding` `set_axis_align` `set_layout_sizing` `set_item_spacing`

**导出**：`export_node_as_image`

**连线（FigJam 场景）**：`set_default_connector` `create_connections`

## 常用配方

### 1. 读全貌（两步摸清一个文件）
```bash
python figma_call.py <ch> --batch '[{"tool":"get_document_info","args":{}},{"tool":"get_selection","args":{}}]'
```
拿到页面/画板 id（如 `2:3`）后：

### 2. 读画板全部内容（含矢量图形）
```bash
python figma_call.py <ch> scan_nodes_by_types '{"nodeId":"2:3","types":["VECTOR","TEXT","FRAME","RECTANGLE","ELLIPSE","GROUP","COMPONENT","INSTANCE"]}'
```

### 3. 画板导出成图片（AI 看图 + 用户验收）
```bash
python figma_call.py <ch> export_node_as_image '{"nodeId":"2:3","format":"PNG","scale":2}'
# → _export_export_node_as_image.png
```

### 4. 改文字
```bash
python figma_call.py <ch> set_text_content '{"nodeId":"2:7","text":"2.000"}'
```

### 5. 改颜色（RGB 0-1 浮点；#1E90FF = r0.118 g0.565 b1.0）
```bash
python figma_call.py <ch> set_fill_color '{"nodeId":"2:9","r":0.118,"g":0.565,"b":1.0,"a":1}'
```

### 6. 移动元素
```bash
python figma_call.py <ch> move_node '{"nodeId":"2:23","x":200,"y":760}'
```

### 7. 典型修改闭环（一次批量完成 + 留证据）
```bash
python figma_call.py <ch> --batch '[
  {"tool":"get_node_info","args":{"nodeId":"2:7"}},
  {"tool":"set_text_content","args":{"nodeId":"2:7","text":"220.5"}},
  {"tool":"get_node_info","args":{"nodeId":"2:7"}},
  {"tool":"export_node_as_image","args":{"nodeId":"2:3","format":"PNG","scale":2}}
]'
```

## 颜色换算表（常用）

| 颜色 | 十六进制 | r / g / b（0-1） |
|---|---|---|
| 亮蓝 | #1E90FF | 0.118 / 0.565 / 1.0 |
| 经典蓝 | #0000FF | 0 / 0 / 1 |
| 红 | #FF0000 | 1 / 0 / 0 |
| 金 | #FFD700 | 1 / 0.843 / 0 |
| 橙 | #FF7A00 | 1 / 0.478 / 0 |
| 绿 | #22C55E | 0.133 / 0.773 / 0.369 |
| 紫 | #8B5CF6 | 0.545 / 0.361 / 0.965 |

换算：字节值 ÷ 255（保留 2~3 位小数即可）。

## 输出解读要点

- 工具结果里的 `Request to Figma timed out` = **插件没应答**（关面板了 / 频道不对 / 正在忙），先查坑 2/3/4。
- `No other clients in channel` 出现在**中继日志**里 = 该频道没有插件在线。
- `get_node_info` 看不到 VECTOR 是**正常过滤**（见坑 5），用 `scan_nodes_by_types`。
- 改完记得导出图片做视觉验收（AI 可直接看）。
