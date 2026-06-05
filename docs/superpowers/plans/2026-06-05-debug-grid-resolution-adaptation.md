# debug_grid 分辨率适配 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 让 `debug_grid.py` 在不同分辨率的截图上正确绘制网格叠加（将预设的基准坐标缩放到截图实际尺寸）。

**架构：** 在 `ResolutionAdapter.get_mss_config` 中增加 `target_w`/`target_h` 可选参数，允许指定目标画布尺寸（而非调用 `get_game_window_rect`）。`debug_grid.py` 打开截图后传入截图尺寸作为目标，复用中心锚点缩放逻辑。

**技术栈：** Python, PIL, win32api

---

### 任务 1：`mss_dpi.py` — `get_mss_config` 接受自定义目标尺寸

**文件：**
- 修改：`mss_dpi.py:38-67`

- [ ] **步骤 1：给 `get_mss_config` 加 `target_w`、`target_h` 可选参数**

将方法签名从：
```python
def get_mss_config(cls, base_config_tuple, base_w=None, base_h=None):
```
改为：
```python
def get_mss_config(cls, base_config_tuple, base_w=None, base_h=None,
                   target_w=None, target_h=None):
```

并将方法体内的：
```python
win_x, win_y, win_w, win_h = cls.get_game_window_rect()
```
改为：
```python
if target_w is not None and target_h is not None:
    win_x, win_y, win_w, win_h = 0, 0, target_w, target_h
else:
    win_x, win_y, win_w, win_h = cls.get_game_window_rect()
```

完整的修改后方法：
```python
    @classmethod
    def get_mss_config(cls, base_config_tuple, base_w=None, base_h=None,
                       target_w=None, target_h=None):
        """ 直接返回 mss 需要的字典格式 """
        if base_w is None: base_w = cls.BASE_W
        if base_h is None: base_h = cls.BASE_H

        base_cx = base_w / 2
        base_cy = base_h / 2

        if target_w is not None and target_h is not None:
            win_x, win_y, win_w, win_h = 0, 0, target_w, target_h
        else:
            win_x, win_y, win_w, win_h = cls.get_game_window_rect()
        scale_factor = win_h / base_h
        orig_x, orig_y, orig_w, orig_h = base_config_tuple

        orig_cx = orig_x + (orig_w / 2)
        orig_cy = orig_y + (orig_h / 2)
        off_x = orig_cx - base_cx
        off_y = orig_cy - base_cy

        curr_cx = win_x + (win_w / 2)
        curr_cy = win_y + (win_h / 2)
        new_cx = curr_cx + (off_x * scale_factor)
        new_cy = curr_cy + (off_y * scale_factor)
        new_w = orig_w * scale_factor
        new_h = orig_h * scale_factor

        return {
            'top': int(new_cy - new_h / 2),
            'left': int(new_cx - new_w / 2),
            'width': int(new_w),
            'height': int(new_h)
        }
```

- [ ] **步骤 2：验证向后兼容 — 不传 target_w/target_h 行为不变**

运行：`python -c "from mss_dpi import ResolutionAdapter; c = ResolutionAdapter.get_mss_config((600, 535, 1280, 640)); print(type(c))"`
预期：`<class 'dict'>` 且不报错

- [ ] **步骤 3：Commit**

```bash
git add mss_dpi.py
git commit -m "feat(mss_dpi): add target_w/target_h params to get_mss_config"
```

---

### 任务 2：`debug_grid.py` — 坐标缩放适配截图分辨率

**文件：**
- 修改：`debug_grid.py:1-77`

- [ ] **步骤 1：添加 `ResolutionAdapter` 导入，保留 `base_w`/`base_h`**

将第 4 行替换为：
```python
from find_num import load_config, select_preset, recognize, grid_recognize
from mss_dpi import ResolutionAdapter
```

将第 9 行 `*_` 改为保留变量：
```python
targets_cfg, grid_cfg, base_w, base_h = select_preset(config)
```

- [ ] **步骤 2：缩放 targets 坐标**

在第 15 行 `screenshot = Image.open(screenshot_path)` 之后插入缩放逻辑，将 `targets_cfg` 和 `grid_cfg` 的坐标从基准分辨率映射到截图尺寸。

