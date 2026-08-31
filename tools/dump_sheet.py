"""Dump a BFFNT sheet as PNG, optionally trying Wii U GX2 detiling."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bffnt  # noqa: E402
import texture2ddecoder  # noqa: E402
from PIL import Image  # noqa: E402


def decode_etc1(data: bytes, w: int, h: int) -> Image.Image:
    raw = texture2ddecoder.decode_etc1(data, w, h)
    return Image.frombytes("RGBA", (w, h), raw, "raw", "BGRA")


def main():
    path, sheet_idx, outpng = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    f = bffnt.parse(open(path, "rb").read())
    t = f.tglp
    data = t.sheets[sheet_idx]
    print(f"sheet {sheet_idx}: {len(data)} bytes, {t.sheet_width}x{t.sheet_height}, fmt={t.fmt}")
    img = decode_etc1(data, t.sheet_width, t.sheet_height)
    img.convert("L").save(outpng)
    print("wrote", outpng)


if __name__ == "__main__":
    main()
