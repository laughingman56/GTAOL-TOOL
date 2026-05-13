# 游戏 HUD 数字识别 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 实现一个纯 Python 微型神经网络，识别游戏中固定位置的 HUD 数字（0-9，1-2 位），推理时零额外依赖。

**架构：** `find_num.py` 负责推理（纯 Python + PIL），`train_num.py` 负责离线训练（numpy），权重存为 JSON。网络结构 256→32→10 全连接 + ReLU。

**技术栈：** Python 3 + PIL（已有）+ json + math（标准库），训练脚本额外使用 numpy。

---

## 文件结构

| 文件 | 新建/修改 | 职责 |
|------|----------|------|
| `find_num.py` | 修改（已有空文件） | 推理引擎：权重加载、图像预处理、前向推理、多区域识别 |
| `train_num.py` | 新建 | 训练脚本：样本加载、训练循环、权重导出 |
| `num_weights.json` | 新建（训练产物） | 训练好的权重和偏置 |
| `num_config.json` | 新建（示例） | 区域配置示例 |
| `test_find_num.py` | 新建 | 测试脚本：可直接 `python test_find_num.py` 运行 |

---

### 任务 1：前向推理核心

**文件：** 修改 `find_num.py`（写入），新建 `test_find_num.py`

- [ ] **步骤 1：编写测试**

在 `test_find_num.py` 中写入：

```python
import math


def test_forward():
    from find_num import forward

    # 使用可预测的简单权重测试
    w1 = [[0.1] * 256 for _ in range(32)]
    b1 = [0.0] * 32
    w2 = [[0.1] * 32 for _ in range(10)]
    b2 = [0.0] * 10

    x = [0.5] * 256
    result = forward(x, w1, b1, w2, b2)

    # 所有输入相同、权重相同 → 所有输出概率应相等 → argmax 可能是任意值
    # 但结果必须在 0-9 之间
    assert 0 <= result <= 9, f"Expected 0-9, got {result}"
    print("  PASS test_forward_bound")

    # 测试：让输出层偏好数字 3
    w2_biased = [[0.0] * 32 for _ in range(10)]
    for i in range(32):
        w2_biased[3][i] = 100.0  # 大幅提升第 3 类的偏置
    b2_biased = [0.0] * 10
    result = forward(x, w1, b1, w2_biased, b2_biased)
    assert result == 3, f"Expected 3 with biased weights, got {result}"
    print("  PASS test_forward_biased")


if __name__ == "__main__":
    test_forward()
    print("All tests passed!")
```

- [ ] **步骤 2：运行测试确认失败**

```bash
python test_find_num.py
```

预期：ImportError，`find_num.forward` 未定义。

- [ ] **步骤 3：实现 forward 函数**

在 `find_num.py` 中写入：

```python
import math


def _dot(a, b):
    return sum(ai * bi for ai, bi in zip(a, b))


def forward(x, w1, b1, w2, b2):
    h = [max(0, _dot(x, row) + b1[i]) for i, row in enumerate(w1)]
    y = [_dot(h, row) + b2[i] for i, row in enumerate(w2)]
    max_y = max(y)
    exps = [math.exp(v - max_y) for v in y]
    total = sum(exps)
    probs = [e / total for e in exps]
    return probs.index(max(probs))
```

- [ ] **步骤 4：运行测试确认通过**

```bash
python test_find_num.py
```

预期：`All tests passed!`

- [ ] **步骤 5：Commit**

```bash
git add find_num.py test_find_num.py
git commit -m "feat: add pure Python neural network forward pass"
```

---

### 任务 2：权重和配置加载

**文件：** 修改 `find_num.py`，追加 `test_find_num.py`

- [ ] **步骤 1：编写测试**

在 `test_find_num.py` 末尾追加（放在 `if __name__ == "__main__":` 之前）：

```python
import os
import json
import tempfile


def test_load_config():
    from find_num import load_config

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"ammo": {"x1": 10, "y1": 20, "x2": 50, "y2": 60, "digits": 2}}, f)
        tmp_path = f.name

    try:
        config = load_config(tmp_path)
        assert "ammo" in config, "Config should have 'ammo' key"
        assert config["ammo"]["digits"] == 2
        print("  PASS test_load_config")
    finally:
        os.unlink(tmp_path)

    # 测试文件不存在
    result = load_config("nonexistent_file.json")
    assert result == {}, f"Expected empty dict for missing config, got {result}"
    print("  PASS test_load_config_missing")


def test_load_weights():
    from find_num import load_weights

    weights = {
        "w1": [[0.1] * 256 for _ in range(32)],
        "b1": [0.01] * 32,
        "w2": [[0.2] * 32 for _ in range(10)],
        "b2": [0.02] * 10
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(weights, f)
        tmp_path = f.name

    try:
        w = load_weights(tmp_path)
        assert len(w["w1"]) == 32
        assert len(w["w1"][0]) == 256
        assert len(w["b1"]) == 32
        assert len(w["w2"]) == 10
        assert len(w["w2"][0]) == 32
        assert len(w["b2"]) == 10
        print("  PASS test_load_weights")
    finally:
        os.unlink(tmp_path)

    # 测试文件不存在
    try:
        load_weights("nonexistent_weights.json")
        assert False, "Should have raised RuntimeError"
    except RuntimeError:
        print("  PASS test_load_weights_missing")
```

