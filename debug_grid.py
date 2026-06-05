import sys
from PIL import Image, ImageDraw, ImageFont
from find_num import load_config, select_preset, recognize, grid_recognize
from mss_dpi import ResolutionAdapter, to_base_region, from_mss_config


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
            to_base_region(region["x1"], region["y1"], region["x2"], region["y2"]),
            base_w=base_w, base_h=base_h,
            target_w=sw, target_h=sh
        )
        r = from_mss_config(mss_cfg)
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


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        shot = sys.argv[1]
        cfg = sys.argv[2] if len(sys.argv) > 2 else "num_config.json"
    else:
        shot = r"C:\Users\Administrator\Desktop\屏幕截图 2026-06-05 210229.png"
        cfg = "num_config.json"
    draw_debug(shot, cfg)
