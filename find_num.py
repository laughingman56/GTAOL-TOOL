import math
import json
import os
import sys


def _resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


def load_config(path="num_config.json"):
    path = _resource_path(path)
    if not os.path.exists(path):
        print(f"[find_num] config not found: {path}")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            print(f"[find_num] invalid JSON in config: {path}")
            return {}


def load_weights(path="num_weights.json"):
    path = _resource_path(path)
    if not os.path.exists(path):
        raise RuntimeError(
            f"Weights file not found: {path}. Run train_num.py first."
        )
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Weights file is invalid JSON: {path}"
            ) from e


def _conv2d_single(x_2d, filters_4d, biases):
    C_out = len(filters_4d)
    KH = len(filters_4d[0][0])
    KW = len(filters_4d[0][0][0])
    H = len(x_2d)
    W = len(x_2d[0])
    OH = H - KH + 1
    OW = W - KW + 1
    out = []
    for f in range(C_out):
        chan = []
        for i in range(OH):
            row = []
            for j in range(OW):
                s = biases[f]
                for ki in range(KH):
                    for kj in range(KW):
                        s += filters_4d[f][0][ki][kj] * x_2d[i + ki][j + kj]
                row.append(s)
            chan.append(row)
        out.append(chan)
    return out


def _maxpool2d(x_chw, size=2):
    C = len(x_chw)
    OH = len(x_chw[0]) // size
    OW = len(x_chw[0][0]) // size
    out = []
    for c in range(C):
        chan = []
        for i in range(OH):
            row = []
            for j in range(OW):
                m = x_chw[c][i * size][j * size]
                for di in range(size):
                    for dj in range(size):
                        v = x_chw[c][i * size + di][j * size + dj]
                        if v > m:
                            m = v
                row.append(m)
            chan.append(row)
        out.append(chan)
    return out


def _dot(a, b):
    return sum(ai * bi for ai, bi in zip(a, b))


def forward_cnn(x_flat, w):
    IMG_SIZE = int(math.sqrt(len(x_flat)))
    x_2d = [x_flat[i * IMG_SIZE:(i + 1) * IMG_SIZE] for i in range(IMG_SIZE)]

    conv_out = _conv2d_single(x_2d, w["conv1_w"], w["conv1_b"])
    for f in range(len(conv_out)):
        for i in range(len(conv_out[f])):
            for j in range(len(conv_out[f][i])):
                conv_out[f][i][j] = max(0.0, conv_out[f][i][j])

    pooled = _maxpool2d(conv_out, size=2)
    flat = []
    for c in range(len(pooled)):
        for i in range(len(pooled[c])):
            flat.extend(pooled[c][i])

    fc1_out_size = len(w["fc1_b"])
    h1 = [max(0.0, _dot(flat, w["fc1_w"][i]) + w["fc1_b"][i])
           for i in range(fc1_out_size)]

    fc2_out_size = len(w["fc2_b"])
    scores = [_dot(h1, w["fc2_w"][i]) + w["fc2_b"][i]
              for i in range(fc2_out_size)]
    max_s = max(scores)
    exps = [math.exp(s - max_s) for s in scores]
    total = sum(exps)
    probs = [e / total for e in exps]
    return probs.index(max(probs))


def forward_mlp(x, w1, b1, w2, b2):
    h = [max(0, _dot(x, row) + b1[i]) for i, row in enumerate(w1)]
    y = [_dot(h, row) + b2[i] for i, row in enumerate(w2)]
    max_y = max(y)
    exps = [math.exp(v - max_y) for v in y]
    total = sum(exps)
    probs = [e / total for e in exps]
    return probs.index(max(probs))


from PIL import Image


def preprocess(image, size=24):
    img = image.convert("L")
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    pixels = list(img.tobytes())
    return [p / 255.0 for p in pixels]


_weights = None


def _set_weights(w):
    global _weights
    _weights = w


def _get_weights():
    global _weights
    if _weights is None:
        _weights = load_weights()
    return _weights


def _is_cnn(w):
    return w.get("arch") == "cnn"


def _forward(x, w):
    if _is_cnn(w):
        return forward_cnn(x, w)
    else:
        return forward_mlp(x, w["w1"], w["b1"], w["w2"], w["b2"])


def recognize(screenshot, config):
    if not config:
        return {}
    w = _get_weights()
    result = {}
    sw, sh = screenshot.size

    for name, region in config.items():
        x1 = region.get("x1")
        y1 = region.get("y1")
        x2 = region.get("x2")
        y2 = region.get("y2")
        if None in (x1, y1, x2, y2):
            print(f"[find_num] missing coords for region: {name}")
            continue
        digits = region.get("digits", 1)

        if x1 < 0 or y1 < 0 or x1 >= sw or y1 >= sh or x2 > sw or y2 > sh:
            continue

        crop = screenshot.crop((x1, y1, x2, y2))

        if digits == 1:
            vec = preprocess(crop)
            idx = _forward(vec, w)
            result[name] = str(idx)
        elif digits == 2:
            cw = crop.size[0]
            if cw < 2:
                continue
            half = cw // 2
            left = crop.crop((0, 0, half, crop.size[1]))
            right = crop.crop((half, 0, cw, crop.size[1]))
            lv = preprocess(left)
            rv = preprocess(right)
            l_idx = _forward(lv, w)
            r_idx = _forward(rv, w)
            result[name] = f"{l_idx}{r_idx}"
        else:
            print(f"[find_num] unsupported digits={digits} for region: {name}")

    return result


def grid_recognize(screenshot, grid_config):
    w = _get_weights()
    gx = grid_config["x"]
    gy = grid_config["y"]
    cw = grid_config["cell_w"]
    ch = grid_config["cell_h"]
    cols = grid_config["cols"]
    rows = grid_config["rows"]

    result = []
    for r in range(rows):
        row_data = []
        for c in range(cols):
            x1 = gx + c * cw
            y1 = gy + r * ch
            x2 = x1 + cw
            y2 = y1 + ch

            sw, sh = screenshot.size
            if x1 < 0 or y1 < 0 or x1 >= sw or y1 >= sh or x2 > sw or y2 > sh:
                row_data.append("")
                continue

            crop = screenshot.crop((x1, y1, x2, y2))

            if crop.size[0] < 2:
                row_data.append("")
                continue

            half = crop.size[0] // 2
            left = crop.crop((0, 0, half, crop.size[1]))
            right = crop.crop((half, 0, crop.size[0], crop.size[1]))

            lv = preprocess(left)
            rv = preprocess(right)
            l_idx = _forward(lv, w)
            r_idx = _forward(rv, w)
            row_data.append(f"{l_idx}{r_idx}")
        result.append(row_data)
    return result