- [ ] **步骤 2：运行测试确认失败**

```bash
python test_find_num.py
```

预期：前两个测试通过，新测试失败（ImportError）。

- [ ] **步骤 3：实现 load_config 和 load_weights**

在 `find_num.py` 的 import math 下方添加：

```python
import json
import os


def load_config(path="num_config.json"):
    if not os.path.exists(path):
        print(f"[find_num] config not found: {path}")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_weights(path="num_weights.json"):
    if not os.path.exists(path):
        raise RuntimeError(
            f"Weights file not found: {path}. Run train_num.py first."
        )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
```

- [ ] **步骤 4：运行测试确认通过**

```bash
python test_find_num.py
```

预期：全部 4 个测试通过。

- [ ] **步骤 5：Commit**

```bash
git add find_num.py test_find_num.py
git commit -m "feat: add config and weight JSON loading"
```

---

### 任务 3：图像预处理

**文件：** 修改 `find_num.py`，追加 `test_find_num.py`

- [ ] **步骤 1：编写测试**

在 `test_find_num.py` 末尾追加：

```python
from PIL import Image


def test_preprocess():
    from find_num import preprocess

    # 创建合成测试图像：16x16 纯白
    img = Image.new("L", (16, 16), color=255)
    vec = preprocess(img)
    assert len(vec) == 256, f"Expected 256, got {len(vec)}"
    assert all(abs(v - 1.0) < 0.01 for v in vec), "White should normalize to ~1.0"
    print("  PASS test_preprocess_white")

    # 创建合成测试图像：纯黑
    img2 = Image.new("L", (16, 16), color=0)
    vec2 = preprocess(img2)
    assert all(abs(v) < 0.01 for v in vec2), "Black should normalize to ~0.0"
    print("  PASS test_preprocess_black")

    # 测试：非 16x16 输入自动 resize
    img3 = Image.new("L", (32, 32), color=128)
    vec3 = preprocess(img3)
    assert len(vec3) == 256, f"Expected 256 after resize, got {len(vec3)}"
    print("  PASS test_preprocess_resize")


def test_preprocess_normalize_range():
    from find_num import preprocess

    img = Image.new("L", (8, 4), color=128)
    vec = preprocess(img)
    for v in vec:
        assert 0.0 <= v <= 1.0, f"Value {v} out of [0,1] range"
    print("  PASS test_preprocess_range")
```

并更新 `if __name__ == "__main__":` 块来调用这些测试。

- [ ] **步骤 2：运行测试确认失败**

```bash
python test_find_num.py
```

预期：preprocess 相关测试失败。

- [ ] **步骤 3：实现 preprocess 函数**

在 `find_num.py` 末尾添加：

```python
from PIL import Image


def preprocess(image, size=16):
    img = image.convert("L")
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    pixels = list(img.getdata())
    return [p / 255.0 for p in pixels]
```

- [ ] **步骤 4：运行测试确认通过**

```bash
python test_find_num.py
```

预期：全部 6 个测试通过。

- [ ] **步骤 5：Commit**

```bash
git add find_num.py test_find_num.py
git commit -m "feat: add image preprocessing to 16x16 grayscale vector"
```

---

### 任务 4：完整推理管线（单数字）

**文件：** 修改 `find_num.py`，追加 `test_find_num.py`

- [ ] **步骤 1：编写测试**

在 `test_find_num.py` 末尾追加：

