import mss

import pydirectinput
import time


from PIL import Image
import  mss_dpi


#init(autoreset=True)

# ==========================================
# 1. 核心配置
# ==========================================

BASE_ROI_TUPLE = (600, 390, 850, 720)
KEY_DELAY = 0.02

# 【重点】Pillow 的 HSV 阈值换算
# OpenCV H(0-180) -> Pillow H(0-255) 公式: H_pil = H_cv2 * (255/180)
# S 和 V 的范围都是 0-255，无需转换

# 蓝色阈值 (原: H 100-124)
# 100 * 1.416 ≈ 142, 124 * 1.416 ≈ 175
BLUE_MIN = (113, 40, 40)
BLUE_MAX = (175, 255, 255)
BLUE_V_MIN = 46
BLUE_V_MAX = 255
# 白色阈值 (原: H 0-180, S 0-60, V 200-255)
# H 范围全包，只看 S 和 V
WHITE_S_MAX = 60
WHITE_V_MIN = 200


# ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼ 分辨率自适应模块 (去 NumPy/PyAutoGUI版) ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼


# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲ 模块结束 ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲




def count_pixels_in_image(img, mode='blue'):
    """
    使用 Pillow 统计符合颜色的像素数量。
    img: 必须是 HSV 模式的 Pillow Image 对象
    """
    # getdata() 返回一个像素列表，虽然是 Python 循环，但对于小区域(如 40x60)速度非常快
    pixels = img.getdata()
    count = 0

    if mode == 'blue':
        # 展开循环以提高一点点性能
        #l0, l1, l2 = BLUE_MIN
        #u0, u1, u2 = BLUE_MAX
        s_max = WHITE_S_MAX
        v_min = WHITE_V_MIN
        l2 = BLUE_V_MIN
        u2 = BLUE_V_MAX
        for p in pixels:
            #if l0 <= p[0] <= u0 and l1 <= p[1] <= u1 and l2 <= p[2] <= u2:
            #   count += 1
            if p[1] > s_max and l2 <= p[2] <= u2:
                count += 1
    elif mode == 'white':
        s_max = WHITE_S_MAX
        v_min = WHITE_V_MIN
        for p in pixels:
            if p[1] <= s_max and p[2] >= v_min:
                count += 1

    return count


def scan_grid_accumulator():
    """识别层 (Pillow版)"""
    cfg = mss_dpi.ResolutionAdapter.get_mss_config(BASE_ROI_TUPLE)
    # 计算每个格子的宽高
    total_w, total_h = cfg['width'], cfg['height']
    col_w = total_w // 6
    row_h = total_h // 5

    print(f"[1/3] 扫描中... {cfg}")

    # 初始化 6列 x 5行 的积分板 (替代 numpy 数组)
    score_board = [[0] * 5 for _ in range(6)]

    with mss.mss() as sct:
        st = time.time()
        # 截图持续 4 秒
        while time.time() - st < 5:
            # 1. 获取截图并转换为 PIL Image (HSV模式)
            sct_img = sct.grab(cfg)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            img_hsv = img.convert("HSV")

            # 2. 遍历网格进行裁剪和计数
            for c in range(6):
                for r in range(5):
                    # 计算裁剪区域 (left, top, right, bottom)
                    box = (c * col_w, r * row_h, (c + 1) * col_w, (r + 1) * row_h)
                    cell_img = img_hsv.crop(box)

                    # 统计蓝色像素
                    count = count_pixels_in_image(cell_img, mode='blue')
                    score_board[c][r] += count


    # 3. 计算结果 (替代 numpy.argmax)
    result = []
    for col in range(6):
        # 找到每一列中分数最高的行的索引
        # col_scores 是一个包含5个数字的列表
        col_scores = score_board[col]

        print(f'第{col+1}列的分数:',col_scores)

        max_val = max(col_scores)
        best_row_index = col_scores.index(max_val)
        result.append(best_row_index + 1)

    #print(result)

    return result


def get_start_cursor_row():
    """定位层 (Pillow版)"""
    print("[2/3] 定位光标...")
    time.sleep(0.5)
    cfg = mss_dpi.ResolutionAdapter.get_mss_config(BASE_ROI_TUPLE)

    total_w, total_h = cfg['width'], cfg['height']
    col_w = total_w // 6
    row_h = total_h // 5

    scores = [0] * 5

    with mss.mss() as sct:
        # 只截一帧
        sct_img = sct.grab(cfg)
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        img_hsv = img.convert("HSV")

        # 只扫描第一列 (col=0)
        for r in range(5):
            box = (0, r * row_h, col_w, (r + 1) * row_h)
            cell_img = img_hsv.crop(box)
            scores[r] = count_pixels_in_image(cell_img, mode='white')

    # 找最大值
    max_score = max(scores)
    best_row_index = scores.index(max_score)

    # 简单的阈值判断 (原: cw * ch * 0.01)
    pixel_threshold = (col_w * row_h) * 0.01

    if max_score < pixel_threshold:
        return 1

    print(f"-> 光标在第 {best_row_index + 1} 行")
    return int(best_row_index + 1)


# ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼ 执行层 (保持不变) ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
def execute_hack(target_rows, start_row):
    print("[3/3] 开始硬核输入 (DirectInput)...")




    curr = start_row
    for target in target_rows:
        diff = (target - curr) % 5
        if diff != 0:
            if diff <= 2:
                pydirectinput.press('s', presses=diff, interval=0.1)
            else:
                pydirectinput.press('w', presses=(5 - diff), interval=0.1)
        #time.sleep(0.1)
        pydirectinput.press('enter')
        curr = target
        time.sleep(2)




# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

def security():
    codes = scan_grid_accumulator()
    print(f"结果: {codes}")
    start_cursor = get_start_cursor_row()
    execute_hack(codes, start_cursor)