完整修改后的 `draw_debug` 函数：
```python
def draw_debug(screenshot_path, config_path="num_config.json", output_path="debug_grid.png"):
    config = load_config(config_path)
    targets_cfg, grid_cfg, base_w, base_h = select_preset(config)

    if not targets_cfg or not grid_cfg:
        print("[debug_grid] targets or grid config missing")
        return

    screenshot = Image.open(screenshot_path)
    sw, sh = screenshot.size

    scaled_targets = {}
    for name, region in targets_cfg.items():
        mss_cfg = ResolutionAdapter.get_mss_config(
            _to_base_region(region["x1"], region["y1"], region["x2"], region["y2"]),
            base_w=base_w, base_h=base_h,
            target_w=sw, target_h=sh
        )
        r = _from_mss_config(mss_cfg)
        r["digits"] = region.get("digits", 2)
        scaled_targets[name] = r

    cols = grid_cfg["cols"]
    rows = grid_cfg["rows"]
    total_w = cols * grid_cfg["cell_w"]
    total_h = rows * grid_cfg["cell_h"]
    mss_cfg = ResolutionAdapter.get_mss_config(
        (grid_cfg["x"], grid_cfg["y"], total_w, total_h),
        base_w=base_w, base_h=base_h,
        target_w=sw, target_h=sh
    )
    scaled_grid = {
        "x": mss_cfg["left"],
        "y": mss_cfg["top"],
        "cell_w": mss_cfg["width"] // cols,
        "cell_h": mss_cfg["height"] // rows,
        "cols": cols,
        "rows": rows,
        "cursor_w": grid_cfg.get("cursor_w", 4),
    }

    draw = ImageDraw.Draw(screenshot)

    try:
        font = ImageFont.truetype("arial.ttf", 12)
    except OSError:
        font = ImageFont.load_default()

    blue = (0, 100, 255)
    green = (0, 200, 0)
    red = (255, 0, 0)
    yellow = (255, 255, 0)

    targets = recognize(screenshot, scaled_targets)

    for name, region in scaled_targets.items():
        x1, y1, x2, y2 = region["x1"], region["y1"], region["x2"], region["y2"]
        draw.rectangle([x1, y1, x2, y2], outline=blue, width=2)
        mid_x = x1 + (x2 - x1) // 2
        draw.line([(mid_x, y1), (mid_x, y2)], fill=red, width=1)
        val = targets.get(name, "?")
        draw.text((x2 + 4, y1 - 2), f"{name}={val}", fill=blue, font=font)

    grade = grid_recognize(screenshot, scaled_grid)

    gx = scaled_grid["x"]
    gy = scaled_grid["y"]
    cw = scaled_grid["cell_w"]
    ch = scaled_grid["cell_h"]

    for r in range(rows):
        for c in range(cols):
            x1 = gx + c * cw
            y1 = gy + r * ch
            x2 = x1 + cw
            y2 = y1 + ch

            draw.rectangle([x1, y1, x2, y2], outline=green, width=1)

            mid_x = x1 + cw // 2
            draw.line([(mid_x, y1), (mid_x, y2)], fill=red, width=1)

            val = grade[r][c] if r < len(grade) and c < len(grade[r]) else "?"
            draw.text((x1 + 2, y1 + 2), val, fill=yellow, font=font)

    screenshot.save(output_path)
    print(f"[debug_grid] saved to {output_path}")
    print(f"[debug_grid] targets: {targets}")
    print("[debug_grid] grid:")
    for row in grade:
        print("  " + " ".join(row))
```

还需要在文件顶部（`draw_debug` 函数之前）添加两个辅助函数，与 `num_match.py` 中同名函数一致：
```python
def _to_base_region(x1, y1, x2, y2):
    return (x1, y1, x2 - x1, y2 - y1)


def _from_mss_config(cfg):
    return {
        "x1": cfg["left"],
        "y1": cfg["top"],
        "x2": cfg["left"] + cfg["width"],
        "y2": cfg["top"] + cfg["height"],
    }
```

- [ ] **步骤 3：验证可调用**

运行：`python -c "from debug_grid import draw_debug; print('import OK')"`
预期：`import OK`

- [ ] **步骤 4：Commit**

```bash
git add debug_grid.py
git commit -m "feat(debug_grid): scale coords to screenshot resolution"
```

---

## 改动文件总览

| 文件 | 改动 |
|------|------|
| `mss_dpi.py` | `get_mss_config` 加 `target_w`/`target_h` 可选参数 |
| `debug_grid.py` | 加 `ResolutionAdapter` 导入、保留 `base_w`/`base_h`、坐标通过 `get_mss_config` 缩放、新增 `_to_base_region`/`_from_mss_config` |

## 验证

在 `debug_grid.py` 入口中已配置默认截图路径。运行 `python debug_grid.py <截图路径>`，确认输出的 `debug_grid.png` 上网格和 targets 矩形框与实际数字位置对齐。
