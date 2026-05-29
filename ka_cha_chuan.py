
import  win32gui
import  win32api

from config_manager import ConfigManager

import mss
import pydirectinput
import time

from PIL import Image, ImageFilter, ImageChops

import ctypes  # 新增
import  io

import ka_ceo

def show_settings_ui(parent_window):

    import customtkinter as ctk



    # 创建置顶设置窗口
    settings_window = ctk.CTkToplevel(parent_window)
    settings_window.title("任务卡差传设置")
    settings_window.geometry("250x100")
    settings_window.resizable(False, False)
    settings_window.transient(parent_window)  # 跟随父窗口
    settings_window.grab_set()  # 模态窗口

    # 获取配置管理器（依赖父窗口传入 config）
    config = parent_window.config

    # 三个联系人配置
    contact_ids = ["ka_cha_chuan"]

    #达内
    def toggle_danei_switch(contact_id, switch_widget):
        """danei字段开关切换回调"""
        is_on = bool(switch_widget.get())
        # 更新danei字段
        with config.lock:  # 确保线程安全
            if contact_id in config.data:
                config.data[contact_id]['danei'] = is_on
        config.save_config()  # 保存配置


    # 创建三行数据
    for row_idx, contact_id in enumerate(contact_ids, start=1):
        data = config.get_function_data(contact_id)
        if not data:
            continue

        # 第二列：名字（只读，灰色背景标签）
        lbl_name = ctk.CTkLabel(
            settings_window,
            text="达内尔有限公司",
            font=("Microsoft YaHei UI", 18, "bold"),
            width=0,
            height=40,

            anchor="w"
        )
        lbl_name.grid(row=row_idx, column=1, padx=10, pady=0, sticky="ew")

        # 第四列：开关（启用/禁用）
        switch = ctk.CTkSwitch(
            settings_window,
            text="",
            width=10,
            height=30,
            progress_color="#4CC768",
            fg_color="#FF474C",
            button_color="white",
            onvalue=True,
            offvalue=False
        )
        if data.get("danei", True):
            switch.select()
        else:
            switch.deselect()

        switch.configure(command=lambda  cid=contact_id, sw=switch: toggle_danei_switch(cid, sw))
        # 左边的 padding 设为 0，右边保持 10
        switch.grid(row=row_idx, column=2, padx=(20, 20), pady=8, sticky="w")


#--------------------------执行层----------------------------

# 坐标定义

m_ROI = (0, 600, 600, 100)


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


def white_pixel_ratio_hsv(image):
    """
    基于 HSV 颜色空间统计白色像素比例（PIL 纯 Python 实现）

    Args:
        image: PIL.Image 对象、文件路径(str)
        h_min: 最小色调(0-180)，默认0
        h_max: 最大色调(0-180)，默认180
        s_max: 最大饱和度(0-255)，低于此值视为白色/灰色，默认30
        v_min: 最小明度(0-255)，高于此值视为明亮，默认200

    Returns:
        float: 白色比例百分比

    原理: 白色在HSV中表现为低饱和度(S低) + 高明度(V高)，H(色相)在特定范围内
    """
    from PIL import Image
    import io

    h_min = 0
    h_max = 180
    s_min = 0
    s_max = 30
    v_min = 220
    v_max = 255

    # 加载图片并转为 HSV
    if isinstance(image, str):
        img = Image.open(image).convert('HSV')
    elif isinstance(image, Image.Image):
        img = image.convert('HSV')
    else:
        img = Image.open(io.BytesIO(image) if isinstance(image, bytes) else image).convert('HSV')

    width, height = img.size
    total_pixels = width * height

    if total_pixels == 0:
        return 0.0

    # 获取HSV像素数据并统计
    pixels = img.getdata()
    white_count = 0

    for h, s, v in pixels:
        # 白色条件：色调在一定范围内 + 饱和度够低 + 明度够高
        if h_min <= h <= h_max and s_min <= s <= s_max and v_min <= v <= v_max:
            white_count += 1

    ratio = white_count / total_pixels
    return ratio * 100


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





def m_ceo(sct=None):

    # 支持外部传入 mss 实例（线程安全使用）
    close_sct = False
    if sct is None:
        sct = mss.mss()
        close_sct = True

    try:
        p1_monitor = ResolutionAdapter.get_mss_config(m_ROI)
        screen1 = capture_screen(sct, p1_monitor)
        #debug_save_image(screen1)
        if screen1 is None:
            return False  # 明确返回 False 而不是 None

        dist = white_pixel_ratio_hsv(screen1)

        print(dist)

        if dist >3.5:
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

def force_scroll(n=1):
    ctypes.windll.user32.mouse_event(0x0800, 0, 0, n * 120, 0)

def run_m(sct=None):

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
    quick_press("m")
    time.sleep(0.3)  # 可根据实际情况调整


    is_ceo = m_ceo(sct)

    if is_ceo:
        quick_press("enter")
        quick_press("up")
        quick_press("enter")
        time.sleep(0.3)
        quick_press("m")
        print("是ceo")


    time.sleep(0.3)
    for _ in range(10):
        force_scroll(1)
        time.sleep(0.05+extra_delay)




    quick_press("enter")
    quick_press("enter")
    quick_press("enter")

def run_ka_cha_chuan():
    # 设置输入库的防卡死和延迟
    pydirectinput.PAUSE = 0.02
    pydirectinput.FAILSAFE = False

    run_phone()
    run_m()

    pydirectinput.PAUSE = 0.1
