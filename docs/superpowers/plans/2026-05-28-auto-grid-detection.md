# 像素投影法自动网格识别 — 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 新增 `auto_grid.py` 模块，用像素投影法自动检测截图中的 8×10 数字网格和上方两个目标数字位置，替代 `num_config.json` 中的固定坐标。

**架构：** 新增独立模块 `auto_grid.py`，导出 `detect_grid(screenshot)` 函数。内部流程：粗定位（缩图投影）→ grid 行列投影分割 → 等距校正 → targets 顶部检测 → 两位数投影分割。`num_match.py` 改为优先使用自动检测，失败时 fallback 到 `num_config.json`。

**技术栈：** Python 3, PIL (Pillow), numpy, 现有 mss/pydirectinput

**设计规格：** `docs/superpowers/specs/2026-05-28-auto-grid-detection-design.md`

---

### 任务 1：创建 `auto_grid.py` 基础框架和辅助函数

**文件：**
- 创建：`auto_grid.py`

- [ ] **步骤 1：创建文件骨架**

```python
"""Auto-detect grid and targets from screenshot using pixel projection."""

import numpy as np
from PIL import Image


class GridDetectError(Exception):
    pass


def _binarize(image, threshold=None):

    gray = np.array(image.convert("L"), dtype=np.float32)
    if threshold is None:
        threshold = gray.mean() * 1.2
    return (gray > threshold).astype(np.uint8)


def _horizontal_projection(binary):

    return binary.sum(axis=1).astype(np.int32)


def _vertical_projection(binary):

    return binary.sum(axis=0).astype(np.int32)


def _smooth(arr, window=5):

    kernel = np.ones(window) / window
    return np.convolve(arr, kernel, mode="same")
```

- [ ] **步骤 2：编写辅助函数单元测试**

```python
import numpy as np
import pytest
from PIL import Image
from auto_grid import _binarize, _horizontal_projection, _vertical_projection, _smooth


def test_binarize_auto_threshold():
    img = Image.new("RGB", (100, 50), color=(0, 0, 0))
    for x in range(20, 30):
        for y in range(10, 20):
            img.putpixel((x, y), (255, 255, 255))
    binary = _binarize(img)
    assert binary.shape == (50, 100)
    assert binary.dtype == np.uint8
    assert binary.sum() > 0


def test_binarize_explicit_threshold():
    img = Image.new("RGB", (10, 10), color=(100, 100, 100))
    binary = _binarize(img, threshold=128)
    assert binary.sum() == 0
    binary = _binarize(img, threshold=50)
    assert binary.sum() == 100


def test_horizontal_projection():
    binary = np.array([
        [1, 0, 1],
        [0, 0, 0],
        [1, 1, 1],
    ], dtype=np.uint8)
    proj = _horizontal_projection(binary)
    assert proj.tolist() == [2, 0, 3]


def test_vertical_projection():
    binary = np.array([
        [1, 0, 1],
        [0, 0, 0],
        [1, 1, 1],
    ], dtype=np.uint8)
    proj = _vertical_projection(binary)
    assert proj.tolist() == [2, 1, 2]


def test_smooth():
    arr = np.array([0, 0, 10, 0, 0], dtype=np.float64)
    result = _smooth(arr, window=3)
    assert len(result) == len(arr)
    assert result[2] > 0
```

- [ ] **步骤 3：运行测试验证通过**

运行：`pytest test_auto_grid.py -v -k "test_binarize or test_horizontal or test_vertical or test_smooth"`
预期：4 tests PASS

- [ ] **步骤 4：Commit**

```bash
git add auto_grid.py test_auto_grid.py
git commit -m "feat(auto_grid): add binary/projection/smooth utilities"
```

---

### 任务 2：实现粗定位

**文件：**
- 修改：`auto_grid.py` — 添加 `_coarse_locate()`

- [ ] **步骤 1：编写粗定位函数**

在 `auto_grid.py` 中添加：

