"""Try micro-tile bit orders for bpp=64 and score decoded sheet smoothness."""
import itertools
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bffnt  # noqa: E402
import gx2_addr  # noqa: E402
import texture2ddecoder  # noqa: E402
from PIL import Image  # noqa: E402

ORDERS = {
    "y0x0x1x2y1y2": ("y0", "x0", "x1", "x2", "y1", "y2"),
    "x0y0x1x2y1y2": ("x0", "y0", "x1", "x2", "y1", "y2"),
    "x0y0x1y1x2y2": ("x0", "y0", "x1", "y1", "x2", "y2"),
    "y0x0x1y1x2y2": ("y0", "x0", "x1", "y1", "x2", "y2"),
    "x0x1y0x2y1y2": ("x0", "x1", "y0", "x2", "y1", "y2"),
    "x0x1x2y0y1y2": ("x0", "x1", "x2", "y0", "y1", "y2"),
}


def patched_index(order):
    def fn(x, y, z, bpp, tile_mode, is_depth):
        vals = {"x0": x & 1, "x1": (x >> 1) & 1, "x2": (x >> 2) & 1,
                "y0": y & 1, "y1": (y >> 1) & 1, "y2": (y >> 2) & 1}
        return sum(vals[name] << i for i, name in enumerate(order))
    return fn


def main():
    path, sheet_idx, outdir = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    os.makedirs(outdir, exist_ok=True)
    f = bffnt.parse(open(path, "rb").read())
    t = f.tglp
    sheet = t.sheets[sheet_idx]
    original = gx2_addr.pixel_index_within_micro_tile
    results = []
    for name, order in ORDERS.items():
        gx2_addr.pixel_index_within_micro_tile = patched_index(order)
        linear = gx2_addr.untile(sheet, t.sheet_width // 4, t.sheet_height // 4,
                                 64, 4, (2 * sheet_idx) % 8, 0)
        raw = texture2ddecoder.decode_bc4(linear, t.sheet_width, t.sheet_height)
        img = Image.frombytes("RGBA", (t.sheet_width, t.sheet_height), raw,
                              "raw", "BGRA").getchannel("R")
        a = np.asarray(img, dtype=np.int32)
        tv = int(np.abs(np.diff(a, axis=1)).sum() + np.abs(np.diff(a, axis=0)).sum())
        img.save(os.path.join(outdir, f"order_{name}.png"))
        results.append((tv, name))
    gx2_addr.pixel_index_within_micro_tile = original
    results.sort()
    for tv, name in results:
        print(f"  TV={tv:12d}  {name}")


if __name__ == "__main__":
    main()
