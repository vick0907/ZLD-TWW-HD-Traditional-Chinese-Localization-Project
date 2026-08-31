"""Render the first N cells of a sheet in index order for visual comparison."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bffnt  # noqa: E402
from decode_font import sheet_swizzle, sheet_to_image  # noqa: E402
from PIL import Image  # noqa: E402


def main():
    path, sheet_idx, count, outpng = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    f = bffnt.parse(open(path, "rb").read())
    t = f.tglp
    img = sheet_to_image(t.sheets[sheet_idx], t.sheet_width, t.sheet_height,
                         4, sheet_swizzle(sheet_idx))
    per_row = 20
    rows = (count + per_row - 1) // per_row
    out = Image.new("L", (per_row * (t.cell_width + 2), rows * (t.cell_height + 2)))
    for i in range(count):
        row, col = divmod(i, t.columns)
        box = (col * t.cell_width, row * t.cell_height,
               (col + 1) * t.cell_width, (row + 1) * t.cell_height)
        r, c = divmod(i, per_row)
        out.paste(img.crop(box), (c * (t.cell_width + 2), r * (t.cell_height + 2)))
    out.save(outpng)

    inv = {}
    for code, idx in f.charmap.items():
        inv.setdefault(idx, chr(code))
    expected = "".join(inv.get(i, "?") for i in range(count))
    print("expected order:", repr(expected))


if __name__ == "__main__":
    main()