```python
def _coarse_locate(screenshot):

    w, h = screenshot.size
    sw, sh = max(w // 4, 1), max(h // 4, 1)
    small = screenshot.resize((sw, sh), Image.LANCZOS)
    binary = _binarize(small)
    h_proj = _horizontal_projection(binary)
    smoothed = _smooth(h_proj.astype(np.float64), window=max(3, sh // 20))

    mean_val = smoothed.mean()
    threshold = max(mean_val * 0.5, 1.0)
    above = smoothed > threshold
    changes = np.diff(np.concatenate([[0], above.astype(np.int32), [0]]))

    starts = np.where(changes == 1)[0]
    ends = np.where(changes == -1)[0]
    if len(starts) == 0:
        raise GridDetectError("no bright regions found in screenshot")

    widths = ends - starts
    densities = [smoothed[s:e].mean() for s, e in zip(starts, ends)]

    sorted_idx = np.argsort([w * d for w, d in zip(widths, densities)])[::-1]

    grid_idx = sorted_idx[0]
    grid_y1_small = starts[grid_idx]
    grid_y2_small = ends[grid_idx]

    target_indices = []
    for idx in sorted_idx[1:]:
        if starts[idx] < grid_y1_small and ends[idx] < grid_y1_small:
            target_indices.append(idx)
    target_indices = target_indices[:2]

    targets = []
    for idx in target_indices:
        t_y1_small = starts[idx]
        t_y2_small = ends[idx]
        v_proj = _vertical_projection(binary[t_y1_small:t_y2_small, :])
        v_smooth = _smooth(v_proj.astype(np.float64), window=3)
        v_mean = v_smooth.mean()
        v_threshold = max(v_mean * 0.5, 1.0)
        v_above = v_smooth > v_threshold
        v_changes = np.diff(np.concatenate([[0], v_above.astype(np.int32), [0]]))
        v_starts = np.where(v_changes == 1)[0]
        v_ends = np.where(v_changes == -1)[0]
        if len(v_starts) > 0:
            max_w = 0
            best_j = 0
            for j in range(len(v_starts)):
                w_seg = v_ends[j] - v_starts[j]
                if w_seg > max_w:
                    max_w = w_seg
                    best_j = j
            tx1 = v_starts[best_j]
            tx2 = v_ends[best_j]
        else:
            tx1, tx2 = 0, sw

        pad = 10
        targets.append({
            "x1_small": max(tx1 - pad, 0),
            "y1_small": max(t_y1_small - pad, 0),
            "x2_small": min(tx2 + pad, sw),
            "y2_small": min(t_y2_small + pad, sh),
        })

    scale_x = w / sw
    scale_y = h / sh
    pad = 20
    grid_region = (
        int(grid_y1_small * scale_y) - pad,
        int(grid_y2_small * scale_y) + pad,
        0,
        w,
    )

    target_regions = []
    for t in targets:
        target_regions.append((
            int(t["x1_small"] * scale_x),
            int(t["y1_small"] * scale_y),
            int(t["x2_small"] * scale_x),
            int(t["y2_small"] * scale_y),
        ))

    return grid_region, target_regions
```

- [ ] **步骤 2：编写粗定位测试**

在 `test_auto_grid.py` 中添加：

```python
from auto_grid import _coarse_locate, GridDetectError


def test_coarse_locate_detects_grid():
    img = Image.new("RGB", (400, 300), color=(0, 0, 0))
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    for r in range(8):
        for c in range(10):
            x = 80 + c * 24
            y = 100 + r * 20
            draw.text((x, y), "42", fill=(255, 255, 255))
    grid_region, targets = _coarse_locate(img)
    assert len(grid_region) == 4
    assert grid_region[0] <= 100 <= grid_region[1]


def test_coarse_locate_dark_image_raises():
    img = Image.new("RGB", (100, 100), color=(0, 0, 0))
    try:
        _coarse_locate(img)
        assert False, "should have raised"
    except GridDetectError:
        pass
```

- [ ] **步骤 3：运行测试**

运行：`pytest test_auto_grid.py -v -k "coarse"`
预期：2 tests PASS

- [ ] **步骤 4：Commit**

```bash
git add auto_grid.py test_auto_grid.py
git commit -m "feat(auto_grid): add coarse localization for grid/targets regions"
```

---

### 任务 3：实现 grid 行分割（水平投影）

**文件：**
- 修改：`auto_grid.py` — 添加 `_detect_rows()`

- [ ] **步骤 1：编写行分割函数**

