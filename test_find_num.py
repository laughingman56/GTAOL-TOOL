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


if __name__ == "__main__":
    test_forward()
    test_load_config()
    test_load_weights()
    test_load_config_invalid_json()
    test_load_weights_invalid_json()
    print("All tests passed!")
