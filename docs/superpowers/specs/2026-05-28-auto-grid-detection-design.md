# 像素投影法自动网格识别 — 设计规格

## 概述

解决当前数字识别系统依赖固定坐标的问题——`num_config.json` 中的 `x`、`y`、`cell_w` 等坐标仅在特定分辨率（1920×1080、2560×1440）下有效，其他分辨率（如 1920×1200）会导致截取偏移、识别失效。

采用像素投影法自动检测网格（8 行 × 10 列 + 上方 2 个目标数字），完全不依赖预设坐标。

## 新增模块

**`auto_grid.py`** — 入口函数 `detect_grid(screenshot)`，输入全屏 PIL RGB Image，输出 `(targets_cfg, grid_cfg)`。

### 入参

| 参数 | 类型 | 说明 |
|------|------|------|
| `screenshot` | `PIL.Image` (RGB) | 全屏截图 |

### 出参

```python
targets_cfg = {
    "t0": {"x1": int, "y1": int, "x2": int, "y2": int, "digits": 2},
    "t1": {"x1": int, "y1": int, "x2": int, "y2": int, "digits": 2},
}

grid_cfg = {
    "x": int, "y": int,
    "cell_w": int, "cell_h": int,
    "cols": 10, "rows": 8,
    "cursor_w": 4,
}
```

与现有 `recognize()` 和 `grid_recognize()` 的 config 格式完全兼容。

### 异常

检测失败时抛出 `GridDetectError`。调用方回退到 `num_config.json` 的现有逻辑。

## 检测流程

### 步骤 1：粗定位——找到 grid 和 targets 的大致区域

全屏截图逐像素扫描太慢，先缩小后粗定位：

1. 将全屏缩小到 1/4 尺寸（如 2560×1440 → 640×360），加速
2. 全局二值化：阈值 = 全图像素均值 × 1.2（暗背景上白色数字占少数，均值偏低，×1.2 分离白色与暗色）
3. 水平投影：逐行统计白色像素数，得到一维数组 H[y]
4. H[y] 中高密度连续带即为数字密集区域。面积最大、分布均匀的一段为 grid 区域；grid 上方的独立小密集块为 targets 区域
5. 映射回原始分辨率，四周各加 padding 20px 得到粗区域

### 步骤 2：grid 行切分——水平投影找 8 行边界

在 grid 粗区域内，以原始分辨率操作：

1. 二值化（阈值同上）
2. 逐行统计白色像素 → 水平投影 H[y]
3. 窗口宽度 5 做滑动平均平滑去噪
4. 找波峰/波谷：局部最小值低于相邻两个波峰均值的为波谷。取两相邻波谷的中点为行分割线
5. 得到 9 条水平线 y[0]..y[8]，形成 8 行

### 步骤 3：grid 列切分——垂直投影找 10 列边界

对每一行区域：

1. 二值化
2. 逐列统计白色像素 → 垂直投影 V[x]
3. 窗口宽度 5 滑动平均平滑
4. 找波谷定列边界，得到 11 条垂直线 x[0]..x[10]

### 步骤 4：等距校正

投影法得到的行列边界可能有 1-3px 局部漂移（取决于该行/列具体数字形状的像素占比，如 "11" vs "88"）。实际网格是机械均匀的，因此做等距校正：

```
avg_row_h = (y[8] - y[0]) / 8
y_corrected[i] = y[0] + i * avg_row_h      (i = 0..8)

avg_cell_w = (x[10] - x[0]) / 10
x_corrected[j] = x[0] + j * avg_cell_w      (j = 0..10)
```

最终 cell_w、cell_h 均为整数，起始坐标取自校正后的 y[0]、x[0]。

### 步骤 5：targets 检测

在步骤 1 粗定位的 targets 区域内：

1. 二值化
2. 垂直投影确定左右边界 → 得到 x1, x2
3. 从粗区域的 y1, y2 确定上下边界
4. 两位数字通过步骤 6 的垂直投影分割
5. 输出 t0、t1 两个区域

### 步骤 6：两位数分割

每个格子里是两位数，需要从中切分成两个独立数字分别识别。

**主方案：格内垂直投影找分割线**

在单格子内部做垂直投影（白像素逐列统计），两个数字之间有一个窄的波谷，以此定位分割中线。

**fallback：50/50 等分**

如果投影找不到明显波谷（如 "11"、"00" 中间没有明显间隙），回退到 `half = cw // 2` 中点切分。

## 集成点

```python
# num_match.py 改动

from auto_grid import detect_grid, GridDetectError

screenshot = capturar_tela()

try:
    targets_cfg, grid_cfg = detect_grid(screenshot)
except GridDetectError:
    config = load_config("num_config.json")
    targets_cfg, grid_cfg = _adapt_config(config)

# 后续流程不变
targets = recognize(screenshot, targets_cfg)
grade = grid_recognize(screenshot, grid_cfg)
```

## 文件结构

```
auto_grid.py          [新增] 网格自动检测模块
find_num.py           [不变] 推理引擎
num_match.py          [改动] 集成 detect_grid + fallback
num_config.json       [保留] fallback 配置
debug_grid.py         [可选扩展] 支持自动检测可视化
```

`find_num.py` 的 `recognize()`、`grid_recognize()` 不动——它们只负责裁剪+推理，不关心坐标来源。

## 错误处理

| 场景 | 处理 |
|------|------|
| 检测不到 8 个行波峰 | 抛出 `GridDetectError` |
| 某行检测不到 10 个列波峰 | 使用 x[0] 和 x[10] 等距推算缺失列 |
| targets 没检测到 | 抛出 `GridDetectError` |
| 截图全暗（游戏未启动/黑屏） | 二值化后白像素极少，提前返回失败 |
| UI 弹窗遮挡网格 | 检测区域白像素占比 < 5% 时判定被遮挡，拒绝返回 |
| 运行中重复检测 | 同一流程中只检测一次，后续帧复用坐标 |

## 边界情况

- **像素色阶中间值**：二值化阈值自动从图像均值计算，不硬编码阈值。
- **小数位**：cell_w 和 cell_h 取整（像素坐标），但等距校正涉及浮点除法时保留精度直到最后一步取整。
- **奇数格宽**：半数分切时左半多 1px（如 cw=171，左 86px、右 85px）。
- **两位数字无间隔**：格内投影无波谷时 fallback 到 50/50 等分。
- **相邻两位数字紧密排列**：列间波谷可能很浅，平滑窗口不宜过大（window=5），否则滤掉窄波谷。

## 性能预估

| 步骤 | 预估耗时 |
|------|---------|
| 粗定位（1/4 缩图投影） | 5-10ms |
| grid 精切（8 行 × 10 列投影） | 10-20ms |
| targets 检测 | 3-5ms |
| 两位数分割 | 1-2ms/格子 |
| 总计（单次检测） | 20-40ms |

单次检测耗时可接受，因为同一流程中坐标检测只执行一次，后续帧直接复用。
