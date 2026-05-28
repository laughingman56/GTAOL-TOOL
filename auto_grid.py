"""Auto-detect grid and targets from screenshot using pixel projection."""

import numpy as np
from PIL import Image


class GridDetectError(Exception):
    pass


def _binarize(image, threshold=None):

    gray = np.array(image.convert("L"), dtype=np.float32)
    if threshold is None:
        threshold = gray.mean() * 1.2
    return (gray > threshold).astype(np.uint8)


def _horizontal_projection(binary):

    return binary.sum(axis=1).astype(np.int32)


def _vertical_projection(binary):

    return binary.sum(axis=0).astype(np.int32)


def _smooth(arr, window=5):

    kernel = np.ones(window) / window
    return np.convolve(arr, kernel, mode="same")
