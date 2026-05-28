"""Auto-detect grid and targets from screenshot using pixel projection."""

import numpy as np
from PIL import Image

_BINARIZE_THRESHOLD_FACTOR = 1.2
_TARGET_PAD_SMALL = 10
_GRID_PAD = 20


class GridDetectError(Exception):
    pass


def _binarize(image, threshold=None):
    gray = np.array(image.convert("L"), dtype=np.float32)
    if threshold is None:
        threshold = gray.mean() * _BINARIZE_THRESHOLD_FACTOR
    return (gray > threshold).astype(np.uint8)


def _horizontal_projection(binary):
    return binary.sum(axis=1).astype(np.int32)


def _vertical_projection(binary):
    return binary.sum(axis=0).astype(np.int32)


def _smooth(arr, window=5):
    kernel = np.ones(window) / window
    return np.convolve(arr, kernel, mode="same")


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

    sorted_idx = np.argsort(widths)[::-1]

    grid_idx = sorted_idx[0]
    grid_y1_small = starts[grid_idx]
    grid_y2_small = ends[grid_idx]

    target_indices = []
    for idx in sorted_idx[1:]:
        if starts[idx] < grid_y1_small and ends[idx] < grid_y1_small:
            target_indices.append(idx)
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

        pad = _TARGET_PAD_SMALL
        targets.append({
            "x1_small": max(tx1 - pad, 0),
            "y1_small": max(t_y1_small - pad, 0),
            "x2_small": min(tx2 + pad, sw),
            "y2_small": min(t_y2_small + pad, sh),
        })

    scale_x = w / sw
    scale_y = h / sh
    pad = _GRID_PAD
    grid_region = (
        0,
        max(int(grid_y1_small * scale_y) - pad, 0),
        w,
        min(int(grid_y2_small * scale_y) + pad, h),
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

    if len(peaks) > num_rows and num_rows > 1:
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
        half_h = int((y_lines[-1] - y_lines[0]) / (num_rows - 1) / 2) if num_rows > 1 else len(smoothed) // (num_rows * 2)
        y1 = max(y_lines[i] - half_h, 0)
        y2 = min(y_lines[i] + half_h, len(binary) - 1)
        row_regions.append((y1, y2))

    return y_lines, row_regions


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

    if len(peaks) > num_cols and num_cols > 1:
        peak_centers = [(p[0] + p[1]) / 2 for p in peaks]
        used = [False] * len(peaks)

        for j in range(num_cols):
            target_x = x_lines[0] + j * (x_lines[-1] - x_lines[0]) / (num_cols - 1)
            best = 0
            best_dist = float("inf")
            for k in range(len(peaks)):
                if not used[k]:
                    d = abs(peak_centers[k] - target_x)
                    if d < best_dist:
                        best_dist = d
                        best = k
            used[best] = True
            x_lines[j] = int(peak_centers[best])

    return x_lines


def _equal_distance_correct(y_lines, x_lines, num_rows=8, num_cols=10):
    if len(y_lines) < 2 or len(x_lines) < 2:
        raise GridDetectError(
            f"insufficient lines for correction: rows={len(y_lines)} cols={len(x_lines)}"
        )
    if num_rows < 2 or num_cols < 2:
        raise GridDetectError(
            f"invalid dimensions: rows={num_rows} cols={num_cols}"
        )

    avg_row_h = (y_lines[-1] - y_lines[0]) / (num_rows - 1)
    y_corrected = [int(y_lines[0] + i * avg_row_h) for i in range(num_rows)]

    avg_cell_w = (x_lines[-1] - x_lines[0]) / (num_cols - 1)
    x_corrected = [int(x_lines[0] + j * avg_cell_w) for j in range(num_cols)]

    return y_corrected, x_corrected, int(avg_row_h), int(avg_cell_w)


def _split_two_digits(cell_image):
    cw = cell_image.size[0]
    if cw < 4:
        return cw // 2

    binary = _binarize(cell_image)
    v_proj = _vertical_projection(binary)
    smoothed = _smooth(v_proj.astype(np.float64), window=3)

    mid_start = cw // 3
    mid_end = 2 * cw // 3

    segment = smoothed[mid_start:mid_end]
    min_idx = int(np.argmin(segment))
    split_x = mid_start + min_idx

    if segment[min_idx] < smoothed.mean() * 0.3:
        return split_x

    return cw // 2


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


def detect_grid(screenshot):
    w, h = screenshot.size
    if w < 100 or h < 100:
        raise GridDetectError(f"screenshot too small: {w}x{h}")

    binary_full = _binarize(screenshot)
    white_ratio = binary_full.sum() / binary_full.size
    if white_ratio < 0.001:
        raise GridDetectError("screenshot appears dark/empty")

    grid_region, target_regions = _coarse_locate(screenshot)

    gx1, gy1, gx2, gy2 = grid_region
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
