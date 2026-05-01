
import mss
from PIL import Image
import time
import customtkinter as ctk
import os
import pydirectinput
import winreg  # 用于查找Steam路径
import re      # 用于提取链接
import datetime # 用于显示时间
from mss_dpi import ResolutionAdapter
from config_manager import ConfigManager
import refresh_cha_chuan_jobtp2
# ... (原有的功能代码保持不变) ...


# --- 实现 GUI 逻辑 ---


def show_settings_ui(parent_window):
    """
    显示参数设置窗口（单页显示，互斥开关）
    直接替换原有的 show_settings_ui 函数
    """
    # ==================== 1. 初始化窗口与配置 ====================
    cfg = ConfigManager()
    data = cfg.get_all_data()

    # 创建设置窗口
    win = ctk.CTkToplevel(parent_window)
    win.title("参数设置")
    win.geometry("450x350")  # 高度增加以容纳所有内容
    win.attributes("-topmost", True)

    # 字体样式常量
    FONT_BOLD = ("Microsoft YaHei", 18, "bold")
    FONT_NORM = ("Microsoft YaHei", 18, "bold")

    # 读取当前模式 (0: 读秒, 1: Steam)
    current_mode = data.get("cha_chuan_2", {}).get("cha_chuan_2_style", 0)
    # 【新增】读取 手动 开关状态
    current_manual = data.get("cha_chuan_2", {}).get("manual", False)

    # ==================== 2. 互斥开关逻辑 (核心修改) ====================
    def set_mode(mode_val):
        """
        切换模式：保证两个开关互斥（只能选一个）
        :param mode_val: 0=读秒模式, 1=Steam模式
        """
        # 1. 更新配置文件
        cfg.update_config_item("cha_chuan_2.cha_chuan_2_style", mode_val)

        # 2. 控制开关状态（实现二选一）
        if mode_val == 0:
            switch_timer.select()  # 勾选读秒
            switch_steam.deselect()  # 取消Steam
        else:
            switch_timer.deselect()  # 取消读秒
            switch_steam.select()  # 勾选Steam

    # ==================== 3. 上半部分：读秒法设置 ====================
    # 使用 Frame 将区域稍微区分开
    frame_timer = ctk.CTkFrame(win)
    frame_timer.pack(fill="x", padx=15, pady=15)

    # --- 3.1 读秒开关 ---
    # command 绑定到 set_mode(0)
    switch_timer = ctk.CTkSwitch(
        frame_timer,
        text="启用 读秒法差传",
        font=FONT_BOLD,
        command=lambda: set_mode(0)
    )
    switch_timer.pack(anchor="w", padx=15, pady=(15, 5))

    # --- 3.2 等待时间输入 (始终显示) ---
    time_box = ctk.CTkFrame(frame_timer, fg_color="transparent")
    time_box.pack(fill="x", padx=15, pady=(0, 15))

    ctk.CTkLabel(time_box, text="等待时间:", font=FONT_NORM).pack(side="left")

    # 时间输入框
    entry_time = ctk.CTkEntry(time_box, width=60, font=FONT_NORM)
    entry_time.pack(side="left", padx=5)

    # 填入当前配置
    initial_time = data.get("cha_chuan_2", {}).get("cha_chuan_2_time", 40)
    entry_time.insert(0, str(initial_time))

    ctk.CTkLabel(time_box, text="秒 (Enter保存)", font=FONT_BOLD).pack(side="left")

    # 保存时间的逻辑
    def save_time(event=None):
        try:
            val = int(entry_time.get())
            if val < 1: val = 1

            cfg.update_config_item("cha_chuan_2.cha_chuan_2_time", val)
            win.focus()  # 移除焦点以确认
        except:
            pass

    entry_time.bind("<Return>", save_time)

    # ==================== 4. 下半部分：Steam差传设置 ====================
    frame_steam = ctk.CTkFrame(win)
    frame_steam.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    # --- 4.1 Steam开关 & 手动开关 ---
    # 创建一个透明容器让两个开关能在同一行并排显示
    steam_switch_box = ctk.CTkFrame(frame_steam, fg_color="transparent")
    steam_switch_box.pack(fill="x", padx=15, pady=(15, 5))

    # 原有的 Steam 开关 (父容器改为 steam_switch_box，布局改为 side="left")
    switch_steam = ctk.CTkSwitch(
        steam_switch_box,
        text="启用 Steam差传",
        font=FONT_BOLD,
        command=lambda: set_mode(1)
    )
    switch_steam.pack(side="left")

    # 【新增】手动开关的保存逻辑
    def set_manual():
        # switch_manual.get() 会返回 1 (开启) 或 0 (关闭)
        is_manual = bool(switch_manual.get())
        cfg.update_config_item("cha_chuan_2.manual", is_manual)

    # 【新增】手动 开关
    switch_manual = ctk.CTkSwitch(
        steam_switch_box,
        text="手动",
        font=FONT_BOLD,
        command=set_manual
    )
    switch_manual.pack(side="left", padx=(30, 0))  # padx=(30, 0) 让它和前面的开关保持一定间距

    # --- 4.2 日志框 (始终显示) ---
    # 1. 增加 height=80 (设置固定高度，数字越小越矮)
    log_box = ctk.CTkTextbox(frame_steam, height=80, font=("Consolas", 12))

    # 2. 将 fill="both", expand=True 改为 fill="x" (禁止自动拉伸，只横向填充)
    log_box.pack(fill="x", padx=15, pady=5)

    def log_msg(msg):
        ts = datetime.datetime.now().strftime("[%H:%M:%S] ")
        log_box.insert("end", ts + msg + "\n")
        log_box.see("end")

    # --- 4.3 操作按钮 ---
    btn_box = ctk.CTkFrame(frame_steam, fg_color="transparent")
    btn_box.pack(fill="x", padx=15, pady=15)

    def on_read():
        log_msg("正在扫描日志...")
        try:
            # 调用外部获取链接的函数
            link, msg = get_latest_steam_link_from_log()
            if link:
                cfg.update_config_item("target_cmd1", link)
                log_msg(f"成功: {msg}")
            else:
                log_msg(f"失败: {msg}")
        except:
            log_msg("错误: 扫描函数未定义")

    def on_clear():
        cfg.update_config_item("target_cmd1", "")
        log_msg("配置已清空")

    ctk.CTkButton(btn_box, text="读取按键", command=on_read, font=FONT_BOLD,fg_color="#2fa572").pack(side="left", expand=True, padx=5)
    ctk.CTkButton(btn_box, text="删除配置", command=on_clear, font=FONT_BOLD,fg_color="#d32f2f").pack(side="right", expand=True,
                                                                                       padx=5)

    # ==================== 5. 初始化开关状态 ====================
    # 根据读取到的配置，强制设置一次开关状态，确保UI与数据一致
    set_mode(current_mode)

    # 【新增】初始化手动开关状态
    if current_manual:
        switch_manual.select()
    else:
        switch_manual.deselect()

