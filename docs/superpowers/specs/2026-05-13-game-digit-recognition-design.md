# 游戏 HUD 数字识别 — 设计规格

## 概述

在游戏自动化脚本中，识别屏幕上固定位置的 HUD 数字（血量、弹药数、计时器等），用于实时决策。采用纯 Python 微型全连接神经网络，推理时零额外依赖。

## 需求

- 识别屏幕上多个固定位置的 HUD 数字
- 数字样式：七段数码管 + 标准等宽字体
- 每位置 1-2 位数字
- 实时连续识别，10-50ms/次
- 体积小：模型文件 ~100KB、无新增运行时依赖、CPU 占用低
- 区域坐标通过配置文件定义

## 文件结构

```
pythonProject1/
  find_num.py          # 推理引擎（纯 Python + PIL）
  train_num.py         # 训练脚本（离线使用，可用 numpy）
  num_weights.json     # 训练后的权重（~100KB）
  num_config.json      # 区域配置文件
  num_samples/         # 训练样本（可选保留）
    0/  *.png
    1/  *.png
    ...
    9/  *.png
```

## 架构

### 网络结构

```
输入层: 16×16 灰度图 → 展平为 256 维向量
隐藏层: 256 → 32 全连接 + ReLU
输出层: 32 → 10 全连接 + softmax（对应数字 0-9）

参数总量: ~8,500 个浮点数
权重文件: ~100KB JSON
```

### 模块职责

| 模块 | 职责 | 依赖 |
|------|------|------|
| `find_num.py` | 加载权重，对截图裁剪区域进行推理，返回识别结果 | PIL（项目已有），标准库 |
| `train_num.py` | 读取训练样本，训练网络，导出 `num_weights.json` | numpy（离线用途） |
| `num_weights.json` | 存储训练好的权重矩阵和偏置 | 无 |
| `num_config.json` | 定义各区域坐标和位数 | 无 |

## 推理引擎 (`find_num.py`)

### 对外接口

```python
import find_num
result = find_num.recognize(screenshot, config)
# screenshot: PIL Image
# config: dict，定义区域
# result: {"ammo": "24", "health": "8"}
```

### 内部流程

1. 加载权重（模块导入时一次性加载，缓存复用）
2. 遍历配置中的每个区域：
   - PIL `crop()` 裁剪
   - `resize()` 至 16×16，转灰度
   - 像素值归一化到 [0, 1]
   - 展平为 256 维列表
3. 1 位数字：直接前向推理 → argmax → 数字字符
4. 2 位数字：水平均分左右半区 → 分别推理 → 拼接为 2 位字符串
5. 返回结果 dict

### 推理核心（纯 Python，零依赖）

```python
def forward(x, w1, b1, w2, b2):
    h = [max(0, sum(a*b for a,b in zip(x, row)) + b1[i]) for i, row in enumerate(w1)]
    y = [sum(a*b for a,b in zip(h, row)) + b2[i] for i, row in enumerate(w2)]
    exp_sum = sum(math.exp(v) for v in y)
    probs = [math.exp(v) / exp_sum for v in y]
    return probs.index(max(probs))
```

### 配置文件格式

```json
{
  "ammo":     {"x1": 100, "y1": 50, "x2": 150, "y2": 80, "digits": 2},
  "health":   {"x1": 200, "y1": 50, "x2": 240, "y2": 80, "digits": 1}
}
```

## 训练脚本 (`train_num.py`)

### 流程

1. **收集样本**：截取游戏画面，按 config 裁剪各区域，人工分入 `num_samples/0/` ~ `9/` 目录
2. **加载数据**：读取所有样本，resize 16×16 灰度，归一化，生成标签
3. **数据增强**：随机亮度 ±10%、平移 ±1px
4. **训练**：梯度下降 + momentum，交叉熵损失，300-500 轮
5. **导出**：将权重矩阵写入 `num_weights.json`

### 训练超参数

| 参数 | 值 |
|------|------|
| 学习率 | 0.01，每 50 轮减半 |
| 动量 | 0.9 |
| 正则化 | L2，λ=0.001 |
| 批量大小 | 全量（数据量小） |
| 轮数 | 300-500 |

## 调用约定

```python
from PIL import Image
import find_num

config = find_num.load_config("num_config.json")
screenshot = Image.open("screenshot.png")  # 或 mss 截屏
result = find_num.recognize(screenshot, config)

if int(result.get("ammo", "0")) < 10:
    reload()
```

不绑定截图方式，接受 PIL Image 即可。

## 错误处理

| 场景 | 处理 |
|------|------|
| 权重文件缺失 | RuntimeError，提示运行训练 |
| 配置文件缺失 | 返回空 dict |
| 区域超出截图边界 | 跳过该区域 |
| 2 位区域宽度 < 4px | 报错 |
| 置信度 < 0.5（可选） | 沿用上次结果 |

## 边界情况

- **数字被遮挡/闪烁**：连续 2 帧一致才更新结果；置信度低时沿用旧值
- **2 位数宽度奇数**：左半多 1px
- **权重缓存**：模块级全局变量，避免重复加载

## 性能预估

| 操作 | 耗时 |
|------|------|
| 裁剪 1 区域 | <1ms |
| resize 16×16 | <1ms |
| 一次前向推理 | 2-5ms |
| 10 区域全识别 | 20-50ms |
