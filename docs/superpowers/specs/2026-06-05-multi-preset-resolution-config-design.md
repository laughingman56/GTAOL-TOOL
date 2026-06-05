# 多预设分辨率配置 — 设计规格

## 概述

当前 `num_config.json` 只有一套坐标（校准于 2560×1440，16:9），通过 `ResolutionAdapter` 缩放到实际分辨率。当实际显示为 16:10（如 1920×1200）时，宽高比不匹配导致网格坐标偏移。

**方案：** 在 `num_config.json` 中存储多套预设，每套自携基准分辨率。运行时根据实际屏幕宽高比自动选择最接近的预设，再将预设坐标通过 `ResolutionAdapter` 缩放。

## num_config.json 格式

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

- `"169"`、`"1610"` 为可读标识，匹配依据为 `base_w / base_h`
- `1610` 预设坐标用 `-1` 占位，用户在 16:10 分辨率下校准后填入
- 每套预设的 `targets`/`grid` 结构与现有格式一致

## mss_dpi.py 改动

`ResolutionAdapter.get_mss_config` 新增可选参数 `base_w`、`base_h`（默认 2560、1440）：

```python
@classmethod
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

不传参数时行为完全不变，兼容所有现有调用方。

## find_num.py 改动

新增 `select_preset(config)` 函数：

```python
def select_preset(config):
    presets = config.get("presets")
    # backward compat: old format with top-level targets/grid
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

## num_match.py 改动

`_adapt_config` 改为先调用 `select_preset`，再将 `base_w`/`base_h` 传入 `get_mss_config`：

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

## debug_grid.py 改动

`draw_debug` 中获取 targets/grid 的方式改为通过 `select_preset`：

```python
config = load_config(config_path)
targets_cfg, grid_cfg, base_w, base_h = select_preset(config)
# 后续不变
```

## 改动文件总览

| 文件 | 改动类型 |
|------|---------|
| `num_config.json` | 重构为 `presets` 结构，加 1610 占位 |
| `mss_dpi.py` | `get_mss_config` 加 `base_w`/`base_h` 可选参数 |
| `find_num.py` | 新增 `select_preset(config)`，新增 import `mss_dpi` |
| `num_match.py` | `_adapt_config` 改用 `select_preset`，传 `base_w`/`base_h` |
| `debug_grid.py` | 改用 `select_preset` 获取坐标 |

## 向后兼容

- `select_preset` 发现 config 中无 `presets` 键时，回退读取顶层 `targets`/`grid`，基准 2560×1440——与当前行为一致
- `get_mss_config` 不传新参数时行为不变——10 个现有调用方零影响

## 边界情况

- **只有一个预设**：直接返回该预设，diff = 0
- **拉相等**：stable，取首个匹配的
- **坐标占位值（-1）**：由用户后续校准填入，校准前该预设不可用
