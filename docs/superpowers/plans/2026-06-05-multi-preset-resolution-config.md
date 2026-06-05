# 多预设分辨率配置 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在 `num_config.json` 中支持多套坐标预设，运行时根据屏幕宽高比自动选择最接近的预设。

**架构：** `find_num.py` 新增 `select_preset(config)` 从 `num_config.json` 的 `presets` 中按宽高比匹配；`mss_dpi.py` 的 `get_mss_config` 接受动态 `base_w`/`base_h`；`num_match.py` 和 `debug_grid.py` 通过 `select_preset` 获取坐标。

**技术栈：** Python, win32api, JSON

---

### 任务 1：重构 num_config.json 为 presets 结构

**文件：**
- 修改：`num_config.json`

- [ ] **步骤 1：将现有配置改写为 presets 格式，添加 1610 占位预设**

```json
{
  "presets": {
    "169": {
      "base_w": 2560, "base_h": 1440,
      "targets": {
        "t0": {"x1": 1015, "y1": 295, "x2": 1123, "y2": 377, "digits": 2},
        "t1": {"x1": 1146, "y1": 295, "x2": 1256, "y2": 377, "digits": 2}
      },
      "grid": {
        "x": 600, "y": 535,
        "cell_w": 128, "cell_h": 80,
        "cols": 10, "rows": 8,
        "cursor_w": 4
      }
    },
    "1610": {
      "base_w": 2560, "base_h": 1600,
      "targets": {
        "t0": {"x1": -1, "y1": -1, "x2": -1, "y2": -1, "digits": 2},
        "t1": {"x1": -1, "y1": -1, "x2": -1, "y2": -1, "digits": 2}
      },
      "grid": {
        "x": -1, "y": -1,
        "cell_w": -1, "cell_h": -1,
        "cols": 10, "rows": 8,
        "cursor_w": 4
      }
    }
  }
}
```

- [ ] **步骤 2：验证 JSON 合法**

运行：`python -c "import json; json.load(open('num_config.json', encoding='utf-8')); print('OK')"`
预期：`OK`

- [ ] **步骤 3：Commit**

```bash
git add num_config.json
git commit -m "feat(config): restructure num_config.json to multi-preset format"
```

---

### 任务 2：mss_dpi.py — get_mss_config 接受动态基准分辨率

**文件：**
- 修改：`mss_dpi.py:38-61`

- [ ] **步骤 1：给 `get_mss_config` 加 `base_w`、`base_h` 可选参数，内部使用传入值**

将方法签名从：
```python
def get_mss_config(cls, base_config_tuple):
    win_x, win_y, win_w, win_h = cls.get_game_window_rect()
    scale_factor = win_h / cls.BASE_H
    orig_x, orig_y, orig_w, orig_h = base_config_tuple

    orig_cx = orig_x + (orig_w / 2)
    orig_cy = orig_y + (orig_h / 2)
    off_x = orig_cx - cls.BASE_CENTER_X
    off_y = orig_cy - cls.BASE_CENTER_Y
```

改为：
```python
def get_mss_config(cls, base_config_tuple, base_w=None, base_h=None):
    if base_w is None: base_w = cls.BASE_W
    if base_h is None: base_h = cls.BASE_H

    base_cx = base_w / 2
    base_cy = base_h / 2

    win_x, win_y, win_w, win_h = cls.get_game_window_rect()
    scale_factor = win_h / base_h
    orig_x, orig_y, orig_w, orig_h = base_config_tuple

    orig_cx = orig_x + (orig_w / 2)
    orig_cy = orig_y + (orig_h / 2)
    off_x = orig_cx - base_cx
    off_y = orig_cy - base_cy
```

方法其余部分（`curr_cx` 到 `return`）不变。

- [ ] **步骤 2：验证向后兼容 — 不传参行为不变**

运行：`python -c "from mss_dpi import ResolutionAdapter; c = ResolutionAdapter.get_mss_config((600, 535, 1280, 640)); print(c)"`
预期：输出与改动前一致（取决于当前屏幕）

- [ ] **步骤 3：Commit**

```bash
git add mss_dpi.py
git commit -m "feat(mss_dpi): accept custom base_w/base_h in get_mss_config"
```

---

### 任务 3：find_num.py — 新增 select_preset()

**文件：**
- 修改：`find_num.py:1-16`（import 区域和 load_config 附近）

- [ ] **步骤 1：在 import 区域添加 mss_dpi 导入**

在 `import os` 之后（第 3 行后）添加：
```python
from mss_dpi import ResolutionAdapter
```

- [ ] **步骤 2：在 `load_config` 函数之后添加 `select_preset` 函数**

