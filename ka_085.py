import subprocess
import ctypes
import sys
import os
import psutil

import socket
from urllib.parse import urlparse
import win32gui
import win32con
import win32api
import pydirectinput
import time

import threading
import queue
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
    settings_win.title("断网设置")
    settings_win.geometry("500x500")
    settings_win.resizable(False, False)

    # 窗口置顶与模态
    settings_win.attributes("-topmost", True)
    settings_win.grab_set()

    # 2. 准备数据
    cfg = ConfigManager()
    data = cfg.get_all_data()
    bot_options = ["断开服务器链接", "断开云存档链接", "断开交易链接","断开云存档和交易链接","全部断网","战局锁单","卡185"]  # 对应索引 0, 1, 2

    # 获取当前配置索引 (防止越界)
    idx1 = data.get("nat_down", {}).get("rule", 0)
    if not (0 <= idx1 <= 6): idx1 = 0

    # 获取定时配置
    timer_enabled = data.get("nat_down", {}).get("time_limited", False)
    timer_seconds = data.get("nat_down", {}).get("time", 0)


    # 3. 定义回调函数 (自动保存逻辑)

    def on_change_rule(choice):
        """当差传1下拉框变化时触发"""
        try:
            new_idx = bot_options.index(choice)
            cfg.update_config_item("nat_down.rule", new_idx)
            print(f"[设置] 断网规则 已切换为: {choice} (ID:{new_idx})")
        except Exception as e:
            print(f"[错误] 断网规则保存失败: {e}")

    def on_timer_toggle():
        """定时开关切换时触发"""
        try:
            state = timer_switch.get()
            cfg.update_config_item("nat_down.time_limited", state)
            # 同步启用/禁用时间输入框
            timer_entry.configure(state="normal" if state else "disabled")
            print(f"[设置] 定时断网 已{'启用' if state else '禁用'}")
        except Exception as e:
            print(f"[错误] 定时开关保存失败: {e}")

    def on_timer_change(*args):
        """时间输入框内容变化时触发"""
        try:
            value = timer_entry.get().strip()
            if value == "":
                return
            seconds = int(value)
            if seconds < 1:
                seconds = 1
            cfg.update_config_item("nat_down.time", seconds)
            print(f"[设置] 定时时间 已设置为: {seconds}秒")
        except ValueError:
            pass  # 输入非数字时忽略
        except Exception as e:
            print(f"[错误] 定时时间保存失败: {e}")


    # 4. 构建 UI
    frame = ctk.CTkFrame(settings_win)
    frame.pack(fill="both", expand=True, padx=15, pady=15)

    # --- 断网规则 ---
    ctk.CTkLabel(frame, text="断网规则:",
                 font=("Microsoft YaHei", 18, "bold")).pack(anchor="w",pady=(5, 5))

    combo_1 = ctk.CTkComboBox(
        frame,
        font=("Microsoft YaHei", 18, "bold"),
        dropdown_font=("Microsoft YaHei", 18, "bold"),
        values=bot_options,
        state="readonly",
        command=on_change_rule
    )
    combo_1.pack(fill="x", pady=(0, 15))
    combo_1.set(bot_options[idx1])

    # --- 定时控制 ---
    timer_frame = ctk.CTkFrame(frame, fg_color="transparent")
    timer_frame.pack(fill="x", pady=(0, 15))

    # 开关
    timer_switch = ctk.CTkSwitch(
        timer_frame,
        text="定时断网",
        font=("Microsoft YaHei", 18, "bold"),
        command=on_timer_toggle
    )
    timer_switch.pack(side="left")
    if timer_enabled:
        timer_switch.select()

    # 时间输入框
    timer_var = ctk.StringVar(value=str(timer_seconds))
    timer_var.trace_add("write", on_timer_change)

    timer_entry = ctk.CTkEntry(
        timer_frame,
        textvariable=timer_var,
        font=("Microsoft YaHei", 18, "bold"),
        width=80,
        justify="center",
        state="normal" if timer_enabled else "disabled"
    )
    timer_entry.pack(side="left", padx=(15, 5))

    ctk.CTkLabel(timer_frame, text="秒",
                 font=("Microsoft YaHei", 18, "bold")).pack(side="left")

    # --- 说明文字 ---
    ctk.CTkLabel(frame,
                 text="  ● 断网：\n"
                      "  - 按一下是断网，再按一下是恢复\n"
                      "  - 卡085，使用断开服务器链接或断开云存档和交易链接\n"
                      "  - 卡085，恢复联网会杀启动器，回到菜单，无需退出\n"
                      "  - 卡085，快到结算位置了再按\n"
                      "  - 卡085，也可用于赌场转盘，转之前断网，转到就恢复\n"
                      "\n"
                      "  - 卡185，必须使用窗口模式\n"
                      "  - 断网功能使用quellgta的wfpcon断网\n"
                      "  - 感谢mageangela，M3351AN 渟雲，onelymaker",
                 font=("Microsoft YaHei", 18, "bold"),
                 justify="left",
                 padx=5).pack(anchor="w", padx=0)

