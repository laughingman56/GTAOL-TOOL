# update.py
import customtkinter as ctk
import json
import threading
import time
import os
import sys
import subprocess
from urllib import request, error
from config_manager import ConfigManager

# ================= 配置区域 =================
# 当前脚本的版本号（每次发布新版时修改这里）
CURRENT_VERSION = "1.1.4"

# Gitee 原始文件直链
VERSION_URL = "https://gitee.com/xmn56/gta-unlocking/raw/master/version.json"


# ===========================================

class UpdateManager:
    @staticmethod
    def check_update_logic(callback):
        try:
            url_with_time = f"{VERSION_URL}?t={int(time.time())}"
            # 添加 User-Agent 防止被部分服务器拦截
            req = request.Request(url_with_time, headers={'User-Agent': 'Mozilla/5.0'})

            with request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = response.read().decode('utf-8')
                    json_data = json.loads(data)
                    callback(True, json_data)
                else:
                    callback(False, f"服务器返回错误: {response.status}")

        except error.URLError:
            callback(False, "网络连接失败，请检查网络")
        except json.JSONDecodeError:
            callback(False, "版本文件解析失败")
        except Exception as e:
            callback(False, f"未知错误: {str(e)}")

    @staticmethod
    def compare_version(local_v, remote_v):
        try:
            l_parts = [int(x) for x in local_v.split('.')]
            r_parts = [int(x) for x in remote_v.split('.')]
            return r_parts > l_parts
        except:
            return False


