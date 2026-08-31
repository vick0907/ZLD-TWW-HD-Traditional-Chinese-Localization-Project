"""Compare the pixel-value distribution of original glyphs against ones we added.

Hard-thresholded glyphs only use a few grey levels; the game's own glyphs are
antialiased, which is what makes added characters look rougher on screen.
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bffnt  # noqa: E402
from atlas import Atlas  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bffnt")
    ap.add_argument("--original", default="我的了一人")
    ap.add_argument("--added", default="們開這時來")
    ap.add_argument("--dump")
    args = ap.parse_args()

    font = bffnt.parse(open(args.bffnt, "rb").read())
    atlas = Atlas(font)

    for label, chars in (("original", args.original), ("added", args.added)):
        print(f"=== {label} glyphs ===")
        for ch in chars:
            cell = atlas.cell_for_char(ch)
            if cell is None:
                print(f"  {ch}: not in font")
                continue
            levels = len(np.unique(cell))
            mid = int(((cell > 16) & (cell < 239)).sum())
            print(f"  {ch}  distinct grey levels={levels:<4} soft-edge pixels={mid}")
            if args.dump:
                os.makedirs(args.dump, exist_ok=True)
                Image.fromarray(cell).resize((cell.shape[1] * 6, cell.shape[0] * 6),
                                             Image.NEAREST).save(
                    os.path.join(args.dump, f"{label}_{ord(ch):04X}.png"))
        print()


if __name__ == "__main__":
    main()
