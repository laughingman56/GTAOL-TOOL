import mss
import pydirectinput
from PIL import Image
from find_num import load_config, recognize, grid_recognize
from mss_dpi import ResolutionAdapter

DELAY = 0
pydirectinput.PAUSE = 0.02
pydirectinput.FAILSAFE = False


def capturar_tela():
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        sct_img = sct.grab(monitor)
        return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")


def mover_cursor(dr, dc):
    if dr > 0:
        pydirectinput.press("down", presses=dr, interval=DELAY)
    elif dr < 0:
        pydirectinput.press("up", presses=-dr, interval=DELAY)

    if dc > 0:
        pydirectinput.press("right", presses=dc, interval=DELAY)
    elif dc < 0:
        pydirectinput.press("left", presses=-dc, interval=DELAY)


def _to_base_region(x1, y1, x2, y2):
    return (x1, y1, x2 - x1, y2 - y1)


def _from_mss_config(cfg):
    return {
        "x1": cfg["left"],
        "y1": cfg["top"],
        "x2": cfg["left"] + cfg["width"],
        "y2": cfg["top"] + cfg["height"],
    }


def _adapt_config(config):
    targets_cfg = config.get("targets", {})
    grid_cfg = config.get("grid", {})

    adapted_targets = {}
    for name, region in targets_cfg.items():
        x1, y1, x2, y2 = region["x1"], region["y1"], region["x2"], region["y2"]
        mss_cfg = ResolutionAdapter.get_mss_config(_to_base_region(x1, y1, x2, y2))
        adapted_region = _from_mss_config(mss_cfg)
        adapted_region["digits"] = region.get("digits", 2)
        adapted_targets[name] = adapted_region

    cols = grid_cfg["cols"]
    rows = grid_cfg["rows"]
    total_w = cols * grid_cfg["cell_w"]
    total_h = rows * grid_cfg["cell_h"]
    mss_cfg = ResolutionAdapter.get_mss_config((grid_cfg["x"], grid_cfg["y"], total_w, total_h))

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


def main():
    START_ROW = 3
    START_COL = 3

    config = load_config("num_config.json")
    targets_cfg, grid_cfg = _adapt_config(config)

    if not targets_cfg:
        print("[num_match] 未找到目标配置")
        return
    if not grid_cfg:
        print("[num_match] 未找到网格配置")
        return

    print("[num_match] 正在截屏...")
    screenshot = capturar_tela()

    print("[num_match] 正在识别目标...")
    targets = recognize(screenshot, targets_cfg)
    t0 = targets.get("t0", "")
    t1 = targets.get("t1", "")
    if not t0 or not t1:
        print(f"[num_match] 识别目标失败: t0={t0} t1={t1}")
        return
    print(f"[num_match] 目标: t0={t0} t1={t1}")

    print("[num_match] 正在识别网格...")
    grade = grid_recognize(screenshot, grid_cfg)
    print("[num_match] 网格识别结果:")
    for row in grade:
        print("  " + " ".join(row))

    print("[num_match] 正在搜索匹配...")
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
        print("[num_match] 未找到匹配")
        return

    r, c = encontrado
    print(f"[num_match] 找到匹配: 第{r}行 第{c}列")
    dr = r - START_ROW
    dc = c - START_COL - 2
    print(f"[num_match] 移动: dr={dr} dc={dc}")
    mover_cursor(dr, dc)
    print("[num_match] 完成")


