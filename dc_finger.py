import mss
import pydirectinput
import time

from PIL import Image
import dhash

import mss_dpi





# ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼ 【核心算法】 ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼






# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

# ==============================================================================
#                               数据硬编码区域
# ==============================================================================

# ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼ 请将 get_hashes.py 生成的内容粘贴到这里 ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼

# 举例 (请务必用你实际生成的数据覆盖):
# --- 阶段一指纹数据 ---
TEMPLATES_P1 = [
    {'id': 1, 'hash': 8203826673565879409},
    {'id': 2, 'hash': 8199028008949435633},
    {'id': 3, 'hash': 8784773329424013553},
    {'id': 4, 'hash': 8273624393118962929},
]

# --- 阶段二指纹数据 ---
TEMPLATES_P2 = {
    1: [ 8224198782617388555, 3816055860743674033, 9235002466843754632, 15179596625028620709 ],
    2: [ 7270350378282301078, 6109215025522724078, 10540908583779214546, 8099841349438065864 ],
    3: [ 14568098766579205320, 8969607404950703180, 9631064654364584658, 1115453011776684782 ],
    4: [ 11013155592004865585, 2929754477203464884, 1745765480297973873, 15741992528882592354 ],
}


# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲




# 坐标定义
PHASE1_ROI = (1247, 206, 540, 700)
PHASE2_ROIS = [
    (636, 363, 150, 150), (828, 363, 150, 150),
    (636, 554, 150, 150), (828, 554, 150, 150),
    (636, 747, 150, 150), (828, 747, 150, 150),
    (636, 938, 150, 150), (828, 938, 150, 150),
]


def capture_screen(sct, monitor):
    """
    使用传入的 sct 实例截图
    """
    try:
        sct_img = sct.grab(monitor)
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        return img
    except Exception as e:
#        print(f"Screenshot Error: {e}")
        return None


def run_task():
#    print("\n---------- [F10] 任务开始 (MSS + Win32API版) ----------")

#    if not TEMPLATES_P1 or not TEMPLATES_P2:
#        print("❌ 错误：未填入哈希数据，请先运行 get_hashes.py 并填充代码！")
#        return

    #低帧率模式
    # 获取配置管理器实例（确保你已经导入并正确初始化了 ConfigManager）
    from config_manager import ConfigManager  # 1. 导入 ConfigManager

    config = ConfigManager()  # 如果是单例且已全局初始化，可以直接用那个实例

    # 读取 low_fps 配置
    config_data = config.get_all_data()
    low_fps_enabled = config_data.get("low_fps", {}).get("enabled", False)

    # 根据配置决定 extra_delay
    extra_delay = 0.05 if low_fps_enabled else 0
    #结束


    # ★关键修改：在任务线程内部初始化 mss，避免跨线程报错
    with mss.mss() as sct:
        # ================= 阶段一 =================
        p1_monitor = mss_dpi.ResolutionAdapter.get_mss_config(PHASE1_ROI)
        screen1 = capture_screen(sct, p1_monitor) # 传入 sct

        if screen1 is None: return

        matched_id = None
        min_dist = 100
        screen1_hash = dhash.calculate_dhash(screen1)

        for t in TEMPLATES_P1:
            dist = dhash.hamming_distance(screen1_hash, t['hash'])
            #print(dist)
            if dist < min_dist:
                min_dist = dist
                matched_id = t['id']

#        if matched_id is None:
#            print(f"❌ 识别失败 (Diff: {min_dist})")
#            return
#        print(f"★ 锁定类型: [{matched_id}] (Diff: {min_dist})")

        # ================= 阶段二 =================
        target_hashes = TEMPLATES_P2.get(matched_id, [])
        grid_results = []

#        print(">>> 分析中...")
        for idx, base_region in enumerate(PHASE2_ROIS):
            grid_monitor = mss_dpi.ResolutionAdapter.get_mss_config(base_region)
            screen = capture_screen(sct, grid_monitor) # 传入 sct
            #screen.save(f"debug_screenshot_{idx}.png")
            min_grid_dist = 999
            if screen:
                h = dhash.calculate_dhash(screen)
                for th in target_hashes:
                    d = dhash.hamming_distance(h, th)
                    if d < min_grid_dist: min_grid_dist = d

            grid_results.append({'idx': idx, 'dist': min_grid_dist})

    # ================= 阶段三 (模拟按键) =================
    # 按键不需要 mss，放在 with 块外面也可以，或者里面也行

    # 设置输入库的防卡死和延迟
    pydirectinput.PAUSE = 0.02
    pydirectinput.FAILSAFE = False


    grid_results.sort(key=lambda x: x['dist'])
    top_4 = sorted([x['idx'] for x in grid_results[:4]])
    last_idx = max(top_4) if top_4 else 0
    for i in range(last_idx + 1):
        if i in top_4:
            pydirectinput.press('enter')
            time.sleep(extra_delay)
        if i < last_idx:
            pydirectinput.press('right')
            time.sleep(extra_delay)
    time.sleep(extra_delay)
    time.sleep(0.02)
    pydirectinput.press('tab')

    pydirectinput.PAUSE = 0.1 #回到默认，防止影响其他函数
#    print("★ 完成")


#if __name__ == "__main__":
#    print(">>> 系统就绪！按 【F10】 开始...")

 #   def on_release(key):
 #       if key == keyboard.Key.f10:
 #           run_task()

 #   with keyboard.Listener(on_release=on_release) as listener:
 #       listener.join()