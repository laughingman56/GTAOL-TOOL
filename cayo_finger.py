import mss
import pydirectinput
import time

from PIL import Image
import dhash
import mss_dpi
from config_manager import ConfigManager  # 1. 导入 ConfigManager

class CayoLogic:
    TEMPLATE_HASHES = {'1.png': 7597978777325473801, '2.png': 8460409310008258577, '3.png': 16848372344164646945,
                       '4.png': 7883948592869748817, '5.png': 16850633008656506933, '6.png': 7597974139430307863,
                       '7.png': 7597978709812918361}
    ROW_COORDS = [(510, 470, 625, 95), (510, 571, 625, 95), (510, 673, 625, 95), (510, 773, 625, 95),
                  (510, 875, 625, 95), (510, 976, 625, 95), (510, 1079, 625, 95), (510, 1181, 625, 95)]
    HASH_DIFF_THRESHOLD = 12

    @staticmethod
    def cayo_finger_run():

        # 设置输入库的防卡死和延迟
        pydirectinput.PAUSE = 0.02
        pydirectinput.FAILSAFE = False

        # 低帧率模式
        # 获取配置管理器实例（确保你已经导入并正确初始化了 ConfigManager）

        config = ConfigManager()  # 如果是单例且已全局初始化，可以直接用那个实例

        # 读取 low_fps 配置
        config_data = config.get_all_data()
        low_fps_enabled = config_data.get("low_fps", {}).get("enabled", False)

        # 根据配置决定 extra_delay
        extra_delay = 0.05 if low_fps_enabled else 0
        # 结束

        print("[Cayo] 运行中...")
        cycle_hashes = []
        row0_cfg =mss_dpi.ResolutionAdapter.get_mss_config(CayoLogic.ROW_COORDS[0])
        with mss.mss() as sct:
            for i in range(8):
                img = Image.frombytes("RGB", sct.grab(row0_cfg).size, sct.grab(row0_cfg).bgra, "raw", "BGRX")
                cycle_hashes.append(dhash.calculate_dhash(img))
                if i < 7: pydirectinput.press('d'); time.sleep(0.05+extra_delay)
            pydirectinput.press('d');
            time.sleep(0.05+extra_delay)
        target_idx, min_diff = -1, 100
        for idx, curr_h in enumerate(cycle_hashes):
            for tmpl_h in CayoLogic.TEMPLATE_HASHES.values():
                diff = dhash.hamming_distance(curr_h, tmpl_h)
                if diff < CayoLogic.HASH_DIFF_THRESHOLD and diff < min_diff: min_diff, target_idx = diff, idx
        if target_idx == -1: return
        moves = [(0, *CayoLogic._get_best_move(0, target_idx))]
        with mss.mss() as sct:
            for row in range(1, 8):
                img = Image.frombytes("RGB", sct.grab(mss_dpi.ResolutionAdapter.get_mss_config(CayoLogic.ROW_COORDS[row])).size,
                                      sct.grab(mss_dpi.ResolutionAdapter.get_mss_config(CayoLogic.ROW_COORDS[row])).bgra, "raw",
                                      "BGRX")
                curr_h = dhash.calculate_dhash(img)
                curr_cycle_idx, best_diff = -1, 100
                for idx, h in enumerate(cycle_hashes):
                    diff = dhash.hamming_distance(h, curr_h)
                    if diff < best_diff: best_diff, curr_cycle_idx = diff, idx
                moves.append((row, *CayoLogic._get_best_move(curr_cycle_idx, (target_idx + row) % 8)))
        for i, (row, direction, count) in enumerate(moves):
            if i > 0:
                pydirectinput.press('s')
                time.sleep(0.05+extra_delay)
            if count > 0: pydirectinput.press(direction, presses=count, interval=0.05+extra_delay)
        print("[Cayo] 完成")

        # 设置输入库的防卡死和延迟
        pydirectinput.PAUSE = 0.1

    @staticmethod
    def _get_best_move(current, target):
        if current == target: return ('none', 0)
        right = (target - current + 8) % 8
        left = (current - target + 8) % 8
        return ('d', right) if right <= left else ('a', left)




