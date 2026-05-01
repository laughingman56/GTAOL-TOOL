
import pydirectinput
import time

import  ctypes
from config_manager import ConfigManager






def delay():
    cfg = ConfigManager()
    data = cfg.get_all_data()
    if data.get("low_fps", {}).get("enabled", False):
        return 0.1
    return  0

def _get_times(key):
    cfg = ConfigManager()
    return int(cfg.get_all_data().get(key, {}).get("times", 0))


def quick_press(btn):
    pydirectinput.keyDown(btn)
    time.sleep(0.05)
    pydirectinput.keyUp(btn)
    time.sleep(0.05)


def force_scroll(n=1):
    ctypes.windll.user32.mouse_event(0x0800, 0, 0, n * 120, 0)


def _run(key):
    """通用流程"""

    extra_delay = delay()
    #print(extra_delay)

    pydirectinput.PAUSE = 0.02
    quick_press("m")
    time.sleep(0.5 + extra_delay)
    for _ in range(7):
        force_scroll(1)
        time.sleep(0.05 + extra_delay)
    quick_press("enter")
    for _ in range(2):
        force_scroll(-1)
        time.sleep(0.05 + extra_delay)
    quick_press("enter")
    time.sleep(0.05 + extra_delay)
    for _ in range(_get_times(key)):
        quick_press("enter")
        time.sleep(0.05 + extra_delay)
    quick_press("m")
    pydirectinput.PAUSE = 0.1

def eat_snack(): _run("snack")