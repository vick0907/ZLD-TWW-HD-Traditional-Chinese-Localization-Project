"""Identify the GX2 tiling by testing which candidate makes the untiled sheet
periodic with the glyph cell pitch (cell_width x cell_height)."""
import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bffnt  # noqa: E402
import gx2_addr  # noqa: E402

EMPTY = bytes.fromhex("0100499224499224")


def periodicity(profile, period):
    """Ratio of folded variance to overall variance: high = strongly periodic."""
    n = len(profile)
    folded = [0.0] * period
    counts = [0] * period
    for i, v in enumerate(profile):
        folded[i % period] += v
        counts[i % period] += 1
    folded = [folded[i] / counts[i] for i in range(period)]
    mean = sum(profile) / n
    var_total = sum((v - mean) ** 2 for v in profile) / n
    var_folded = sum((v - mean) ** 2 for v in folded) / period
    return var_folded / var_total if var_total else 0.0


def score_map(sheet, addrs, bw, bh, cell_w, cell_h):
    col = [0] * bw
    row = [0] * bh
    for i, a in enumerate(addrs):
        if sheet[a:a + 8] != EMPTY:
            col[i % bw] += 1
            row[i // bw] += 1
    col_px = [col[i // 4] for i in range(bw * 4)]
    row_px = [row[i // 4] for i in range(bh * 4)]
    return periodicity(col_px, cell_w) + periodicity(row_px, cell_h)


def main():
    path = sys.argv[1]
    sheet_idx = int(sys.argv[2])
    f = bffnt.parse(open(path, "rb").read())
    t = f.tglp
    bw, bh = t.sheet_width // 4, t.sheet_height // 4
    sheet = t.sheets[sheet_idx]

    baseline = score_map(sheet, [i * 8 for i in range(bw * bh)], bw, bh,
                         t.cell_width, t.cell_height)
    print(f"raw/tiled baseline score = {baseline:.4f}")

    results = []
    for tile_mode, swizzle, mtt, direction in itertools.product(
            (2, 3, 4, 5, 6, 7, 8, 9, 10), range(8), (0, 1, 2), ("fwd", "rev")):
        try:
            addrs, _ = gx2_addr.build_address_map(bw, bh, 64, tile_mode, swizzle, mtt)
        except Exception:
            continue
        if max(addrs) + 8 > len(sheet):
            continue
        if direction == "rev":
            inv = [0] * len(addrs)
            for i, a in enumerate(addrs):
                inv[a // 8] = i * 8
            addrs = inv
        results.append((score_map(sheet, addrs, bw, bh, t.cell_width, t.cell_height),
                        tile_mode, swizzle, mtt, direction))
    results.sort(reverse=True)
    for s, tm, sw, mtt, d in results[:10]:
        print(f"  {s:8.4f}  tileMode={tm} swizzle={sw} microTileType={mtt} {d}")


if __name__ == "__main__":
    main()
