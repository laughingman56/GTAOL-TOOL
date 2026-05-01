




from config_manager import ConfigManager

import  win32gui
import  win32api

import mss
import pydirectinput
import time


from PIL import Image, ImageChops
import ctypes  # 新增
import  io
import ka_ceo


def show_settings_ui(parent_window):
    """显示电话联系人设置界面（四列：热键 | 名字 | 次数 | 开关）"""
    import customtkinter as ctk



    # 创建置顶设置窗口
    settings_window = ctk.CTkToplevel(parent_window)
    settings_window.title("战斗相关设置")
    settings_window.geometry("600x700")
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
    headers = ["热键", "功能", "次数", "启用"]
    for col, text in enumerate(headers):
        lbl = ctk.CTkLabel(
            settings_window,
            text=text,
            font=("Microsoft YaHei UI", 18, "bold"),
            text_color="#3B8ED0"
        )
        lbl.grid(row=0, column=col, padx=15, pady=(15, 10), sticky="w")

    # 三个联系人配置
    contact_ids = ["pill","bullet","ghost","revolver","rpg","shot","cloth","thermal","flight_thermal","snack"]

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

        # 第三列：次数（可编辑输入框）
        # 第三列：次数（可编辑输入框），pill/bullet/revolver 不显示
        if contact_id not in ("pill", "bullet", "ghost","revolver","thermal","flight_thermal"):

            entry_times = ctk.CTkEntry(
                settings_window,
                font=("Microsoft YaHei UI", 18, "bold"),
                width=100,
                height=35,
                border_width=2,
                border_color="#CCCCCC",
                fg_color="white",
                text_color="black"
            )
            entry_times.insert(0, str(data.get('times', '0')))
            entry_times.grid(row=row_idx, column=2, padx=5, pady=8)

            # 绑定保存事件（失焦或回车）
            entry_times.bind('<FocusOut>', lambda e, cid=contact_id, ent=entry_times: update_times(cid, ent))
            entry_times.bind('<Return>', lambda e, cid=contact_id, ent=entry_times: update_times(cid, ent))

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
        switch.grid(row=row_idx, column=3, padx=(20, 20), pady=8, sticky="w")


#--------------------------执行层----------------------------

# 坐标定义

m_ROI = (0, 600, 600, 100)


def get_key(key):
    cfg = ConfigManager()
    data = cfg.get_all_data()
    orign_key = data.get(key, {}).get("key", False)
    key = orign_key.lower()
    return key




def force_scroll(n=1):
    ctypes.windll.user32.mouse_event(0x0800, 0, 0, n * 120, 0)

def quick_press(button):
    pydirectinput.keyDown(button)
    time.sleep(0.05)
    pydirectinput.keyUp(button)
    time.sleep(0.05)


def delay():
    cfg = ConfigManager()
    data = cfg.get_all_data()
    if data.get("low_fps", {}).get("enabled", False):
        return 0.1
    return  0

def _get_times(key):
    cfg = ConfigManager()
    return int(cfg.get_all_data().get(key, {}).get("times", 0))

def eat_pill(sct=None):

    # 设置输入库的防卡死和延迟
    pydirectinput.PAUSE = 0.02
    pydirectinput.FAILSAFE = False

    extra_delay = delay()

    m_menu = get_key("m_menu")
    weapon_menu = get_key("weapon_menu")
    no_weapon = get_key("no_weapon")
    shotgun_weapon = get_key("shotgun_weapon")
    rpg_weapon = get_key("rpg_weapon")
    c4_weapon = get_key("c4_weapon")
    pistol_weapon = get_key("pistol_weapon")
    sniper_weapon = get_key("sniper_weapon")


    """主运行函数，支持复用 mss 实例"""
    quick_press(m_menu)
    time.sleep(0.3)  # 可根据实际情况调整

    is_ceo = ka_ceo.judge(m_ROI,350,400,sct)

    if is_ceo:
        quick_press("enter")
        for _ in range(3):
            force_scroll(1)
            time.sleep(0.05+extra_delay)
        quick_press("enter")
        for _ in range(1):
            force_scroll(-1)
            time.sleep(0.05+extra_delay)
        quick_press("enter")

        pydirectinput.PAUSE = 0.1

    else:

        for _ in range(1):
            force_scroll(-1)
            time.sleep(0.05+extra_delay)
        for _ in range(3):
            quick_press("enter")

        quick_press(m_menu)

        quick_press("enter")
        for _ in range(3):
            force_scroll(1)
            time.sleep(0.05+extra_delay)
        quick_press("enter")
        for _ in range(1):
            force_scroll(-1)
            time.sleep(0.05+extra_delay)
        quick_press("enter")

        pydirectinput.PAUSE = 0.1


