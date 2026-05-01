
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
    settings_window.geometry("600x700")
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
    headers = ["热键", "名称", "点击修改代码", "启用"]
    for col, text in enumerate(headers):
        lbl = ctk.CTkLabel(
            settings_window,
            text=text,
            font=("Microsoft YaHei UI", 18, "bold"),
            text_color="#3B8ED0"
        )
        lbl.grid(row=0, column=col, padx=15, pady=(15, 10), sticky="w")

    # 三个联系人配置
    contact_ids = ["script_0","script_1","script_2","script_3","script_4","script_5","script_6","script_7","script_8","script_9"]

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
        # ==================== 修改：第三列改为编辑按钮 ====================
        btn_edit = ctk.CTkButton(
            settings_window,
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
        # =================================================================

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
        text="修改名称后，按 Enter 键或点击空白处保存",
        font=("Microsoft YaHei UI", 20, "bold"),
        text_color="#888888"
    )
    lbl_tip.grid(row=12, column=0, columnspan=4, pady=(15, 10))

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
    editor_win.geometry("650x600")
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

    # 核心文本框 (使用等宽字体，适合写代码)
    textbox = ctk.CTkTextbox(
        editor_win,
        font=("Consolas", 14),  # 等宽字体
        fg_color="#FDFDFD",
        text_color="#333333",
        border_width=2,
        border_color="#CCCCCC",
        wrap="none",  # 关闭自动换行，代码编辑器通常不自动换行
        spacing3=2  # 设置一点行间距，更好看
    )
    textbox.pack(padx=15, pady=10, fill="both", expand=True)

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
