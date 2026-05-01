# gui_app.py
import customtkinter as ctk


# [新增] 导入 ScriptExecutor，用于调用打开窗口的方法
from game_scripts import ScriptExecutor


# 设置外观
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


class GTAUnlockApp(ctk.CTk):
    def __init__(self, config_manager):
        super().__init__()

        self.config = config_manager

        # 窗口设置
        self.title("GTA开锁助手")
        self.geometry("800x600")
        self.resizable(False, False)

        # ==========================================
        # [修复 Bug]: 拦截 F10 键的系统默认行为，防止 GUI 主循环被阻塞卡死
        self.bind_all("<Key-F10>", lambda event: "break")
        # ==========================================

        # 网格配置
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)


        # 动态存储控件引用，用于后续更新
        self.ui_elements = {}  # { "casino": {"btn": obj, "switch": obj}, ... }

        # 从 Config 初始化界面
        data = self.config.get_all_data()

        # 这里的顺序决定显示顺序
        func_list = ["ka_cha_chuan","casino","cha_chuan_1","security","cha_chuan_2", "cayo", "refresh_cha_chuan_bot","photo","nat_down","sudden_stop","phone","mk2","fight","ka_ceo","low_fps","custom_script","hang_up_and_key_setting","update","instruction"]


        for index, func_id in enumerate(func_list):
            if func_id in data:
                item = data[func_id]
                # [修改] 直接传入 index，不再需要 row_idx 或 col_offset
                self.create_row(index, func_id, item['name'], item['key'], item['enabled'])

        # 【在此处添加代码】
        # 计算下一行的索引 (原循环结束 index 为 14，行号为 14//2 = 7，所以新起一行应为 8)
        bottom_row = (len(func_list) + 1) // 2

        bottom_label = ctk.CTkLabel(
            self,
            text="第一次使用请先点击，使用说明，以及，按键设置",
            font=("Microsoft YaHei", 20, "bold"),

        )
        # 跨越两列显示，置于底部
        bottom_label.grid(row=bottom_row, column=0, columnspan=2, pady=10, sticky="s")

        # 启动 GUI 的定时轮询器 (每100ms检查一次状态)
        self.check_status_loop()



    # [修改] 参数改为接收 index
    def create_row(self, index, func_id, desc_text, key_text, is_enabled):
            """创建界面行（容器封装版）"""

            # 1. 创建容器 Frame (背景透明)
            container = ctk.CTkFrame(self, fg_color="transparent")
            # 核心布局算法：行=整除2，列=取余2
            container.grid(row=index // 2, column=index % 2, sticky="ew", padx=10, pady=5)

            # 2. 按键按钮 (父对象改为 container, 使用 pack)
            btn_key = ctk.CTkButton(
                container,  # 父对象变了
                text=key_text,
                font=("Microsoft YaHei UI", 18, "bold"),
                text_color="black",
                fg_color="white",
                hover_color="#F0F0F0",
                border_width=2,
                border_color="#3B8ED0",
                width=140,
                height=45,
                corner_radius=0
            )
            if func_id in ["low_fps", "instruction","phone","mk2","update","fight","hang_up_and_key_setting","custom_script"]:
                btn_key.configure(text="设置项", state="disabled", fg_color="#E0E0E0")
            else:
                btn_key.configure(command=lambda f=func_id: self.request_recording(f))

            btn_key.pack(side="left", padx=5)  # 使用 pack 自动排列

            # 3. 描述文字 (父对象改为 container, 使用 pack)
            lbl_desc = ctk.CTkLabel(
                container,  # 父对象变了
                text=desc_text,
                font=("Microsoft YaHei UI", 16, "bold"),
                text_color="#333333",
                anchor="w",
                cursor="hand2"
            )
            lbl_desc.bind("<Button-1>", lambda event, f=func_id: ScriptExecutor.open_settings_window(f, self))

            # 让文字占据中间剩余空间
            lbl_desc.pack(side="left", padx=10, fill="x", expand=True)

            # 4. 开关 (父对象改为 container, 使用 pack)
            switch = ctk.CTkSwitch(
                container,  # 父对象变了
                text="",
                width=60,
                height=30,
                progress_color="#4CC768",
                fg_color="#FF474C",
                button_color="white",
                onvalue=True,
                offvalue=False
            )
            if is_enabled:
                switch.select()
            else:
                switch.deselect()

            switch.configure(command=lambda f=func_id, s=switch: self.toggle_func(f, s))
            switch.pack(side="right", padx=5)  # 靠右排列

            # 保存引用 (保持不变)
            self.ui_elements[func_id] = {"btn": btn_key, "switch": switch}

    def request_recording(self, func_id):
        """GUI 请求开始录入"""
        # 如果已经在录入，忽略
        if self.config.is_recording:
            return

        # 1. 更新按钮外观
        btn = self.ui_elements[func_id]["btn"]
        btn.configure(text="请按键...", fg_color="#D6EAF8", text_color="#3B8ED0")
        print("开始录入")

        # 2. 通知数据层开启录入模式
        self.config.set_recording_mode(func_id)

    def toggle_func(self, func_id, switch_widget):
        """开关切换回调"""
        is_on = bool(switch_widget.get())
        self.config.update_switch_state(func_id, is_on)
        print(f"[GUI] {func_id} 开关状态更新为: {is_on}")

    def check_status_loop(self):
        """
        GUI 轮询循环
        职责：
        1. 检查录入是否结束
        2. 如果结束，刷新界面上的按键文字
        """
        # 如果当前没有在录入，但在 GUI 上还有"请按键"的状态，说明录入刚结束
        if not self.config.is_recording:
            self.refresh_ui_keys()

        # 继续轮询 (100ms)
        self.after(100, self.check_status_loop)

    def refresh_ui_keys(self):
        """从配置刷新所有按键显示（恢复白底黑字）"""
        data = self.config.get_all_data()
        for func_id, elements in self.ui_elements.items():
            if func_id in data:
                new_key = data[func_id]['key']
                btn = elements['btn']

                # 只有当文字不一致或颜色不对时才刷新，节省资源
                if btn.cget("text") != new_key or btn.cget("fg_color") != "white":
                    btn.configure(
                        text=new_key,
                        fg_color="white",
                        text_color="black"
                    )

