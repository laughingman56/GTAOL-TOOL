import math


def test_forward():
    from find_num import forward

    w1 = [[0.1] * 256 for _ in range(32)]
    b1 = [0.0] * 32
    w2 = [[0.1] * 32 for _ in range(10)]
    b2 = [0.0] * 10

    x = [0.5] * 256
    result = forward(x, w1, b1, w2, b2)

    assert 0 <= result <= 9, f"Expected 0-9, got {result}"
    print("  PASS test_forward_bound")

    w2_biased = [[0.0] * 32 for _ in range(10)]
    for i in range(32):
        w2_biased[3][i] = 100.0
    b2_biased = [0.0] * 10
    result = forward(x, w1, b1, w2_biased, b2_biased)
    assert result == 3, f"Expected 3 with biased weights, got {result}"
    print("  PASS test_forward_biased")


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


from PIL import Image


def test_recognize_single_digit():
    from find_num import _get_weights, _set_weights, recognize, load_config

    mock_weights = {
        "w1": [[0.01] * 256 for _ in range(32)],
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


def test_recognize_two_digit():
    from find_num import _set_weights, recognize

    mock_weights = {
        "w1": [[0.01] * 256 for _ in range(32)],
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
    print("  PASS test_recognize_two_digit")


def test_recognize_missing_field():
    from find_num import _set_weights, recognize

    mock_weights = {
        "w1": [[0.01] * 256 for _ in range(32)],
        "b1": [0.0] * 32,
        "w2": [[0.0] * 32 for _ in range(10)],
        "b2": [0.0] * 10
    }
    _set_weights(mock_weights)

    screenshot = Image.new("RGB", (100, 50))
    config = {"bad": {"x1": 10}}  # missing y1/x2/y2

    result = recognize(screenshot, config)
    assert result == {}, f"Expected empty dict for missing coords, got {result}"
    print("  PASS test_recognize_missing_field")


def test_recognize_negative_coords():
    from find_num import _set_weights, recognize

    mock_weights = {
        "w1": [[0.01] * 256 for _ in range(32)],
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
        "w1": [[0.01] * 256 for _ in range(32)],
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


if __name__ == "__main__":
    test_forward()
    test_load_config()
    test_load_weights()
    test_load_config_invalid_json()
    test_load_weights_invalid_json()
    test_preprocess()
    test_preprocess_normalize_range()
    test_recognize_single_digit()
    test_recognize_out_of_bounds()
    test_recognize_empty_config()
    test_recognize_two_digit()
    test_recognize_missing_field()
    test_recognize_negative_coords()
    test_recognize_unsupported_digits()
    print("All tests passed!")
