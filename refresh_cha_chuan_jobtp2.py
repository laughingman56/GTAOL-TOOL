import time

import requests

import customtkinter as ctk
from config_manager import ConfigManager

#------------guii界面---------------

# 注意：需确保你已导入了 cha_chuan_1 和 cha_chuan_2 函数
# 或者将此函数放在同一个文件中

def show_settings_ui(parent_window):
    """
    显示设置界面的GUI (无保存按钮，即选即存)
    """
    # 1. 创建顶级弹窗
    settings_win = ctk.CTkToplevel(parent_window)
    settings_win.title("差传源设置")
    settings_win.geometry("400x400")
    settings_win.resizable(False, False)

    # 窗口置顶与模态
    settings_win.attributes("-topmost", True)
    settings_win.grab_set()

    # 2. 准备数据
    cfg = ConfigManager()
    data = cfg.get_all_data()
    bot_options = ["1号bot--jobtp2", "2号bot--jobtp2", "3号bot--jobtp2", "4号bot--jobtp2"]  # 对应索引 0, 1, 2

    # 获取当前配置索引 (防止越界)
    idx1 = data.get("cha_chuan_1", {}).get("target_cmd1_style", 0)
    idx2 = data.get("cha_chuan_2", {}).get("target_cmd2_style", 0)
    if not (0 <= idx1 <= 3): idx1 = 0
    if not (0 <= idx2 <= 3): idx2 = 0

    # 3. 定义回调函数 (自动保存逻辑)

    def on_change_cmd1(choice):
        """当差传1下拉框变化时触发"""
        try:
            new_idx = bot_options.index(choice)  # 获取文本对应的索引(0,1,2)
            cfg.update_config_item("cha_chuan_1.target_cmd1_style", new_idx)  # 写入配置
            print(f"[设置] 差传1 已切换为: {choice} (ID:{new_idx})")
            cha_chuan_1()  # 立即刷新差传1链接
        except Exception as e:
            print(f"[错误] 更新差传1失败: {e}")

    def on_change_cmd2(choice):
        """当差传2下拉框变化时触发"""
        try:
            new_idx = bot_options.index(choice)
            cfg.update_config_item("cha_chuan_2.target_cmd2_style", new_idx)  # 写入配置
            print(f"[设置] 差传2 已切换为: {choice} (ID:{new_idx})")
            cha_chuan_2()  # 立即刷新差传2链接
        except Exception as e:
            print(f"[错误] 更新差传2失败: {e}")

    # 4. 构建 UI
    frame = ctk.CTkFrame(settings_win)
    frame.pack(fill="both", expand=True, padx=15, pady=15)

    # --- 差传 1 ---
    ctk.CTkLabel(frame, text="差传1:",
                 font=("Microsoft YaHei", 18, "bold")).pack(anchor="w", pady=(5, 5))

    combo_1 = ctk.CTkComboBox(
        frame,
        font=("Microsoft YaHei", 18, "bold"),
        dropdown_font=("Microsoft YaHei", 18, "bold"),
        values=bot_options,
        state="readonly",
        command=on_change_cmd1  # 绑定回调函数
    )
    combo_1.pack(fill="x", pady=(0, 15))
    combo_1.set(bot_options[idx1])  # 设置初始值

    # --- 差传 2 ---
    ctk.CTkLabel(frame, text="差传2:",
                 font=("Microsoft YaHei", 18, "bold")).pack(anchor="w", pady=(0, 5))

    combo_2 = ctk.CTkComboBox(
        frame,
        font=("Microsoft YaHei", 18, "bold"),
        dropdown_font=("Microsoft YaHei", 18, "bold"),
        values=bot_options,
        state="readonly",
        command=on_change_cmd2  # 绑定回调函数
    )
    combo_2.pack(fill="x", pady=(0, 10))
    combo_2.set(bot_options[idx2])  # 设置初始值


    ctk.CTkLabel(frame,
                 text="-jobtp2的QQ:189311215\n"
                      #"-ksyyds的QQ:736867759\n"
                      "-开启软件后更新一次差传，\n"
                      "-之后每5分钟更新一次\n"
                      "-如果差传用不了，\n"
                      "-可以更换bot或者F6手动刷新",
                 font=("Microsoft YaHei", 18, "bold"),
                 justify="left",
                 padx=0).pack(anchor="w", padx=0)


#------------执行层-----------------
# 全局控制标志
_running = True
_text = ""


def stop():
    """停止刷新循环"""
    global _running
    _running = False

