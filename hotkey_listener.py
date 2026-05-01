# hotkey_listener.py
import time
import threading
import win32api
import win32gui  # <--- 新增此行
import winsound
from key_mapper import KeyMapper
from game_scripts import ScriptExecutor


class Win32HotkeyListener(threading.Thread):
    """
    后台监听线程 (支持单键与双键序列)
    逻辑:
    1. 单键触发: 按下 -> 执行
    2. 双键序列: 按下 Key1 -> 松开 -> 0.5s内按下 Key2 -> 执行
    """

    def __init__(self, config_manager):
        super().__init__()
        self.config = config_manager
        self.daemon = True
        self.running = True
        self.delay = 0.01

        # --- 连击状态管理 (同键多击) ---
        self.current_key = None  # 当前正在追踪的连击按键 (VK Code)
        self.press_count = 0  # 当前该按键连续点击的次数
        self.pending_time = 0  # 上次该按键松开的时间戳
        self.sequence_timeout = 0.2  # 连击判定超时时间 (秒，建议0.3-0.4)

        # --- 录制模式防干扰状态管理 ---
        self._recording_initialized = False
        self._ignored_ghost_keys = set()

    def _play_sound(self):
        """播放提示音 (读取配置)"""
        data = self.config.get_all_data()
        if data.get("instruction", {}).get("enabled", False):
            winsound.MessageBeep(-1)

    def _is_game_window_active(self):
        """检查当前前台窗口是否匹配目标游戏标题"""
        # TODO: 这里建议改为从 self.config 读取，例如: target = self.config.game_title
        target_title = "Grand Theft Auto"  # <--- 请修改为你游戏的窗口标题关键字

        if not target_title:
            return True  # 未配置时默认全生效

        try:
            hwnd = win32gui.GetForegroundWindow()
            current_title = win32gui.GetWindowText(hwnd)
            return target_title.lower() in current_title.lower()
        except:
            return False



    def run(self):
        print("[-] 监听线程已启动 (支持双键序列模式)")
        while self.running:
            if self.config.is_recording:
                self._handle_recording()
            else:
                self._handle_listening()

            time.sleep(self.delay)

    def _wait_for_release(self, vk_code):
        """阻塞直到指定按键释放"""
        while win32api.GetAsyncKeyState(vk_code) & 0x8000:
            time.sleep(0.01)

    def _is_key_down(self, vk_code):
        """检查按键是否按下 (最高位为1表示当前按下)"""
        return win32api.GetAsyncKeyState(vk_code) & 0x8000

    # ---------------------------------------------------------
    #  录入模式 (智能判断单键或双键)
    # ---------------------------------------------------------
    def _handle_recording(self):
        """
        录入逻辑 (同键连击模式):
        1. 拍快照屏蔽幽灵键。
        2. 捕获首键后，开启倒计时循环。
        3. 规定时间内反复按同一个键，连击数增加；按其他键或超时则结算。
        """
        if not self._recording_initialized:
            self._recording_initialized = True
            self._ignored_ghost_keys.clear()

            for key_name, vk_code in KeyMapper.NAME_TO_VK.items():
                if self._is_key_down(vk_code):
                    self._ignored_ghost_keys.add(vk_code)
                    print(f"[Record Init] 屏蔽幽灵键: {key_name} (VK: {vk_code})")

            hardcode_ignores = ["NUMLOCK", "SCROLL", "CAPS"]
            for name in hardcode_ignores:
                if vk := KeyMapper.NAME_TO_VK.get(name):
                    self._ignored_ghost_keys.add(vk)

        # --- 1. 扫描首次按键 ---
        target_vk = None
        target_name = None

        for key_name, vk_code in KeyMapper.NAME_TO_VK.items():
            if vk_code in self._ignored_ghost_keys:
                continue

            if self._is_key_down(vk_code):
                target_name = key_name
                target_vk = vk_code
                print(f"[Record] 捕获按键: {target_name}, 开始记录连击...")
                self._wait_for_release(vk_code)
                break

        if not target_vk:
            return  # 没按键继续等

        # --- 2. 进入连击捕获阶段 ---
        click_count = 1
        start_wait = time.time()

        while time.time() - start_wait < self.sequence_timeout:
            for key_name, vk_code in KeyMapper.NAME_TO_VK.items():
                if vk_code in self._ignored_ghost_keys:
                    continue

                if self._is_key_down(vk_code):
                    if vk_code == target_vk:
                        # 续上连击
                        click_count += 1
                        print(f"[Record] 连击+1, 当前: {target_name} (x{click_count})")
                        self._wait_for_release(vk_code)
                        start_wait = time.time()  # 刷新超时倒计时
                    else:
                        # 按了别的键，直接打断并结束录制
                        print(f"[Record] 按了其他键，连击录制终止。")
                        start_wait = 0  # 强制退出循环
                    break
            time.sleep(0.01)

        # --- 3. 生成最终键名 (如 A 或 A+A+A) ---
        final_key_str = "+".join([target_name] * click_count)
        print(f"[Record] 最终录入: {final_key_str}")

        # 保存并退出
        target_func = self.config.recording_target_key
        self.config.update_key_binding(target_func, final_key_str)
        self.config.stop_recording_mode()

        self._recording_initialized = False
        time.sleep(0.2)

    # ---------------------------------------------------------
    #  监听模式 (状态机)
    # ---------------------------------------------------------
    def _handle_listening(self):
        # 窗口激活检查
        if not self._is_game_window_active():
            if self.current_key is not None:
                self.current_key = None
                self.press_count = 0
            return

        """
        同键连击监听逻辑:
        1. 解析配置为: { 虚拟键码: { 次数: 功能ID } }
        2. 状态机判定连击与打断
        """
        # 1. 解析当前配置
        key_map = {}  # 结构: { vk: { count: func_id } }
        data = self.config.get_all_data()

        for func_id, settings in data.items():
            if not isinstance(settings, dict) or not settings.get('enabled', False):
                continue

            father_id = settings.get('father')
            if father_id:
                father_settings = data.get(father_id)
                if not isinstance(father_settings, dict) or not father_settings.get('enabled', False):
                    continue

            key_str = settings.get('key')
            vk_list = KeyMapper.parse_key_combo(key_str)

            if not vk_list:
                continue

            # 仅支持同键配置，校验是否全为一个键
            if len(set(vk_list)) > 1:
                # 如果用户乱配置不同键(比如A+B)，在当前模式下忽略
                continue

            vk = vk_list[0]
            count = len(vk_list)

            if vk not in key_map:
                key_map[vk] = {}
            key_map[vk][count] = func_id

        # 2. 状态机处理
        current_time = time.time()

        # --- 状态 A: 正在追踪某键的连击 ---
        if self.current_key is not None:
            # 2.1 检查是否超时 (超时代表连击结束，执行对应功能)
            if current_time - self.pending_time > self.sequence_timeout:
                # 查询当前按键在这个连击次数下有没有配置功能
                func_to_run = key_map.get(self.current_key, {}).get(self.press_count)
                if func_to_run:
                    self._trigger_function(func_to_run)

                # 结算完毕，重置状态
                self.current_key = None
                self.press_count = 0

            # 2.2 没超时，检测后续按键
            else:
                for vk in key_map.keys():
                    if self._is_key_down(vk):
                        if vk == self.current_key:
                            # 续上连击
                            self.press_count += 1
                            self._wait_for_release(vk)
                            self.pending_time = time.time()  # 刷新超时
                        else:
                            # 【打断机制】如果在连击间隙按了别的功能键
                            # 1. 强制结算刚才的连击
                            func_to_run = key_map.get(self.current_key, {}).get(self.press_count)
                            if func_to_run:
                                self._trigger_function(func_to_run)

                            # 2. 立刻把新按的键作为新的追踪对象
                            self.current_key = vk
                            self.press_count = 1
                            self._wait_for_release(vk)
                            self.pending_time = time.time()
                        break  # 一次只捕获一个按键

        # --- 状态 B: 空闲状态 (检测第一下) ---
        else:
            for vk in key_map.keys():
                if self._is_key_down(vk):
                    self.current_key = vk
                    self.press_count = 1
                    self._wait_for_release(vk)
                    self.pending_time = time.time()
                    break
    def _trigger_function(self, func_id):
        """执行功能的封装"""
        print(f"[Execute] 触发功能: {func_id}")
        self._play_sound()
        ScriptExecutor.run_script(func_id)

    def stop(self):
        self.running = False