
import pydirectinput
import time

import  ctypes
from config_manager import ConfigManager
import customtkinter as ctk


def show_settings_ui(parent_window):
    """显示电话联系人设置界面（四列：热键 | 名字 | 次数 | 开关）"""


    # 创建置顶设置窗口
    settings_window = ctk.CTkToplevel(parent_window)
    settings_window.title("自定义宏设置")
    settings_window.geometry("600x750")
    settings_window.resizable(False, False)
    settings_window.transient(parent_window)  # 跟随父窗口
    settings_window.grab_set()  # 模态窗口

    # 获取配置管理器（依赖父窗口传入 config）
    config = parent_window.config

    contact_ids_all = ["script_0","script_1","script_2","script_3","script_4","script_5","script_6","script_7","script_8","script_9",
                       "script_10","script_11","script_12","script_13","script_14","script_15","script_16","script_17","script_18","script_19"]

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

    # ==================== 删除 update_times 函数 ====================

    # ==================== 新增：打开编辑器的回调函数 ====================
    def open_macro_editor(contact_id):
        """打开宏编辑子窗口"""
        # 这里导入宏编辑器函数（假设我们等下写在同一个文件或另一个文件）

        show_macro_editor_window(settings_window, contact_id, config)
    # =================================================================

    def toggle_switch(contact_id, switch_widget):
        """开关切换回调"""
        is_on = bool(switch_widget.get())
        config.update_switch_state(contact_id, is_on)
        print(f"[PhoneCall] {contact_id} 启用状态: {is_on}")

    def _render_tab_rows(tab_frame, ids):
        """在标签页内渲染表头 + 数据行"""
        tab_frame.grid_columnconfigure(0, weight=1)
        tab_frame.grid_columnconfigure(1, weight=2)
        tab_frame.grid_columnconfigure(2, weight=1)
        tab_frame.grid_columnconfigure(3, weight=1)

        headers = ["热键", "名称", "点击修改代码", "启用"]
        for col, text in enumerate(headers):
            lbl = ctk.CTkLabel(
                tab_frame,
                text=text,
                font=("Microsoft YaHei UI", 18, "bold"),
                text_color="#3B8ED0"
            )
            lbl.grid(row=0, column=col, padx=15, pady=(15, 10), sticky="w")

        for row_idx, contact_id in enumerate(ids, start=1):
            data = config.get_function_data(contact_id)
            if not data:
                continue

            btn_key = ctk.CTkButton(
                tab_frame,
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

            entry_name = ctk.CTkEntry(
                tab_frame,
                font=("Microsoft YaHei UI", 18, "bold"),
                height=35,
                border_width=2,
                border_color="#CCCCCC",
                fg_color="white",
                text_color="black"
            )
            entry_name.insert(0, str(data.get('name', contact_id)))
            entry_name.grid(row=row_idx, column=1, padx=5, pady=8, sticky="ew")
            entry_name.bind('<FocusOut>', lambda e, cid=contact_id, ent=entry_name: update_name(cid, ent))
            entry_name.bind('<Return>', lambda e, cid=contact_id, ent=entry_name: update_name(cid, ent))

            btn_edit = ctk.CTkButton(
                tab_frame,
                text="编辑",
                font=("Microsoft YaHei UI", 18, "bold"),
                width=100,
                height=35,
                corner_radius=5,
                fg_color="#3B8ED0",
                hover_color="#2B6EA8"
            )
            btn_edit.configure(command=lambda cid=contact_id: open_macro_editor(cid))
            btn_edit.grid(row=row_idx, column=2, padx=5, pady=8)

            switch = ctk.CTkSwitch(
                tab_frame,
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

    # 标签页控件
    tabview = ctk.CTkTabview(
        settings_window,
        corner_radius=8,
        fg_color="transparent",
        segmented_button_fg_color="#F0F0F0",
        segmented_button_selected_color="#3B8ED0",
        segmented_button_selected_hover_color="#2B6EA8",
        segmented_button_unselected_color="#D0D0D0",
        segmented_button_unselected_hover_color="#C0C0C0",
        text_color="black",
        text_color_disabled="#888888"
    )
    tabview.grid(row=0, column=0, columnspan=4, sticky="nsew", padx=10, pady=(5, 5))
    settings_window.grid_rowconfigure(0, weight=1)
    settings_window.grid_columnconfigure(0, weight=1)
    settings_window.grid_columnconfigure(1, weight=1)
    settings_window.grid_columnconfigure(2, weight=1)
    settings_window.grid_columnconfigure(3, weight=1)

    tab1 = tabview.add("第1页  (1-10)")
    tab2 = tabview.add("第2页 (11-20)")

    tabview._segmented_button.configure(
        font=("Microsoft YaHei UI", 18, "bold"),
        height=40
    )

    _render_tab_rows(tab1, contact_ids_all[:10])
    _render_tab_rows(tab2, contact_ids_all[10:])

    lbl_tip = ctk.CTkLabel(
        settings_window,
        text="修改名称后，按 Enter 键或点击空白处保存",
        font=("Microsoft YaHei UI", 20, "bold"),
        text_color="#888888"
    )
    lbl_tip.grid(row=1, column=0, columnspan=4, pady=(15, 10))

#-----------------小窗口-----------------------------



def show_macro_editor_window(parent_window, script_id, config):
    """纯代码文本编辑器子窗口"""

    # 获取当前数据
    macro_data = config.get_function_data(script_id)
    macro_name = macro_data.get('name', script_id)
    raw_code = macro_data.get('code', "")  # 直接读取字符串

    # 创建子窗口
    editor_win = ctk.CTkToplevel(parent_window)
    editor_win.title(f"编辑代码 - {macro_name}")
    editor_win.geometry("900x600")
    editor_win.resizable(True, True)
    editor_win.transient(parent_window)
    editor_win.grab_set()

    # 顶部提示
    lbl_tip = ctk.CTkLabel(
        editor_win,
        text="直接编写代码。按 Tab 键自动缩进，Shift+Tab 减少缩进。",
        font=("Microsoft YaHei UI", 12),
        text_color="#888888"
    )
    lbl_tip.pack(padx=15, pady=(15, 5), anchor="w")

    # 主内容区：左右分栏
    main_frame = ctk.CTkFrame(editor_win, fg_color="transparent")
    main_frame.pack(padx=15, pady=10, fill="both", expand=True)
    main_frame.grid_columnconfigure(0, weight=3)
    main_frame.grid_columnconfigure(1, weight=1)
    main_frame.grid_rowconfigure(0, weight=1)

    # 左侧：代码编辑器 (使用等宽字体，适合写代码)
    textbox = ctk.CTkTextbox(
        main_frame,
        font=("Microsoft YaHei UI", 18, "bold"),  # 等宽字体
        fg_color="#FDFDFD",
        text_color="#333333",
        border_width=2,
        border_color="#CCCCCC",
        wrap="none",  # 关闭自动换行，代码编辑器通常不自动换行
        spacing3=2  # 设置一点行间距，更好看
    )
    textbox.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

    # 右侧：固定模板面板
    template_frame = ctk.CTkScrollableFrame(
        main_frame,
        label_text="代码模板",
        label_font=("Microsoft YaHei UI", 18, "bold"),
        label_fg_color="#3B8ED0",
        fg_color="#F0F4F8",
        width=220
    )
    template_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

    def insert_template(code):
        textbox.insert("insert", code)
        textbox.focus_set()

    templates = [
        ("按键间隔", "pydirectinput.PAUSE = 0.02"),

        ("按键按下", "pydirectinput.keyDown('')"),
        ("按键抬起", "pydirectinput.keyUp('')"),
        ("延迟等待", "time.sleep(1.0)"),
        ("长按", "pydirectinput.keyDown('shift')\ntime.sleep(1.0)\npydirectinput.keyUp('shift')"),
        ("按键点击", "pydirectinput.press('')"),
        ("鼠标相对移动", "pydirectinput.moveRel(x, y, relative=True)"),
        ("鼠标点击", "pydirectinput.click()"),

        ("循环N次", "for i in range(10):\n    pass"),

        ("鼠标按下", "pydirectinput.mouseDown(button='left')"),
        ("鼠标释放", "pydirectinput.mouseUp(button='left')"),
        ("右键点击", "pydirectinput.rightClick()"),
        ("双击", "pydirectinput.doubleClick()"),
    ]

    for tpl_label, tpl_code in templates:
        btn = ctk.CTkButton(
            template_frame,
            text=tpl_label,
            font=("Microsoft YaHei UI", 18,"bold"),
            height=32,
            corner_radius=5,
            fg_color="#3B8ED0",
            hover_color="#2B6EA8",
            command=lambda c=tpl_code: insert_template(c)
        )
        btn.pack(padx=10, pady=3, fill="x")

    # ================= 核心逻辑：解决 Python 缩进问题 =================
    def handle_tab(event):
        """拦截 Tab 键，插入 4 个空格而不是跳转焦点"""
        textbox.insert("insert", "    ")  # 插入4个空格
        return "break"  # "break" 会阻止组件的默认行为（默认行为是切走焦点）

    def handle_shift_tab(event):
        """拦截 Shift+Tab 键，删除前面的缩进"""
        # 获取当前光标所在行的开头内容
        line_start = textbox.index("insert linestart")
        current_pos = textbox.index("insert")
        line_text = textbox.get(line_start, current_pos)

        if line_text.startswith("    "):
            # 如果有4个空格，删掉它们
            textbox.delete(current_pos, f"{current_pos}-4c")
        elif line_text.startswith("\t"):
            # 如果是制表符，删掉它
            textbox.delete(current_pos, f"{current_pos}-1c")

        return "break"

    # 绑定按键事件
    textbox.bind("<Tab>", handle_tab)
    textbox.bind("<Shift-Tab>", handle_shift_tab)
    # ================================================================

    # 初始化文本框内容
    if raw_code:
        textbox.insert("1.0", raw_code)

    # 获取焦点并将光标放到开头
    textbox.focus_set()
    textbox.mark_set("insert", "1.0")

    # ================= 保存逻辑：原样存取 =================
    def save_and_close():
        # 获取文本框里的所有内容（原封不动）
        code_content = textbox.get("1.0", "end")

        # 去除末尾可能多出来的一个换行符（记事本通病）
        if code_content.endswith("\n"):
            code_content = code_content[:-1]

        # 直接把字符串存进 config 的 code 字段里
        config.update_config_item(f"{script_id}.code", code_content)

        print(f"[宏编辑器] {macro_name} 代码已保存。")
        editor_win.destroy()

    # =======================================================

    # 底部按钮
    btn_frame = ctk.CTkFrame(editor_win, fg_color="transparent")
    btn_frame.pack(pady=15, fill="x", padx=15)

    btn_cancel = ctk.CTkButton(
        btn_frame, text="取消", width=100, height=40,
        fg_color="#888888", hover_color="#666666",
        command=editor_win.destroy
    )
    btn_cancel.pack(side="left")

    btn_save = ctk.CTkButton(
        btn_frame, text="保存", width=100, height=40,
        fg_color="#4CC768", hover_color="#3BA855",
        command=save_and_close
    )
    btn_save.pack(side="right")

#--------------执行部分---------------------------

def run(script_id):
    # 内部直接拿单例，不需要外部传参
    config = ConfigManager()
    code_str = config.get_function_data(script_id).get("code", "")
    if code_str:
        exec(code_str)

def run_script_0(): run("script_0")
def run_script_1(): run("script_1")
def run_script_2(): run("script_2")
def run_script_3(): run("script_3")
def run_script_4(): run("script_4")
def run_script_5(): run("script_5")
def run_script_6(): run("script_6")
def run_script_7(): run("script_7")
def run_script_8(): run("script_8")
def run_script_9(): run("script_9")
def run_script_10(): run("script_10")
def run_script_11(): run("script_11")
def run_script_12(): run("script_12")
def run_script_13(): run("script_13")
def run_script_14(): run("script_14")
def run_script_15(): run("script_15")
def run_script_16(): run("script_16")
def run_script_17(): run("script_17")
def run_script_18(): run("script_18")
def run_script_19(): run("script_19")
