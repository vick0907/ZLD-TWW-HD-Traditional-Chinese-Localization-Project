"""Solve the Wii U macro-tile layout empirically.

Within one 32x16-block macro tile the address reduces to

    addr = base + (e >= 256) * 2048 + bp * 256 + (e & 0xFF)

with e = 8 * mortonIndex and bp in 0..7 a bijection of the 8 micro tiles.
We search every invertible GF(2) map (mx0, mx1, my0) -> bp plus a constant XOR,
scoring by total variation of the "is this block empty" bitmap: the correct
layout makes glyph strokes contiguous.
"""
import itertools
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bffnt  # noqa: E402

EMPTY = bytes.fromhex("0100499224499224")

MORTON_VARIANTS = {
    "nondisp": (0, 1, 2, 3, 4, 5),   # x0 y0 x1 y1 x2 y2
    "disp64": None,                  # x0 y0 x1 x2 y1 y2
}


def morton_index(px, py, variant):
    x0, x1, x2 = px & 1, (px >> 1) & 1, (px >> 2) & 1
    y0, y1, y2 = py & 1, (py >> 1) & 1, (py >> 2) & 1
    if variant == "nondisp":
        bits = (x0, y0, x1, y1, x2, y2)
    else:
        bits = (x0, y0, x1, x2, y1, y2)
    return sum(b << i for i, b in enumerate(bits))


def invertible_matrices():
    for cols in itertools.product(range(8), repeat=3):
        rows = []
        for r in range(3):
            rows.append([(c >> r) & 1 for c in cols])
        m = np.array(rows, dtype=np.uint8)
        # rank over GF(2)
        a = m.copy()
        rank = 0
        for col in range(3):
            piv = None
            for r in range(rank, 3):
                if a[r, col]:
                    piv = r
                    break
            if piv is None:
                continue
            a[[rank, piv]] = a[[piv, rank]]
            for r in range(3):
                if r != rank and a[r, col]:
                    a[r] ^= a[rank]
            rank += 1
        if rank == 3:
            yield cols


def build_addresses(bw, bh, cols, xor, variant):
    x = np.arange(bw, dtype=np.int64)[None, :].repeat(bh, axis=0)
    y = np.arange(bh, dtype=np.int64)[:, None].repeat(bw, axis=1)
    mtx, mty = x // 32, y // 16
    base = (mtx + (bw // 32) * mty) * 4096
    mx = (x % 32) // 8
    my = (y % 16) // 8
    mx0, mx1, my0 = mx & 1, (mx >> 1) & 1, my & 1
    bp = np.zeros_like(x)
    for bit, src in enumerate((mx0, mx1, my0)):
        bp ^= np.where(src == 1, cols[bit], 0)
    bp ^= xor
    px, py = x % 8, y % 8
    mi = np.vectorize(lambda a, b: morton_index(a, b, variant))(px, py)
    e = mi * 8
    return base + (e >= 256) * 2048 + bp * 256 + (e & 0xFF)


def main():
    path, sheet_idx = sys.argv[1], int(sys.argv[2])
    f = bffnt.parse(open(path, "rb").read())
    t = f.tglp
    bw, bh = t.sheet_width // 4, t.sheet_height // 4
    sheet = np.frombuffer(t.sheets[sheet_idx], dtype=np.uint8).reshape(-1, 8)
    empty_flat = np.all(sheet == np.frombuffer(EMPTY, dtype=np.uint8), axis=1)

    best = []
    mats = list(invertible_matrices())
    print(f"{len(mats)} invertible matrices x 8 xors x 2 morton variants")
    for variant in ("nondisp", "disp64"):
        for cols in mats:
            for xor in range(8):
                addrs = build_addresses(bw, bh, cols, xor, variant)
                img = empty_flat[(addrs // 8).ravel()].reshape(bh, bw)
                tv = int(np.count_nonzero(img[:, 1:] != img[:, :-1]) +
                         np.count_nonzero(img[1:, :] != img[:-1, :]))
                best.append((tv, cols, xor, variant))
    best.sort()
    for tv, cols, xor, variant in best[:8]:
        print(f"  TV={tv:7d}  cols={cols} xor={xor} morton={variant}")
    print("  ...")
    for tv, cols, xor, variant in best[-3:]:
        print(f"  TV={tv:7d}  cols={cols} xor={xor} morton={variant}  (worst)")


if __name__ == "__main__":
    main()