def fetch_quellgtacode():

    """
    抓取差传数据，加入了防缓存机制
    """
    # 增加时间戳参数，强制每次请求都是全新的，防止被路由器/运营商/CDN缓存
    timestamp = int(time.time() * 1000)
    url = f"https://www.*******.nyat.app:*****/?_t={timestamp}"

    try:
        # 设置请求头，模拟浏览器访问
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'
        }

        # 发送GET请求，设置5秒超时
        response = requests.get(url, headers=headers, timeout=5)

        # 检查状态码
        response.raise_for_status()

        # 自动检测编码
        response.encoding = response.apparent_encoding

        # 输出结果
        #print(f"状态码: {response.status_code}")
        #print(f"编码: {response.encoding}")
        #print(f"内容长度: {len(response.text)} 字符")
        #print("-" * 50)
        #print(response.text)

        return response.text

    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None






#差传1-郑州联通12bot-自由瞄准|steam://rungame/3240220/76561199074735990/-steamjvp%3D
#差传2-郑州移动13bot-辅助瞄准|steam://rungame/3240220/76561198451940904/-steamjvp%3D
def cha_chuan_1():
    cfg = ConfigManager()
    data = cfg.get_all_data()
    NUM = data.get("cha_chuan_1", {}).get("target_cmd1_style", 0)
    link = data.get(f"link{NUM}","")
    # 写入配置
    cfg.update_config_item("target_cmd1", link)

def cha_chuan_2():
    cfg = ConfigManager()
    data = cfg.get_all_data()
    NUM = data.get("cha_chuan_2", {}).get("target_cmd2_style", 0)
    link = data.get(f"link{NUM}","")
    # 写入配置
    cfg.update_config_item("target_cmd2", link)

def refersh_link(n, data=None):


    if not data: return  # 容错

    # 按行分割数据
    lines = data.strip().split('\n')

    # 提取第n行（差传）的内容
    link = lines[n]

    #print(link)
    if link:
        # 创建 ConfigManager 实例
        cfg = ConfigManager()
        data = cfg.get_all_data()
        old_link = data.get(f"link{n}","")
        if link != old_link:
            # 写入配置
            cfg.update_config_item(f"link{n}", link)
            print(f"link{n}写入成功")
        else:
            print(f"link{n}相同，不写入")

def enabled():
    cfg = ConfigManager()
    data = cfg.get_all_data()
    if data.get("refresh_cha_chuan_bot", {}).get("enabled", False) is not None and data.get("refresh_cha_chuan_bot", {}).get("enabled", False):
        print("刷新差传已打开")
        return True
    elif not data.get("refresh_cha_chuan_bot", {}).get("enabled", False) :
        print("刷新差传已关闭")
        return False
    else:
        print("刷新差传开关未找到，默认开启")
        return  True




def delay():
        cfg = ConfigManager()
        data = cfg.get_all_data()
        if data.get("low_fps", {}).get("enabled", False):
            return 0.1
        return 0

    # 调用函数
def refersh_main():
    print("刷新差传启动")
    global  _running,_text

    while _running:  # 使用标志位控制循环
        if not enabled():
            time.sleep(5)  # 如果禁用，5秒检查一次是否开启
            continue

        try:
            data = fetch_quellgtacode()
            # 【修复重点】增加对返回数据的格式判定 (确保至少有3行数据，避免把服务器报错网页写进配置)
            if data is not None and len(data.strip().split('\n')) >= 3:

                if data != _text:
                    # 更新差传链接
                    for i in range(4):
                        refersh_link(i, data)

                    # 更新差传1,2
                    cha_chuan_1()
                    cha_chuan_2()

                    _text = data
                    print(f"[差传刷新] 已更新 - {time.strftime('%H:%M:%S')}")
                    time.sleep(300)
                else:
                    # 只有在初次测试时打开，正常使用时不用打印“无变化”，避免刷死控制台
                    print("[差传刷新] 数据无变化")
                    time.sleep(300)

            elif data is not None:
                # 拿到了数据，但不足3行（通常是服务器崩溃或代理页报错）
                print("[差传刷新] 拿到的数据格式不符合规范(不足3行)，放弃本次更新")
                time.sleep(10)
            else:
                print("[差传刷新] 获取失败，10秒后重试")
                time.sleep(10)

        except Exception as e:
            print(f"[差传刷新] 致命错误: {e}")
            time.sleep(10)

    print("刷新差传已停止")

def refersh_manual():

    print("执行手动刷新...") # 修改提示语以免混淆
    global _text

    try:

        data = fetch_quellgtacode()

        # 手动更新同样需要防崩溃保护
        if data is not None and len(data.strip().split('\n')) >= 3:
            for i in range(4):
                refersh_link(i, data)

            cha_chuan_1()
            cha_chuan_2()

            _text = data
            print(f"[差传刷新] 手动更新完成 - {time.strftime('%H:%M:%S')}")

        elif data is not None:
            print("[差传刷新] 手动获取成功，但数据格式不对(可能是报错页)")
        else:
            print("[差传刷新] 手动获取失败")



    except Exception as e:
        print(f"[差传刷新] 错误: {e}")


