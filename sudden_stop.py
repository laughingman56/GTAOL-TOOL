import pydirectinput
import time
import subprocess
import ctypes
import sys
import os
import psutil
from config_manager import ConfigManager
import socket
from urllib.parse import urlparse


import customtkinter as ctk
from config_manager import ConfigManager

#------------guii界面---------------

# 注意：需确保你已导入了 cha_chuan_1 和 cha_chuan_2 函数
# 或者将此函数放在同一个文件中

def show_settings_ui(parent_window):
    """
    显示设置界面的GUI (无保存按钮，即选即存)
    """
    # 1. 创建顶级弹窗
    settings_win = ctk.CTkToplevel(parent_window)
    settings_win.title("瞬间悬停设置")
    settings_win.geometry("400x300")
    settings_win.resizable(False, False)

    # 窗口置顶与模态
    settings_win.attributes("-topmost", True)
    settings_win.grab_set()

    # 2. 准备数据
    cfg = ConfigManager()
    data = cfg.get_all_data()
    bot_options = ["断网悬停", "切换角色悬停"]  # 对应索引 0, 1, 2

    # 获取当前配置索引 (防止越界)
    idx1 = data.get("sudden_stop", {}).get("style", 0)

    if not (0 <= idx1 < 2): idx1 = 0


    # 3. 定义回调函数 (自动保存逻辑)

    def on_change_rule(choice):
        """当差传1下拉框变化时触发"""
        try:
            new_idx = bot_options.index(choice)  # 获取文本对应的索引(0,1,2)
            cfg.update_config_item("sudden_stop.style", new_idx)  # 写入配置
            print(f"[设置] 瞬间悬停 已切换为: {choice} (ID:{new_idx})")

        except Exception as e:
            print(f"[错误] 瞬间悬停保存失败: {e}")



    # 4. 构建 UI
    frame = ctk.CTkFrame(settings_win)
    frame.pack(fill="both", expand=True, padx=15, pady=15)

    # --- 断网规则 ---
    ctk.CTkLabel(frame, text="瞬间悬停:",
                 font=("Microsoft YaHei", 18, "bold")).pack(anchor="w",pady=(5, 5))

    combo_1 = ctk.CTkComboBox(
        frame,
        font=("Microsoft YaHei", 18, "bold"),
        dropdown_font=("Microsoft YaHei", 18, "bold"),
        values=bot_options,
        state="readonly",
        command=on_change_rule  # 绑定回调函数
    )
    combo_1.pack(fill="x", pady=(0, 15))
    combo_1.set(bot_options[idx1])  # 设置初始值




#------------执行层-----------------

def is_admin():
    """检查当前是否具有管理员权限"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def get_running_gta5_path() -> str:
    """
    寻找当前正在运行的 GTA5 程序的完整路径。
    兼容增强版 (GTA5_Enhanced.exe) 和 传承版 (GTA5.exe)。
    """
    # 将目标进程名全部小写，方便忽略大小写匹配
    target_processes = ["gta5.exe", "gta5_enhanced.exe"]

    # 遍历当前系统中所有正在运行的进程
    for proc in psutil.process_iter(['name', 'exe']):
        try:
            # 获取进程名并转为小写
            process_name = proc.info['name'].lower()

            # 如果进程名在我们的目标列表中
            if process_name in target_processes:
                exe_path = proc.info['exe']
                if exe_path:
                    return exe_path
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # 忽略系统进程因权限不足或进程刚结束导致的报错
            continue

    return None


def get_resource_path(relative_path):
    """
    获取资源文件的绝对路径。
    兼容开发环境和 PyInstaller 打包后的环境。
    """
    if hasattr(sys, '_MEIPASS'):
        # 如果是被 PyInstaller 打包后的环境，文件会被解压到 _MEIPASS 临时目录下
        base_path = sys._MEIPASS
    else:
        # 如果是正常开发环境，直接使用当前脚本所在目录
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)



def get_system_ip(url):
    """
    使用系统默认解析，获取加速器路由模式下的IP（可能是加速器虚拟IP）
    """
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    domain = urlparse(url).netloc.split(':')[0]

    try:
        # 这个方法会直接命中加速器的虚拟网卡DNS规则
        ip = socket.gethostbyname(domain)
        return ip
    except socket.gaierror as e:
        print(f"解析失败 (可能被加速器拦截): {e}")
        return None

def natdown_stop():





    gta_path = get_running_gta5_path()

    exe_path = get_resource_path("WFPcon.exe")

    # 判断一下文件是否存在，避免报错
    if not os.path.exists(exe_path):
        print(f"找不到文件: {exe_path}")
        return




    try:
        # 使用 subprocess.Popen 相当于易语言运行命令参数中的“假”（不等待，异步执行）
        print("断网悬停")
        print(f"正在执行: 断开服务器链接")

        #保险命令，进程模式断开服务器链接
        subprocess.Popen(f'"{exe_path}" -c -p "{gta_path}" -ip 127.0.0.1 -proto tcp', shell=True)


        #主要命令
        subprocess.Popen(f'"{exe_path}" -c -p "{gta_path}"  -rp 80', shell=True)
        subprocess.Popen(f'"{exe_path}" -c -p "{gta_path}"  -rp 443', shell=True)
        print("WFPcon 已成功启动！")



        pydirectinput.PAUSE = 0.02

        pydirectinput.keyDown("alt")
        time.sleep(0.02)
        pydirectinput.keyDown("f4")

        pydirectinput.keyUp("f4")
        pydirectinput.keyUp("alt")

        time.sleep(0.2)

        pydirectinput.keyDown("esc")
        time.sleep(0.1)
        pydirectinput.keyUp("esc")

        pydirectinput.PAUSE = 0.1
        time.sleep(0.5)

        subprocess.Popen(f'"{exe_path}" -d', shell=True)





    except Exception as e:
        print(f"运行失败: {e}")

def chara_stop():
    print("切换角色悬停")
    pydirectinput.PAUSE = 0.02

    pydirectinput.keyDown("alt")
    time.sleep(0.5)
    # 向上移动100像素（y轴减少）
    pydirectinput.moveRel(0, -100,relative= True)




    pydirectinput.keyUp("alt")


    for i in range(1):
        pydirectinput.keyDown("esc")

        pydirectinput.keyUp("esc")

    pydirectinput.PAUSE = 0.1


def main():
    cfg = ConfigManager()
    data = cfg.get_all_data()

    is_admin()

    if data.get("sudden_stop", {}).get("style", 0) == 0 :

        natdown_stop()

    else:
        chara_stop()