"""Inspect existing glyph cells: widths and rendered bounding boxes."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bffnt  # noqa: E402
from decode_font import sheet_swizzle, sheet_to_image  # noqa: E402
from PIL import Image  # noqa: E402


def main():
    path, outdir = sys.argv[1], sys.argv[2]
    chars = sys.argv[3]
    os.makedirs(outdir, exist_ok=True)
    f = bffnt.parse(open(path, "rb").read())
    t = f.tglp
    widths = f.cwdh[0][2]

    cache = {}
    lines = []
    strip = Image.new("L", (t.cell_width * len(chars), t.cell_height))
    for n, ch in enumerate(chars):
        idx = f.charmap.get(ord(ch))
        if idx is None:
            lines.append(f"{ch!r}: not in font")
            continue
        s, rem = divmod(idx, t.per_sheet)
        row, col = divmod(rem, t.columns)
        if s not in cache:
            cache[s] = sheet_to_image(t.sheets[s], t.sheet_width, t.sheet_height,
                                      4, sheet_swizzle(s))
        box = (col * t.cell_width, row * t.cell_height,
               (col + 1) * t.cell_width, (row + 1) * t.cell_height)
        cell = cache[s].crop(box)
        strip.paste(cell, (n * t.cell_width, 0))
        a = np.asarray(cell)
        ys, xs = np.nonzero(a > 32)
        bbox = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())) if len(xs) else None
        lines.append(f"{ch!r} idx={idx} sheet={s} row={row} col={col} "
                     f"cwdh={widths[idx] if idx < len(widths) else None} ink_bbox={bbox}")
    strip.resize((strip.width * 4, strip.height * 4), Image.NEAREST).save(
        os.path.join(outdir, "glyph_strip.png"))
    report = "\n".join(lines)
    open(os.path.join(outdir, "glyph_metrics.txt"), "w", encoding="utf-8").write(report)
    print(report[:400])


if __name__ == "__main__":
    main()
