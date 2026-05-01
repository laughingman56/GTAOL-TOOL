# anti_idle_manager.py
import time
import threading
import win32api
import win32gui
import pydirectinput
import ctypes
from config_manager import ConfigManager


class AntiIdleManager(threading.Thread):
    """完全独立的挂机防休眠管理器（无需传参版）"""

    def __init__(self):
        super().__init__(daemon=True)  # 设为守护线程，主程序退出时自动结束

        # ====== 内部写死配置，无需外部传参 ======
        self.target_title = "Grand Theft Auto"
        self.idle_threshold = 300 # 10分钟 (600秒)
        self.check_interval = 2  # 每2秒检测一次
        # ========================================

        # 状态控制
        self.running = False


        # 检测相关状态
        self.last_active_time = time.time()
        self.last_mouse_pos = win32api.GetCursorPos()
        self._is_pressing_key = False

        # 抽查的按键列表 (虚拟键码)：W, A, S, D, 空格, Shift
        self.watch_keys = [0x57, 0x41, 0x53, 0x44, 0x20, 0x10]

    def _is_game_window_active(self):
        """检查当前前台窗口是否匹配目标游戏标题"""
        if not self.target_title:
            return True
        try:
            hwnd = win32gui.GetForegroundWindow()
            current_title = win32gui.GetWindowText(hwnd)
            return self.target_title.lower() in current_title.lower()
        except:
            return False

    def _check_player_activity(self):
        """检测当前是否有真实的玩家活动"""
        if self._is_pressing_key:
            return False

        current_pos = win32api.GetCursorPos()
        dx = abs(current_pos[0] - self.last_mouse_pos[0])
        dy = abs(current_pos[1] - self.last_mouse_pos[1])

        if dx > 3 or dy > 3:
            self.last_mouse_pos = current_pos
            return True

        self.last_mouse_pos = current_pos

        for key_code in self.watch_keys:
            if win32api.GetAsyncKeyState(key_code) & 0x8000:
                return True

        return False

    def enable(self):
        cfg = ConfigManager()
        data = cfg.get_all_data()
        if data.get("hang_up_and_key_setting", {}).get("enabled", False) is not None and data.get("hang_up_and_key_setting",{}).get("enabled",False):

            #print("自动挂机已打开")
            return True
        elif not data.get("hang_up_and_key_setting", {}).get("enabled", False):
            #print("自动挂机已关闭")
            return False
        else:
            #print("自动挂机未找到，默认开启")
            return True

    def force_scroll(self,n=1):
        ctypes.windll.user32.mouse_event(0x0800, 0, 0, n * 120, 0)
    def _send_c_key(self):
        """发送C键"""
        self._is_pressing_key = True
        try:
            for _ in range(5):
                self.force_scroll(1)
                time.sleep(0.1)

            pydirectinput.keyDown("c")
            time.sleep(0.1)
            pydirectinput.keyUp("c")

            print(f"[{time.strftime('%H:%M:%S')}] 检测到挂机，已自动按下 上滚轮 和c键防休眠。")
        except Exception as e:
            print(f"发送C键失败: {e}")
        finally:
            time.sleep(0.5)
            self._is_pressing_key = False

    def run(self):
        """线程主循环"""
        print("防挂机休眠服务已后台运行。")
        self.running = True

        while self.running:
            if not self.enable():
                time.sleep(5)
                continue

            if not self._is_game_window_active():
                self.last_active_time = time.time()
                time.sleep(self.check_interval)
                continue

            if self._check_player_activity():
                self.last_active_time = time.time()

            idle_time = time.time() - self.last_active_time

            if idle_time >= self.idle_threshold:
                self._send_c_key()
                self.last_active_time = time.time()

            time.sleep(self.check_interval)

    def stop(self):
        """安全停止线程"""
        self.running = False