#-------------------------执行部分----------------------

# --- 新增的辅助函数：查找并读取 Steam 日志 ---
def get_latest_steam_link_from_log():
    """
    尝试自动获取 Steam console_log.txt 中最新的包含 rungame 和 jvp 的 ExecuteSteamURL
    返回: (tuple) (链接str, 状态消息str)
    """
    steam_path = None
    # 1. 尝试从注册表获取 Steam 安装路径
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
        winreg.CloseKey(key)
    except Exception as e:
        print(f"注册表查找 Steam 失败: {e}")
    # 2. 如果注册表失败，尝试默认路径
    if not steam_path:
        default_paths = [
            r"C:\Program Files (x86)\Steam",
            r"C:\Program Files\Steam",
            r"D:\Steam"
        ]
        for p in default_paths:
            if os.path.exists(p):
                steam_path = p
                break
    if not steam_path:
        return None, "未找到 Steam 安装目录"
    # 3. 定位日志文件
    log_file = os.path.join(steam_path, "logs", "console_log.txt")
    if not os.path.exists(log_file):
        return None, f"未找到日志文件: {log_file}"
    # 4. 读取并解析 (倒序查找)
    try:
        # 使用 errors='ignore' 防止因为特殊字符导致读取崩溃
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        # 正则表达式：匹配 ExecuteSteamURL: "链接"
        pattern = re.compile(r'ExecuteSteamURL: "([^"]+)"')
        # 从最后一行往前找
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i]
            if "ExecuteSteamURL" in line:
                match = pattern.search(line)
                if match:
                    url = match.group(1)
                    # 增加判断：链接中必须同时包含 rungame 和 jvp
                    if "rungame" in url and "steamjvp" in url:
                        return url, "成功找到链接"
        return None, "日志中未发现符合条件(包含 rungame 和 jvp)的 ExecuteSteamURL 记录"
    except Exception as e:
        return None, f"读取日志出错: {e}"

