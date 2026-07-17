
import  win32gui
import  win32api

from config_manager import ConfigManager

import mss
import pydirectinput
import time
import dhash
import mss_dpi
from PIL import Image, ImageFilter, ImageChops,ImageOps

import ctypes  # 新增
import  io
import ka_cha_chuan


m_ROI = (0, 580, 700, 200)
find_job_ROI = (1940, 1300, 620, 50)
job_ROI = (400,130,300,80)

#十六进制哈希值: 0x78f6fa39f35ffca9

# ================= 分辨率适配器 (修复版 - MSS适配 - 左侧基准) =================

class ResolutionAdapter:
    BASE_W = 2560
    BASE_H = 1440
    # 注意：如果改为左侧基准，BASE_CENTER 定义其实不再需要，但保留也无妨
    BASE_CENTER_X = BASE_W / 2
    BASE_CENTER_Y = BASE_H / 2

    @staticmethod
    def get_screen_size():
        x = win32api.GetSystemMetrics(0)
        y = win32api.GetSystemMetrics(1)
        return x, y

    @staticmethod
    def get_game_window_rect():
        hwnd = win32gui.FindWindow(None, "Grand Theft Auto V")
        if hwnd:
            left, top, right, bottom = win32gui.GetClientRect(hwnd)
            x, y = win32gui.ClientToScreen(hwnd, (left, top))
            w, h = right - left, bottom - top
            sw, sh = ResolutionAdapter.get_screen_size()
            if w == 0 or h == 0: return (0, 0, sw, sh)
            return (x, y, w, h)
        sw, sh = ResolutionAdapter.get_screen_size()
        return (0, 0, sw, sh)

    @classmethod
    def get_mss_config(cls, base_config_tuple):
        """
        直接返回 mss 需要的字典格式
        已修改：以左上角为基准进行缩放 (Left/Top Aligned)
        """
        win_x, win_y, win_w, win_h = cls.get_game_window_rect()

        # 依然通常以高度为基准计算缩放比例，保持 UI 元素的宽高比
        scale_factor = win_h / cls.BASE_H

        # base_config_tuple 格式应为 (原分辨率下x, 原分辨率下y, 宽度, 高度)
        orig_x, orig_y, orig_w, orig_h = base_config_tuple

        # 计算新的宽高
        new_w = orig_w * scale_factor
        new_h = orig_h * scale_factor

        # 计算新的坐标 (以窗口左上角 win_x, win_y 为基准)
        # 逻辑：当前窗口左边距 + (原始X坐标 * 缩放比例)
        new_x = win_x + (orig_x * scale_factor)
        new_y = win_y + (orig_y * scale_factor)

        return {
            'top': int(new_y),
            'left': int(new_x),
            'width': int(new_w),
            'height': int(new_h)
        }


