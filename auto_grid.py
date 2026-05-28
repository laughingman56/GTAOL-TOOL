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
