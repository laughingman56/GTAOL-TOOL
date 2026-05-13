import math
import json
import os


def load_config(path="num_config.json"):
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


from PIL import Image


def preprocess(image, size=16):
    img = image.convert("L")
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    pixels = list(img.getdata())
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
