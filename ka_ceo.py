
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



m_ROI = (0, 600, 600, 100)
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




def analyze_text_info_pil(image):
    """
    终极纯 PIL 实现：
    1. 相对色差：无惧游戏亮度拉满/白天泛白
    2. 错位交叉：精准定位“白贴黑”的文字阴影边缘
    3. 边界计算：识别文字跨度与像素量，预估字数
    """
    import io

    # 1. 载入并转为灰度图
    if isinstance(image, str):
        gray = Image.open(image).convert('L')
    elif isinstance(image, bytes):
        gray = Image.open(io.BytesIO(image)).convert('L')
    else:
        gray = image.convert('L')

    # 2. 提取高亮区域 (阈值适度放宽到 200，以防高亮度下文字本身变灰)
    # 这张图里的白色代表：可能是文字的像素
    white_mask = gray.point(lambda p: 255 if p > 200 else 0, mode='1')

    # 3. 生成错位图（获取每个像素的【右侧】和【下方】像素）
    # 向左平移1像素（把右边的画面拉过来）
    shifted_left = ImageChops.offset(gray, -1, 0)
    # 向上平移1像素（把下边的画面拉过来）
    shifted_up = ImageChops.offset(gray, 0, -1)

    # 4. 错位交叉相减：计算相对反差！(底层C语言瞬间完成)
    # ImageChops.subtract 会计算 原图 - 错位图 (如果结果是负数自动变0)
    # diff_x 代表：当前像素 比 它右边的像素 亮多少？
    diff_x = ImageChops.subtract(gray, shifted_left)
    # diff_y 代表：当前像素 比 它下方的像素 亮多少？
    diff_y = ImageChops.subtract(gray, shifted_up)

    # 5. 寻找“相对的黑白交界”
    # 只要比旁边的像素亮超过 50 个色阶，就认为是“白贴黑”
    # 这样就算游戏亮度拉满，阴影被洗白到了 150，文字是 255，差值 105 (>50) 依然能被完美抓出！
    edge_x = diff_x.point(lambda p: 255 if p > 50 else 0, mode='1')
    edge_y = diff_y.point(lambda p: 255 if p > 50 else 0, mode='1')

    # 合并 X 和 Y 方向的边缘
    dark_adjacent_mask = ImageChops.logical_or(edge_x, edge_y)

    # 6. 经典取交集：当前像素既是“绝对高亮”，且旁边“存在相对较暗的阴影”
    text_edges = ImageChops.logical_and(white_mask, dark_adjacent_mask)

    # --- 下面是统计文字长短的逻辑 ---

    # 获取包含这些有效边缘像素的最小矩形框
    bbox = text_edges.getbbox()

    if not bbox:
        return {
            "has_text": False,
            "text_width": 0,
            "pixel_count": 0
        }

    left, upper, right, lower = bbox
    text_width = right - left  # 文字横向总跨度（判定字数的最强指标）

    # 统计有效边缘的像素量
    colors = text_edges.convert('L').getcolors()
    pixel_count = 0
    if colors:
        for count, color in colors:
            if color == 255:
                pixel_count = count
                break

    return {
        #"has_text": pixel_count > 10,  # 超过 10 个边缘像素才算有字，过滤极限微小噪点
        "text_width": text_width,
        #"pixel_count": pixel_count
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

        info = analyze_text_info_pil(screen1)
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

def run_m(sct=None):

    # 设置输入库的防卡死和延迟
    pydirectinput.PAUSE = 0.02
    pydirectinput.FAILSAFE = False

    m_menu = get_key("m_menu")
    weapon_menu = get_key("weapon_menu")
    no_weapon = get_key("no_weapon")
    shotgun_weapon = get_key("shotgun_weapon")
    rpg_weapon = get_key("rpg_weapon")
    c4_weapon = get_key("c4_weapon")
    pistol_weapon = get_key("pistol_weapon")
    sniper_weapon = get_key("sniper_weapon")


    # 低帧率模式
    # 获取配置管理器实例（确保你已经导入并正确初始化了 ConfigManager）

    config = ConfigManager()  # 如果是单例且已全局初始化，可以直接用那个实例

    # 读取 low_fps 配置
    config_data = config.get_all_data()
    low_fps_enabled = config_data.get("low_fps", {}).get("enabled", False)

    # 根据配置决定 extra_delay
    extra_delay = 0.05 if low_fps_enabled else 0



    """主运行函数，支持复用 mss 实例"""
    quick_press(m_menu)
    time.sleep(0.3)  # 可根据实际情况调整


    is_ceo = judge(m_ROI,350,400,sct)

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
    pydirectinput.PAUSE = 0.02
    pydirectinput.FAILSAFE = False

    run_phone()

    start_time = time.time()
    while True:
        if time.time() - start_time > 45:
            cancel_phone()
            print("超过时间，跳出循环")
            break

        pydirectinput.moveRel(0, 1000,relative=True)

        is_job = judge(find_job_ROI,100,500, sct)
        in_job = judge(job_ROI, 100,500,sct)



        if is_job:
            print("匹配到差事，取消差事，卡ceo")
            time.sleep(0.1)
            cancel_phone()
            time.sleep(0.1)
            run_m()

            if judge(job_ROI, 100,500,sct):
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
