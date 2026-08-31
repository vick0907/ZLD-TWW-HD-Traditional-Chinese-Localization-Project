"""Try tile mode / swizzle / slice combinations and dump decoded sheets."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bffnt  # noqa: E402
import gx2_addr  # noqa: E402
import texture2ddecoder  # noqa: E402
from PIL import Image  # noqa: E402


def decode_sheet(sheet, w, h, tile_mode, swizzle, slice_index):
    linear = gx2_addr.untile(sheet, w // 4, h // 4, 64, tile_mode, swizzle, slice_index)
    raw = texture2ddecoder.decode_etc1(linear, w, h)
    return Image.frombytes("RGBA", (w, h), raw, "raw", "BGRA").convert("L")


def sharpness(img):
    px = list(img.getdata())
    w, h = img.size
    tv = 0
    for y in range(0, h, 3):
        base = y * w
        for x in range(1, w):
            tv += abs(px[base + x] - px[base + x - 1])
    return tv


def main():
    path, sheet_idx, outdir = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    os.makedirs(outdir, exist_ok=True)
    f = bffnt.parse(open(path, "rb").read())
    t = f.tglp
    results = []
    for swizzle in range(8):
        img = decode_sheet(t.sheets[sheet_idx], t.sheet_width, t.sheet_height,
                           4, swizzle, 0)
        s = sharpness(img)
        img.save(os.path.join(outdir, f"s{sheet_idx}_tm4_sw{swizzle}.png"))
        results.append((s, swizzle))
    results.sort()
    for s, sw in results:
        print(f"  swizzle={sw}  edge-energy={s}")


if __name__ == "__main__":
    main()
