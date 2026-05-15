import math
import numpy as np


def test_forward_mlp():
    from find_num import forward_mlp

    w1 = [[0.1] * 576 for _ in range(32)]
    b1 = [0.0] * 32
    w2 = [[0.1] * 32 for _ in range(10)]
    b2 = [0.0] * 10

    x = [0.5] * 576
    result = forward_mlp(x, w1, b1, w2, b2)

    assert 0 <= result <= 9, f"Expected 0-9, got {result}"
    print("  PASS test_forward_mlp_bound")

    w2_biased = [[0.0] * 32 for _ in range(10)]
    for i in range(32):
        w2_biased[3][i] = 100.0
    b2_biased = [0.0] * 10
    result = forward_mlp(x, w1, b1, w2_biased, b2_biased)
    assert result == 3, f"Expected 3 with biased weights, got {result}"
    print("  PASS test_forward_mlp_biased")


def test_forward_cnn():
    from find_num import forward_cnn

    conv1_w = [[[[0.1] * 3 for _ in range(3)] for _ in range(1)] for _ in range(8)]
    conv1_b = [0.0] * 8
    fc1_in = 8 * 11 * 11
    fc1_w = [[0.01] * fc1_in for _ in range(64)]
    fc1_b = [0.0] * 64
    fc2_w = [[0.0] * 64 for _ in range(10)]
    fc2_b = [0.0] * 10
    for i in range(64):
        fc2_w[3][i] = 100.0

    w = {
        "conv1_w": conv1_w,
        "conv1_b": conv1_b,
        "fc1_w": fc1_w,
        "fc1_b": fc1_b,
        "fc2_w": fc2_w,
        "fc2_b": fc2_b,
        "arch": "cnn",
    }
    x = [0.5] * 576
    result = forward_cnn(x, w)
    assert 0 <= result <= 9, f"Expected 0-9, got {result}"
    print("  PASS test_forward_cnn_bound")


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
        print("  PASS test_load_weights")
    finally:
        os.unlink(tmp_path)

    try:
        load_weights("nonexistent_weights.json")
        assert False, "Should have raised RuntimeError"
    except RuntimeError:
        print("  PASS test_load_weights_missing")


def test_load_config_invalid_json():
    from find_num import load_config

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("not valid json{{{")
        tmp_path = f.name

    try:
        result = load_config(tmp_path)
        assert result == {}, f"Expected empty dict for corrupt JSON, got {result}"
        print("  PASS test_load_config_invalid_json")
    finally:
        os.unlink(tmp_path)


def test_load_weights_invalid_json():
    from find_num import load_weights

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("not valid json{{{")
        tmp_path = f.name

    try:
        load_weights(tmp_path)
        assert False, "Should have raised RuntimeError"
    except RuntimeError:
        print("  PASS test_load_weights_invalid_json")
    finally:
        os.unlink(tmp_path)


from PIL import Image


def test_preprocess():
    from find_num import preprocess

    img = Image.new("L", (24, 24), color=255)
    vec = preprocess(img)
    assert len(vec) == 576, f"Expected 576, got {len(vec)}"
    assert all(abs(v - 1.0) < 0.01 for v in vec), "White should normalize to ~1.0"
    print("  PASS test_preprocess_white")

    img2 = Image.new("L", (24, 24), color=0)
    vec2 = preprocess(img2)
    assert all(abs(v) < 0.01 for v in vec2), "Black should normalize to ~0.0"
    print("  PASS test_preprocess_black")

    img3 = Image.new("L", (32, 32), color=128)
    vec3 = preprocess(img3)
    assert len(vec3) == 576, f"Expected 576 after resize, got {len(vec3)}"
    print("  PASS test_preprocess_resize")


def test_preprocess_normalize_range():
    from find_num import preprocess

    img = Image.new("L", (8, 4), color=128)
    vec = preprocess(img)
    for v in vec:
        assert 0.0 <= v <= 1.0, f"Value {v} out of [0,1] range"
    print("  PASS test_preprocess_range")


