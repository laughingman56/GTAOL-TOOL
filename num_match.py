import time
import mss
import pydirectinput
from PIL import Image
from find_num import load_config, recognize, grid_recognize
from mss_dpi import ResolutionAdapter

DELAY = 0.05
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


def _scale_config(config, config_base_h, game_h):
    if config_base_h <= 0 or game_h <= 0:
        return config
    scale = float(game_h) / config_base_h
    if abs(scale - 1.0) < 0.01:
        return config
    print(f"[num_match] resolucao: base={config_base_h}p atual={game_h}p escala={scale:.3f}")
    import copy
    scaled = copy.deepcopy(config)
    for name, region in scaled.get("targets", {}).items():
        for key in ("x1", "y1", "x2", "y2"):
            if key in region:
                region[key] = int(region[key] * scale)
    grid = scaled.get("grid", {})
    for key in ("x", "y", "cell_w", "cell_h"):
        if key in grid:
            grid[key] = int(grid[key] * scale)
    return scaled


def main():
    START_ROW = 3
    START_COL = 3

    config = load_config("num_config.json")
    targets_cfg = config.get("targets", {})
    grid_cfg = config.get("grid", {})

    config_base_h = config.get("base_h", 0)
    if config_base_h > 0:
        _, _, _, game_h = ResolutionAdapter.get_game_window_rect()
        config = _scale_config(config, config_base_h, game_h)
        targets_cfg = config.get("targets", {})
        grid_cfg = config.get("grid", {})

    if not targets_cfg:
        print("[num_match] targets config not found")
        return
    if not grid_cfg:
        print("[num_match] grid config not found")
        return

    print("[num_match] capturando tela...")
    screenshot = capturar_tela()

    print("[num_match] reconhecendo alvos...")
    targets = recognize(screenshot, targets_cfg)
    t0 = targets.get("t0", "")
    t1 = targets.get("t1", "")
    if not t0 or not t1:
        print(f"[num_match] falha ao reconhecer alvos: t0={t0} t1={t1}")
        return
    print(f"[num_match] alvos: t0={t0} t1={t1}")

    print("[num_match] reconhecendo grade...")
    grade = grid_recognize(screenshot, grid_cfg)
    print("[num_match] grade reconhecida:")
    for row in grade:
        print("  " + " ".join(row))

    print("[num_match] buscando correspondencia...")
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
        print("[num_match] correspondencia nao encontrada")
        return

    r, c = encontrado
    print(f"[num_match] correspondencia encontrada: linha={r} coluna={c}")
    dr = r - START_ROW
    dc = c - START_COL - 2
    print(f"[num_match] movendo: dr={dr} dc={dc}")
    mover_cursor(dr, dc)

    print("[num_match] aguardando numeros sob o cursor...")
    for tentativa in range(200):
        time.sleep(0.05)
        screenshot = capturar_tela()
        grade = grid_recognize(screenshot, grid_cfg)
        for cc in range(max(0, c - 2), min(c + 2, cols - 1)):
            if grade[r][cc] == t0 and grade[r][cc + 1] == t1:
                print(f"[num_match] conferido: {t0} {t1} na coluna {cc}")
                pydirectinput.press("enter")
                print("[num_match] concluido")
                return

    print("[num_match] timeout")


if __name__ == "__main__":
    main()