def buy_bullet(sct=None):
    # 设置输入库的防卡死和延迟
    pydirectinput.PAUSE = 0.02
    pydirectinput.FAILSAFE = False

    extra_delay = delay()

    m_menu = get_key("m_menu")
    weapon_menu = get_key("weapon_menu")
    no_weapon = get_key("no_weapon")
    shotgun_weapon = get_key("shotgun_weapon")
    rpg_weapon = get_key("rpg_weapon")
    c4_weapon = get_key("c4_weapon")
    pistol_weapon = get_key("pistol_weapon")
    sniper_weapon = get_key("sniper_weapon")

    quick_press(no_weapon)
    quick_press(weapon_menu)
    quick_press(m_menu)
    time.sleep(0.3)  # 等待M菜单完全弹出

    for _ in range(7):
        force_scroll(1)
        time.sleep(0.05 + extra_delay)

    time.sleep(0.05 + extra_delay)
    quick_press("enter")
    time.sleep(0.05 + extra_delay)  # 等待子菜单渲染
    quick_press("enter")
    time.sleep(0.05 + extra_delay)  # 等待"购买弹药"菜单完全显示

    quick_press("left")
    quick_press("down")
    quick_press("enter")
    quick_press(m_menu)

    pydirectinput.keyDown(weapon_menu)
    pydirectinput.moveRel(-100, 0, relative=True)
    pydirectinput.keyUp(weapon_menu)


#连发左轮
def revolver():

    # 设置输入库的防卡死和延迟
    pydirectinput.PAUSE = 0.02
    pydirectinput.FAILSAFE = False

    m_menu = get_key("m_menu")
    weapon_menu = get_key("weapon_menu")
    no_weapon = get_key("no_weapon")
    shotgun_weapon = get_key("shotgun_weapon")
    rpg_weapon = get_key("rpg_weapon")
    c4_weapon = get_key("c4_weapon")
    pistol_weapon = get_key("pistol_weapon")
    sniper_weapon = get_key("sniper_weapon")


    pydirectinput.keyDown("shift")
    time.sleep(0.03)
    pydirectinput.keyUp("shift")

    pydirectinput.keyDown(shotgun_weapon)
    time.sleep(0.03)
    pydirectinput.keyUp(shotgun_weapon)
    time.sleep(0.03)
    pydirectinput.keyDown(pistol_weapon)
    time.sleep(0.03)
    pydirectinput.keyUp(pistol_weapon)
    time.sleep(0.03)
    pydirectinput.keyDown(no_weapon)
    time.sleep(0.03)
    pydirectinput.keyUp(no_weapon)
    time.sleep(0.03)
    pydirectinput.keyDown(pistol_weapon)
    time.sleep(0.03)
    pydirectinput.keyUp(pistol_weapon)
    time.sleep(0.03)

    pydirectinput.keyDown(weapon_menu)
    time.sleep(0.03)
    pydirectinput.keyUp(weapon_menu)

    '''
    time.sleep(0.05)
    pydirectinput.keyDown("c")
    time.sleep(2)
    pydirectinput.mouseDown()
    pydirectinput.mouseUp()
    pydirectinput.keyUp("c")
    '''
    pydirectinput.PAUSE = 0.1

