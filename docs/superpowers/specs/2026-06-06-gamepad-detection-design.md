# 游戏手柄活动检测 — 设计规格

日期：2026-06-06
文件：`hang_up.py`

## 目标

在 `AntiIdleManager` 现有键鼠活动检测的基础上，增加游戏手柄（所有类型）输入检测。当玩家使用手柄操作时，视为玩家活跃，重置挂机计时器。

## 范围

- 支持 Xbox / PlayStation / Switch / DInput 杂牌手柄
- 检测输入类型：摇杆（轴）、按钮、D-pad
- 支持热插拔（运行时插入/拔出手柄）
- 依赖：`pygame`（新增 pip 依赖）

## 方案选择

选用 `pygame.joystick`（方案 A），理由：
- 一行 `pip install pygame`，代码简洁（约 20 行）
- 原生支持所有主流手柄类型，无需手动处理 PS4/PS5 映射
- 与项目已有的 `pydirectinput` 风格一致
- 无需创建窗口或 display surface，仅使用 joystick 模块即可

## 架构

```
AntiIdleManager.__init__()
    ├── 现有: pydirectinput, win32api 初始化
    └── 新增: pygame.init() / pygame.joystick.init()
               self._gamepad_available = True/False
               self._joystick_count = 0
               self._joysticks = []

AntiIdleManager.run() 主循环
    └── 原有: _check_player_activity()  ← 鼠标+键盘
        OR
        新增: _check_gamepad_activity() ← 手柄轴/按钮/hat
              → 任一为 True → 重置 last_active_time

AntiIdleManager.stop()
    └── 新增: pygame.quit()
```

## 新增方法：`_check_gamepad_activity()`

```python
def _check_gamepad_activity(self):
    if not self._gamepad_available:
        return False

    # 热插拔检测
    count = pygame.joystick.get_count()
    if count != self._joystick_count:
        self._joystick_count = count
        self._joysticks = []

    # 初始化新检测到的手柄
    for i in range(count):
        if i >= len(self._joysticks) or self._joysticks[i] is None:
            js = pygame.joystick.Joystick(i)
            js.init()
            if len(self._joysticks) <= i:
                self._joysticks.append(js)
            else:
                self._joysticks[i] = js

    pygame.event.pump()

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

## 配置常量

| 常量 | 值 | 说明 |
|------|-----|------|
| 摇杆死区 | `0.2` | 绝对值 < 0.2 视为无操作，过滤物理漂移 |
| 检测间隔 | 复用 `self.check_interval`（2秒） | 与键鼠检测同步 |

## 错误处理

| 场景 | 行为 |
|------|------|
| pygame 未安装（ImportError） | `self._gamepad_available = False`，键鼠检测正常工作，无崩溃 |
| pygame.init() 失败（无 joystick 设备等） | 同上，`self._gamepad_available = False` |
| 无手柄插入 | `_check_gamepad_activity()` 直接返回 `False` |
| 手柄中途断开 | 热插拔逻辑重建列表，断开的手柄不再遍历 |
| pydirectinput/pygame 冲突 | 两者独立运行在不同子系统，不会冲突 |

`__init__` 中导入方式：
```python
try:
    import pygame
    pygame.init()
    pygame.joystick.init()
    self._gamepad_available = True
except (ImportError, Exception):
    self._gamepad_available = False
```

## 测试要点

1. 无手柄环境下运行，确认程序不崩溃，键鼠检测正常工作
2. 插入 Xbox 手柄，摇动摇杆/按按钮，确认挂机计时器重置
3. 插入 PS4 手柄，同上验证
4. 运行时拔出手柄，确认不崩溃
5. 摇杆不动（死区内），确认不误判为活跃
6. pygame 未安装时，确认程序仍正常运行（降级处理）

## 依赖变更

新增：`pygame >= 2.0`（joystick 模块）
打包 EXE 时需一并包含。
