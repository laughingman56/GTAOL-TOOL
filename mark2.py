
import pydirectinput
import time

import  ctypes
from config_manager import ConfigManager


def show_settings_ui(parent_window):
    """显示电话联系人设置界面（四列：热键 | 名字 | 次数 | 开关）"""
    import customtkinter as ctk



    # 创建置顶设置窗口
    settings_window = ctk.CTkToplevel(parent_window)
    settings_window.title("马克兔设置")
    settings_window.geometry("400x500")
    settings_window.resizable(False, False)
    settings_window.transient(parent_window)  # 跟随父窗口
    settings_window.grab_set()  # 模态窗口

    # 获取配置管理器（依赖父窗口传入 config）
    config = parent_window.config

    # 配置网格（四列等比）
    settings_window.grid_columnconfigure(0, weight=1)  # 热键
    settings_window.grid_columnconfigure(1, weight=2)  # 名字（更宽一些）

    settings_window.grid_columnconfigure(3, weight=1)  # 开关



    # 表头
    headers = ["热键", "功能",  "启用"]
    for col, text in enumerate(headers):
        lbl = ctk.CTkLabel(
            settings_window,
            text=text,
            font=("Microsoft YaHei UI", 18, "bold"),
            text_color="#3B8ED0"
        )
        lbl.grid(row=0, column=col, padx=15, pady=(15, 10), sticky="w")

    # 三个联系人配置
    contact_ids = ["call_mk2","send_mk2","call_mk2_truck","call_sparrow","call_whale","send_sparrow","call_car","open_door"]
    #"call_mk2","send_mk2","call_mk2_truck","call_sparrow","call_whale","send_sparrow","call_car","open_door"
    #"m_menu", "weapon_menu", "no_weapon", "shotgun_weapon", "rpg_weapon", "c4_weapon", "pistol_weapon", "sniper_weapon"

    def start_recording(contact_id, btn_widget):
        """开始录制热键（参考 gui_app.request_recording）"""
        if config.is_recording:
            return

        # 更新按钮为录制状态（蓝底）
        btn_widget.configure(text="请按键...", fg_color="#D6EAF8", text_color="#3B8ED0")
        config.set_recording_mode(contact_id)

        # 启动轮询检查录制结果
        check_recording_status(btn_widget, contact_id)

    def check_recording_status(btn_widget, contact_id):
        """轮询检查是否完成录制"""
        if config.is_recording:
            settings_window.after(100, lambda: check_recording_status(btn_widget, contact_id))
        else:
            # 录制结束，恢复白底并显示新按键
            data = config.get_function_data(contact_id)
            new_key = data.get('key', 'NONE')
            btn_widget.configure(text=new_key, fg_color="white", text_color="black")

    def update_times(contact_id, entry_widget):
        """失去焦点或回车时保存次数"""
        try:
            value = entry_widget.get().strip()
            if value.isdigit():
                with config.lock:
                    config.data[contact_id]['times'] = value
                config.save_config()
                print(f"[PhoneCall] {contact_id} 次数更新为: {value}")
        except Exception as e:
            print(f"[PhoneCall] 更新次数失败: {e}")

    def toggle_switch(contact_id, switch_widget):
        """开关切换回调"""
        is_on = bool(switch_widget.get())
        config.update_switch_state(contact_id, is_on)
        print(f"[PhoneCall] {contact_id} 启用状态: {is_on}")

    # 创建三行数据
    for row_idx, contact_id in enumerate(contact_ids, start=1):
        data = config.get_function_data(contact_id)
        if not data:
            continue

        # 第一列：热键按钮（可录制）
        btn_key = ctk.CTkButton(
            settings_window,
            text=data.get('key', 'NONE'),
            font=("Microsoft YaHei UI", 18, "bold"),
            text_color="black",
            fg_color="white",
            hover_color="#F0F0F0",
            border_width=2,
            border_color="#3B8ED0",
            width=100,
            height=40,
            corner_radius=0
        )
        # 使用默认参数固化循环变量，避免闭包问题
        btn_key.configure(command=lambda cid=contact_id, btn=btn_key: start_recording(cid, btn))
        btn_key.grid(row=row_idx, column=0, padx=5, pady=8, sticky="w")

        # 第二列：名字（只读，灰色背景标签）
        lbl_name = ctk.CTkLabel(
            settings_window,
            text=data.get('name', contact_id),
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
        if data.get('enabled', True):
            switch.select()
        else:
            switch.deselect()

        switch.configure(command=lambda cid=contact_id, sw=switch: toggle_switch(cid, sw))
        # 左边的 padding 设为 0，右边保持 10
        switch.grid(row=row_idx, column=2, padx=(20, 20), pady=8, sticky="w")



#------------执行部分--------------

def delay():
    cfg = ConfigManager()
    data = cfg.get_all_data()
    if data.get("low_fps", {}).get("enabled", False):
        return 0.1
    return  0


def quick_press(btn):
    pydirectinput.keyDown(btn)
    time.sleep(0.05)
    pydirectinput.keyUp(btn)
    time.sleep(0.05)


def force_scroll(n=1):
    ctypes.windll.user32.mouse_event(0x0800, 0, 0, n * 120, 0)

def get_key(key):
    cfg = ConfigManager()
    data = cfg.get_all_data()
    orign_key = data.get(key, {}).get("key", False)
    key = orign_key.lower()
    return key


def call_mk2__run():
    """通用流程"""

    extra_delay = delay()
    #print(extra_delay)

    m_menu = get_key("m_menu")

    pydirectinput.PAUSE = 0.02
    quick_press(m_menu)
    time.sleep(0.5 + extra_delay)
    for _ in range(8):
        force_scroll(1)
        time.sleep(0.05 + extra_delay)
    quick_press("enter")
    for _ in range(3):
        force_scroll(1)
        time.sleep(0.05 + extra_delay)
    quick_press("enter")
    for _ in range(2):
        force_scroll(-1)
        time.sleep(0.05 + extra_delay)
    quick_press("enter")
    quick_press(m_menu)

    pydirectinput.PAUSE = 0.1

def call_mk2_truck__run():
    """通用流程"""

    extra_delay = delay()
    #print(extra_delay)

    m_menu = get_key("m_menu")

    pydirectinput.PAUSE = 0.02
    quick_press(m_menu)
    time.sleep(0.5 + extra_delay)
    for _ in range(8):
        force_scroll(1)
        time.sleep(0.05 + extra_delay)
    quick_press("enter")
    for _ in range(3):
        force_scroll(1)
        time.sleep(0.05 + extra_delay)
    quick_press("enter")

    quick_press("enter")
    quick_press(m_menu)

    pydirectinput.PAUSE = 0.1

def send_mk2__run():
    """通用流程"""

    extra_delay = delay()
    #print(extra_delay)

    m_menu = get_key("m_menu")

    pydirectinput.PAUSE = 0.02
    quick_press(m_menu)
    time.sleep(0.5 + extra_delay)
    for _ in range(9):
        force_scroll(1)
        time.sleep(0.05 + extra_delay)
    quick_press("enter")
    for _ in range(3):
        force_scroll(1)
        time.sleep(0.05 + extra_delay)
    #time.sleep(0.5 + extra_delay)
    quick_press("enter")
    quick_press(m_menu)

    pydirectinput.PAUSE = 0.1

def call_car__run():
    """通用流程"""

    extra_delay = delay()
    #print(extra_delay)

    m_menu = get_key("m_menu")

    pydirectinput.PAUSE = 0.02
    quick_press(m_menu)
    time.sleep(0.5 + extra_delay)
    for _ in range(9):
        force_scroll(1)
        time.sleep(0.05 + extra_delay)
    quick_press("enter")

    #time.sleep(0.5 + extra_delay)
    quick_press("enter")
    quick_press(m_menu)

    pydirectinput.PAUSE = 0.1

def open_door__run():
    """通用流程"""

    extra_delay = delay()
    #print(extra_delay)

    m_menu = get_key("m_menu")

    pydirectinput.PAUSE = 0.02
    quick_press(m_menu)
    time.sleep(0.5 + extra_delay)
    for _ in range(9):
        force_scroll(1)
        time.sleep(0.05 + extra_delay)
    quick_press("enter")
    for _ in range(1):
        force_scroll(1)
        time.sleep(0.05 + extra_delay)
    quick_press("enter")
    for _ in range(2):
        force_scroll(-1)
        time.sleep(0.05 + extra_delay)
    #time.sleep(0.5 + extra_delay)
    quick_press("enter")
    for _ in range(4):
        force_scroll(-1)
        time.sleep(0.05 + extra_delay)
    quick_press("enter")
    time.sleep(extra_delay)
    quick_press("enter")
    quick_press(m_menu)

    pydirectinput.PAUSE = 0.1

def call_sparrow__run():
    """通用流程"""

    extra_delay = delay()
    #print(extra_delay)

    m_menu = get_key("m_menu")

    pydirectinput.PAUSE = 0.02
    quick_press(m_menu)
    time.sleep(0.5 + extra_delay)
    for _ in range(8):
        force_scroll(1)
        time.sleep(0.05 + extra_delay)
    quick_press("enter")
    for _ in range(2):
        force_scroll(1)
        time.sleep(0.05 + extra_delay)
    quick_press("enter")
    for _ in range(1):
        force_scroll(-1)
        time.sleep(0.05 + extra_delay)
    quick_press("enter")
    #quick_press(m_menu)

    pydirectinput.PAUSE = 0.1

def call_whale__run():
    """通用流程"""

    extra_delay = delay()
    #print(extra_delay)

    m_menu = get_key("m_menu")

    pydirectinput.PAUSE = 0.02
    quick_press(m_menu)
    time.sleep(0.5 + extra_delay)
    for _ in range(8):
        force_scroll(1)
        time.sleep(0.05 + extra_delay)
    quick_press("enter")
    for _ in range(2):
        force_scroll(1)
        time.sleep(0.05 + extra_delay)
    quick_press("enter")

    time.sleep(0.05 + extra_delay)

    quick_press("enter")
    #quick_press(m_menu)

    pydirectinput.PAUSE = 0.1

def send_sparrow__run():
    """通用流程"""

    extra_delay = delay()
    #print(extra_delay)

    m_menu = get_key("m_menu")

    pydirectinput.PAUSE = 0.02
    quick_press(m_menu)
    time.sleep(0.5 + extra_delay)
    for _ in range(8):
        force_scroll(1)
        time.sleep(0.05 + extra_delay)
    quick_press("enter")
    for _ in range(2):
        force_scroll(1)
        time.sleep(0.05 + extra_delay)
    quick_press("enter")
    for _ in range(3):
        force_scroll(-1)
        time.sleep(0.05 + extra_delay)
    quick_press("enter")
    for _ in range(2):
        force_scroll(1)
        time.sleep(0.05 + extra_delay)
    quick_press("enter")
    #quick_press(m_menu)

    pydirectinput.PAUSE = 0.1