#连发rpg
def rpg():
    # 设置输入库的防卡死和延迟
    pydirectinput.PAUSE = 0.02
    pydirectinput.FAILSAFE = False

    m_menu = get_key("m_menu")
    weapon_menu = get_key("weapon_menu")
    no_weapon = get_key("no_weapon")
    shotgun_weapon = get_key("shotgun_weapon")
    rpg_weapon = get_key("rpg_weapon")
    c4_weapon = get_key("c4_weapon")
    pistol_weapon = get_key("pistol_weapon")
    sniper_weapon = get_key("sniper_weapon")


    for i in range(_get_times("rpg")):


        pydirectinput.keyDown(c4_weapon)
        #time.sleep(0.05)
        pydirectinput.keyUp(c4_weapon)
        time.sleep(0.05)
        pydirectinput.keyDown(rpg_weapon)
        #time.sleep(0.05)
        pydirectinput.keyUp(rpg_weapon)
        time.sleep(0.05)
        pydirectinput.mouseDown()
        time.sleep(0.35)
        pydirectinput.mouseUp()
        time.sleep(0.1)

#连发狙
def sniper():
    # 设置输入库的防卡死和延迟
    pydirectinput.PAUSE = 0.02
    pydirectinput.FAILSAFE = False

    m_menu = get_key("m_menu")
    weapon_menu = get_key("weapon_menu")
    no_weapon = get_key("no_weapon")
    shotgun_weapon = get_key("shotgun_weapon")
    rpg_weapon = get_key("rpg_weapon")
    c4_weapon = get_key("c4_weapon")
    pistol_weapon = get_key("pistol_weapon")
    sniper_weapon = get_key("sniper_weapon")

    for i in range(_get_times("shot")):


        pydirectinput.keyDown(c4_weapon)
        # time.sleep(0.1)
        pydirectinput.keyUp(c4_weapon)
        time.sleep(0.05)
        pydirectinput.keyDown(sniper_weapon)
        # time.sleep(0.1)
        pydirectinput.keyUp(sniper_weapon)
        time.sleep(0.3)
        pydirectinput.mouseDown(button="right")
        pydirectinput.mouseDown()
        time.sleep(0.3)
        pydirectinput.mouseUp()
        time.sleep(0.1)

#热感
def thermal():
    """通用流程"""

    m_menu = get_key("m_menu")
    weapon_menu = get_key("weapon_menu")
    no_weapon = get_key("no_weapon")
    shotgun_weapon = get_key("shotgun_weapon")
    rpg_weapon = get_key("rpg_weapon")
    c4_weapon = get_key("c4_weapon")
    pistol_weapon = get_key("pistol_weapon")
    sniper_weapon = get_key("sniper_weapon")
    extra_delay = delay()
    #print(extra_delay)

    pydirectinput.PAUSE = 0.02
    quick_press(m_menu)
    time.sleep(0.5 + extra_delay)
    for _ in range(6):
        force_scroll(1)
        time.sleep(0.05 + extra_delay)
    quick_press("enter")
    for _ in range(1):
        force_scroll(-1)
        time.sleep(0.05 + extra_delay)
    quick_press("enter")
    quick_press("space")
    quick_press(m_menu)

    pydirectinput.PAUSE = 0.1

#换衣服
def cloth():
    """通用流程"""

    m_menu = get_key("m_menu")
    weapon_menu = get_key("weapon_menu")
    no_weapon = get_key("no_weapon")
    shotgun_weapon = get_key("shotgun_weapon")
    rpg_weapon = get_key("rpg_weapon")
    c4_weapon = get_key("c4_weapon")
    pistol_weapon = get_key("pistol_weapon")
    sniper_weapon = get_key("sniper_weapon")

    extra_delay = delay()
    #print(extra_delay)

    pydirectinput.PAUSE = 0.02
    quick_press(m_menu)
    time.sleep(0.5 + extra_delay)
    for _ in range(6):
        force_scroll(1)
        time.sleep(0.05 + extra_delay)
    quick_press("enter")

    for _ in range(3):
        force_scroll(-1)
        time.sleep(0.05 + extra_delay)

    for _ in range(_get_times("cloth")):
        quick_press("left")
        time.sleep(0.05 + extra_delay)

    quick_press("enter")
    quick_press("space")
    quick_press(m_menu)

    pydirectinput.PAUSE = 0.1