在 `load_config` 函数体之后（第 15 行 `return {}` 之后）插入：
```python
def select_preset(config):
    presets = config.get("presets")
    if not presets:
        return config.get("targets", {}), config.get("grid", {}), 2560, 1440

    presets = list(presets.values())
    sw, sh = ResolutionAdapter.get_screen_size()
    actual_ratio = sw / sh

    best = presets[0]
    best_diff = abs(best["base_w"] / best["base_h"] - actual_ratio)
    for p in presets[1:]:
        d = abs(p["base_w"] / p["base_h"] - actual_ratio)
        if d < best_diff:
            best_diff = d
            best = p

    return best["targets"], best["grid"], best["base_w"], best["base_h"]
```

- [ ] **步骤 3：验证导入无误，函数可被调用**

运行：`python -c "from find_num import select_preset, load_config; c = load_config('num_config.json'); t, g, bw, bh = select_preset(c); print('targets keys:', list(t.keys()), 'grid cols:', g.get('cols'), 'base:', bw, bh)"`
预期：`targets keys: ['t0', 't1'] grid cols: 10 base: 2560 1440`

- [ ] **步骤 4：Commit**

```bash
git add find_num.py
git commit -m "feat(find_num): add select_preset for multi-preset config"
```

---

### 任务 4：num_match.py — _adapt_config 改用 select_preset

**文件：**
- 修改：`num_match.py:44-72`

- [ ] **步骤 1：替换 import**

将第 4 行：
```python
from find_num import load_config, recognize, grid_recognize
```
改为：
```python
from find_num import load_config, select_preset, recognize, grid_recognize
```

- [ ] **步骤 2：重写 `_adapt_config`**

将现有的 `_adapt_config` 函数（第 44-72 行）替换为：
```python
def _adapt_config(config):
    targets_cfg, grid_cfg, base_w, base_h = select_preset(config)

    adapted_targets = {}
    for name, region in targets_cfg.items():
        x1, y1, x2, y2 = region["x1"], region["y1"], region["x2"], region["y2"]
        mss_cfg = ResolutionAdapter.get_mss_config(
            _to_base_region(x1, y1, x2, y2),
            base_w=base_w, base_h=base_h
        )
        adapted_region = _from_mss_config(mss_cfg)
        adapted_region["digits"] = region.get("digits", 2)
        adapted_targets[name] = adapted_region

    cols = grid_cfg["cols"]
    rows = grid_cfg["rows"]
    total_w = cols * grid_cfg["cell_w"]
    total_h = rows * grid_cfg["cell_h"]
    mss_cfg = ResolutionAdapter.get_mss_config(
        (grid_cfg["x"], grid_cfg["y"], total_w, total_h),
        base_w=base_w, base_h=base_h
    )

    adapted_grid = {
        "x": mss_cfg["left"],
        "y": mss_cfg["top"],
        "cell_w": mss_cfg["width"] // cols,
        "cell_h": mss_cfg["height"] // rows,
        "cols": cols,
        "rows": rows,
        "cursor_w": grid_cfg.get("cursor_w", 4),
    }

    return adapted_targets, adapted_grid
```

- [ ] **步骤 3：验证导入无误**

运行：`python -c "from num_match import _adapt_config; from find_num import load_config; c = load_config('num_config.json'); t, g = _adapt_config(c); print('grid x:', g['x'], 'y:', g['y'])"`
预期：输出 grid x/y 值（取决于当前屏幕分辨率）

- [ ] **步骤 4：Commit**

```bash
git add num_match.py
git commit -m "feat(num_match): use select_preset with dynamic base resolution"
```

---

### 任务 5：debug_grid.py — 改用 select_preset

**文件：**
- 修改：`debug_grid.py:4-12`

- [ ] **步骤 1：替换 import**

将第 4 行：
```python
from find_num import load_config, recognize, grid_recognize
```
改为：
```python
from find_num import load_config, select_preset, recognize, grid_recognize
```

- [ ] **步骤 2：更新 `draw_debug` 中获取配置的方式**

将第 8-10 行：
```python
    config = load_config(config_path)
    targets_cfg = config.get("targets", {})
    grid_cfg = config.get("grid", {})
```

改为：
```python
    config = load_config(config_path)
    targets_cfg, grid_cfg, base_w, base_h = select_preset(config)
```

- [ ] **步骤 3：验证导入无误**

运行：`python -c "from debug_grid import draw_debug; print('import OK')"`
预期：`import OK`（如果截图文件不存在会报其他错，但 import 本身应成功）

- [ ] **步骤 4：Commit**

```bash
git add debug_grid.py
git commit -m "feat(debug_grid): use select_preset for multi-preset support"
```

---

## 验证

全部完成后，在 16:9 分辨率下运行 `python -c "from num_match import main; main()"` 确认行为与改动前一致（坐标不变）。在 16:10 分辨率下填入 1610 预设的坐标后同样验证。