```python
def _detect_rows(roi, num_rows=8):

    binary = _binarize(roi)
    h_proj = _horizontal_projection(binary)
    smoothed = _smooth(h_proj.astype(np.float64), window=5)

    total_h = len(smoothed)
    mean_val = smoothed.mean()
    threshold = max(mean_val * 0.3, 1.0)

    peaks = []
    in_peak = False
    peak_start = 0
    for i in range(total_h):
        if smoothed[i] > threshold and not in_peak:
            in_peak = True
            peak_start = i
        elif smoothed[i] <= threshold and in_peak:
            in_peak = False
            peaks.append((peak_start, i))

    if in_peak:
        peaks.append((peak_start, total_h))

    if len(peaks) < num_rows:
        sorted_peaks = sorted(peaks, key=lambda p: p[1] - p[0], reverse=True)
        peaks = sorted_peaks[:num_rows]
        peaks.sort(key=lambda p: p[0])

    if len(peaks) < num_rows:
        raise GridDetectError(
            f"detected only {len(peaks)} rows, need {num_rows}"
        )

    y_lines = []
    for i in range(num_rows):
        cy = (peaks[i][0] + peaks[i][1]) // 2
        y_lines.append(cy)

    if len(peaks) > num_rows:
        peak_centers = [(p[0] + p[1]) / 2 for p in peaks]
        used = [False] * len(peaks)

        for i in range(num_rows):
            target_y = y_lines[0] + i * (y_lines[-1] - y_lines[0]) / (num_rows - 1)
            best = 0
            best_dist = float("inf")
            for j in range(len(peaks)):
                if not used[j]:
                    d = abs(peak_centers[j] - target_y)
                    if d < best_dist:
                        best_dist = d
                        best = j
            used[best] = True
            y_lines[i] = int(peak_centers[best])

    row_regions = []
    for i in range(num_rows):
        half_h = (y_lines[1] - y_lines[0]) // 2 if num_rows > 1 else len(smoothed) // (num_rows * 2)
        y1 = max(y_lines[i] - half_h, 0)
        y2 = min(y_lines[i] + half_h, len(binary) - 1)
        row_regions.append((y1, y2))

    return y_lines, row_regions
```

- [ ] **步骤 2：编写行分割测试**

```python
from PIL import ImageDraw
from auto_grid import _detect_rows


def test_detect_rows_8_rows():
    img = Image.new("RGB", (240, 200), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    for r in range(8):
        y = 20 + r * 20
        for c in range(10):
            x = 10 + c * 22
            draw.text((x, y), "42", fill=(255, 255, 255))
    y_lines, regions = _detect_rows(img, num_rows=8)
    assert len(y_lines) == 8
    for i in range(1, 8):
        assert y_lines[i] > y_lines[i - 1]
```

- [ ] **步骤 3：运行测试**

运行：`pytest test_auto_grid.py -v -k "detect_rows"`
预期：PASS

- [ ] **步骤 4：Commit**

```bash
git add auto_grid.py test_auto_grid.py
git commit -m "feat(auto_grid): add horizontal projection row detection"
```

---

### 任务 4：实现 grid 列分割（垂直投影）

**文件：**
- 修改：`auto_grid.py` — 添加 `_detect_columns()`

- [ ] **步骤 1：编写列分割函数**

```python
def _detect_columns(row_roi, num_cols=10):

    binary = _binarize(row_roi)
    v_proj = _vertical_projection(binary)
    smoothed = _smooth(v_proj.astype(np.float64), window=5)

    total_w = len(smoothed)
    mean_val = smoothed.mean()
    threshold = max(mean_val * 0.3, 1.0)

    peaks = []
    in_peak = False
    peak_start = 0
    for i in range(total_w):
        if smoothed[i] > threshold and not in_peak:
            in_peak = True
            peak_start = i
        elif smoothed[i] <= threshold and in_peak:
            in_peak = False
            peaks.append((peak_start, i))

    if in_peak:
        peaks.append((peak_start, total_w))

    if len(peaks) < num_cols:
        sorted_peaks = sorted(peaks, key=lambda p: p[1] - p[0], reverse=True)
        peaks = sorted_peaks[:num_cols]
        peaks.sort(key=lambda p: p[0])

    if len(peaks) < num_cols:
        raise GridDetectError(
            f"detected only {len(peaks)} columns, need {num_cols}"
        )

    x_lines = []
    for j in range(num_cols):
        cx = (peaks[j][0] + peaks[j][1]) // 2
        x_lines.append(cx)

    return x_lines
```

