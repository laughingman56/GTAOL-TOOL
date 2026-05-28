"""Auto grid detection debug tool."""
import sys
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from auto_grid import (
    detect_grid, GridDetectError,
    _coarse_locate, _detect_rows, _detect_columns,
    _equal_distance_correct, _binarize,
)
from find_num import recognize, grid_recognize


def _get_font():
    try:
        return ImageFont.truetype("arial.ttf", 12)
    except OSError:
        try:
            return ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 12)
        except OSError:
            return ImageFont.load_default()


def draw_debug_auto(screenshot_path, output_dir="debug_output"):
    os.makedirs(output_dir, exist_ok=True)
    screenshot = Image.open(screenshot_path)
    w, h = screenshot.size
    font = _get_font()
    print(f"[debug] screenshot: {w}x{h}")

    binary_full = _binarize(screenshot)
    white_ratio = binary_full.sum() / binary_full.size
    print(f"[debug] white pixel ratio: {white_ratio:.4f}")

    if white_ratio < 0.001:
        print("[debug] SCREENSHOT APPEARS DARK - detection will fail")
        Image.fromarray((binary_full * 255).astype(np.uint8)).save(
            os.path.join(output_dir, "00_binary_full.png"))
        return

    Image.fromarray((binary_full * 255).astype(np.uint8)).save(
        os.path.join(output_dir, "00_binary_full.png"))

    try:
        grid_region, target_regions = _coarse_locate(screenshot)
    except GridDetectError as e:
        print(f"[debug] COARSE LOCATE FAILED: {e}")
        return

    gx1, gy1, gx2, gy2 = grid_region
    print(f"[debug] grid_region: ({gx1}, {gy1}, {gx2}, {gy2})")
    print(f"[debug] target_regions: {target_regions}")

    coarse_img = screenshot.copy()
    draw = ImageDraw.Draw(coarse_img)
    draw.rectangle([gx1, gy1, gx2, gy2], outline=(0, 200, 0), width=3)
    for tr in target_regions:
        draw.rectangle([tr[0], tr[1], tr[2], tr[3]], outline=(200, 0, 0), width=3)
    coarse_img.save(os.path.join(output_dir, "01_coarse_regions.png"))
    print("[debug] saved 01_coarse_regions.png")

    grid_roi = screenshot.crop((gx1, gy1, gx2, gy2))
    grid_roi.save(os.path.join(output_dir, "02_grid_roi.png"))

    roi_binary = _binarize(grid_roi)
    Image.fromarray((roi_binary * 255).astype(np.uint8)).save(
        os.path.join(output_dir, "03_roi_binary.png"))
    print("[debug] saved 02_grid_roi.png, 03_roi_binary.png")

    try:
        y_lines, row_regions = _detect_rows(grid_roi, num_rows=8)
    except GridDetectError as e:
        print(f"[debug] ROW DETECTION FAILED: {e}")
        return

    print(f"[debug] detected {len(y_lines)} row centers: {y_lines}")
    print(f"[debug] row_regions: {row_regions}")

    rows_img = grid_roi.copy()
    dr = ImageDraw.Draw(rows_img)
    for i, y in enumerate(y_lines):
        dr.line([(0, y), (grid_roi.size[0], y)], fill=(255, 0, 0), width=1)
        dr.text((4, y + 2), str(i), fill=(0, 255, 0), font=font)
    for y1, y2 in row_regions:
        dr.rectangle([0, y1, grid_roi.size[0], y2], outline=(0, 0, 255), width=1)
    rows_img.save(os.path.join(output_dir, "04_detected_rows.png"))
    print("[debug] saved 04_detected_rows.png")

    all_x_lines = []
    for i, (ry1, ry2) in enumerate(row_regions):
        row_img = grid_roi.crop((0, ry1, grid_roi.size[0], ry2))
        row_img.save(os.path.join(output_dir, f"05_row_{i}.png"))
        row_binary = _binarize(row_img)
        Image.fromarray((row_binary * 255).astype(np.uint8)).save(
            os.path.join(output_dir, f"05_row_{i}_binary.png"))

        try:
            x_lines = _detect_columns(row_img, num_cols=10)
        except GridDetectError as e:
            print(f"[debug] COLUMN DETECTION FAILED for row {i}: {e}")
            if all_x_lines:
                x_lines = list(all_x_lines[-1])
            else:
                raise

        print(f"[debug] row {i} x_lines: {x_lines}")

        cols_img = row_img.copy()
        dc = ImageDraw.Draw(cols_img)
        for j, x in enumerate(x_lines):
            dc.line([(x, 0), (x, row_img.size[1])], fill=(255, 0, 0), width=1)
            dc.text((x + 2, 2), str(j), fill=(0, 255, 0), font=font)
        cols_img.save(os.path.join(output_dir, f"05_row_{i}_cols.png"))

        all_x_lines.append(x_lines)

    avg_x_lines = []
    for j in range(10):
        cols_at_j = [xl[j] for xl in all_x_lines if j < len(xl)]
        if cols_at_j:
            avg_x_lines.append(int(np.median(cols_at_j)))
        elif avg_x_lines:
            spacing = avg_x_lines[-1] - (avg_x_lines[-2] if len(avg_x_lines) > 1 else 0)
            avg_x_lines.append(avg_x_lines[-1] + spacing)
    print(f"[debug] avg_x_lines: {avg_x_lines}")

    avg_y_lines = y_lines
    print(f"[debug] y_lines (pre-correct): {avg_y_lines}")

    try:
        y_corrected, x_corrected, avg_row_h, avg_cell_w = _equal_distance_correct(
            avg_y_lines, avg_x_lines
        )
    except GridDetectError as e:
        print(f"[debug] CORRECTION FAILED: {e}")
        return

    print(f"[debug] y_corrected: {y_corrected}")
    print(f"[debug] x_corrected: {x_corrected}")
    print(f"[debug] cell_w={avg_cell_w}, cell_h={avg_row_h}")

    grid_cfg = {
        "x": gx1 + x_corrected[0] - avg_cell_w // 2,
        "y": gy1 + y_corrected[0] - avg_row_h // 2,
        "cell_w": avg_cell_w,
        "cell_h": avg_row_h,
        "cols": 10,
        "rows": 8,
        "cursor_w": 4,
    }
    print(f"[debug] grid_cfg: {grid_cfg}")

    result_img = screenshot.copy()
    draw = ImageDraw.Draw(result_img)

    gx = grid_cfg["x"]
    gy = grid_cfg["y"]
    cw = grid_cfg["cell_w"]
    ch = grid_cfg["cell_h"]
    cols = grid_cfg["cols"]
    rows = grid_cfg["rows"]

    try:
        targets_cfg, _ = detect_grid(screenshot)
    except GridDetectError as e:
        print(f"[debug] TARGET DETECTION FAILED: {e}")
        targets_cfg = {}

    print(f"[debug] targets_cfg: {targets_cfg}")

    for name, region in targets_cfg.items():
        x1, y1, x2, y2 = region["x1"], region["y1"], region["x2"], region["y2"]
        draw.rectangle([x1, y1, x2, y2], outline=(0, 100, 255), width=2)
        mid_x = x1 + (x2 - x1) // 2
        draw.line([(mid_x, y1), (mid_x, y2)], fill=(255, 0, 0), width=1)
        draw.text((x2 + 4, y1 - 2), f"{name}", fill=(0, 100, 255), font=font)

    grade = grid_recognize(screenshot, dict(grid_cfg)) if targets_cfg else [[]]

    for r in range(rows):
        for c in range(cols):
            x1 = gx + c * cw
            y1 = gy + r * ch
            x2 = x1 + cw
            y2 = y1 + ch
            draw.rectangle([x1, y1, x2, y2], outline=(0, 200, 0), width=1)
            mid_x = x1 + cw // 2
            draw.line([(mid_x, y1), (mid_x, y2)], fill=(255, 0, 0), width=1)
            val = grade[r][c] if r < len(grade) and c < len(grade[r]) else "?"
            draw.text((x1 + 2, y1 + 2), val, fill=(255, 255, 0), font=font)

    out_path = os.path.join(output_dir, "99_final_grid.png")
    result_img.save(out_path)
    print(f"[debug] saved {out_path}")

    print("[debug] grid recognition result:")
    for row in grade:
        print("  " + " ".join(row))


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        shot = sys.argv[1]
        out = sys.argv[2] if len(sys.argv) > 2 else "debug_output"
    else:
        shot = r"C:\Users\Administrator\Desktop\shot.png"
        out = "debug_output"
    draw_debug_auto(shot, out)