#
def analyze_text_info_pil(image, debug=False):
    import io

    if isinstance(image, str):
        img = Image.open(image).convert('RGB')
    elif isinstance(image, bytes):
        img = Image.open(io.BytesIO(image)).convert('RGB')
    else:
        img = image.convert('RGB')

    w, h = img.size
    gray = img.convert('L')

    # 分辨率修正：将当前分辨率下的文字宽度归一化到1440p基准
    _, _, _, game_h = ResolutionAdapter.get_game_window_rect()
    if game_h > 0:
        scale_correction = ResolutionAdapter.BASE_H / game_h
    else:
        scale_correction = 1.0

    if debug:
        ts = int(__import__('time').time())
        img.save(f"debug_0_original_{ts}.png")

    # 1. RGB三通道白像素 (R,G,B > 200)
    r, g, b = img.split()
    r_mask = r.point(lambda p: 255 if p > 200 else 0, mode='1')
    g_mask = g.point(lambda p: 255 if p > 200 else 0, mode='1')
    b_mask = b.point(lambda p: 255 if p > 200 else 0, mode='1')
    white_mask = ImageChops.logical_and(r_mask, g_mask)
    white_mask = ImageChops.logical_and(white_mask, b_mask)
    white_px = white_mask.convert('L').histogram()[255]

    if debug:
        white_mask.convert('L').save(f"debug_1_white_mask_{ts}.png")
        print(f"[DEBUG] white_mask pixels: {white_px}")

    # 2. 错位交叉相减（边缘 > 45）
    shifted_left = ImageChops.offset(gray, -1, 0)
    shifted_up = ImageChops.offset(gray, 0, -1)
    diff_x = ImageChops.subtract(gray, shifted_left)
    diff_y = ImageChops.subtract(gray, shifted_up)
    edge_x = diff_x.point(lambda p: 255 if p > 45 else 0, mode='1')
    edge_y = diff_y.point(lambda p: 255 if p > 45 else 0, mode='1')
    dark_adjacent_mask = ImageChops.logical_or(edge_x, edge_y)
    edge_px = dark_adjacent_mask.convert('L').histogram()[255]

    if debug:
        dark_adjacent_mask.convert('L').save(f"debug_2_edge_mask_{ts}.png")
        print(f"[DEBUG] edge_mask pixels: {edge_px}")

    # 3. 取交集
    text_edges = ImageChops.logical_and(white_mask, dark_adjacent_mask)
    raw_px = text_edges.convert('L').histogram()[255]

    if debug:
        text_edges.convert('L').save(f"debug_3_text_edges_raw_{ts}.png")
        print(f"[DEBUG] text_edges (raw) pixels: {raw_px}")

    # 4. 形态学去噪 MaxFilter(3) 消除孤立1px噪点
    text_l = text_edges.convert('L')
    text_l = text_l.filter(ImageFilter.MaxFilter(3))
    text_edges = text_l.point(lambda p: 255 if p > 128 else 0, mode='1')
    after_px = text_edges.convert('L').histogram()[255]

    if debug:
        text_edges.convert('L').save(f"debug_4_text_edges_morph_{ts}.png")
        print(f"[DEBUG] text_edges (after morph) pixels: {after_px}")

    bbox = text_edges.getbbox()
    if not bbox:
        if debug:
            print(f"[DEBUG] RESULT: no bbox → 0")
        return {"has_text": False, "text_width": 0, "pixel_count": 0}

    left, upper, right, lower = bbox
    text_width = right - left
    text_height = lower - upper

    # 5. 宽度上限 > 0.95 图宽 → 噪声
    if text_width > w * 0.95:
        if debug:
            print(f"[DEBUG] RESULT: width {text_width} > {w * 0.95} → 0")
        return {"has_text": False, "text_width": 0, "pixel_count": 0}

    pixel_count = after_px

    # 6. 密度校验 < 0.01 → 噪声
    bbox_area = text_width * text_height
    if bbox_area > 0:
        density = pixel_count / bbox_area
        if debug:
            print(f"[DEBUG] bbox=({left},{upper},{right},{lower}) w={text_width} h={text_height} area={bbox_area} px={pixel_count} density={density:.4f}")
        if density < 0.01:
            if debug:
                print(f"[DEBUG] RESULT: density {density:.4f} < 0.01 → 0")
            return {"has_text": False, "text_width": 0, "pixel_count": 0}
    elif debug:
        print(f"[DEBUG] bbox=({left},{upper},{right},{lower}) w={text_width} h={text_height} area=0")

    # 7. 水平投影：用列密度截取真实文字区域，过滤面板边框/图标
    crop = text_edges.crop(bbox)
    crop_w, crop_h = crop.size
    col_white = [0] * crop_w
    crop_data = list(crop.getdata())
    for y in range(crop_h):
        row_start = y * crop_w
        for x in range(crop_w):
            if crop_data[row_start + x] == 255:
                col_white[x] += 1

    if col_white and max(col_white) > 0:
        max_col = max(col_white)
        threshold = max_col * 0.15
        first = 0
        last = crop_w - 1
        for i in range(crop_w):
            if col_white[i] >= threshold:
                first = i
                break
        for i in range(crop_w - 1, -1, -1):
            if col_white[i] >= threshold:
                last = i
                break
        refined_width = last - first + 1
        if debug:
            print(f"[DEBUG] projection: max_col={max_col} threshold={threshold:.1f} first={first} last={last} refined_width={refined_width}")


        text_width = int(refined_width * scale_correction)

    if debug:
        print(f"[DEBUG] RESULT: text_width={text_width}")

    return {
        "text_width": text_width,
    }

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