#------------执行层-----------------

global rule_exist
rule_exist = False

#在085后杀掉启动器就不需要大退重进
def kill_process_by_name(process_name):
    # /F 强制终止 /IM 映像名称
    print(f"尝试终止: {process_name}")
    # >nul 2>&1 用于隐藏系统命令的输出，让界面更清爽
    os.system(f'taskkill /F /IM "{process_name}" >nul 2>&1')

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

def delay():
    cfg = ConfigManager()
    data = cfg.get_all_data()
    if data.get("nat_down", {}).get("rule", 0) == 1:
        return 0.1
    return  0


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


def quick_click():
    is_admin()
    hwnd = win32gui.GetForegroundWindow()

    # 【核心】直接向窗口发送“弹出标题栏系统菜单”的指令
    # 这一步不需要移动鼠标，不需要切焦点，游戏也不会失去响应
    win32gui.PostMessage(hwnd, win32con.WM_SYSCOMMAND, win32con.SC_KEYMENU, 0)

    # 此时，游戏的系统菜单（移动/大小/关闭等）已经弹出了！
    # 如果你后续需要用键盘选择菜单里的选项，可以直接用 pydirectinput 按上下箭头和回车


def run_natdown():

    cfg = ConfigManager()
    data = cfg.get_all_data()

    global rule_exist

    rule_exist = True


    gta_path = get_running_gta5_path()

    exe_path = get_resource_path("WFPcon.exe")

    # 判断一下文件是否存在，避免报错
    if not os.path.exists(exe_path):
        print(f"找不到文件: {exe_path}")
        return


    # 保险命令，进程模式断开服务器链接
    command = f'"{exe_path}" -c -p "{gta_path}" -ip 127.0.0.1 -proto tcp'

    try:
        # 使用 subprocess.Popen 相当于易语言运行命令参数中的“假”（不等待，异步执行）

        if data.get("nat_down", {}).get("rule", 0) == 0:
            print(f"正在执行: 断开服务器链接")

            #保险命令，进程模式断开服务器链接
            subprocess.Popen(command, shell=True)

            #主要命令
            subprocess.Popen(f'"{exe_path}" -c -p "{gta_path}"  -rp 80', shell=True)
            subprocess.Popen(f'"{exe_path}" -c -p "{gta_path}"  -rp 443', shell=True)


        elif data.get("nat_down", {}).get("rule", 0) == 1:
            print(f"正在执行: 断开云存档链接")

            #保险命令，进程模式断开服务器链接
            subprocess.Popen(command, shell=True)

            # 主要命令
            ip_0 = get_system_ip("cs-gta5-prod.ros.rockstargames.com")
            if ip_0 == "" or ip_0 == None:
                ip_0 = "192.81.241.17"
            print(f'服务器ip:{ip_0}')

            subprocess.Popen(f'"{exe_path}" -c -p "{gta_path}"  -ip "{ip_0}"', shell=True)

        elif data.get("nat_down", {}).get("rule", 0) == 2:
            print(f"正在执行: 断开交易链接")

            #保险命令，进程模式断开服务器链接
            subprocess.Popen(command, shell=True)

            # 主要命令
            ip_1 = get_system_ip("prod.p01sjc.pod.rockstargames.com")
            ip_2 = get_system_ip("prod.p02sjc.pod.rockstargames.com")
            if ip_1 == "" or ip_1 == None:
                ip_1 = "192.81.245.200"
            if ip_2 == "" or ip_2 == None:
                ip_2 = "192.81.245.201"
            print(f'服务器ip:{ip_1}')
            print(f'服务器ip:{ip_2}')

            subprocess.Popen(f'"{exe_path}" -c -p "{gta_path}"  -ip "{ip_1}"', shell=True)
            subprocess.Popen(f'"{exe_path}" -c -p "{gta_path}"  -ip "{ip_2}"', shell=True)

        elif data.get("nat_down", {}).get("rule", 0) == 3:
            print(f"正在执行: 断开云存档和交易链接")

            #保险命令，进程模式断开服务器链接
            subprocess.Popen(command, shell=True)

            #主要命令
            ip_0 = get_system_ip("cs-gta5-prod.ros.rockstargames.com")
            ip_1 = get_system_ip("prod.p01sjc.pod.rockstargames.com")
            ip_2 = get_system_ip("prod.p02sjc.pod.rockstargames.com")
            if ip_0 == "" or ip_0 == None:
                ip_0 = "192.81.241.17"
            print(f'服务器ip:{ip_0}')
            if ip_1 == "" or ip_1 == None:
                ip_1 = "192.81.245.200"
            if ip_2 == "" or ip_2 == None:
                ip_2 = "192.81.245.201"
            print(f'服务器ip:{ip_1}')
            print(f'服务器ip:{ip_2}')

            subprocess.Popen(f'"{exe_path}" -c -p "{gta_path}"  -ip "{ip_0}"', shell=True)
            subprocess.Popen(f'"{exe_path}" -c -p "{gta_path}"  -ip "{ip_1}"', shell=True)
            subprocess.Popen(f'"{exe_path}" -c -p "{gta_path}"  -ip "{ip_2}"', shell=True)



        elif data.get("nat_down", {}).get("rule", 0) == 4:
            print(f"正在执行: 全部断网")

            #保险命令，进程模式断开服务器链接
            subprocess.Popen(command, shell=True)

            #主要命令
            subprocess.Popen(f'"{exe_path}" -c -p "{gta_path}" ', shell=True)

        elif data.get("nat_down", {}).get("rule", 0) == 5:
            print(f"正在执行: 战局锁单")

            #主要命令
            subprocess.Popen(f'"{exe_path}" -c -p "{gta_path}"  -lp 6672', shell=True)

        elif data.get("nat_down", {}).get("rule", 0) == 6:
            print(f"正在执行: 卡185")

            #主要命令
            quick_click()


        else:
            print(f"断网失败")

        print("WFPcon 已成功启动！")
    except Exception as e:
        print(f"运行失败: {e}")


