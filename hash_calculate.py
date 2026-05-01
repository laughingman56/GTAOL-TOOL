import mss
import time
from PIL import Image
import  keyboard
import  mss_dpi
import dhash
# ==========================================
#              用户配置区域
# ==========================================
# 在这里修改你需要截图的屏幕坐标和大小
SCREEN_CONFIG =  (1940, 1300, 620, 50)
screen_hash = 0x78f6fa39f35ffca9
'''''  
    {
    'left':40, # 屏幕左上角 X 坐标
    'top': 600,# 屏幕左上角 Y 坐标
    'width': 575,#截图宽度
    'height': 100# 截图高度
}
'''

# ==========================================

def calculate_dhash(image, hash_size=8):
    """
    dHash 算法 (差异哈希算法)
    原理：缩小图片 -> 转灰度 -> 计算相邻像素差异 -> 生成指纹
    """
    # 1. 转为灰度图
    image = image.convert("L")

    # 2. 缩放图片 (宽度比高度多1个像素，为了便于左右比较)
    image = image.resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)

    pixels = list(image.getdata())
    difference = []

    # 3. 比较差异
    for row in range(hash_size):
        for col in range(hash_size):
            # 获取当前像素和右边的一个像素
            pixel_left = pixels[row * (hash_size + 1) + col]
            pixel_right = pixels[row * (hash_size + 1) + col + 1]
            # 如果左边比右边亮(大)，记为 True(1)，否则为 False(0)
            difference.append(pixel_left > pixel_right)

    # 4. 生成哈希值 (二进制转十进制整数)
    decimal_value = 0
    for index, value in enumerate(difference):
        if value:
            decimal_value += 2 ** index

    return decimal_value

def capture_screen(sct, monitor):
    """
    使用传入的 sct 实例截图
    """
    try:
        sct_img = sct.grab(monitor)
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        return img
    except Exception as e:
#        print(f"Screenshot Error: {e}")
        return None

def esc_job():
#    print("\n---------- [F10] 任务开始 (MSS + Win32API版) ----------")

#    if not TEMPLATES_P1 or not TEMPLATES_P2:
#        print("❌ 错误：未填入哈希数据，请先运行 get_hashes.py 并填充代码！")
#        return
    # ★关键修改：在任务线程内部初始化 mss，避免跨线程报错
    with mss.mss() as sct:
        # ================= 阶段一 =================
        p1_monitor = mss_dpi.ResolutionAdapter.get_mss_config(SCREEN_CONFIG)
        screen1 = capture_screen(sct, p1_monitor) # 传入 sct

        if screen1 is None: return

        screen1_hash = dhash.calculate_dhash(screen1)

        dist = dhash.hamming_distance(screen1_hash, screen_hash)
        return dist
def capture_and_hash():
    """
    使用 mss 截图指定区域并计算哈希值
    """
    # 初始化 mss 上下文管理器
    with mss.mss() as sct:
        try:
            # 1. 截取屏幕
            # sct.grab 返回的是一个 MSS ScreenShot 对象
            p1_monitor = mss_dpi.ResolutionAdapter.get_mss_config(SCREEN_CONFIG)
            sct_img = sct.grab(p1_monitor)

            # 2. 将 mss 对象转换为 PIL Image 对象
            # mss 默认是 BGRA 格式，Pillow 需要 RGB，所以这里做转换
            # 参数解释: "RGB" (目标模式), size, bgra (原始数据), "raw", "BGRX" (原始模式解析)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

            # (可选) 如果你想看看截到了什么，可以取消下面这行的注释来保存图片
            img.save("debug_screenshot.png")

            # 3. 计算哈希值
            # 记录开始时间（用于性能测试，可选）
            start_time = time.time()

            dhash_value = calculate_dhash(img)


            end_time = time.time()

            # 4. 输出结果
            print("-" * 30)
            print(f"截图区域: {SCREEN_CONFIG}")
            print(f"十进制哈希值: {dhash_value}")
            print(f"十六进制哈希值: {hex(dhash_value)}")  # 十六进制通常更短，方便记录
            print(f"计算耗时: {(end_time - start_time) * 1000:.2f} ms")

            print(f"距离: {esc_job()}")
            print("-" * 30)

            return dhash_value

        except Exception as e:
            print(f"发生错误: {e}")
            return None



    # 执行主函数
while True:
    if keyboard.is_pressed('i'):
        capture_and_hash()
        # Add a small delay to prevent multiple triggers from a single press
        keyboard.wait('i', suppress=True)  # Wait until 'i' is released