def test_is_cnn():
    from find_num import _is_cnn

    mlp_w = {"w1": [], "b1": [], "w2": [], "b2": []}
    assert not _is_cnn(mlp_w), "MLP weights should not be CNN"
    cnn_w = {"conv1_w": [], "arch": "cnn"}
    assert _is_cnn(cnn_w), "CNN weights should be CNN"
    mixed_w = {"w1": [], "b1": []}
    assert not _is_cnn(mixed_w), "Weights without arch should default to MLP"
    print("  PASS test_is_cnn")


def test_recognize_single_digit_mlp():
    from find_num import _set_weights, recognize

    mock_weights = {
        "w1": [[0.01] * 576 for _ in range(32)],
        "b1": [0.0] * 32,
        "w2": [[0.0] * 32 for _ in range(10)],
        "b2": [0.0] * 10
    }
    for i in range(32):
        mock_weights["w2"][3][i] = 100.0

    _set_weights(mock_weights)

    screenshot = Image.new("RGB", (200, 100), color=(0, 0, 0))
    for x in range(10, 30):
        for y in range(10, 30):
            screenshot.putpixel((x, y), (255, 255, 255))

    config = {
        "test_num": {"x1": 10, "y1": 10, "x2": 30, "y2": 30, "digits": 1}
    }

    result = recognize(screenshot, config)
    assert "test_num" in result, "Should have 'test_num' key"
    assert result["test_num"] == "3", f"Expected '3', got {result['test_num']}"
    print("  PASS test_recognize_single_digit_mlp")


def test_recognize_two_digit_mlp():
    from find_num import _set_weights, recognize

    mock_weights = {
        "w1": [[0.01] * 576 for _ in range(32)],
        "b1": [0.0] * 32,
        "w2": [[0.0] * 32 for _ in range(10)],
        "b2": [0.0] * 10
    }
    for i in range(32):
        mock_weights["w2"][0][i] = 100.0

    _set_weights(mock_weights)

    screenshot = Image.new("RGB", (200, 100), color=(0, 0, 0))
    for x in range(10, 30):
        for y in range(10, 30):
            screenshot.putpixel((x, y), (255, 255, 255))
    for x in range(30, 50):
        for y in range(10, 30):
            screenshot.putpixel((x, y), (255, 255, 255))

    config = {
        "ammo": {"x1": 10, "y1": 10, "x2": 50, "y2": 30, "digits": 2}
    }

    result = recognize(screenshot, config)
    assert "ammo" in result, "Should have 'ammo' key"
    assert result["ammo"] == "00", f"Expected '00', got {result['ammo']}"
    print("  PASS test_recognize_two_digit_mlp")


