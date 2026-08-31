"""Brute-force the GX2 tile mode / swizzle for a BFFNT sheet and score legibility."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bffnt  # noqa: E402
import gx2_addr  # noqa: E402
import texture2ddecoder  # noqa: E402
from PIL import Image  # noqa: E402


def decode(sheet_bytes, w, h, tile_mode, swizzle, slice_index):
    bw, bh = w // 4, h // 4
    linear = gx2_addr.untile(sheet_bytes, bw, bh, 64, tile_mode, swizzle, slice_index)
    raw = texture2ddecoder.decode_etc1(linear, w, h)
    return Image.frombytes("RGBA", (w, h), raw, "raw", "BGRA").convert("L")


def score(img, cols, rows, cell_w, cell_h):
    px = img.load()
    w, h = img.size
    # margins beyond the glyph grid must be empty
    margin_sum = 0
    margin_n = 0
    for y in range(rows * cell_h, h):
        for x in range(0, w, 2):
            margin_sum += px[x, y]
            margin_n += 1
    for x in range(cols * cell_w, w):
        for y in range(0, rows * cell_h, 2):
            margin_sum += px[x, y]
            margin_n += 1
    margin = margin_sum / max(1, margin_n)
    # horizontal smoothness inside the grid (glyph strokes are contiguous)
    tv = 0
    n = 0
    for y in range(0, rows * cell_h, 4):
        prev = px[0, y]
        for x in range(1, cols * cell_w):
            cur = px[x, y]
            tv += abs(cur - prev)
            prev = cur
            n += 1
    return margin, tv / max(1, n)


def main():
    path, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    f = bffnt.parse(open(path, "rb").read())
    t = f.tglp
    results = []
    for tile_mode in (2, 4):
        for swizzle in range(8):
            img = decode(t.sheets[0], t.sheet_width, t.sheet_height, tile_mode, swizzle, 0)
            m, tv = score(img, t.columns, t.rows, t.cell_width, t.cell_height)
            results.append((tv, m, tile_mode, swizzle))
            img.save(os.path.join(outdir, f"tm{tile_mode}_sw{swizzle}.png"))
    results.sort()
    for tv, m, tile_mode, swizzle in results:
        print(f"tileMode={tile_mode} swizzle={swizzle}  smoothness={tv:8.2f}  margin={m:7.3f}")


if __name__ == "__main__":
    main()