```python
def test_recognize_single_digit():
    from find_num import _get_weights, _set_weights, recognize, load_config

    # 注入模拟权重，训练数字 3 映射到索引 3
    mock_weights = {
        "w1": [[0.01] * 256 for _ in range(32)],
        "b1": [0.0] * 32,
        "w2": [[0.0] * 32 for _ in range(10)],
        "b2": [0.0] * 10
    }
    # 让输出层第 3 个神经元权重极高，确保 argmax = 3
    for i in range(32):
        mock_weights["w2"][3][i] = 100.0

    _set_weights(mock_weights)

    # 创建合成截图：20x20 白色区域
    screenshot = Image.new("RGB", (200, 100), color=(0, 0, 0))
    # 在 (10,10) 到 (30,30) 画一个白底黑字区域
    for x in range(10, 30):
        for y in range(10, 30):
            screenshot.putpixel((x, y), (255, 255, 255))

    config = {
        "test_num": {"x1": 10, "y1": 10, "x2": 30, "y2": 30, "digits": 1}
    }

    result = recognize(screenshot, config)
    assert "test_num" in result, "Should have 'test_num' key"
    assert result["test_num"] == "3", f"Expected '3', got {result['test_num']}"
    print("  PASS test_recognize_single_digit")


def test_recognize_out_of_bounds():
    from find_num import _set_weights, recognize

    mock_weights = {
        "w1": [[0.01] * 256 for _ in range(32)],
        "b1": [0.0] * 32,
        "w2": [[0.0] * 32 for _ in range(10)],
        "b2": [0.0] * 10
    }
    _set_weights(mock_weights)

    screenshot = Image.new("RGB", (100, 50))
    config = {
        "bad": {"x1": 200, "y1": 10, "x2": 250, "y2": 30, "digits": 1}
    }

    result = recognize(screenshot, config)
    assert result == {}, f"Expected empty dict for OOB, got {result}"
    print("  PASS test_recognize_out_of_bounds")


def test_recognize_empty_config():
    from find_num import recognize

    screenshot = Image.new("RGB", (100, 50))
    result = recognize(screenshot, {})
    assert result == {}, f"Expected empty dict, got {result}"
    print("  PASS test_recognize_empty_config")
```

- [ ] **步骤 2：运行测试确认失败**

```bash
python test_find_num.py
```

预期：新测试失败。

- [ ] **步骤 3：实现 recognize 函数和权重缓存**

在 `find_num.py` 末尾添加（替换模块顶部可能存在的旧内容）：

```python
_weights = None


def _set_weights(w):
    global _weights
    _weights = w


def _get_weights():
    global _weights
    if _weights is None:
        _weights = load_weights()
    return _weights


def recognize(screenshot, config):
    if not config:
        return {}
    w = _get_weights()
    result = {}
    sw, sh = screenshot.size

    for name, region in config.items():
        x1, y1 = region["x1"], region["y1"]
        x2, y2 = region["x2"], region["y2"]
        digits = region.get("digits", 1)

        if x1 >= sw or y1 >= sh or x2 > sw or y2 > sh:
            continue

        crop = screenshot.crop((x1, y1, x2, y2))

        if digits == 1:
            vec = preprocess(crop)
            idx = forward(vec, w["w1"], w["b1"], w["w2"], w["b2"])
            result[name] = str(idx)
        else:
            cw = crop.size[0]
            half = cw // 2
            left = crop.crop((0, 0, half, crop.size[1]))
            right = crop.crop((half, 0, cw, crop.size[1]))
            lv = preprocess(left)
            rv = preprocess(right)
            l_idx = forward(lv, w["w1"], w["b1"], w["w2"], w["b2"])
            r_idx = forward(rv, w["w1"], w["b1"], w["w2"], w["b2"])
            result[name] = f"{l_idx}{r_idx}"

    return result
```

- [ ] **步骤 4：运行测试确认通过**

```bash
python test_find_num.py
```

预期：全部测试通过。

- [ ] **步骤 5：Commit**

```bash
git add find_num.py test_find_num.py
git commit -m "feat: add full inference pipeline with recognize function"
```

---

### 任务 5：创建示例配置文件

**文件：** 新建 `num_config.json`（示例）

- [ ] **步骤 1：写入示例配置**

在 `num_config.json` 中写入：

```json
{
  "ammo": {
    "x1": 0,
    "y1": 0,
    "x2": 10,
    "y2": 10,
    "digits": 2
  }
}
```

- [ ] **步骤 2：Commit**

```bash
git add num_config.json
git commit -m "feat: add example num_config.json"
```

---

### 任务 6：训练脚本

**文件：** 新建 `train_num.py`

- [ ] **步骤 1：写入完整训练脚本**

