import numpy as np
import pytest
from PIL import Image, ImageDraw
from auto_grid import _binarize, _horizontal_projection, _vertical_projection, _smooth, _coarse_locate, GridDetectError


def test_binarize_auto_threshold():
    img = Image.new("RGB", (100, 50), color=(0, 0, 0))
    for x in range(20, 30):
        for y in range(10, 20):
            img.putpixel((x, y), (255, 255, 255))
    binary = _binarize(img)
    assert binary.shape == (50, 100)
    assert binary.dtype == np.uint8
    assert binary.sum() > 0


def test_binarize_explicit_threshold():
    img = Image.new("RGB", (10, 10), color=(100, 100, 100))
    binary = _binarize(img, threshold=128)
    assert binary.sum() == 0
    binary = _binarize(img, threshold=50)
    assert binary.sum() == 100


def test_horizontal_projection():
    binary = np.array([
        [1, 0, 1],
        [0, 0, 0],
        [1, 1, 1],
    ], dtype=np.uint8)
    proj = _horizontal_projection(binary)
    assert proj.tolist() == [2, 0, 3]


def test_vertical_projection():
    binary = np.array([
        [1, 0, 1],
        [0, 0, 0],
        [1, 1, 1],
    ], dtype=np.uint8)
    proj = _vertical_projection(binary)
    assert proj.tolist() == [2, 1, 2]


def test_smooth():
    arr = np.array([0, 0, 10, 0, 0], dtype=np.float64)
    result = _smooth(arr, window=3)
    assert len(result) == len(arr)
    expected = np.array([0.0, 10/3, 10/3, 10/3, 0.0])
    assert np.allclose(result, expected, atol=0.01)


def test_coarse_locate_detects_grid():
    img = Image.new("RGB", (400, 300), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    for r in range(8):
        for c in range(10):
            x = 80 + c * 24
            y = 100 + r * 20
            draw.text((x, y), "42", fill=(255, 255, 255))
    grid_region, targets = _coarse_locate(img)
    assert len(grid_region) == 4
    assert grid_region[1] <= 100 <= grid_region[3]
    assert isinstance(targets, list)


def test_coarse_locate_dark_image_raises():
    img = Image.new("RGB", (100, 100), color=(0, 0, 0))
    with pytest.raises(GridDetectError):
        _coarse_locate(img)


from auto_grid import _detect_rows, _detect_columns


def test_detect_rows_8_rows():
    img = Image.new("RGB", (240, 200), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    for r in range(8):
        y = 20 + r * 20
        for c in range(10):
            x = 10 + c * 22
            draw.text((x, y), "42", fill=(255, 255, 255))
    y_lines, regions = _detect_rows(img, num_rows=8)
    assert len(y_lines) == 8
    for i in range(1, 8):
        assert y_lines[i] > y_lines[i - 1]


def test_detect_columns_10_cols():
    img = Image.new("RGB", (260, 20), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    for c in range(10):
        x = 10 + c * 24
        draw.text((x, 2), "42", fill=(255, 255, 255))
    x_lines = _detect_columns(img, num_cols=10)
    assert len(x_lines) == 10
    for i in range(1, 10):
        assert x_lines[i] > x_lines[i - 1]


def test_detect_rows_error_on_empty():
    img = Image.new("RGB", (100, 100), color=(0, 0, 0))
    with pytest.raises(GridDetectError):
        _detect_rows(img, num_rows=8)


def test_detect_columns_error_on_empty():
    img = Image.new("RGB", (100, 10), color=(0, 0, 0))
    with pytest.raises(GridDetectError):
        _detect_columns(img, num_cols=10)
