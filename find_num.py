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
