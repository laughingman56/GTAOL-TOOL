
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

def get_key(key):
    cfg = ConfigManager()
    data = cfg.get_all_data()
    return data.get(key, {}).get("key", False)



m_menu = get_key("m_menu")
weapon_menu  = get_key("weapon_menu")
no_weapon  = get_key("no_weapon")
shotgun_weapon  = get_key("shotgun_weapon")
rpg_weapon = get_key("rpg_weapon")
c4_weapon  = get_key("c4_weapon")
pistol_weapon  = get_key("pistol_weapon")
sniper_weapon = get_key("sniper_weapon")

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

    m_menu = get_key("m_menu")

    """主运行函数，支持复用 mss 实例"""
    quick_press(m_menu)
    time.sleep(0.3)  # 可根据实际情况调整


    is_ceo = ka_ceo.judge(m_ROI,350,400,sct)

    if is_ceo:
        quick_press("enter")
        quick_press("up")
        quick_press("enter")
        time.sleep(0.3)
        quick_press(m_menu)
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
