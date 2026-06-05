# 游戏手柄活动检测 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在 `hang_up.py` 的 `AntiIdleManager` 中增加 gamepad 活动检测，支持所有类型手柄的轴/按钮/D-pad 输入识别

**架构：** 使用 `pygame.joystick` 模块，新增 `_check_gamepad_activity()` 方法和 `_gamepad_available` 降级标志。主循环中与现有键鼠检测用 `or` 并联

**技术栈：** Python 3, pygame, pydirectinput（已有）, win32api（已有）, ctypes（已有）

---

### 任务 1：安装 pygame 依赖并验证

- [ ] **步骤 1：安装 pygame**

```bash
pip install pygame
```

- [ ] **步骤 2：验证 import 可用**

```bash
python -c "import pygame; pygame.init(); pygame.joystick.init(); print('pygame OK')"
```

预期：输出 `pygame OK`，无报错

---

### 任务 2：修改 `__init__` 增加手柄初始化

**文件：**
- 修改：`hang_up.py:14-33`

- [ ] **步骤 1：在 `__init__` 中已有的状态变量之后、`self.target_title` 之前，插入 pygame 初始化代码**

将：
```python
        # ====== 内部写死配置，无需外部传参 ======
        self.target_title = "Grand Theft Auto"
```

改为：
```python
        # ====== 游戏手柄检测初始化 ======
        try:
            import pygame
            self.pygame = pygame
            self.pygame.init()
            self.pygame.joystick.init()
            self._gamepad_available = True
            self._joystick_count = 0
            self._joysticks = []
        except (ImportError, Exception):
            self._gamepad_available = False
            self.pygame = None
        # ================================

        # ====== 内部写死配置，无需外部传参 ======
        self.target_title = "Grand Theft Auto"
```

---

### 任务 3：新增 `_check_gamepad_activity()` 方法

**文件：**
- 修改：`hang_up.py` — 在 `_check_player_activity()` 方法之后插入

- [ ] **步骤 1：在 `_check_player_activity()` 的 `return False` 之后、`enable()` 方法之前（第 66 行），插入新方法**

```python
    def _check_gamepad_activity(self):
        if not self._gamepad_available:
            return False

        count = self.pygame.joystick.get_count()
        if count != self._joystick_count:
            self._joystick_count = count
            self._joysticks = []

        for i in range(count):
            if i >= len(self._joysticks) or self._joysticks[i] is None:
                js = self.pygame.joystick.Joystick(i)
                js.init()
                if len(self._joysticks) <= i:
                    self._joysticks.append(js)
                else:
                    self._joysticks[i] = js

        self.pygame.event.pump()

        for js in self._joysticks:
            if js is None:
                continue
            for axis in range(js.get_numaxes()):
                if abs(js.get_axis(axis)) > 0.2:
                    return True
            for btn in range(js.get_numbuttons()):
                if js.get_button(btn):
                    return True
            for hat in range(js.get_numhats()):
                if js.get_hat(hat) != (0, 0):
                    return True

        return False
```

---

### 任务 4：修改 `run()` 主循环，并联手柄检测

**文件：**
- 修改：`hang_up.py:119-121`（`_check_player_activity()` 调用处）

- [ ] **步骤 1：将单一的 `_check_player_activity()` 判断改为并联 `_check_gamepad_activity()`**

将：
```python
            if self._check_player_activity():
                self.last_active_time = time.time()
```

改为：
```python
            if self._check_player_activity() or self._check_gamepad_activity():
                self.last_active_time = time.time()
```

---

### 任务 5：修改 `stop()` 增加 pygame 清理

**文件：**
- 修改：`hang_up.py:130-132`

- [ ] **步骤 1：在 `stop()` 中增加 `pygame.quit()`**

将：
```python
    def stop(self):
        """安全停止线程"""
        self.running = False
```

改为：
```python
    def stop(self):
        """安全停止线程"""
        self.running = False
        if self._gamepad_available:
            try:
                self.pygame.quit()
            except Exception:
                pass
```

---

### 任务 6：验证 — 运行程序确认不崩溃

- [ ] **步骤 1：导入验证**

```bash
python -c "from hang_up import AntiIdleManager; print('import OK')"
```

预期：输出 `import OK`

- [ ] **步骤 2：无手柄环境下启动线程，验证键鼠检测仍正常**

手工运行程序，观察控制台输出 `防挂机休眠服务已后台运行。`，确认没有崩溃或异常。

---

### 任务 7：Commit

```bash
git add hang_up.py
git commit -m "feat: add gamepad activity detection via pygame.joystick"
```
