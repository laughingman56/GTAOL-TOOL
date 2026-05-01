
import pydirectinput
import time

from mss_dpi import  ResolutionAdapter
import tkinter as tk
import threading
import win32gui

import ctypes


class PhotoClimbLogic:

    _ui_root = None          # Tk 窗口单例
    _ui_thread = None        # UI 线程单例
    _ui_hide_event = threading.Event()  # 隐藏信号（替代每次的 stop_event）

    @staticmethod
    def _show_overlay():
        """
        GUI 线程函数：显示底部透明提示字
        """
        """单例 UI：只创建一次，通过显示/隐藏控制"""
        # 如果窗口已存在，直接显示并返回
        if PhotoClimbLogic._ui_root is not None:
            try:
                PhotoClimbLogic._ui_root.deiconify()
                return
            except tk.TclError:
                pass  # 万一窗口被外部销毁，重新创建

        root = tk.Tk()
        PhotoClimbLogic._ui_root = root
        # 1. 基础去边框和置顶
        root.overrideredirect(True)
        root.wm_attributes("-topmost", True)

        # 2. 【关键修改】设置背景透明
        # 选定一种颜色作为背景色（这里用黑色），然后设置该颜色为透明色
        transparent_color = "black"
        root.configure(bg=transparent_color)
        root.wm_attributes("-transparentcolor", transparent_color)

        # 3. 设置字体样式 (亮绿色，大号字体，加粗)
        fg_color = "#00FF00"  # 亮绿色
        font_style = ("Microsoft YaHei", 20, "bold")  # 20号字体

        # 4. 提示文本 (使用 \n 换行)
        text = "右键关闭相机后移动\n空格键停止脚本"

        label = tk.Label(root, text=text, font=font_style,
                         fg=fg_color, bg=transparent_color,  # 背景色必须与透明色一致
                         padx=10, pady=10)
        label.pack()

        # 5. 计算位置：屏幕底部居中
        # 更新组件以获取实际大小
        root.update_idletasks()
        window_width = root.winfo_width()
        window_height = root.winfo_height()
        # ================= [修改开始] 使用适配器计算位置 =================
        # 获取游戏窗口的位置和大小 (game_x, game_y, game_w, game_h)
        gx, gy, gw, gh = ResolutionAdapter.get_game_window_rect()

        # 计算居中 X：游戏左边距 + (游戏宽 - 窗口宽) / 2
        x_pos = int(gx + (gw - window_width) // 2)

        # 计算底部 Y：游戏顶边距 + 游戏高 - 窗口高 - 偏移量(150)
        # 这样无论游戏是全屏还是窗口化，字都在游戏画面底部上方
        y_pos = int(gy + gh - window_height - 150)
        # ================= [修改结束] =================

        root.geometry(f"{window_width}x{window_height}+{x_pos}+{y_pos}")

        # ========================== [修改开始：插入以下代码] ==========================
        # 1. 设置【鼠标穿透】：让鼠标点击直接穿过字幕层，作用在游戏上
        # -20 是 GWL_EXSTYLE
        # 0x80000 是 WS_EX_LAYERED (分层窗口)
        # 0x20 是 WS_EX_TRANSPARENT (鼠标穿透，不拦截事件)
        hwnd = win32gui.GetParent(root.winfo_id())
        current_style = win32gui.GetWindowLong(hwnd, -20)
        win32gui.SetWindowLong(hwnd, -20, current_style | 0x80000 | 0x20)

        # 2. 强制【归还焦点】：把操作权立刻还给游戏窗口
        game_hwnd = win32gui.FindWindow(None, "Grand Theft Auto V")
        if game_hwnd:
            try:
                # 发送一个假的Alt键防止切换报错，然后置顶游戏
                win32gui.SetForegroundWindow(game_hwnd)
            except Exception:
                pass

            # ========================== [修改结束] ==========================

        # 修改定时检查逻辑：从"销毁"改为"隐藏"
        def check_hide():
            if PhotoClimbLogic._ui_hide_event.is_set():
                root.withdraw()  # 隐藏窗口（内存不释放）
                PhotoClimbLogic._ui_hide_event.clear()
            root.after(100, check_hide)

        check_hide()
        root.mainloop()

    @staticmethod
    def force_scroll(clicks=1):
        MOUSEEVENTF_WHEEL = 0x0800
        delta = clicks * 120
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, delta, 0)

    def get_key(key):
        from config_manager import ConfigManager
        cfg = ConfigManager()
        data = cfg.get_all_data()
        orign_key = data.get(key, {}).get("key", False)
        key = orign_key.lower()
        return key

    @staticmethod
    def gta_photo_climb():
        no_weapon = PhotoClimbLogic.get_key("no_weapon")

        print("开始执行攀爬动作...")


        # 1. 贴墙
        pydirectinput.keyDown(no_weapon)
        pydirectinput.keyUp(no_weapon)

        time.sleep(1.5)
        pydirectinput.keyDown('q')
        pydirectinput.keyUp('q')


        # 2. 拿出手机
        pydirectinput.keyDown("up")
        pydirectinput.keyUp("up")
        pydirectinput.keyDown("up")
        pydirectinput.keyUp("up")
        time.sleep(2.3)

        # 3. 攀爬
        pydirectinput.keyDown('w')
        pydirectinput.keyDown('space')

        # 4. 收手机
        pydirectinput.keyDown("up")
        pydirectinput.keyUp("up")
        pydirectinput.keyDown("up")
        pydirectinput.keyUp("up")

        pydirectinput.keyUp('w')
        pydirectinput.keyUp('space')

        time.sleep(2.3)

        # 5. 右键
        pydirectinput.mouseDown(button='right')
        time.sleep(0.1)
        pydirectinput.mouseUp(button='right')
        time.sleep(0.5)

        # 6. 滚轮
        PhotoClimbLogic.force_scroll(-1)
        time.sleep(0.1)
        PhotoClimbLogic.force_scroll(-1)

        # 7. 左键确认
        pydirectinput.mouseDown()
        time.sleep(0.05)
        pydirectinput.mouseUp()

        print("攀爬动作结束")

    @staticmethod
    def right_click_loop():
        print("\n>>> 模式启动：【右键】触发 -> 1.7秒后点击左键")
        print(">>> 按下【空格键】结束整个脚本")

        # --- 启动 UI 线程 ---
        # 只在首次运行或线程死亡时创建，否则直接显示已有窗口
        if PhotoClimbLogic._ui_thread is None or not PhotoClimbLogic._ui_thread.is_alive():
            PhotoClimbLogic._ui_thread = threading.Thread(target=PhotoClimbLogic._show_overlay)
            PhotoClimbLogic._ui_thread.daemon = True
            PhotoClimbLogic._ui_thread.start()
        else:
            # 线程存活但窗口可能被隐藏，触发显示
            PhotoClimbLogic._ui_hide_event.clear()  # 确保清除隐藏信号
            if PhotoClimbLogic._ui_root:
                PhotoClimbLogic._ui_root.deiconify()


        VK_RBUTTON = 0x02
        VK_SPACE = 0x20  # 空格键虚拟键码

        try:
            while True:
                # 1. 检测空格退出 (使用 win32api)
                if ctypes.windll.user32.GetAsyncKeyState(VK_SPACE) & 0x8000:
                    print("检测到空格，退出循环。")
                    break

                # 2. 检测右键按下
                if ctypes.windll.user32.GetAsyncKeyState(VK_RBUTTON) & 0x8000:
                    print("检测到右键，开始1.7秒倒计时...")

                    start_time = time.time()
                    interrupted = False

                    # 等待1.5秒，期间检测空格
                    while time.time() - start_time < 1.5:
                        if ctypes.windll.user32.GetAsyncKeyState(VK_SPACE) & 0x8000:
                            interrupted = True
                            break
                        time.sleep(0.01)

                    if interrupted:
                        print("倒计时被打断，停止。")
                        break

                    print(">>> 执行左键点击")
                    pydirectinput.mouseDown(button='left')
                    time.sleep(0.05)
                    pydirectinput.mouseUp(button='left')

                    # 等待右键释放，期间检测空格
                    while ctypes.windll.user32.GetAsyncKeyState(VK_RBUTTON) & 0x8000:
                        if ctypes.windll.user32.GetAsyncKeyState(VK_SPACE) & 0x8000:
                            interrupted = True
                            break
                        time.sleep(0.05)

                    if interrupted:
                        break

                time.sleep(0.01)
        finally:
            PhotoClimbLogic._ui_hide_event.set()  # 触发隐藏而非销毁
            print("UI 已隐藏（单例保留）")


    @staticmethod
    def run():
        # 设置输入库的防卡死和延迟
        pydirectinput.PAUSE = 0.1
        pydirectinput.FAILSAFE = False

        print("[PhotoClimb] 启动...")
        time.sleep(0.5)
        PhotoClimbLogic.gta_photo_climb()
        PhotoClimbLogic.right_click_loop()
        print("[PhotoClimb] 结束")