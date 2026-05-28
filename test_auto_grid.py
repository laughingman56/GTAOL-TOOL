import numpy as np
import pytest
from PIL import Image
from auto_grid import _binarize, _horizontal_projection, _vertical_projection, _smooth


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
    assert result[2] > 0