def show_settings_ui(parent_window, remote_data=None):
    app = ctk.CTkToplevel(parent_window)
    app.title("检查更新")
    app.geometry("400x380")  # 稍微调高一点容纳进度条
    app.resizable(False, False)
    app.attributes("-topmost", True)

    info_frame = ctk.CTkFrame(app)
    info_frame.pack(pady=10, padx=20, fill="x")

    ctk.CTkLabel(info_frame, text=f"当前版本: {CURRENT_VERSION}", text_color="black",
                 font=("Microsoft YaHei UI", 18, "bold")).pack(pady=5)

    status_label = ctk.CTkLabel(info_frame, text="准备就绪", font=("Microsoft YaHei", 18))
    status_label.pack(pady=5)

    log_textbox = ctk.CTkTextbox(app, height=100)
    log_textbox.pack(pady=10, padx=20, fill="x")
    log_textbox.insert("0.0", "点击下方按钮开始检查...")
    log_textbox.configure(state="disabled")

    # === 新增：进度条区域 (默认隐藏) ===
    progress_frame = ctk.CTkFrame(app, fg_color="transparent")

    progress_bar = ctk.CTkProgressBar(progress_frame, width=300)
    progress_bar.pack(pady=5)
    progress_bar.set(0)

    progress_label = ctk.CTkLabel(progress_frame, text="0%", font=("Microsoft YaHei", 14, "bold"))
    progress_label.pack()

    # ==============================

    def update_log_text(text):
        log_textbox.configure(state="normal")
        log_textbox.delete("0.0", "end")
        log_textbox.insert("0.0", text)
        log_textbox.configure(state="disabled")

    # ====== 新增：下载与替换核心逻辑 ======
    def start_download(download_url):
        """点击立即更新后的事件"""
        check_btn.pack_forget()
        download_btn.pack_forget()
        progress_frame.pack(pady=10)  # 显示进度条
        status_label.configure(text="正在下载更新...", text_color="#3B8ED0")

        # 开启后台下载线程
        t = threading.Thread(target=download_and_replace_logic, args=(download_url,))
        t.daemon = True
        t.start()

    def update_progress_ui(percent):
        """在主线程更新进度条"""
        progress_bar.set(percent)
        progress_label.configure(text=f"{int(percent * 100)}%")

    def download_and_replace_logic(url):
            """后台下载与 BAT 替换逻辑 (BAT内强力清洗环境变量，彻底解决报错)"""
            import sys
            import os
            import time
            import subprocess
            from urllib import request

            # 安全验证：如果不是打包好的exe，拒绝替换
            if not getattr(sys, 'frozen', False):
                app.after(0, lambda: status_label.configure(text="请编译成exe后再测试！", text_color="red"))
                return

            current_exe = sys.executable
            exe_dir = os.path.dirname(current_exe)
            new_exe_temp = os.path.join(exe_dir, "update_download_temp.exe")
            bat_path = os.path.join(exe_dir, "update_helper.bat")
            exe_name = os.path.basename(current_exe)

            try:
                # 1. 发起下载请求
                req = request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with request.urlopen(req, timeout=10) as response:
                    total_size = int(response.info().get('Content-Length', -1))
                    downloaded = 0
                    with open(new_exe_temp, 'wb') as f:
                        while True:
                            chunk = response.read(8192)
                            if not chunk: break
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                app.after(0, update_progress_ui, downloaded / total_size)

                app.after(0, lambda: status_label.configure(text="下载完成，正在重启...", text_color="#2CC985"))
                time.sleep(0.5)

                # 2. 生成超级强化的 BAT 脚本
                # 逻辑：强力清空环境变量 -> 死循环尝试删除旧文件 -> 重命名 -> 启动 -> 自毁
                bat_content = f"""@echo off
    chcp 65001
    :: 等待1.5秒让旧程序有时间关闭
    timeout /t 1 /nobreak > NUL

    :: === 核心修复：在 CMD 层级彻底抹除 PyInstaller 的所有污染变量 ===
    set _MEIPASS2=
    set _PYI_APPLICATION_HOME_DIR=
    set _PYI_SPLASH_IPC=
    set _PYI_ARCHIVE_FILE=
    set TCL_LIBRARY=
    set TK_LIBRARY=
    :: ===============================================================

    :: 死循环删除旧程序 (防止被杀毒软件或系统短时间占用)
    :retry_del
    del /f /q "{current_exe}"
    if exist "{current_exe}" (
        timeout /t 1 /nobreak > NUL
        goto retry_del
    )

    :: 替换新程序并启动
    ren "{new_exe_temp}" "{exe_name}"
    start "" "{current_exe}"

    :: 删除脚本自身
    del "%~f0"
    """
                with open(bat_path, "w", encoding="utf-8") as f:
                    f.write(bat_content)

                # 3. 后台静默运行 BAT 脚本 (0x08000000 代表完全隐藏 CMD 黑框)
                subprocess.Popen([bat_path], creationflags=0x08000000)

                # 4. 瞬间强杀当前进程，立即释放文件句柄给 BAT 去删除
                os._exit(0)

            except Exception as e:
                if os.path.exists(new_exe_temp):
                    try:
                        os.remove(new_exe_temp)
                    except:
                        pass
                app.after(0, lambda: status_label.configure(text="更新失败！", text_color="red"))
                app.after(0, lambda: update_log_text(f"错误详情: {str(e)}"))
                app.after(0, lambda: progress_frame.pack_forget())
                app.after(0, lambda: download_btn.pack(pady=10, padx=20, fill="x"))
    # ==================================

    def on_check_finished(success, result):
        check_btn.configure(state="normal", text="重新检查")

        if not success:
            status_label.configure(text=result, text_color="red")
            update_log_text(f"检查失败: {result}")
            return

        remote_ver = result.get("version", "0.0.0")
        remote_log = result.get("log", "无更新日志")
        download_url = result.get("url", "https://gitee.com")
        #download_url = "https://gitee.com/xmn56/gta-unlocking/releases/download/%E5%A4%9A%E5%90%88%E4%B8%80%E5%BC%80%E9%94%81V1.0.4/%E5%A4%9A%E5%90%88%E4%B8%80%E5%BC%80%E9%94%81v1.0.4.exe"

        if UpdateManager.compare_version(CURRENT_VERSION, remote_ver):
            status_label.configure(text=f"发现新版本: {remote_ver} !", font=("Microsoft YaHei UI", 18, "bold"),
                                   text_color="#2CC985")
            update_log_text(remote_log)

            download_btn.configure(
                state="normal",
                text="立即更新",  # 改成应用内更新
                command=lambda: start_download(download_url)
            )
            download_btn.pack(pady=10, padx=20, fill="x")

        else:
            status_label.configure(text="当前已是最新版本", text_color="gray")
            update_log_text("暂无更新。")
            download_btn.pack_forget()

    def start_check():
        check_btn.configure(state="disabled", text="正在检查...")
        status_label.configure(text="正在连接服务器...", text_color="white")
        download_btn.pack_forget()
        progress_frame.pack_forget()  # 隐藏进度条

        t = threading.Thread(target=UpdateManager.check_update_logic, args=(on_check_finished,))
        t.daemon = True
        t.start()

    check_btn = ctk.CTkButton(app, text="检查更新", command=start_check, font=("Microsoft YaHei UI", 18, "bold"),
                              text_color="black", fg_color="white", hover_color="#F0F0F0", border_width=2,
                              border_color="#3B8ED0", width=100, height=40, corner_radius=0)
    check_btn.pack(pady=10, padx=20, fill="x")

    download_btn = ctk.CTkButton(app, text="立即更新", font=("Microsoft YaHei UI", 18, "bold"),
                                 text_color="black", fg_color="white", hover_color="#F0F0F0", border_width=2,
                                 border_color="#3B8ED0", width=100, height=40, corner_radius=0)

    if remote_data:
        on_check_finished(True, remote_data)
    else:
        app.after(500, start_check)


def check_update_on_startup(root_window):
    def callback(success, result):
        cfg = ConfigManager()
        data = cfg.get_all_data()
        if data.get("update", {}).get("enabled", False):
            if not root_window.winfo_exists():
                return
            if success:
                remote_ver = result.get("version", "0.0.0")
                if UpdateManager.compare_version(CURRENT_VERSION, remote_ver):
                    root_window.after(0, lambda: show_settings_ui(root_window, result))

    t = threading.Thread(target=UpdateManager.check_update_logic, args=(callback,))
    t.daemon = True
    t.start()