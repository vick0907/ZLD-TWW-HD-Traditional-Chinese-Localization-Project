"""Measure the pixel-value profile of existing glyphs so new ones can match."""
import collections
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bffnt  # noqa: E402
from decode_font import sheet_swizzle, sheet_to_image  # noqa: E402


def main():
    path, out = sys.argv[1], sys.argv[2]
    chars = sys.argv[3]
    f = bffnt.parse(open(path, "rb").read())
    t = f.tglp
    cache = {}
    lines = []
    hist = collections.Counter()
    for ch in chars:
        idx = f.charmap.get(ord(ch))
        if idx is None:
            continue
        s, rem = divmod(idx, t.per_sheet)
        row, col = divmod(rem, t.columns)
        if s not in cache:
            cache[s] = np.asarray(sheet_to_image(t.sheets[s], t.sheet_width,
                                                 t.sheet_height, 4, sheet_swizzle(s)))
        cell = cache[s][row * t.cell_height:(row + 1) * t.cell_height,
                        col * t.cell_width:(col + 1) * t.cell_width]
        hist.update(cell.ravel().tolist())
        core = np.nonzero(cell >= 250)
        halo = np.nonzero((cell > 20) & (cell < 250))
        lines.append(
            f"{ch!r}: core_bbox="
            f"{(int(core[1].min()), int(core[0].min()), int(core[1].max()), int(core[0].max())) if len(core[0]) else None}"
            f"  halo_px={len(halo[0])}  core_px={len(core[0])}")
    lines.append("\nvalue histogram (top 20):")
    for v, n in hist.most_common(20):
        lines.append(f"  {v:3d} -> {n}")
    open(out, "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
