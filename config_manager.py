# config_manager.py
import json
import os
import threading
import copy
import  sys

class ConfigManager:
    """
    配置管理器 (单例模式建议)
    职责：
    1. 管理功能的按键映射和开关状态
    2. 提供线程安全的读写操作 (因为GUI和监听线程都会访问)
    3. 管理'正在录入'的全局状态
    """
    """
    配置管理器 (已实现单例模式)
    """
    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        # 确保多线程环境下全局只有一个实例
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self, filename=None):
        # 防止单例被多次执行 __init__ 导致配置重新加载
        if getattr(self, '_initialized', False):
            return
        self._initialized = True

        # 新增：设置配置文件路径
        def get_exe_dir():
            """获取exe文件所在的目录（兼容开发模式和打包后运行）"""
            if getattr(sys, 'frozen', False):  # 如果是打包后的exe
                return os.path.dirname(sys.executable)  # sys.executable是exe的路径
            else:  # 如果是开发模式
                return os.path.dirname(os.path.abspath(__file__))

        CONFIG_DIR = get_exe_dir()

        # --- 【迁移逻辑开始】 ---
        # 定义新文件名
        new_config_name = "GTA多合一开锁助手.json"
        new_filepath = os.path.join(CONFIG_DIR, new_config_name)

        # 定义旧文件名列表（按版本从新到旧排序，优先迁移最新版本）
        old_config_names = [
            "GTA多合一开锁助手v1.0.3.json",
            "GTA多合一开锁助手v1.0.2.json",
            "GTA多合一开锁助手v1.0.1.json"
        ]

        # 遍历旧文件列表
        for old_name in old_config_names:
            old_filepath = os.path.join(CONFIG_DIR, old_name)
            # 如果旧文件存在
            if os.path.exists(old_filepath):
                try:
                    # 如果新文件尚不存在，直接重命名
                    if not os.path.exists(new_filepath):
                        os.rename(old_filepath, new_filepath)
                    else:
                        # 如果新文件已经存在（可能是之前迁移过），则直接删除旧的残留文件
                        os.remove(old_filepath)
                except Exception as e:
                    print(f"处理旧配置文件 {old_name} 时出错: {e}")

        if filename is None:
            # 修改：使用新的默认路径
            self.filename = new_filepath
        else:

            self.filename = os.path.join(CONFIG_DIR, filename)

        self.lock = threading.RLock()  # 线程锁，防止读写冲突

        # 录入状态标志
        self.is_recording = False
        self.recording_target_key = None  # 当前正在修改哪个功能的按键 (例如 'casino')

        # 默认配置结构
        self.default_config = {
            "ka_cha_chuan": {"name": "任务卡差传", "key": "O","danei":True ,"enabled": True},
            #差传相关
            #"cha_chuan": {"name": "差传", "key": "NONE", "enabled": True},
            "cha_chuan_1": {"name": "差传1", "key": "F7","cha_chuan_1_style": 1, "cha_chuan_1_time":40, "target_cmd1_style": 0,"manual":False,"enabled": True},
            "cha_chuan_2": {"name": "差传2", "key": "F8","cha_chuan_2_style": 1, "cha_chuan_2_time":40, "target_cmd2_style": 1,"manual":False,"enabled": True},
            #"refresh_cha_chuan_1": {"name": "刷新差传1", "key": "F7+F7", "enabled": True},
            #"refresh_cha_chuan_2": {"name": "刷新差传2", "key": "F8+F8", "enabled": True},
            "refresh_cha_chuan_bot": {"name": "自动刷新差传", "key": "F6", "enabled": True},
            "ka_ceo": {"name": "卡CEO", "key": ";", "danei": True, "enabled": True},

            "casino": {"name": "赌场指纹", "key": "F9", "enabled": True},
            "security": {"name": "保安圆点", "key": "F10", "enabled": True},
            "cayo": {"name": "佩岛指纹", "key": "F11", "enabled": False},
            "photo": {"name": "拍照攀爬", "key": "L", "enabled": False},

            "nat_down": {"name": "断网", "key": "NUM 十", "rule":0,"time_limited":True,"time":20,"enabled": False},
            "sudden_stop":{"name": "瞬间悬停", "key": "NUM .","style":0, "enabled": False},


            "low_fps": {"name": "低帧率模式", "key": "NONE", "enabled": False},
            "instruction": {"name": "使用说明|音效", "key": "NONE", "enabled": True},
            "update": {"name": "检查更新", "key": "NONE", "enabled": True},

            "phone": {"name": "打电话", "key": "NONE", "enabled": True},
            "mk2": {"name": "马克兔", "key": "NONE", "enabled": True},
            "fight": {"name": "战斗相关", "key": "NONE", "enabled": True},




            # --- 新增部分: 电话联系人专用配置 ---
            "ji_gong": {"name": "技工", "key": "NUM /", "father": "phone", "times": "19", "enabled": True},
            "bao_xian": {"name": "共荣保险", "key": "NUM *", "father": "phone", "times": "17", "enabled": True},
            "lester": {"name": "莱斯特", "key": "NUM -", "father": "phone", "times": "23", "enabled": True},
            "custom_1": {"name": "自定义1", "key": "NUM / + NUM /", "father": "phone", "times": "23", "enabled": False},
            "custom_2": {"name": "自定义2", "key": "NUM * + NUM *", "father": "phone", "times": "23", "enabled": False},
            "custom_3": {"name": "自定义3", "key": "NUM - + NUM -", "father": "phone", "times": "23", "enabled": False},




            # --- 新增部分: 马克兔专用配置 ---
            "call_mk2": {"name": "呼叫马克兔", "key": "T", "father": "mk2", "enabled": True},
            "send_mk2": {"name": "送回载具", "key": "T+T", "father": "mk2", "enabled": True},
            "call_mk2_truck": {"name": "呼叫恐霸", "key": "T+T+T", "father": "mk2", "enabled": True},


            "call_sparrow": {"name": "呼叫麻雀", "key": "Y", "father": "mk2", "enabled": True},
            "call_whale": {"name": "呼叫虎鲸", "key": "Y+Y", "father": "mk2", "enabled": True},
            "send_sparrow": {"name": "送回麻雀", "key": "Y+Y+Y", "father": "mk2", "enabled": True},

            "call_car": {"name": "呼叫载具", "key": "U", "father": "mk2", "enabled": True},
            "open_door": {"name": "打开车门并启动", "key": "U+U", "father": "mk2", "enabled": True},

            # --- 新增部分: 战斗相关配置 ---
            "pill": {"name": "牛鲨睾酮", "key": "I", "father": "fight", "enabled": True},
            "bullet": {"name": "弹药全满", "key": "I+I", "father": "fight", "enabled": True},
            "ghost": {"name": "幽灵组织", "key": "I+I+I", "father": "fight", "enabled": False},

            "revolver": {"name": "连发左轮", "key": "J", "father": "fight", "enabled": True},

            "rpg": {"name": "连发重武器", "key": "侧键下", "times": "10","father": "fight", "enabled": True},
            "shot": {"name": "连发狙", "key": "侧键上", "times": "0","father": "fight", "enabled": True},

            "cloth": {"name": "换衣服", "key": "K", "times": "0","father": "fight", "enabled": True},
            "thermal": {"name": "热成像", "key": "K+K", "father": "fight", "enabled": True},
            "flight_thermal": {"name": "飞机热成像", "key": "K+K+K", "father": "fight", "enabled": True},
            "snack": {"name": "M菜单吃零食", "key": "B","father": "fight", "times": "5", "enabled": False},


            "hang_up_and_key_setting": {"name": "按键设置|自动挂机", "key": "NONE", "enabled": True},

            "m_menu": {"name": "M菜单", "key": "m"},
            "weapon_menu": {"name": "武器轮盘", "key": "tab"},
            "no_weapon": {"name": "空手", "key": "1"},
            "shotgun_weapon": {"name": "散弹枪",  "key": "3"},
            "rpg_weapon": {"name": "火箭筒", "key": "4"},
            "c4_weapon": {"name":  "投掷物", "key": "5"},
            "pistol_weapon": {"name": "手枪", "key": "6"},
            "sniper_weapon": {"name": "狙击枪", "key": "9"},


            "custom_script":{"name": "自定义宏","key": "NONE", "enabled": False},
            "script_0": {"name": "示例", "key": "", "father": "custom_script", "enabled": False, "code": "#这是注释和示例\n#pydirectinput.PAUSE = 0.02\n#\n#按键停顿为0.02秒\n#for i in range(5):\n#    pydirectinput.keyDown(\"a\")\n#    time.sleep(0.03)\n#    pydirectinput.keyUp(\"a\")\n#    time.sleep(0.03)\n#循环5次，按下a键，等待0.03秒，抬起a键，等待0.03秒，注意代码缩进\n#\n#pydirectinput.mouseDown(button=\"right\")\n#time.sleep(0.3)\n#pydirectinput.mouseUp(button=\"right\")\n#按下鼠标右键，等待0.3秒，抬起\n#\n#pydirectinput.moveRel(-100, 0, relative=True)\n#鼠标x坐标向左移动100个像素\n#\n#更多语法去搜索pydirectinput"},
            "script_1": {"name": "左轮连发", "key": "\\", "father": "custom_script", "enabled": False, "code": "# 设置输入库的防卡死和延迟\npydirectinput.PAUSE = 0.02\npydirectinput.FAILSAFE = False\n\npydirectinput.keyDown(\"3\")\ntime.sleep(0.03)\npydirectinput.keyUp(\"3\")\ntime.sleep(0.03)\npydirectinput.keyDown(\"6\")\ntime.sleep(0.03)\npydirectinput.keyUp(\"6\")\ntime.sleep(0.03)\npydirectinput.keyDown(\"1\")\ntime.sleep(0.03)\npydirectinput.keyUp(\"1\")\ntime.sleep(0.03)\npydirectinput.keyDown(\"6\")\ntime.sleep(0.03)\npydirectinput.keyUp(\"6\")\ntime.sleep(1)\npydirectinput.keyDown(\"c\")\ntime.sleep(0.1)\npydirectinput.mouseDown()\npydirectinput.mouseUp()\npydirectinput.keyUp(\"c\")\n\npydirectinput.PAUSE = 0.1"},
            "script_2": {"name": "", "key": "", "father": "custom_script", "enabled": False, "code": ""},
            "script_3": {"name": "", "key": "", "father": "custom_script", "enabled": False, "code": ""},
            "script_4": {"name": "", "key": "", "father": "custom_script", "enabled": False, "code": ""},
            "script_5": {"name": "", "key": "", "father": "custom_script", "enabled": False, "code": ""},
            "script_6": {"name": "", "key": "", "father": "custom_script", "enabled": False, "code": ""},
            "script_7": {"name": "", "key": "", "father": "custom_script", "enabled": False, "code": ""},
            "script_8": {"name": "", "key": "", "father": "custom_script", "enabled": False, "code": ""},
            "script_9": {"name": "", "key": "", "father": "custom_script", "enabled": False, "code": ""},






            "target_cmd1": "",
            "target_cmd2": "",


            "link0": "",
            "link1": "",
            "link2": "",
            "link3": ""

                }

        self.data = self.load_config()

    def _merge_config(self, old_data, default_config):
        """
        递归合并配置：以 default_config 为基准，用 old_data 的值进行覆盖。
        保证新增的 key 能自动补全，已有的用户设置能保留。
        """
        # 修复 Bug 1：使用深拷贝，防止后续修改 data 时污染默认配置
        merged = copy.deepcopy(default_config)

        # 增加容错：如果读取的旧文件完全损坏不是字典，直接返回默认配置
        if not isinstance(old_data, dict):
            return merged

        for key, value in old_data.items():
            if key in merged:

                '''
                # 修复 Bug 2：防止版本升级导致的数据结构类型改变引发崩溃                
                # 如果新旧版本该字段的数据类型完全不同（例如旧版是布尔值，新版变成了字典），则丢弃旧值，使用新默认值
                if type(value) != type(merged[key]):
                    print(f"配置项 [{key}] 结构已更新，旧数据被废弃。")
                    continue
                '''
                # 如果键存在，判断是否需要递归合并（针对嵌套字典）
                if isinstance(value, dict) and isinstance(merged[key], dict):
                    # 递归合并嵌套字典
                    merged[key] = self._merge_config(value, merged[key])
                else:
                    # 非字典类型，直接用旧值覆盖默认值（保留用户设置）
                    merged[key] = value
            else:
                # 如果键不存在于新版默认配置中（说明是废弃的旧字段）
                # 这里选择保留（原逻辑 pass 是忽略，如果你需要严格清理废弃项，保持 pass 即可）
                merged[key] = value

        return merged

    def load_config(self):
        """加载配置，如果不存在则创建默认配置"""
        if not os.path.exists(self.filename):
            # 新增：确保目录存在
            os.makedirs(os.path.dirname(self.filename), exist_ok=True)

            self.save_config(self.default_config)
            return self.default_config

        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                old_data = json.load(f)

            # 2. 【核心修改】执行配置合并，实现自动兼容
            # 以 default_config 为蓝本，填充 old_data 的内容
            merged_data = self._merge_config(old_data, self.default_config)

            # 3. 检查是否有更新（可选优化：只有配置结构变化时才重新写入）
            # 如果合并后的数据与旧数据不同，说明发生了版本升级，保存新配置
            if merged_data != old_data:
                print("检测到配置版本更新，正在升级配置文件...")
                self.save_config(merged_data)

            return merged_data

        except Exception as e:
            print(f"配置文件加载失败，使用默认配置: {e}")
            return self.default_config

    def save_config(self, data=None):
        """保存配置到文件"""
        if data:
            self.data = data
        with self.lock:  # 写入文件时上锁
            # 新增：确保目录存在
            os.makedirs(os.path.dirname(self.filename), exist_ok=True)

            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)

    def update_key_binding(self, func_id, new_key_name):
        """更新某个功能的按键绑定"""
        with self.lock:
            if func_id in self.data:
                self.data[func_id]['key'] = new_key_name
        self.save_config()

    def update_switch_state(self, func_id, is_enabled):
        """更新开关状态"""
        with self.lock:
            if func_id in self.data:
                self.data[func_id]['enabled'] = is_enabled
        self.save_config()

        # --- 【新增代码开始】 ---

    def update_config_item(self, key, value, separator="."):
        """通用更新方法：支持嵌套路径的更新"""
        # 方法1：使用点分隔符
        #cfg.update_nested_item("nat_down.rule", new_idx)
        # 方法2：使用列表
        #cfg.update_nested_item(["nat_down", "rule"], new_idx)

        with self.lock:
            # 检查是否是嵌套路径
            if isinstance(key, str) and separator in key:
                # 处理嵌套路径
                keys = key.split(separator)
                data = self.data

                # 遍历到最后一个键的父级
                for k in keys[:-1]:
                    if k not in data:
                        data[k] = {}
                    data = data[k]

                # 设置最后一个键的值
                last_key = keys[-1]
                data[last_key] = value
            else:
                # 原始逻辑：更新顶级键
                self.data[key] = value

        self.save_config()
    # --- 【新增代码结束】 ---

    def set_recording_mode(self, func_id):
        """开启录入模式"""
        self.recording_target_key = func_id
        self.is_recording = True

    def stop_recording_mode(self):
        """结束录入模式"""
        self.is_recording = False
        self.recording_target_key = None

    def get_function_data(self, func_id):
        return self.data.get(func_id, {})

    def get_all_data(self):
        return self.data

