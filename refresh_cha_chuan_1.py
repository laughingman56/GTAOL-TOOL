import win32gui
import win32con
import win32com.client
import os
import time
import pydirectinput  # 必须引入这个库
import  mss
from mss_dpi import ResolutionAdapter
from config_manager import ConfigManager
from PIL import Image
import winreg  # 用于查找Steam路径
import re      # 用于提取链接

# ================= 配置区域 =================



# 2. 窗口标题关键词
TARGET_KEYWORDS = ["差传"]

# 3. 点击坐标设置 (相对于窗口左上角的偏移量)
# 假设你想点击窗口
CLICK_OFFSET_X = 20
CLICK_OFFSET_Y = 20
CLICK_OFFSET_X1 = 30
CLICK_OFFSET_Y1 = 250

# ===========================================

def get_cmd1_id(config=None):
    """
    读取配置文件中的 target_cmd1 内容
    """
    """
    读取配置文件中的 target_cmd1 内容
    """
    if config is None:
        config = ConfigManager()
    # 2. 获取所有配置数据
    all_data = config.get_all_data()
    # 3. 提取 target_cmd1，使用 .get 防止报错（如果没找到返回空字符串）
    cmd1 = all_data.get("target_cmd1", "")

    # 方法2：正则表达式匹配数字串
    match = re.search(r'steam://rungame/\d+/(\d+)/', cmd1)
    if match:
        BOT_ID = match.group(1)
        print(f"grouid: {BOT_ID}")  # 输出:
        return BOT_ID


def launch_steam_chat(id):
    """使用 Steam 协议启动聊天"""
    url = f"steam://friends/message/{id}"
    print(f"[1/3] 正在启动 Steam 协议: {url}")
    # os.startfile 是 Windows 下打开 URL 最稳妥的方式
    os.startfile(url)



def find_target_window(keywords):
    """查找窗口句柄"""
    target_hwnd = None

    def callback(hwnd, _):
        nonlocal target_hwnd
        if target_hwnd: return
        if win32gui.IsWindowVisible(hwnd):
            text = win32gui.GetWindowText(hwnd)
            for key in keywords:
                if key in text:
                    # 简单校验类名防止误判
                    cls = win32gui.GetClassName(hwnd)
                    if "SDL_app" in cls or "Chrome_WidgetWin" in cls:
                        target_hwnd = hwnd

    win32gui.EnumWindows(callback, None)
    return target_hwnd


def bring_to_front(hwnd):
    """强制置顶窗口"""
    print(f"[3/4] 激活窗口...")
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

        # 尝试绕过 Windows 限制
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.SendKeys('%')
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception as e:
        print(f"置顶警告: {e}")
        return False


def right_click_on_window(hwnd, offset_x, offset_y, click):
    """在窗口指定相对位置点击右键 (使用 pydirectinput)"""
    print(f"[4/4] 准备执行右键点击...")

    # 1. 获取窗口在屏幕上的绝对位置 (Left, Top, Right, Bottom)
    rect = win32gui.GetWindowRect(hwnd)
    win_x = rect[0]
    win_y = rect[1]

    # 2. 计算实际点击坐标
    target_x = win_x + offset_x
    target_y = win_y + offset_y

    print(f"      -> 窗口位置: ({win_x}, {win_y})")
    print(f"      -> 目标坐标: ({target_x}, {target_y})")

    # 3. 移动并点击
    # 暂停一下，防止窗口刚弹出来还没渲染完 UI
    time.sleep(0.5)

    # pydirectinput 默认会有防故障保护，移动鼠标
    pydirectinput.moveTo(target_x, target_y)

    # 执行右键点击
    # duration=0.1 模拟按下的持续时间，让 Steam 能够感应到
    pydirectinput.click(button=click)

    # 点击加入游戏

    print("Done. 点击完成。")


def close_window(hwnd):
    """发送关闭信号给指定窗口"""
    print(f"[5/4] 正在关闭窗口...")
    # PostMessage 发送 WM_CLOSE 消息，无需窗口处于前台即可生效
    # 这比 Alt+F4 更稳定，不会误关其他窗口
    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)


def get_aim_style1(config = None):
    """
    读取配置文件中的 target_cmd1 内容
    """

    if config is None:
        config = ConfigManager()
    # 2. 获取所有配置数据
    all_data = config.get_all_data()

    # 3. 提取 target_cmd1，使用 .get 防止报错（如果没找到返回空字符串）
    aim_style1 = all_data.get("aim_style1", )

    return aim_style1


def auto_enter_on_black_screen():
    # 初始化截图工具
    with mss.mss() as sct:

        print("脚本已启动，正在监控屏幕黑色占比...")

        while True:

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
                print(f"检测到黑屏 (占比: {ratio:.1%}) -> 按下 Enter")
                pydirectinput.press('enter')
                break
                # 按完后等待几秒，防止在一个黑屏里疯狂连按
                # time.sleep(0.1)

                # 每次循环稍微暂停一下，降低CPU占用
            time.sleep(0.1)


def auto_esc_on_black_screen():
    # 初始化截图工具
    with mss.mss() as sct:

        print("脚本已启动，正在监控屏幕黑色占比...")

        while True:

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
                print(f"检测到黑屏 (占比: {ratio:.1%}) -> 按下 Esc")
                pydirectinput.press('esc')
                break
                # 按完后等待几秒，防止在一个黑屏里疯狂连按
                # time.sleep(0.1)

                # 每次循环稍微暂停一下，降低CPU占用
            time.sleep(0.1)


def get_latest_steam_link_from_log():
    """
    尝试自动获取 Steam console_log.txt 中最新的 ExecuteSteamURL
    返回: (str) 链接 或 None
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
                    return match.group(1), "成功找到链接"

        return None, "日志中未发现 ExecuteSteamURL 记录"

    except Exception as e:
        return None, f"读取日志出错: {e}"


def on_read_key(config = None):
    link, msg = get_latest_steam_link_from_log()


    if config is None:
        config = ConfigManager()

    if link:
        # 写入配置
        config.update_config_item("target_cmd1", link)


def main():


    # 只创建一个 ConfigManager 实例
    config = ConfigManager()

    ID = get_cmd1_id(config)  # 传递实例
    aim_style = get_aim_style1(config)

    launch_steam_chat(ID)

    # 查找窗口
    print(f"[2/4] 寻找窗口...")
    for i in range(10):
        found_hwnd = find_target_window(TARGET_KEYWORDS)
        if found_hwnd: break
        time.sleep(0.5)

    if found_hwnd:
        if bring_to_front(found_hwnd):
            # 只有置顶成功了才点击
            right_click_on_window(found_hwnd, CLICK_OFFSET_X, CLICK_OFFSET_Y,"right")
            time.sleep(0.5)
            right_click_on_window(found_hwnd, CLICK_OFFSET_X1, CLICK_OFFSET_Y1, "left")
            close_window(found_hwnd)
            #回到游戏
            pydirectinput.click(button="right")

            on_read_key(config)

            time.sleep(1)
            auto_enter_on_black_screen()
            time.sleep(1)
            if aim_style == True:
                auto_enter_on_black_screen()
            else:
                auto_esc_on_black_screen()

    else:
        print("超时: 未找到窗口。")
