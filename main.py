# main.py
import sys
import os
import threading
import  ctypes
# 确保安装了相关库: pip install customtkinter pywin32
import time
from config_manager import ConfigManager
from hotkey_listener import Win32HotkeyListener
from gui_app import GTAUnlockApp
import  refresh_cha_chuan_jobtp2
# === 新增导入 ===
from update import check_update_on_startup

import ka_085

# ===== 新增导入 =====
from hang_up import AntiIdleManager
# ===================
def run_as_admin():
    """

    如果当前进程不是管理员，则重新以管理员权限运行
    """
    try:
        # 检查是否已是管理员
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except:
        is_admin = False

    if not is_admin:
        # 重新以管理员权限运行当前脚本
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
        except Exception as e:
            print(f"请求管理员权限失败: {e}")
        sys.exit(0)  # 退出当前非管理员进程



# ============================================
# === 新增：防多开相关逻辑 ===
ERROR_ALREADY_EXISTS = 183
global_mutex = None  # 必须使用全局变量保存句柄，防止被 Python 垃圾回收机制清理


def check_single_instance():
    """
    检查程序是否已经运行，如果是则退出，并尝试唤醒已有窗口
    """
    global global_mutex
    # 互斥体名称，全局唯一，可随意起名但不带特殊字符
    mutex_name = "Global\\GTAUnlockApp_Unique_Mutex_2024"

    # 向系统申请互斥体
    global_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    last_error = ctypes.windll.kernel32.GetLastError()

    # 如果错误码为 183，说明互斥体已存在（即程序已经在运行了）
    if last_error == ERROR_ALREADY_EXISTS:
        print("检测到程序已经在运行...")

        # 【可选优化】尝试把已经运行的程序窗口置顶
        # ⚠️ 注意：请将 "GTAUnlockApp" 换成你 GUI 窗口真正的标题名（app.title() 设定的名字）
        window_title = "多合一开锁"
        hwnd = ctypes.windll.user32.FindWindowW(None, window_title)
        if hwnd:
            # 9 代表 SW_RESTORE (恢复最小化的窗口)
            ctypes.windll.user32.ShowWindow(hwnd, 9)
            # 把窗口提到最前面
            ctypes.windll.user32.SetForegroundWindow(hwnd)

        # 直接退出当前的重复实例
        sys.exit(0)


# ===========================
# ============================================

def main():
    # 以管理员权限运行当前脚本
    run_as_admin()

    # === 新增：防多开检查 (必须放在提权之后) ===
    check_single_instance()
    # =========================================

    # 1. 初始化数据层
    print("正在初始化配置...")
    config = ConfigManager()

    # 2. 初始化并启动监听层 (后台线程)
    print("正在启动 Win32 监听器...")
    listener = Win32HotkeyListener(config)
    listener.start()

    # ===== 新增：实例化防挂机休眠管理器 =====
    print("正在启动防挂机休眠服务...")
    afk_manager = AntiIdleManager()  # 无需传参，直接实例化
    afk_manager.start()              # 启动后台线程
    # ========================================



    try:
        # 3. 启动 GUI (主线程阻塞在这里)
        print("启动 GUI...")

        app = GTAUnlockApp(config)

        # === 新增：启动时自动检查更新 ===
        # 在主循环开始前检查，如果有更新会弹出窗口
        check_update_on_startup(app)
        # ==============================


        # ===== 新增：启动自动刷新差传线程 =====
        print("正在启动差传刷新服务...")
        refresh_thread = threading.Thread(
            target=refresh_cha_chuan_jobtp2.refersh_main,
            name="RefreshChaChuan",
            daemon=True  # 设置为守护线程，主程序退出时自动结束
        )
        refresh_thread.start()
        # =====================================



        app.mainloop()

    except KeyboardInterrupt:
        pass
    finally:
        # 4. 清理工作
        print("正在退出程序...")
        listener.stop()



        # ===== 新增：清空断网规则 =====
        ka_085.recover_natdown()
        # =============================

        # ===== 新增：停止防挂机线程 =====
        afk_manager.stop()
        # ================================


        # ===== 新增：停止刷新线程 =====
        refresh_cha_chuan_jobtp2.stop()
        refresh_thread.join(timeout=2)  # 等待2秒让线程结束
        # =============================

        sys.exit(0)




if __name__ == "__main__":

    main()