def test_recognize_out_of_bounds():
    from find_num import _set_weights, recognize

    mock_weights = {
        "w1": [[0.01] * 576 for _ in range(32)],
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


def test_recognize_missing_field():
    from find_num import _set_weights, recognize

    mock_weights = {
        "w1": [[0.01] * 576 for _ in range(32)],
        "b1": [0.0] * 32,
        "w2": [[0.0] * 32 for _ in range(10)],
        "b2": [0.0] * 10
    }
    _set_weights(mock_weights)

    screenshot = Image.new("RGB", (100, 50))
    config = {"bad": {"x1": 10}}

    result = recognize(screenshot, config)
    assert result == {}, f"Expected empty dict for missing coords, got {result}"
    print("  PASS test_recognize_missing_field")


def test_recognize_negative_coords():
    from find_num import _set_weights, recognize

    mock_weights = {
        "w1": [[0.01] * 576 for _ in range(32)],
        "b1": [0.0] * 32,
        "w2": [[0.0] * 32 for _ in range(10)],
        "b2": [0.0] * 10
    }
    _set_weights(mock_weights)

    screenshot = Image.new("RGB", (100, 50))
    config = {"bad": {"x1": -5, "y1": 10, "x2": 20, "y2": 30, "digits": 1}}

    result = recognize(screenshot, config)
    assert result == {}, f"Expected empty dict for negative coords, got {result}"
    print("  PASS test_recognize_negative_coords")


def test_recognize_unsupported_digits():
    from find_num import _set_weights, recognize

    mock_weights = {
        "w1": [[0.01] * 576 for _ in range(32)],
        "b1": [0.0] * 32,
        "w2": [[0.0] * 32 for _ in range(10)],
        "b2": [0.0] * 10
    }
    _set_weights(mock_weights)

    screenshot = Image.new("RGB", (100, 50))
    config = {"bad": {"x1": 10, "y1": 10, "x2": 30, "y2": 30, "digits": 3}}

    result = recognize(screenshot, config)
    assert result == {}, f"Expected empty dict for unsupported digits, got {result}"
    print("  PASS test_recognize_unsupported_digits")


def test_end_to_end_mlp():
    from find_num import _set_weights, forward_mlp, preprocess

    samples = []
    template_rng = np.random.RandomState(42)
    templates = {}
    for digit in range(10):
        templates[digit] = (template_rng.randint(0, 256, (20, 20), dtype=np.uint8))

    for digit in range(10):
        for variant in range(20):
            base = templates[digit].astype(np.int16)
            noise_rng = np.random.RandomState(digit * 100 + variant)
            noise = noise_rng.randint(-30, 30, (20, 20), dtype=np.int16)
            arr = np.clip(base + noise, 0, 255).astype(np.uint8)
            img = Image.fromarray(arr, mode="L")
            vec = preprocess(img, size=16)  # MLP uses 16x16
            samples.append((vec, digit))

    X = np.array([s[0] for s in samples], dtype=np.float32)
    y = np.array([s[1] for s in samples], dtype=np.int64)

    rng = np.random.RandomState(42)
    w1 = (rng.randn(256, 32) * 0.01).astype(np.float32)
    b1 = np.zeros(32, dtype=np.float32)
    w2 = (rng.randn(32, 10) * 0.01).astype(np.float32)
    b2 = np.zeros(10, dtype=np.float32)

    lr = 0.01
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

        w2 -= lr * dw2
        b2 -= lr * db2
        w1 -= lr * dw1
        b1 -= lr * db1

        if epoch > 0 and epoch % 100 == 0:
            lr *= 0.5

        if epoch % 200 == 0:
            acc = np.mean(np.argmax(probs, axis=1) == y)
            print(f"    e2e train epoch {epoch} accuracy={acc:.3f}")

    mock_w = {
        "w1": w1.T.tolist(),
        "b1": b1.tolist(),
        "w2": w2.T.tolist(),
        "b2": b2.tolist(),
    }
    _set_weights(mock_w)

    correct = 0
    for vec, label in samples:
        idx = forward_mlp(vec, mock_w["w1"], mock_w["b1"], mock_w["w2"], mock_w["b2"])
        if idx == label:
            correct += 1
    acc = correct / len(samples)
    assert acc >= 0.5, f"E2E accuracy too low: {acc:.2f}"
    print(f"  PASS test_end_to_end_mlp (accuracy={acc:.2f})")


if __name__ == "__main__":
    test_forward_mlp()
    test_forward_cnn()
    test_load_config()
    test_load_weights()
    test_load_config_invalid_json()
    test_load_weights_invalid_json()
    test_preprocess()
    test_preprocess_normalize_range()
    test_is_cnn()
    test_recognize_single_digit_mlp()
    test_recognize_out_of_bounds()
    test_recognize_empty_config()
    test_recognize_two_digit_mlp()
    test_recognize_missing_field()
    test_recognize_negative_coords()
    test_recognize_unsupported_digits()
    test_end_to_end_mlp()
    print("All tests passed!")