def recover_natdown():

    global rule_exist
    rule_exist = False

    cfg = ConfigManager()
    data = cfg.get_all_data()


    exe_path = get_resource_path("WFPcon.exe")

    # 判断一下文件是否存在，避免报错
    if not os.path.exists(exe_path):
        print(f"找不到文件: {exe_path}")
        return

    # 3. 拼接完整的命令行字符串
    # 对应：运行_引号 (..., “-c” ＋ WFP_进程 ＋ “ -lp 6672”, 假, 1)
    # 给路径加上引号，防止路径中有空格
    command = f'"{exe_path}" -d'

    try:
        if data.get("nat_down", {}).get("rule", 0) == 6:

            pydirectinput.move(500, 500)
            pydirectinput.leftClick()


        else:
            # 使用 subprocess.Popen 相当于易语言运行命令参数中的“假”（不等待，异步执行）
            print(f"正在执行: {command}")
            subprocess.Popen(command, shell=True)
            print("删除wfp规则")



    except Exception as e:
        print(f"运行失败: {e}")

# ---- 左上角浮窗 ----
_overlay = None  # 全局引用，防止被GC回收

class FloatingText:
    def __init__(self):
        global _overlay
        _overlay = self

        self.win = ctk.CTkToplevel()
        self.win.overrideredirect(True)          # 无标题栏
        self.win.attributes("-topmost", True)    # 置顶
        self.win.attributes("-alpha", 0.85)      # 半透明

        frame = ctk.CTkFrame(self.win, fg_color=("white"))
        frame.pack(padx=2, pady=2)

        self.label = ctk.CTkLabel(frame, text="", font=("Microsoft YaHei", 25, "bold"))
        self.label.pack(side="left", padx=(10, 4), pady=6)

        '''
        ctk.CTkButton(
            frame, text="✕", width=26, height=26,
            font=("Microsoft YaHei", 20, "bold"),
            fg_color="white",
            hover_color=("gray40", "gray70"),
            command=self._on_close
        ).pack(side="left", padx=(2, 6), pady=6)
        '''

    def show(self, text: str):
        self.label.configure(text=text)
        self.win.geometry("+15+15")
        self.win.deiconify()

    def update(self, text: str):  # ← 新增，紧跟 show 后面
        self.label.configure(text=text)

    def hide(self):
        self.win.withdraw()

    def destroy(self):
        global _overlay
        try:
            self.win.destroy()
        except:
            pass
        _overlay = None

    def _on_close(self):
        """方案A：只隐藏浮窗，不管断网状态"""
        self.hide()


def main():

    is_admin()

    cfg = ConfigManager()
    data = cfg.get_all_data()

    start_time = time.time()

    time_limited = data.get("nat_down", {}).get("time_limited", False)
    times = data.get("nat_down", {}).get("time", 0)
    rule = data.get("nat_down", {}).get("rule", 0)

    d = {0:"断开服务器链接",1:"断开云存档链接",2:"断开交易链接",3:"断开云存档和交易链接", 4:"全部断网", 5:"战局锁单",6:"卡185"}
    text =(f"已断网,规则：{d[rule]}")


    if not rule_exist:

        overlay = FloatingText()       # 第一调用：创建浮窗
        run_natdown()
        overlay.show(text)


        if time_limited:

            while True:

                if time.time() - start_time > times:
                    print("超过时间，跳出循环")
                    recover_natdown()

                    if _overlay:
                        _overlay.destroy()

                    if rule in (0, 3):
                        # 杀掉启动器
                        print("杀掉启动器")
                        kill_process_by_name("Launcher.exe")


                    break

                else:
                    if _overlay:
                        _overlay.update(f"{text},计时：{int(time.time() - start_time)}秒")
                    print(f"已断网{int(time.time() - start_time)}秒")

                time.sleep(1)

    else:
        recover_natdown()

        if _overlay:
            _overlay.destroy()


        if rule in (0, 3):
            # 杀掉启动器
            print("杀掉启动器")
            kill_process_by_name("Launcher.exe")



