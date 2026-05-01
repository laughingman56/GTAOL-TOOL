import mss
import pydirectinput
import time
import win32gui
import win32api

from PIL import Image


# ================= 分辨率适配器 (修复版 - MSS适配) =================

class ResolutionAdapter:
    BASE_W = 2560
    BASE_H = 1440
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
        """ 直接返回 mss 需要的字典格式 """
        win_x, win_y, win_w, win_h = cls.get_game_window_rect()
        scale_factor = win_h / cls.BASE_H
        orig_x, orig_y, orig_w, orig_h = base_config_tuple

        orig_cx = orig_x + (orig_w / 2)
        orig_cy = orig_y + (orig_h / 2)
        off_x = orig_cx - cls.BASE_CENTER_X
        off_y = orig_cy - cls.BASE_CENTER_Y

        curr_cx = win_x + (win_w / 2)
        curr_cy = win_y + (win_h / 2)
        new_cx = curr_cx + (off_x * scale_factor)
        new_cy = curr_cy + (off_y * scale_factor)
        new_w = orig_w * scale_factor
        new_h = orig_h * scale_factor

        return {
            'top': int(new_cy - new_h / 2),
            'left': int(new_cx - new_w / 2),
            'width': int(new_w),
            'height': int(new_h)
        }