def run_steam_jvp(jvp_command):
        """
        执行 Steam JVP 命令

        Args:
            jvp_command (str): 完整的 steam:// 链接
        """
        # 简单的安全检查，确保是 steam 协议
        if not jvp_command.startswith("steam://rungame"):
            print("错误: 这不是一个有效的 steam:// 命令")
            return

        try:
            print(f"正在执行: {jvp_command[:50]}...")  # 只打印前50个字符避免刷屏
            # os.startfile 是 Windows 专用的，等同于在“运行”里输入
            os.startfile(jvp_command)
            print("命令已发送给系统。")
        except Exception as e:
            print(f"执行失败: {e}")


def get_cmd2():
    """
    读取配置文件中的 target_cmd1 内容
    """
    # 1. 初始化管理器 (这会自动从 Documents 目录加载 json 文件)
    config = ConfigManager()

    # 2. 获取所有配置数据
    all_data = config.get_all_data()

    # 3. 提取 target_cmd1，使用 .get 防止报错（如果没找到返回空字符串）
    cmd1 = all_data.get("target_cmd2", "")

    return cmd1

def get_style2():
    """
    读取配置文件中的 target_cmd1 内容
    """
    cfg = ConfigManager()
    data = cfg.get_all_data()

    # 3. 提取 target_cmd1，使用 .get 防止报错（如果没找到返回空字符串）
    style = data.get("cha_chuan_2", {}).get("cha_chuan_2_style", 0)

    return style


def get_time2():
    """
    读取配置文件中的 target_cmd1 内容
    """
    cfg = ConfigManager()
    data = cfg.get_all_data()

    # 3. 提取 target_cmd1，使用 .get 防止报错（如果没找到返回空字符串）
    time = data.get("cha_chuan_2", {}).get("cha_chuan_2_time", 40)

    return time

def manual():
    """
    读取配置文件中的 target_cmd1 内容
    """
    cfg = ConfigManager()
    data = cfg.get_all_data()

    # 3. 提取 target_cmd1，使用 .get 防止报错（如果没找到返回空字符串）
    manual = data.get("cha_chuan_2", {}).get("manual", False)


    return manual



# 坐标定义

m_ROI = (720, 720, 1120, 140)

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
            p1_monitor = ResolutionAdapter.get_mss_config(m_ROI)
            screen1 = capture_screen(sct, p1_monitor)
            #debug_save_image(screen1)
            if screen1 is None:
                return False  # 明确返回 False 而不是 None

            dist = white_pixel_ratio_hsv(screen1)

            print(f"白色像素占比{dist}")

            if dist > 12.5:
                pydirectinput.press("esc")
            else:
                pydirectinput.press("enter")

            # 按完后等待几秒，防止在一个黑屏里疯狂连按
            time.sleep(0.1)

            # 每次循环稍微暂停一下，降低CPU占用
            time.sleep(0.1)


    finally:
        if close_sct:
            sct.close()  # 确保资源释放





def run(sct=None):
    start_time = time.time()

    if get_style2() == 1:

        if not manual():
            pydirectinput.press("space")
            time.sleep(0.1)
            pydirectinput.press("enter")


        run_steam_jvp(get_cmd2())
        time.sleep(1)

        if not manual():
            while True:
                if time.time() - start_time > 18:
                    print("超过时间，跳出循环")
                    break
                auto_key_on_black_screen(sct)
                time.sleep(0.2)


    elif get_style2() == 0:
        pydirectinput.press("space")
        time.sleep(0.1)
        pydirectinput.press("enter")
        time.sleep(3)

        pydirectinput.keyDown("alt")
        pydirectinput.press("f4")
        pydirectinput.keyUp("alt")

        time.sleep(get_time2())
        pydirectinput.press("esc")