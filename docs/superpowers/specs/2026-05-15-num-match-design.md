# Number Match — 设计规格说明

## 概述

在现有数字识别系统（find_num.py + train_num.py）基础上，新增一个游戏辅助脚本：截屏识别游戏中的目标数字和网格数字，自动用方向键移动光标到匹配位置。

## 游戏场景

- 屏幕中上方有 **2 个目标两位数**（红色，从左到右）
- 下方有 **8 行 × 10 列** 两位数网格（80 格，红色）
- 光标宽度为 **1×4**（覆盖连续 4 格），起始位置：第 4 行、第 4~7 列（索引从 0 算：row=3, col=3~6）
- 目标：移动光标，使光标下第 1、2 格数字与上方目标数字一致（顺序相同）
- 操作方式：方向键移动

## 架构

```
num_match.py  (入口脚本, ~80行)
  ├─ mss 截屏
  ├─ find_num.recognize()     → 识别 t0, t1（现有函数）
  ├─ find_num.grid_recognize() → 识别 8×10 矩阵（新增函数）
  ├─ 搜索：grid[r][c]==t0 and grid[r][c+1]==t1
  └─ pydirectinput 方向键移动：(r,c) - (3,3)
```

## 文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| `num_config.json` | 修改 | 新增 `targets` 和 `grid` 配置块 |
| `find_num.py` | 新增函数 | `grid_recognize(screenshot, grid_config)` 返回 8×10 矩阵 |
| `num_match.py` | 新增 | 入口脚本，串起全流程，约 80~100 行 |

不修改的文件：`hotkey_listener.py`、`train_num.py`、`gui_app.py`、`test_find_num.py`。

## 配置格式

```json
{
  "targets": {
    "t0": {"x1": 100, "y1": 50, "x2": 130, "y2": 70, "digits": 2},
    "t1": {"x1": 140, "y1": 50, "x2": 170, "y2": 70, "digits": 2}
  },
  "grid": {
    "x": 50, "y": 100,
    "cell_w": 30, "cell_h": 20,
    "cols": 10, "rows": 8,
    "cursor_w": 4
  }
}
```

- `targets` — 复用现有 region 格式，t0/t1 按从左到右顺序
- `grid` — 左上角坐标、格子宽高、行列数、光标覆盖宽度
- 格子坐标自动计算：`cell(r,c) = (grid.x + c*cell_w, grid.y + r*cell_h)`

## 执行流程

1. `mss` 截取全屏，得到 PIL Image
2. `recognize(screenshot, config["targets"])` 识别 t0, t1 的值
3. `grid_recognize(screenshot, config["grid"])` 逐格截取、预处理、识别，返回 `list[list[str]]`（8×10）
4. 遍历 r(0..7)、c(0..6)，检查 `grid[r][c]==t0 and grid[r][c+1]==t1`
5. 若找到匹配 `(r,c)`：计算方向键次数 `dr=r-3, dc=c-3`，依次按 ↓/↑ 和 →/←，每次间隔约 50ms
6. 若未找到：打印提示，结束

## 错误处理

- `num_weights.json` 不存在 → 提示先运行 train_num.py
- `num_config.json` 格式错误 → 打印错误，退出
- 目标或网格识别结果为空 → 打印提示，结束
- 未找到匹配 → 打印"未找到匹配"，不做操作
- 越界格子 → 跳过

## 数字识别原理

- 两位数：区域从中间切开，左右各识别一位 0~9，拼接
- 颜色（红色）：`preprocess()` 转为灰度后颜色信息丢失，不影响识别
- 神经网络：纯 Python 前向传播，无 numpy 依赖；256→32→10，ReLU + Softmax

## 外部依赖

全部使用项目中已有依赖：
- `mss` — 截屏
- `PIL` — 图像处理
- `pydirectinput` — 方向键输入
- `find_num` — 数字识别

## 不需要实现

- 热键绑定（用户自行处理）
- GUI 集成
- `hotkey_listener.py` 修改