```python
import numpy as np
import json
import os
from PIL import Image


def load_samples(data_dir="num_samples"):
    X, y = [], []
    for label in range(10):
        label_dir = os.path.join(data_dir, str(label))
        if not os.path.isdir(label_dir):
            continue
        for fname in os.listdir(label_dir):
            if not fname.lower().endswith(".png"):
                continue
            fpath = os.path.join(label_dir, fname)
            img = Image.open(fpath).convert("L")
            img = img.resize((16, 16), Image.Resampling.LANCZOS)
            pixels = np.array(img.getdata(), dtype=np.float32) / 255.0
            X.append(pixels)
            y.append(label)
    if not X:
        raise RuntimeError(f"No .png samples found in {data_dir}/0-9/")
    indices = np.arange(len(X))
    np.random.shuffle(indices)
    return np.array(X)[indices], np.array(y)[indices]


class Net:
    def __init__(self, input_dim=256, hidden_dim=32, output_dim=10):
        rng = np.random.RandomState(42)
        self.w1 = rng.randn(input_dim, hidden_dim).astype(np.float32) * 0.01
        self.b1 = np.zeros(hidden_dim, dtype=np.float32)
        self.w2 = rng.randn(hidden_dim, output_dim).astype(np.float32) * 0.01
        self.b2 = np.zeros(output_dim, dtype=np.float32)

    def forward(self, X):
        self.h = np.maximum(0, X @ self.w1 + self.b1)
        scores = self.h @ self.w2 + self.b2
        shifted = scores - np.max(scores, axis=1, keepdims=True)
        exps = np.exp(shifted)
        self.probs = exps / np.sum(exps, axis=1, keepdims=True)
        return self.probs

    def loss(self, y):
        N = len(y)
        correct_probs = self.probs[np.arange(N), y]
        return -np.mean(np.log(correct_probs + 1e-8))

    def backward(self, X, y):
        N = len(y)
        dout = self.probs.copy()
        dout[np.arange(N), y] -= 1
        dout /= N

        dw2 = self.h.T @ dout
        db2 = np.sum(dout, axis=0)
        dh = dout @ self.w2.T
        dh[self.h <= 0] = 0

        dw1 = X.T @ dh
        db1 = np.sum(dh, axis=0)

        return dw1, db1, dw2, db2


def augment(X, y):
    X_aug = X.copy()
    noise = np.random.normal(0, 0.02, X_aug.shape).astype(np.float32)
    X_aug += noise
    X_aug = np.clip(X_aug, 0.0, 1.0)
    X_aug = np.roll(X_aug, shift=np.random.randint(-1, 2), axis=1)
    return X_aug, y


def train(data_dir="num_samples", epochs=400, lr=0.01, momentum=0.9):
    X, y = load_samples(data_dir)
    print(f"Loaded {len(X)} samples")

    net = Net()
    v_w1, v_b1, v_w2, v_b2 = 0, 0, 0, 0

    for epoch in range(epochs):
        if epoch > 0 and epoch % 100 == 0:
            lr *= 0.5

        X_batch, y_batch = augment(X, y)

        net.forward(X_batch)
        loss_val = net.loss(y_batch)

        dw1, db1, dw2, db2 = net.backward(X_batch, y_batch)

        # L2 regularization
        dw2 += 0.001 * net.w2
        dw1 += 0.001 * net.w1

        # Momentum update
        v_w2 = momentum * v_w2 - lr * dw2
        v_b2 = momentum * v_b2 - lr * db2
        v_w1 = momentum * v_w1 - lr * dw1
        v_b1 = momentum * v_b1 - lr * db1

        net.w2 += v_w2
        net.b2 += v_b2
        net.w1 += v_w1
        net.b1 += v_b1

        if epoch % 50 == 0:
            preds = np.argmax(net.probs, axis=1)
            acc = np.mean(preds == y_batch)
            print(f"  Epoch {epoch:3d}  loss={loss_val:.4f}  acc={acc:.3f}  lr={lr:.4f}")

    return net


def save_weights(net, path="num_weights.json"):
    w = {
        "w1": net.w1.T.tolist(),
        "b1": net.b1.tolist(),
        "w2": net.w2.T.tolist(),
        "b2": net.b2.tolist(),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(w, f, separators=(",", ":"))
    size_kb = os.path.getsize(path) / 1024
    print(f"Weights saved to {path} ({size_kb:.1f} KB)")


def collect_samples(screenshot_path, config_path="num_config.json", output_dir="num_samples"):
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from find_num import load_config

    screenshot = Image.open(screenshot_path)
    config = load_config(config_path)
    os.makedirs(output_dir, exist_ok=True)

    for name, region in config.items():
        x1, y1 = region["x1"], region["y1"]
        x2, y2 = region["x2"], region["y2"]
        crop = screenshot.crop((x1, y1, x2, y2))
        fname = f"{name}.png"
        fpath = os.path.join(output_dir, fname)
        crop.save(fpath)
        print(f"Saved {fpath}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="?", default="train",
                        choices=["train", "collect"])
    parser.add_argument("--data-dir", default="num_samples")
    parser.add_argument("--weights", default="num_weights.json")
    parser.add_argument("--screenshot")
    args = parser.parse_args()

    if args.command == "collect":
        if not args.screenshot:
            print("Usage: python train_num.py collect --screenshot shot.png")
            exit(1)
        collect_samples(args.screenshot)
    else:
        net = train(args.data_dir)
        save_weights(net, args.weights)
```

