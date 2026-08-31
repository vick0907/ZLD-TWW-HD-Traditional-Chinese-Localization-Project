"""Align glyph indices to atlas cells by comparing CWDH widths with measured ink widths."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bffnt  # noqa: E402
from decode_font import sheet_swizzle, sheet_to_image  # noqa: E402


def main():
    path = sys.argv[1]
    out = sys.argv[2]
    f = bffnt.parse(open(path, "rb").read())
    t = f.tglp
    widths = f.cwdh[0][2]

    measured = []
    for s in range(t.sheet_count):
        img = sheet_to_image(t.sheets[s], t.sheet_width, t.sheet_height, 4, sheet_swizzle(s))
        a = np.asarray(img)
        for cell in range(t.per_sheet):
            row, col = divmod(cell, t.columns)
            sub = a[row * t.cell_height:(row + 1) * t.cell_height,
                    col * t.cell_width:(col + 1) * t.cell_width]
            cols_with_ink = np.nonzero(sub.max(axis=0) > 96)[0]
            measured.append(0 if len(cols_with_ink) == 0
                            else int(cols_with_ink.max() - cols_with_ink.min() + 1))

    declared = [w[1] for w in widths]
    lines = [f"cells={len(measured)} cwdh={len(declared)}"]

    def score(offset, limit=200):
        errs = []
        for i, d in enumerate(declared[:limit]):
            j = i + offset
            if 0 <= j < len(measured):
                errs.append(abs(measured[j] - d))
        return sum(errs) / len(errs) if errs else 1e9

    best = sorted((score(off), off) for off in range(0, 5520 - 200))
    lines.append("best offsets (mean abs width error over first 200 glyphs):")
    for sc, off in best[:8]:
        lines.append(f"  {sc:8.3f}  offset={off}")
    lines.append("\nmeasured[0:60]  " + " ".join(f"{v:2d}" for v in measured[:60]))
    lines.append("declared[0:60]  " + " ".join(f"{v:2d}" for v in declared[:60]))
    off = best[0][1]
    lines.append(f"measured[{off}:{off+60}]  " +
                 " ".join(f"{v:2d}" for v in measured[off:off + 60]))
    open(out, "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