- [ ] **步骤 2：编写列分割测试**

```python
from auto_grid import _detect_columns


def test_detect_columns_10_cols():
    img = Image.new("RGB", (260, 20), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    for c in range(10):
        x = 10 + c * 24
        draw.text((x, 2), "42", fill=(255, 255, 255))
    x_lines = _detect_columns(img, num_cols=10)
    assert len(x_lines) == 10
    for i in range(1, 10):
        assert x_lines[i] > x_lines[i - 1]
```

- [ ] **步骤 3：运行测试**

运行：`pytest test_auto_grid.py -v -k "detect_columns"`
预期：PASS

- [ ] **步骤 4：Commit**

```bash
git add auto_grid.py test_auto_grid.py
git commit -m "feat(auto_grid): add vertical projection column detection"
```

---

### 任务 5：实现等距校正和两位数投影分割

**文件：**
- 修改：`auto_grid.py` — 添加 `_equal_distance_correct()` 和 `_split_two_digits()`

- [ ] **步骤 1：编写等距校正函数**

```python
def _equal_distance_correct(y_lines, x_lines, num_rows=8, num_cols=10):

    if len(y_lines) >= 2:
        avg_row_h = (y_lines[-1] - y_lines[0]) / (num_rows - 1)
    else:
        avg_row_h = 20
    y_corrected = [int(y_lines[0] + i * avg_row_h) for i in range(num_rows)]

    if len(x_lines) >= 2:
        avg_cell_w = (x_lines[-1] - x_lines[0]) / (num_cols - 1)
    else:
        avg_cell_w = 20
    x_corrected = [int(x_lines[0] + j * avg_cell_w) for j in range(num_cols)]

    return y_corrected, x_corrected, int(avg_row_h), int(avg_cell_w)
```

- [ ] **步骤 2：编写两位数分割函数**

```python
def _split_two_digits(cell_image):

    cw = cell_image.size[0]
    if cw < 4:
        return cw // 2

    gray = np.array(cell_image.convert("L"), dtype=np.float32)
    binary = (gray > gray.mean() * 1.2).astype(np.uint8)
    v_proj = _vertical_projection(binary)
    smoothed = _smooth(v_proj.astype(np.float64), window=3)

    mid_start = cw // 3
    mid_end = 2 * cw // 3
    if mid_end <= mid_start:
        return cw // 2

    segment = smoothed[mid_start:mid_end]
    min_idx = int(np.argmin(segment))
    split_x = mid_start + min_idx

    if segment[min_idx] < smoothed.mean() * 0.3:
        return split_x

    return cw // 2
```

- [ ] **步骤 3：编写测试**

```python
from auto_grid import _equal_distance_correct, _split_two_digits


def test_equal_distance_correct():
    y_lines = [100, 120, 140, 160, 180, 200, 220, 240]
    x_lines = [10, 30, 50, 70, 90, 110, 130, 150, 170, 190]
    yc, xc, avg_h, avg_w = _equal_distance_correct(y_lines, x_lines)
    assert avg_h == 20
    assert avg_w == 20
    assert yc == [100, 120, 140, 160, 180, 200, 220, 240]


def test_split_two_digits_fallback():
    img = Image.new("RGB", (30, 20), color=(0, 0, 0))
    split = _split_two_digits(img)
    assert split == 15


def test_split_two_digits_gap():
    img = Image.new("RGB", (40, 20), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((2, 2), "1", fill=(255, 255, 255))
    draw.text((24, 2), "2", fill=(255, 255, 255))
    split = _split_two_digits(img)
    assert 15 <= split <= 25
```

- [ ] **步骤 4：运行测试**

运行：`pytest test_auto_grid.py -v -k "equal_distance or split_two"`
预期：3 tests PASS

- [ ] **步骤 5：Commit**

```bash
git add auto_grid.py test_auto_grid.py
git commit -m "feat(auto_grid): add equal-distance correction and two-digit splitting"
```

---

### 任务 6：实现 targets 检测和主入口函数

**文件：**
- 修改：`auto_grid.py` — 添加 `_detect_targets()` 和 `detect_grid()`

- [ ] **步骤 1：编写 targets 检测函数**