- [ ] **步骤 2：验证训练脚本可以加载（无语法错误）**

```bash
python -c "import train_num; print('train_num OK')"
```

预期：`train_num OK`（numpy 需已安装；若未安装，运行 `pip install numpy pillow`）

- [ ] **步骤 3：Commit**

```bash
git add train_num.py
git commit -m "feat: add training script with gradient descent + momentum"
```

---

### 任务 7：端到端验证

**文件：** 追加 `test_find_num.py`

- [ ] **步骤 1：编写端到端测试**

在 `test_find_num.py` 末尾追加：

```python
def test_end_to_end():
    from find_num import _set_weights, forward, preprocess, recognize

    # 用真正的训练流程验证：合成 0-9 数字图像，训练，然后识别
    samples = []
    for digit in range(10):
        for variant in range(20):
            img = Image.new("L", (20, 20), color=0)
            # 在图像中央画白色数字形状（简化：不同数字有不同的白色区域密度）
            center = digit * 2  # 0-18 范围内的偏移
            for x in range(2, 18):
                for y in range(2, 18):
                    brightness = (x + y + center * 3) % 256
                    if brightness > 128:
                        img.putpixel((x, y), brightness)
            vec = preprocess(img)
            samples.append((vec, digit))

    # 训练一个小网络
    X = np.array([s[0] for s in samples], dtype=np.float32)
    y = np.array([s[1] for s in samples], dtype=np.int64)

    rng = np.random.RandomState(42)
    w1 = (rng.randn(256, 32) * 0.01).astype(np.float32)
    b1 = np.zeros(32, dtype=np.float32)
    w2 = (rng.randn(32, 10) * 0.01).astype(np.float32)
    b2 = np.zeros(10, dtype=np.float32)

    for epoch in range(500):
        h = np.maximum(0, X @ w1 + b1)
        scores = h @ w2 + b2
        shifted = scores - np.max(scores, axis=1, keepdims=True)
        exps = np.exp(shifted)
        probs = exps / np.sum(exps, axis=1, keepdims=True)

        N = len(y)
        dout = probs.copy()
        dout[np.arange(N), y] -= 1
        dout /= N

        dw2 = h.T @ dout + 0.001 * w2
        db2 = np.sum(dout, axis=0)
        dh = dout @ w2.T
        dh[h <= 0] = 0
        dw1 = X.T @ dh + 0.001 * w1
        db1 = np.sum(dh, axis=0)

        lr = 0.01
        w2 -= lr * dw2
        b2 -= lr * db2
        w1 -= lr * dw1
        b1 -= lr * db1

        if epoch % 200 == 0:
            acc = np.mean(np.argmax(probs, axis=1) == y)
            print(f"    e2e train epoch {epoch} accuracy={acc:.3f}")

    # 将 numpy 权重转为 list 格式
    mock_w = {
        "w1": w1.T.tolist(),
        "b1": b1.tolist(),
        "w2": w2.T.tolist(),
        "b2": b2.tolist(),
    }
    _set_weights(mock_w)

    # 验证识别准确率
    correct = 0
    for vec, label in samples:
        idx = forward(vec, mock_w["w1"], mock_w["b1"], mock_w["w2"], mock_w["b2"])
        if idx == label:
            correct += 1
    acc = correct / len(samples)
    assert acc >= 0.5, f"E2E accuracy too low: {acc:.2f}"
    print(f"  PASS test_end_to_end (accuracy={acc:.2f})")
```

并在文件开头添加 `import numpy as np`，在 `if __name__ == "__main__":` 中添加调用。

- [ ] **步骤 2：运行所有测试**

```bash
python test_find_num.py
```

预期：所有测试通过，端到端准确率 >= 50%。

- [ ] **步骤 3：Commit**

```bash
git add test_find_num.py
git commit -m "test: add end-to-end synthetic training + recognition test"
```

---

### 任务 8：清理与收尾

- [ ] **步骤 1：确认 git 状态干净**

```bash
git status
```

- [ ] **步骤 2：最终 Commit（如有遗漏文件）**

```bash
git add -A
git status
```

如果已有全部提交，跳过此步。
