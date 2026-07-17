
import pydirectinput
import time

import  ctypes
from config_manager import ConfigManager

def show_settings_ui(parent_window):
    """显示电话联系人设置界面（四列：热键 | 名字 | 次数 | 开关）"""
    import customtkinter as ctk

    # 创建置顶设置窗口
    settings_window = ctk.CTkToplevel(parent_window)
    settings_window.title("电话联系人设置")
    settings_window.geometry("600x500")
    settings_window.resizable(False, False)
    settings_window.transient(parent_window)  # 跟随父窗口
    settings_window.grab_set()  # 模态窗口

    # 获取配置管理器（依赖父窗口传入 config）
    config = parent_window.config

    # 配置网格（四列等比）
    settings_window.grid_columnconfigure(0, weight=1)  # 热键
    settings_window.grid_columnconfigure(1, weight=2)  # 名字（更宽一些）
    settings_window.grid_columnconfigure(2, weight=1)  # 次数
    settings_window.grid_columnconfigure(3, weight=1)  # 开关

    # 表头
    headers = ["热键", "联系人", "方向键“↑”次数", "启用"]
    for col, text in enumerate(headers):
        lbl = ctk.CTkLabel(
            settings_window,
            text=text,
            font=("Microsoft YaHei UI", 18, "bold"),
            text_color="#3B8ED0"
        )
        lbl.grid(row=0, column=col, padx=15, pady=(15, 10), sticky="w")

    # 三个联系人配置
    contact_ids = ["ji_gong", "bao_xian", "lester","custom_1","custom_2","custom_3"]

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

    # ==================== 新增：更新名字的回调函数 ====================
    def update_name(contact_id, entry_widget):
        """失去焦点或回车时保存联系人名字"""
        try:
            value = entry_widget.get().strip()
            if value:  # 确保名字不为空
                with config.lock:
                    config.data[contact_id]['name'] = value
                config.save_config()
                print(f"[PhoneCall] {contact_id} 名字更新为: {value}")
        except Exception as e:
            print(f"[PhoneCall] 更新名字失败: {e}")
    # =================================================================

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

    # 创建多行数据
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
        btn_key.configure(command=lambda cid=contact_id, btn=btn_key: start_recording(cid, btn))
        btn_key.grid(row=row_idx, column=0, padx=5, pady=8, sticky="w")

        # ==================== 修改：将 Label 改为 Entry ====================
        # 第二列：名字（可编辑输入框）
        entry_name = ctk.CTkEntry(
            settings_window,
            font=("Microsoft YaHei UI", 18, "bold"),
            height=35,
            border_width=2,
            border_color="#CCCCCC",
            fg_color="white",
            text_color="black"
        )
        entry_name.insert(0, str(data.get('name', contact_id)))
        entry_name.grid(row=row_idx, column=1, padx=5, pady=8, sticky="ew")

        # 绑定保存事件（失焦或回车）
        entry_name.bind('<FocusOut>', lambda e, cid=contact_id, ent=entry_name: update_name(cid, ent))
        entry_name.bind('<Return>', lambda e, cid=contact_id, ent=entry_name: update_name(cid, ent))
        # =================================================================

        # 第三列：次数（可编辑输入框）
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
            width=100,
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
        switch.grid(row=row_idx, column=3, padx=5, pady=8, sticky="e")

    # 底部提示文字
    lbl_tip = ctk.CTkLabel(
        settings_window,
        text="修改联系人名字或次数后，按 Enter 键或点击空白处保存",
        font=("Microsoft YaHei UI", 20, "bold"),
        text_color="#888888"
    )
    lbl_tip.grid(row=7, column=0, columnspan=4, pady=(15, 10))



#--------------执行部分---------------------------





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
    quick_press("up")
    time.sleep(0.5 + extra_delay)
    force_scroll(1)
    time.sleep(0.05 + extra_delay)
    force_scroll(1)
    quick_press("enter")
    time.sleep(0.05 + extra_delay)
    for _ in range(_get_times(key)):
        force_scroll(1)
        time.sleep(0.05 + extra_delay)
    quick_press("enter")
    pydirectinput.PAUSE = 0.1


# 保持原有调用接口
def ji_gong_phone(): _run("ji_gong")


def bao_xian_phone(): _run("bao_xian")


def lester_phone(): _run("lester")

def custom_1_phone():_run("custom_1")

def custom_2_phone():_run("custom_2")

def custom_3_phone():_run("custom_3")