```python
def _detect_targets(screenshot, target_region):

    x1, y1, x2, y2 = target_region
    if x2 <= x1 or y2 <= y1:
        raise GridDetectError("invalid target region")

    roi = screenshot.crop((x1, y1, x2, y2))
    binary = _binarize(roi)
    v_proj = _vertical_projection(binary)
    smoothed = _smooth(v_proj.astype(np.float64), window=3)
    mean_val = smoothed.mean()
    threshold = max(mean_val * 0.3, 1.0)

    above = smoothed > threshold
    changes = np.diff(np.concatenate([[0], above.astype(np.int32), [0]]))
    starts = np.where(changes == 1)[0]
    ends = np.where(changes == -1)[0]

    digit_regions = []
    for s, e in zip(starts, ends):
        if e - s >= 5:
            digit_regions.append((s, e))

    if len(digit_regions) < 1:
        raise GridDetectError("no target digits detected")

    digit_regions.sort(key=lambda r: r[1] - r[0], reverse=True)
    digit_regions = digit_regions[:2]
    digit_regions.sort(key=lambda r: r[0])

    targets_cfg = {}
    names = ["t0", "t1"]
    for i, (s, e) in enumerate(digit_regions):
        if i >= 2:
            break
        tx1 = x1 + max(s - 2, 0)
        tx2 = x1 + min(e + 2, x2 - x1)
        targets_cfg[names[i]] = {
            "x1": tx1,
            "y1": y1,
            "x2": tx2,
            "y2": y2,
            "digits": 2,
        }

    return targets_cfg
```

- [ ] **步骤 2：编写主入口函数**

```python
def detect_grid(screenshot):

    w, h = screenshot.size
    if w < 100 or h < 100:
        raise GridDetectError(f"screenshot too small: {w}x{h}")

    binary_full = _binarize(screenshot)
    white_ratio = binary_full.sum() / binary_full.size
    if white_ratio < 0.001:
        raise GridDetectError("screenshot appears dark/empty")

    grid_region, target_regions = _coarse_locate(screenshot)

    gy1, gy2, gx1, gx2 = grid_region
    grid_roi = screenshot.crop((gx1, gy1, gx2, gy2))

    y_lines, row_regions = _detect_rows(grid_roi, num_rows=8)

    all_x_lines = []
    for ry1, ry2 in row_regions:
        row_img = grid_roi.crop((0, ry1, grid_roi.size[0], ry2))
        try:
            x_lines = _detect_columns(row_img, num_cols=10)
        except GridDetectError:
            if all_x_lines:
                x_lines = list(all_x_lines[-1])
            else:
                raise
        all_x_lines.append(x_lines)

    avg_x_lines = []
    for j in range(10):
        cols_at_j = [xl[j] for xl in all_x_lines if j < len(xl)]
        if cols_at_j:
            avg_x_lines.append(int(np.median(cols_at_j)))
        elif avg_x_lines:
            spacing = avg_x_lines[-1] - (avg_x_lines[-2] if len(avg_x_lines) > 1 else 0)
            avg_x_lines.append(avg_x_lines[-1] + spacing)

    avg_y_lines = []
    for i in range(8):
        avg_y_lines.append((row_regions[i][0] + row_regions[i][1]) // 2)

    y_corrected, x_corrected, avg_row_h, avg_cell_w = _equal_distance_correct(
        avg_y_lines, avg_x_lines
    )

    grid_cfg = {
        "x": gx1 + x_corrected[0] - avg_cell_w // 2,
        "y": gy1 + y_corrected[0] - avg_row_h // 2,
        "cell_w": avg_cell_w,
        "cell_h": avg_row_h,
        "cols": 10,
        "rows": 8,
        "cursor_w": 4,
    }

    targets_cfg = {}
    if target_regions:
        for i, tr in enumerate(target_regions[:2]):
            names = ["t0", "t1"]
            try:
                t_cfg = _detect_targets(screenshot, tr)
                targets_cfg.update(t_cfg)
            except GridDetectError:
                if i == 0:
                    raise

    if not targets_cfg:
        px = max(grid_cfg["x"] - 300, 0)
        py = max(grid_cfg["y"] - 80, 0)
        pw = 600
        ph = min(80, grid_cfg["y"] - py)
        try:
            t_cfg = _detect_targets(screenshot, (px, py, px + pw, py + ph))
            targets_cfg.update(t_cfg)
        except GridDetectError:
            raise GridDetectError("failed to detect targets")

    return targets_cfg, grid_cfg
```

