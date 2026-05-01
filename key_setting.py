
def show_settings_ui(parent_window):
    """显示电话联系人设置界面（四列：热键 | 名字 | 次数 | 开关）"""
    import customtkinter as ctk



    # 创建置顶设置窗口
    settings_window = ctk.CTkToplevel(parent_window)
    settings_window.title("按键设置")
    settings_window.geometry("400x500")
    settings_window.resizable(False, False)
    settings_window.transient(parent_window)  # 跟随父窗口
    settings_window.grab_set()  # 模态窗口

    # 获取配置管理器（依赖父窗口传入 config）
    config = parent_window.config

    # 配置网格（四列等比）

    settings_window.grid_columnconfigure(0, weight=1)  # 热键
    settings_window.grid_columnconfigure(1, weight=1)  # 名字（更宽一些）





    # 表头
    headers = ["热键", "功能"]
    for col, text in enumerate(headers):
        lbl = ctk.CTkLabel(
            settings_window,
            text=text,
            font=("Microsoft YaHei UI", 18, "bold"),
            text_color="#3B8ED0"
        )
        lbl.grid(row=0, column=col, padx=15, pady=(15, 10), sticky="w")

    # 配置
    # 配置
    contact_ids = ["m_menu", "weapon_menu", "no_weapon", "shotgun_weapon", "rpg_weapon", "c4_weapon", "pistol_weapon","sniper_weapon"]


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



    # 创建行数据
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





