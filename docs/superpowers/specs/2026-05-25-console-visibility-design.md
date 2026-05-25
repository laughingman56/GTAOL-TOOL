# Console Window Visibility Control

**Date:** 2026-05-25
**Context:** PyInstaller packaging uses console-based mode, console visibility togglable at runtime.

## Overview

新增 `console_window.py` 模块，提供运行时控制台窗口显示/隐藏能力。打包时使用 `console=True`，
启动时从配置文件恢复上次状态。

## Architecture

```
main.py (启动时恢复状态)
    │
    ▼
console_window.py
    ├── show_console()      → ctypes: ShowWindow(GetConsoleWindow(), SW_SHOW)
    ├── hide_console()      → ctypes: ShowWindow(GetConsoleWindow(), SW_HIDE)
    ├── toggle_console()    → is_visible ? hide : show
    └── is_console_visible()→ ctypes: IsWindowVisible(GetConsoleWindow())
    │
    ▼
config_manager.py (读写 console_visible 字段)
    │
    ▼
GTA多合一开锁助手.json (持久化)
```

## Components

### 1. `console_window.py` — 控制台窗口控制

纯 `ctypes` 实现，零额外依赖。

- `get_console_hwnd()` — 获取当前控制台窗口句柄（无窗口时返回 None）
- `show_console()` — 显示控制台窗口
- `hide_console()` — 隐藏控制台窗口
- `is_console_visible()` — 返回控制台是否可见
- `toggle_console()` — 切换可见状态，返回切换后是否可见

### 2. `main.py` — 启动时恢复状态

在 `main()` 函数中（GUI 创建之前），读取 `console_visible` 配置，调用对应函数恢复状态。
首次运行（无配置时）默认显示控制台。

### 3. `test.spec` — PyInstaller 配置

`console=False` → `console=True`

### 4. `GTA多合一开锁助手.json` — 新增字段

```json
{
  "console_visible": true
}
```

## Data Flow

```
启动
  → main() 读取 config.get("console_visible", True)
  → True: 无需操作（控制台已显示）
  → False: hide_console()

用户切换（GUI 开关回调）
  → toggle_console()
  → config.set("console_visible", result)
```

## Error Handling

- **非 Windows 环境**: 所有函数返回 None/False，不抛异常（但本项目仅 Windows 运行）
- **无控制台窗口**: `get_console_hwnd()` 返回 None，其他函数降级为空操作
- **ctypes 调用失败**: 捕获异常，静默降级

## Testing

- 手动测试：在 Windows 环境下运行打包后的 exe，点击 GUI 开关验证控制台显示/隐藏
- 状态持久化验证：关闭程序后重新打开，确认控制台状态被记住