def debug_save_image(img, name="debug"):
    """保存截图到本地以供检查"""
    try:
        ts = int(time.time())
        filename = f"{name}_{ts}.png"
        img.save(filename)
        print(f"[-] 已保存调试图片: {filename}")
    except Exception as e:
        print(e)

def judge(roi,min,max,sct=None):
    # 支持外部传入 mss 实例（线程安全使用）
    close_sct = False
    if sct is None:
        sct = mss.mss()
        close_sct = True

    try:
        p1_monitor = ResolutionAdapter.get_mss_config(roi)
        screen1 = capture_screen(sct, p1_monitor)
        #debug_save_image(screen1)
        if screen1 is None:
            return False  # 明确返回 False 而不是 None

        info = analyze_text_info_pil(screen1,debug=False)
        length = info['text_width']

        print(f"文字总跨度: {info['text_width']} 像素")
        #print(f"占比: {info['ratio']} ")

        if min < length < max:
            print(f"文字总跨度: {length} 像素")
            return True  # 距离在允许范围内，匹配成功
        else:
            return False  # 距离过大，匹配失败
    finally:
        if close_sct:
            sct.close()  # 确保资源释放





def phone_danei():
    """检测手机弹窗，支持传入外部 mss 实例"""
    cfg = ConfigManager()
    data = cfg.get_all_data()
    if data.get("ka_cha_chuan", {}).get("danei", False):
        return True
    return  False



def quick_press(button):
    pydirectinput.keyDown(button)
    time.sleep(0.05)
    pydirectinput.keyUp(button)
    time.sleep(0.05)




def run_phone():

    # 设置输入库的防卡死和延迟
    pydirectinput.PAUSE = 0.05
    pydirectinput.FAILSAFE = False

    # 低帧率模式
    # 获取配置管理器实例（确保你已经导入并正确初始化了 ConfigManager）

    config = ConfigManager()  # 如果是单例且已全局初始化，可以直接用那个实例

    # 读取 low_fps 配置
    config_data = config.get_all_data()
    low_fps_enabled = config_data.get("low_fps", {}).get("enabled", False)

    # 根据配置决定 extra_delay
    extra_delay = 0.05 if low_fps_enabled else 0

    """主运行函数，支持复用 mss 实例"""
    quick_press("up")
    time.sleep(0.5)  # 可根据实际情况调整

    # 检测手机弹窗
    is_phone = phone_danei()

    if is_phone:

        quick_press("right")
        time.sleep(extra_delay)
        quick_press("right")
    else:
        quick_press("left")
        time.sleep(extra_delay)

    quick_press("enter")
    time.sleep(extra_delay)
    quick_press("up")
    time.sleep(extra_delay)
    quick_press("enter")
    time.sleep(extra_delay)
    quick_press("enter")
    time.sleep(extra_delay)
    quick_press("enter")
    time.sleep(1)

def cancel_phone():

    # 设置输入库的防卡死和延迟
    pydirectinput.PAUSE = 0.05
    pydirectinput.FAILSAFE = False

    # 低帧率模式
    # 获取配置管理器实例（确保你已经导入并正确初始化了 ConfigManager）

    config = ConfigManager()  # 如果是单例且已全局初始化，可以直接用那个实例

    # 读取 low_fps 配置
    config_data = config.get_all_data()
    low_fps_enabled = config_data.get("low_fps", {}).get("enabled", False)

    # 根据配置决定 extra_delay
    extra_delay = 0.05 if low_fps_enabled else 0

    """主运行函数，支持复用 mss 实例"""
    quick_press("up")
    time.sleep(0.5)  # 可根据实际情况调整

    # 检测手机弹窗
    is_phone = phone_danei()

    if is_phone:

        quick_press("right")
        time.sleep(extra_delay)
        quick_press("right")
    else:
        quick_press("left")
        time.sleep(extra_delay)

    quick_press("enter")
    time.sleep(0.05+extra_delay)

    for i in range(3):
        pydirectinput.mouseDown(button="right")
        time.sleep(0.05+extra_delay)
        pydirectinput.mouseUp(button="right")
        time.sleep(0.05 + extra_delay)


    time.sleep(1)

