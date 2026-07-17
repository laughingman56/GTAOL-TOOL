import mss
import pydirectinput
import time

from PIL import Image
import dhash
import mss_dpi
from config_manager import ConfigManager


class CayoLogic:
    TEMPLATE_HASHES = {
        '1.png': 7597978777325473801,
        '2.png': 8460409310008258577,
        '3.png': 16848372344164646945,
        '4.png': 7883948592869748817,
        '5.png': 16850633008656506933,
        '6.png': 7597974139430307863,
        '7.png': 7597978709812918361,
    }
    ROW_COORDS = [
        (510, 470, 625, 95),
        (510, 571, 625, 95),
        (510, 673, 625, 95),
        (510, 773, 625, 95),
        (510, 875, 625, 95),
        (510, 976, 625, 95),
        (510, 1079, 625, 95),
        (510, 1181, 625, 95),
    ]
    HASH_DIFF_THRESHOLD = 12

    @staticmethod
    def _press_key(key, count=1, interval=0.05):
        for _ in range(count):
            pydirectinput.keyDown(key)
            pydirectinput.keyUp(key)
            if count > 1:
                time.sleep(interval)

    @staticmethod
    def _get_best_move(current, target):
        if current == target:
            return ('none', 0)

        right = (target - current + 8) % 8
        left = (current - target + 8) % 8

        if right <= left:
            return ('d', right)
        else:
            return ('a', left)


    @staticmethod
    def cayo_finger_run():

        pydirectinput.PAUSE = 0.05
        pydirectinput.FAILSAFE = False

        print("[Cayo] 运行中...")

        # --- 第1轮：采集8个位置的哈希 ---
        cycle_hashes = []
        row0_cfg = mss_dpi.ResolutionAdapter.get_mss_config(CayoLogic.ROW_COORDS[0])
        with mss.mss() as sct:
            for i in range(8):
                sct_img = sct.grab(row0_cfg)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                cycle_hashes.append(dhash.calculate_dhash(img))

                if i < 7:
                    CayoLogic._press_key('d')
                    time.sleep(0.05)

            CayoLogic._press_key('d')
            time.sleep(0.05)

        # --- 从模板中匹配当前在第几个 ---
        target_idx = -1
        min_diff = 100
        for idx, curr_h in enumerate(cycle_hashes):
            for tmpl_h in CayoLogic.TEMPLATE_HASHES.values():
                diff = dhash.hamming_distance(curr_h, tmpl_h)
                if diff < CayoLogic.HASH_DIFF_THRESHOLD and diff < min_diff:
                    min_diff = diff
                    target_idx = idx

        if target_idx == -1:
            return

        # --- 计算第0行的移动量 ---
        moves = [(0, *CayoLogic._get_best_move(0, target_idx))]

        # --- 第2轮：扫描剩余行 ---
        with mss.mss() as sct:
            for row in range(1, 8):
                row_cfg = mss_dpi.ResolutionAdapter.get_mss_config(CayoLogic.ROW_COORDS[row])
                sct_img = sct.grab(row_cfg)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                curr_h = dhash.calculate_dhash(img)

                best_diff = 100
                curr_cycle_idx = -1
                for idx, h in enumerate(cycle_hashes):
                    diff = dhash.hamming_distance(h, curr_h)
                    if diff < best_diff:
                        best_diff = diff
                        curr_cycle_idx = idx

                expected_target = (target_idx + row) % 8
                moves.append((row, *CayoLogic._get_best_move(curr_cycle_idx, expected_target)))

        # --- 执行移动 ---
        for i, (row, direction, count) in enumerate(moves):
            if i > 0:
                CayoLogic._press_key('s')
                #time.sleep(0.05)

            if count > 0:
                CayoLogic._press_key(direction, count=count, interval=0.05 )

        print("[Cayo] 完成")
        pydirectinput.PAUSE = 0.1

