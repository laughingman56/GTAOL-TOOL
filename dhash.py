
from PIL import Image



def calculate_dhash(image, hash_size=8):
    """ dHash 算法 """
    image = image.convert("L")
    image = image.resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = list(image.getdata())
    difference = []
    for row in range(hash_size):
        for col in range(hash_size):
            pixel_left = pixels[row * (hash_size + 1) + col]
            pixel_right = pixels[row * (hash_size + 1) + col + 1]
            difference.append(pixel_left > pixel_right)
    decimal_value = 0
    for index, value in enumerate(difference):
        if value:
            decimal_value += 2 ** index
    return decimal_value


def hamming_distance(hash1, hash2):
    """ 计算二进制差异位数 """
    if hash1 is None or hash2 is None: return 999
    return bin(hash1 ^ hash2).count('1')

# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲ 模块结束 ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