- [ ] **步骤 3：编写集成测试**

```python
from auto_grid import detect_grid


def test_detect_grid_synthetic():
    img = Image.new("RGB", (800, 600), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.text((350, 50), "42", fill=(255, 255, 255))
    draw.text((420, 50), "17", fill=(255, 255, 255))

    gx, gy = 100, 150
    cw, ch = 55, 40
    for r in range(8):
        for c in range(10):
            x = gx + c * cw
            y = gy + r * ch
            draw.text((x + 2, y + 2), "42", fill=(255, 255, 255))

    targets_cfg, grid_cfg = detect_grid(img)
    assert "t0" in targets_cfg
    assert grid_cfg["cols"] == 10
    assert grid_cfg["rows"] == 8
    assert abs(grid_cfg["cell_w"] - cw) <= 5
    assert abs(grid_cfg["cell_h"] - ch) <= 5
```

- [ ] **步骤 4：运行测试**

运行：`pytest test_auto_grid.py -v -k "detect_grid or target"`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add auto_grid.py test_auto_grid.py
git commit -m "feat(auto_grid): add targets detection and main detect_grid entry"
```

---

### 任务 7：集成到 `num_match.py`

**文件：**
- 修改：`num_match.py`

- [ ] **步骤 1：修改 `num_match.py` 的 main 函数**

将 `main()` 函数中的配置加载改为：

```python
def main():
    START_ROW = 3
    START_COL = 3

    screenshot = capturar_tela()

    try:
        from auto_grid import detect_grid, GridDetectError
        targets_cfg, grid_cfg = detect_grid(screenshot)
        print("[num_match] auto grid detection succeeded")
    except (ImportError, GridDetectError) as e:
        print(f"[num_match] auto detection failed ({e}), falling back to config")
        config = load_config("num_config.json")
        targets_cfg, grid_cfg = _adapt_config(config)

    if not targets_cfg:
        print("[num_match] no targets config")
        return
    if not grid_cfg:
        print("[num_match] no grid config")
        return

    print("[num_match] recognizing targets...")
    targets = recognize(screenshot, targets_cfg)
    t0 = targets.get("t0", "")
    t1 = targets.get("t1", "")
    if not t0 or not t1:
        print(f"[num_match] target recognition failed: t0={t0} t1={t1}")
        return
    print(f"[num_match] targets: t0={t0} t1={t1}")

    print("[num_match] recognizing grid...")
    grade = grid_recognize(screenshot, grid_cfg)
    print("[num_match] grid:")
    for row in grade:
        print("  " + " ".join(row))

    print("[num_match] searching for match...")
    rows = grid_cfg["rows"]
    cols = grid_cfg["cols"]
    encontrado = None
    for r in range(rows):
        for c in range(cols - 1):
            if grade[r][c] == t0 and grade[r][c + 1] == t1:
                encontrado = (r, c)
                break
        if encontrado:
            break

    if encontrado is None:
        print("[num_match] no match found")
        return

    r, c = encontrado
    print(f"[num_match] match found: row {r}, col {c}")
    dr = r - START_ROW
    dc = c - START_COL - 2
    print(f"[num_match] moving: dr={dr} dc={dc}")
    mover_cursor(dr, dc)
    print("[num_match] done")


if __name__ == "__main__":
    main()
```

- [ ] **步骤 2：运行完整流程测试**

（需要游戏在运行，使用实际截图测试）

- [ ] **步骤 3：Commit**

```bash
git add num_match.py
git commit -m "feat(num_match): integrate auto grid detection with config fallback"
```

---

### 任务 8：最终验证和清理

**文件：**
- 修改：`auto_grid.py` — 任何修复
- 修改：`num_match.py` — 任何修复

- [ ] **步骤 1：运行全部单元测试**

```bash
pytest test_auto_grid.py -v
```

预期：所有测试 PASS

- [ ] **步骤 2：运行现有测试确保无回归**

```bash
python test_find_num.py
```

预期：All tests passed!

- [ ] **步骤 3：用 debug_grid.py 验证实际截图**

```bash
python debug_grid.py C:\path\to\screenshot.png
```

预期：网格线正确对齐，数字识别准确。

- [ ] **步骤 4：Commit 最终修复**

```bash
git add -A
git commit -m "chore: final verification and cleanup"
```