def force_scroll(n=1):
    ctypes.windll.user32.mouse_event(0x0800, 0, 0, n * 120, 0)

def get_key(key):
    cfg = ConfigManager()
    data = cfg.get_all_data()
    orign_key = data.get(key, {}).get("key", False)
    key = orign_key.lower()
    return key




    is_ceo = judge(m_ROI,500,600,sct)

    if is_ceo:
        quick_press("enter")
        quick_press("up")
        quick_press("enter")
        time.sleep(0.3)
        quick_press(m_menu)
        print("是ceo")
    else:
        print("不是ceo")


    time.sleep(0.3)
    for _ in range(10):
        force_scroll(1)
        time.sleep(0.05+extra_delay)




    quick_press("enter")
    quick_press("enter")
    quick_press("enter")


def auto_key_on_black_screen(sct=None):

    # 支持外部传入 mss 实例（线程安全使用）
    close_sct = False
    if sct is None:
        sct = mss.mss()
        close_sct = True
        #print("脚本已启动，正在监控屏幕黑色占比...")

    try:

        # 【修改点 2】：在这里定义基准并获取动态区域
        # 这里的 (0, 0, 2560, 1440) 是为了告诉适配器：我想截取“整个游戏画面”
        # 适配器会自动帮你换算成当前游戏窗口的实际坐标和大小
        base_full_screen = (0, 0, 2560, 1440)
        monitor = ResolutionAdapter.get_mss_config(base_full_screen)
        # 1. 截图
        sct_img = sct.grab(monitor)
        # mss截的数据是BGRA格式，转为PIL的RGB格式
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

        # 2. 极简化处理 (缩小到100x100 + 转灰度)
        # 缩小图片能极大提高检测速度，且不影响占比判断
        small_img = img.resize((100, 100)).convert('L')

        # 3. 统计黑色像素
        # 获取所有像素点数据 (0是纯黑，255是纯白)
        pixels = list(small_img.getdata())
        # 设定阈值：亮度小于 20 的都算作“黑色” (容错处理，避免压缩噪点影响)
        black_count = sum(1 for p in pixels if p < 20)

        # 计算比例
        ratio = black_count / len(pixels)
        # print(ratio)

        # 4. 触发条件
        if ratio > 0.80:
            time.sleep(0.1)


            pydirectinput.press("enter")
            return True

            # 按完后等待几秒，防止在一个黑屏里疯狂连按
            time.sleep(0.1)

        return False



    finally:
        if close_sct:
            sct.close()  # 确保资源释放


def run_ka_ceo(sct=None):
    # 设置输入库的防卡死和延迟
    pydirectinput.PAUSE = 0.05
    pydirectinput.FAILSAFE = False

    run_phone()

    start_time = time.time()
    while True:
        if time.time() - start_time > 59:
            cancel_phone()
            print("超过时间，跳出循环")
            break

        pydirectinput.moveRel(0, 2000,relative=True)

        is_job = judge(find_job_ROI,100,600, sct)
        in_job = judge(job_ROI, 100,600,sct)



        if is_job:
            print("匹配到差事，取消差事，卡ceo")
            time.sleep(0.1)
            cancel_phone()
            time.sleep(0.1)
            ka_cha_chuan.run_m()

            if judge(job_ROI, 100,600,sct):
                print("匹配进入差事，esc退出")
                time.sleep(0.5)

                for i in range(30):
                    quick_press("esc")
                    time.sleep(0.1)
                    if auto_key_on_black_screen():
                        break

            break

        elif in_job and not is_job:
            print("匹配进入差事，esc退出")
            time.sleep(0.5)

            for i in range(30):
                quick_press("esc")
                time.sleep(0.1)
                if auto_key_on_black_screen():
                    break
            break



        time.sleep(0.5)


    pydirectinput.PAUSE = 0.1
