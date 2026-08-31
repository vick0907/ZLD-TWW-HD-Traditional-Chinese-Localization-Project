"""Re-save PNGs without metadata, keeping the pixels bit-for-bit identical."""
import sys

import numpy as np
from PIL import Image


def strip(path):
    original = Image.open(path)
    before = np.asarray(original.convert("RGBA"))
    clean = Image.frombytes(original.mode, original.size, original.tobytes())
    clean.save(path, optimize=True)

    after = np.asarray(Image.open(path).convert("RGBA"))
    assert np.array_equal(before, after), f"{path}: pixels changed"
    return before.shape


for path in sys.argv[1:]:
    shape = strip(path)
    print(f"stripped {path}  ({shape[1]}x{shape[0]}, pixels verified identical)")
