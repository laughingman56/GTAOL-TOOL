import ctypes
import sys

SW_HIDE = 0
SW_SHOW = 5


def get_console_hwnd():
    kernel32 = ctypes.windll.kernel32
    hwnd = kernel32.GetConsoleWindow()
    if hwnd == 0:
        return None
    return hwnd


def is_console_visible():
    hwnd = get_console_hwnd()
    if hwnd is None:
        return False
    user32 = ctypes.windll.user32
    return bool(user32.IsWindowVisible(hwnd))


def show_console():
    hwnd = get_console_hwnd()
    if hwnd is None:
        return
    user32 = ctypes.windll.user32
    user32.ShowWindow(hwnd, SW_SHOW)


def hide_console():
    hwnd = get_console_hwnd()
    if hwnd is None:
        return
    user32 = ctypes.windll.user32
    user32.ShowWindow(hwnd, SW_HIDE)


def toggle_console():
    if is_console_visible():
        hide_console()
    else:
        show_console()
    return is_console_visible()
