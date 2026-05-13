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
