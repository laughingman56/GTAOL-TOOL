# 控制台窗口显示/隐藏 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 提供运行时控制台窗口显示/隐藏能力，PyInstaller 使用 console 模式打包，状态持久化到配置文件。

**架构：** 新增 `console_window.py` 模块封装 Windows API 调用；`main.py` 启动时从 config 恢复上次状态；`test.spec` 改为 `console=True`。

**技术栈：** ctypes（标准库）、Windows API（GetConsoleWindow / ShowWindow / IsWindowVisible）

---

### 任务 1：创建 `console_window.py` 模块

**文件：**
- 创建：`console_window.py`

- [ ] **步骤 1：编写 `console_window.py`**

```python
import ctypes
import sys

SW_HIDE = 0
SW_SHOW = 5


def get_console_hwnd():
    kernel32 = ctypes.windll.kernel32
    hwnd = kernel32.GetConsoleWindow()
    if hwnd == 0:
        return None
    return hwnd


def is_console_visible():
    hwnd = get_console_hwnd()
    if hwnd is None:
        return False
    user32 = ctypes.windll.user32
    return bool(user32.IsWindowVisible(hwnd))


def show_console():
    hwnd = get_console_hwnd()
    if hwnd is None:
        return
    user32 = ctypes.windll.user32
    user32.ShowWindow(hwnd, SW_SHOW)


def hide_console():
    hwnd = get_console_hwnd()
    if hwnd is None:
        return
    user32 = ctypes.windll.user32
    user32.ShowWindow(hwnd, SW_HIDE)


def toggle_console():
    if is_console_visible():
        hide_console()
    else:
        show_console()
    return is_console_visible()
```

- [ ] **步骤 2：Commit**

```bash
git add console_window.py
git commit -m "feat: add console_window module for runtime console visibility control"
```

---

### 任务 2：在配置默认值中添加 `console_visible` 字段

**文件：**
- 修改：`config_manager.py:86`

- [ ] **步骤 1：在 `default_config` 中新增字段**

在 `config_manager.py` 的 `self.default_config` 字典末尾（第 203 行 `}` 之前）添加：

```python
"console_visible": True,
```

修改后第 86-204 行变为：

```python
self.default_config = {
    "ka_cha_chuan": {"name": "任务卡差传", "key": "O","danei":True ,"enabled": True},
    # ... 所有现有配置保持不变 ...
    "link3": "",
    "console_visible": True,
}
```

> 说明：`_merge_config` 方法会自动将新增的 `console_visible` 合并到用户已有的配置文件中，无需手动处理迁移逻辑。

- [ ] **步骤 2：Commit**

```bash
git add config_manager.py
git commit -m "feat: add console_visible field to default config"
```

---

### 任务 3：`main.py` 启动时恢复控制台状态

**文件：**
- 修改：`main.py:90-93`

- [ ] **步骤 1：在 main.py 顶部添加导入**

在 `main.py` 第 5 行 `import ctypes` 之后插入一行：

```python
import console_window
```

- [ ] **步骤 2：在 `main()` 函数中，初始化 config 之后，恢复控制台状态**

修改 `main.py` 第 90-93 行区域。在 `print("正在初始化配置...")` 和 `config = ConfigManager()` 之后，插入控制台恢复逻辑。

将：

```python
    # 1. 初始化数据层
    print("正在初始化配置...")
    config = ConfigManager()

    # 2. 初始化并启动监听层 (后台线程)
    print("正在启动 Win32 监听器...")
```

改为：

```python
    # 1. 初始化数据层
    print("正在初始化配置...")
    config = ConfigManager()

    # 恢复控制台窗口状态
    console_visible = config.data.get("console_visible", True)
    if console_visible:
        console_window.show_console()
    else:
        console_window.hide_console()

    # 2. 初始化并启动监听层 (后台线程)
    print("正在启动 Win32 监听器...")
```

- [ ] **步骤 3：Commit**

```bash
git add main.py
git commit -m "feat: restore console visibility state on startup from config"
```

---

### 任务 4：修改 PyInstaller spec 为 console 模式

**文件：**
- 修改：`test.spec:39`

- [ ] **步骤 1：将 `console=False` 改为 `console=True`**

`test.spec` 第 39 行：

```
    console=True,
```

- [ ] **步骤 2：Commit**

```bash
git add test.spec
git commit -m "fix: change PyInstaller build mode to console-based (console=True)"
```

---

### 验证与测试

**手动验证步骤（仅限 Windows 环境）：**

1. 运行 `python main.py`，确认控制台窗口正常显示
2. 在 Python 交互环境中测试：
   ```python
   import console_window
   console_window.hide_console()  # 控制台应隐藏
   console_window.show_console()  # 控制台应显示
   console_window.toggle_console()  # 控制台应切换
   ```
3. 修改 `GTA多合一开锁助手.json` 中 `"console_visible": false`，重新启动 → 控制台应隐藏
4. 改回 `true`，重新启动 → 控制台应显示
5. 使用 PyInstaller 打包：`pyinstaller test.spec`，运行 `dist/test/test.exe` 验证效果
