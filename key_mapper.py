# key_mapper.py
class KeyMapper:
    """
    虚拟键码映射类 (纯 Win32 版)
    用于在 字符串名称 和 16进制虚拟键码(VK) 之间进行转换
    """
    NAME_TO_VK = {
        # --- 鼠标侧键 ---
        #"RBUTTON":0x02,"MBUTTON":0x04,
        "侧键下": 0x05, "侧键上": 0x06,

        # --- 左右修饰键 (区分左右) ---
        # Shift
        "LSHIFT": 0xA0, "RSHIFT": 0xA1,
        # Ctrl
        "LCTRL": 0xA2, "RCTRL": 0xA3,
        # Alt (Menu)
        "LALT": 0xA4, "RALT": 0xA5,
        # Win键
        "LWIN": 0x5B, "RWIN": 0x5C,

        # --- 通用修饰键 (不区分左右，向后兼容) ---
        #"SHIFT": 0x10, "CTRL": 0x11, "ALT": 0x12,

        # --- 功能键 ---
        "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73,
        "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
        "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
        "F13": 0x7C, "F14": 0x7D, "F15": 0x7E, "F16": 0x7F,
        "F17": 0x80, "F18": 0x81, "F19": 0x82, "F20": 0x83,
        "F21": 0x84, "F22": 0x85, "F23": 0x86, "F24": 0x87,

        # --- 控制键 ---
        "ESC": 0x1B, "TAB": 0x09, "CAPS": 0x14,
        "SPACE": 0x20, "ENTER": 0x0D, "RETURN": 0x0D,  # RETURN别名
        "BACK": 0x08, "BACKSPACE": 0x08,  # BACKSPACE别名
        "DEL": 0x2E, "DELETE": 0x2E,  # DELETE别名
        "INS": 0x2D, "INSERT": 0x2D,  # INSERT别名

        # --- 导航键 ---
        "HOME": 0x24, "END": 0x23,
        "PGUP": 0x21, "PAGEUP": 0x21,  # PAGEUP别名
        "PGDN": 0x22, "PAGEDOWN": 0x22,  # PAGEDOWN别名

        # --- 方向键 ---
        "LEFT": 0x25, "UP": 0x26, "RIGHT": 0x27, "DOWN": 0x28,

        # --- 主键盘数字 (0-9) ---
        **{str(i): 0x30 + i for i in range(10)},

        # --- 主键盘符号 ---
        "-": 0xBD,  # VK_OEM_MINUS
        "=": 0xBB,  # VK_OEM_PLUS
        "[": 0xDB,  # VK_OEM_4
        "]": 0xDD,  # VK_OEM_6
        "\\": 0xDC,  # VK_OEM_5 (反斜杠)
        ";": 0xBA,  # VK_OEM_1
        "'": 0xDE,  # VK_OEM_7 (单引号)
        "`": 0xC0,  # VK_OEM_3 (反引号/波浪号)
        ",": 0xBC,  # VK_OEM_COMMA
        ".": 0xBE,  # VK_OEM_PERIOD
        "/": 0xBF,  # VK_OEM_2 (斜杠)



        # --- 字母 (A-Z) ---
        **{chr(i): i for i in range(0x41, 0x5B)},

        # --- 小键盘 (NumPad) ---
        "NUM 0": 0x60, "NUM 1": 0x61, "NUM 2": 0x62, "NUM 3": 0x63,
        "NUM 4": 0x64, "NUM 5": 0x65, "NUM 6": 0x66, "NUM 7": 0x67,
        "NUM 8": 0x68, "NUM 9": 0x69,
        "NUM *": 0x6A,  # 乘号
        "NUM 十": 0x6B,  # 加号
        "NUM -": 0x6D,  # 减号
        "NUM .": 0x6E,   # 小数点
        "NUM /": 0x6F,  # 除号
        "NUM ENTER": 0x0D,  # 小键盘回车(与主回车同码，但扫描码不同)

        # 小键盘开关
        "NUMLOCK": 0x90,
        "SCROLL": 0x91, "SCROLLLOCK": 0x91,

        # --- 浏览器/多媒体键 (部分键盘支持) ---
        "BROWSER_BACK": 0xA6,
        "BROWSER_FORWARD": 0xA7,
        "BROWSER_REFRESH": 0xA8,
        "BROWSER_STOP": 0xA9,
        "BROWSER_SEARCH": 0xAA,
        "BROWSER_FAVORITES": 0xAB,
        "BROWSER_HOME": 0xAC,
        "VOLUME_MUTE": 0xAD,
        "VOLUME_DOWN": 0xAE,
        "VOLUME_UP": 0xAF,
        "MEDIA_NEXT": 0xB0,
        "MEDIA_PREV": 0xB1,
        "MEDIA_STOP": 0xB2,
        "MEDIA_PLAY": 0xB3,
    }

    # 反向映射：通过键码找名字 (用于录入时回显)
    VK_TO_NAME = {v: k for k, v in NAME_TO_VK.items()}

    @classmethod
    def get_vk(cls, key_name):
        return cls.NAME_TO_VK.get(key_name, 0)

    @classmethod
    def get_name(cls, vk_code):
        return cls.VK_TO_NAME.get(vk_code, None)

    @classmethod
    def parse_key_combo(cls, key_str):
        """
        解析组合键字符串
        例如: "F1" -> [0x70]
        例如: "E+NUM 1" -> [0x45, 0x61]
        """
        if not key_str or key_str == "NONE":
            return []

        # 支持 + 号连接
        parts = key_str.upper().split('+')
        vk_list = []
        for part in parts:
            part = part.strip()
            vk = cls.get_vk(part)
            if vk != 0:
                vk_list.append(vk)
        return vk_list