def flight_thermal(sct=None):
    """通用流程"""

    m_menu = get_key("m_menu")
    weapon_menu = get_key("weapon_menu")
    no_weapon = get_key("no_weapon")
    shotgun_weapon = get_key("shotgun_weapon")
    rpg_weapon = get_key("rpg_weapon")
    c4_weapon = get_key("c4_weapon")
    pistol_weapon = get_key("pistol_weapon")
    sniper_weapon = get_key("sniper_weapon")

    extra_delay = delay()
    #print(extra_delay)

    # 设置输入库的防卡死和延迟
    pydirectinput.PAUSE = 0.02
    pydirectinput.FAILSAFE = False

    """主运行函数，支持复用 mss 实例"""
    quick_press(m_menu)
    time.sleep(0.3)  # 可根据实际情况调整

    is_ceo = ka_ceo.judge(m_ROI,350,400,sct)

    if not is_ceo:

        for _ in range(10):
            force_scroll(1)
            time.sleep(0.05 + extra_delay)

        quick_press("enter")
        quick_press("enter")
        quick_press("enter")
        quick_press(m_menu)

    time.sleep(0.5 + extra_delay)

    #换ceo风格
    for _ in range(2):
        quick_press("enter")
        force_scroll(-1)
        time.sleep(0.05 + extra_delay)
    quick_press("enter")
    quick_press("left")
    quick_press("right")
    quick_press(m_menu)

    #开热感
    quick_press(m_menu)
    time.sleep(0.5 + extra_delay)
    for _ in range(6):
        force_scroll(1)
        time.sleep(0.05 + extra_delay)
    quick_press("enter")
    for _ in range(1):
        force_scroll(-1)
        time.sleep(0.05 + extra_delay)
    quick_press("enter")
    quick_press("space")
    quick_press(m_menu)

    pydirectinput.PAUSE = 0.1


def ghost(sct=None):

    m_menu = get_key("m_menu")
    weapon_menu = get_key("weapon_menu")
    no_weapon = get_key("no_weapon")
    shotgun_weapon = get_key("shotgun_weapon")
    rpg_weapon = get_key("rpg_weapon")
    c4_weapon = get_key("c4_weapon")
    pistol_weapon = get_key("pistol_weapon")
    sniper_weapon = get_key("sniper_weapon")

    # 设置输入库的防卡死和延迟
    pydirectinput.PAUSE = 0.02
    pydirectinput.FAILSAFE = False

    extra_delay = delay()


    """主运行函数，支持复用 mss 实例"""
    quick_press(m_menu)
    time.sleep(0.3)  # 可根据实际情况调整

    is_ceo = ka_ceo.judge(m_ROI,350,400,sct)

    if is_ceo:
        quick_press("enter")
        for _ in range(3):
            force_scroll(1)
            time.sleep(0.05+extra_delay)
        quick_press("enter")
        for _ in range(3):
            force_scroll(1)
            time.sleep(0.05+extra_delay)
        quick_press("enter")

        pydirectinput.PAUSE = 0.1

    else:

        for _ in range(1):
            force_scroll(-1)
            time.sleep(0.05+extra_delay)
        for _ in range(3):
            quick_press("enter")

        quick_press(m_menu)

        quick_press("enter")
        for _ in range(3):
            force_scroll(1)
            time.sleep(0.05+extra_delay)
        quick_press("enter")
        for _ in range(3):
            force_scroll(1)
            time.sleep(0.05+extra_delay)
        quick_press("enter")

        pydirectinput.PAUSE = 0.1

def _run(key):
    """通用流程"""

    m_menu = get_key("m_menu")
    weapon_menu = get_key("weapon_menu")
    no_weapon = get_key("no_weapon")
    shotgun_weapon = get_key("shotgun_weapon")
    rpg_weapon = get_key("rpg_weapon")
    c4_weapon = get_key("c4_weapon")
    pistol_weapon = get_key("pistol_weapon")
    sniper_weapon = get_key("sniper_weapon")

    extra_delay = delay()
    #print(extra_delay)

    pydirectinput.PAUSE = 0.02
    quick_press(m_menu)
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
    quick_press(m_menu)
    pydirectinput.PAUSE = 0.1

def eat_snack(): _run("snack")