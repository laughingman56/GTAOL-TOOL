# pc_settings.bin 管理功能设计

## 背景

R星对留红行为已做出严格制裁。为防止断网导致红名，需要在断网前后管理 `pc_settings.bin` 文件，确保每次断网后恢复到干净状态。

## 功能概述

三个功能：
1. **删除 pc_settings.bin** — 按钮触发，删除原文件
2. **备份 pc_settings.bin** — 按钮触发，复制到桌面
3. **自动恢复** — 每次断网恢复后自动从桌面复制备份回原位置

## UI 变更

### 断网设置弹窗 (`show_settings_ui` in ka_085.py)

在定时控制行 (`timer_frame`) 右侧增加两个按钮：

```
[定时断网开关] [__时间__] [秒]    [删除pc_settings.bin]  [备份pc_settings.bin]
```

- 按钮宽度自适应文字，高度30
- 删除按钮：红色系边框 (`#FF474C`)
- 备份按钮：绿色系边框 (`#4CC768`)
- 字体：Microsoft YaHei 14号

## 核心函数

文件：`ka_085.py`

### `find_pc_settings_bin() -> str | None`
- 递归搜索 `%USERPROFILE%\Documents\Rockstar Games\` 下所有 `pc_settings.bin`
- 兼容 GTA V 传承版和增强版
- 返回找到的第一个路径，未找到返回 None

### `delete_pc_settings_bin()`
- 调用 `find_pc_settings_bin()` 获取路径
- 删除文件
- 弹出成功/失败提示
- 找到多个文件时只删第一个

### `backup_pc_settings_bin()`
- 调用 `find_pc_settings_bin()` 获取路径
- 复制到 `%USERPROFILE%\Desktop\pc_settings.bin`
- 目标已存在则覆盖
- 弹出成功/失败提示

### `restore_pc_settings_bin()`
- 检查 `%USERPROFILE%\Desktop\pc_settings.bin` 是否存在
- 存在则复制回原位置（覆盖）
- 不存在则静默跳过
- 仅在控制台输出日志，不弹窗

## 数据流

1. **用户首次使用** → 点击删除 → 游戏重新生成干净的 pc_settings.bin
2. **游玩后** → 点击备份 → 保存干净副本到桌面
3. **每次断网** → `run_natdown()` → `main()` 倒计时 → `recover_natdown()` → `restore_pc_settings_bin()` → 桌面备份覆盖原文件

## 触发时机

在 `ka_085.py` 的 `main()` 函数中，`recover_natdown()` 被调用的两个分支之后，均插入 `restore_pc_settings_bin()` 调用。

## 错误处理

| 场景 | 行为 |
|------|------|
| 找不到 pc_settings.bin | messagebox 弹窗 "未找到 pc_settings.bin" |
| 删除成功 | console print 记录，不弹窗 |
| 备份成功 | messagebox 弹窗 "已备份到桌面" |
| 桌面备份已存在 | 直接覆盖，不额外提示 |
| 自动恢复无桌面备份 | 静默跳过 |
| 文件占用/权限不足 | messagebox 弹窗提示具体错误 |

## 涉及文件

| 文件 | 变更 |
|------|------|
| `ka_085.py` | 新增4个函数；`show_settings_ui` 中 timer_frame 增加两个按钮；`main()` 中增加恢复调用 |
