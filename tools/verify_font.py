"""Verify a rebuilt BFFNT: old glyphs untouched, new glyphs render correctly."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bffnt  # noqa: E402
from atlas import Atlas  # noqa: E402
from PIL import Image  # noqa: E402


def main():
    old_path, new_path, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    sample = sys.argv[4] if len(sys.argv) > 4 else "風國來說們這時會對開薩爾達魯儂"
    os.makedirs(outdir, exist_ok=True)
    old = bffnt.parse(open(old_path, "rb").read())
    new = bffnt.parse(open(new_path, "rb").read())

    lines = [f"old glyphs={len(old.charmap)} new glyphs={len(new.charmap)}"]

    moved = [chr(c) for c, i in old.charmap.items() if new.charmap.get(c) != i]
    lines.append(f"existing chars that changed index: {len(moved)} {''.join(moved[:20])}")

    same_sheets = [i for i in range(old.tglp.sheet_count)
                   if old.tglp.sheets[i] == new.tglp.sheets[i]]
    lines.append(f"byte-identical sheets: {same_sheets}")

    a_old, a_new = Atlas(old), Atlas(new)
    diffs = []
    for c, i in old.charmap.items():
        if i >= old.tglp.per_sheet * 9:      # only sheets 9+ were rewritten
            d = np.abs(a_old.cell(i).astype(int) - a_new.cell(i).astype(int)).mean()
            if d > 1.0:
                diffs.append((d, chr(c)))
    diffs.sort(reverse=True)
    lines.append(f"pre-existing glyphs on rewritten sheets that changed: {len(diffs)}"
                 f" worst={diffs[:5]}")

    strip = Image.new("L", (new.tglp.cell_w * len(sample), new.tglp.cell_h))
    missing = []
    for n, ch in enumerate(sample):
        cell = a_new.cell_for_char(ch)
        if cell is None:
            missing.append(ch)
            continue
        strip.paste(Image.fromarray(cell), (n * new.tglp.cell_w, 0))
    strip.resize((strip.width * 4, strip.height * 4), Image.NEAREST).save(
        os.path.join(outdir, "new_glyphs.png"))
    lines.append(f"sample chars missing from new font: {''.join(missing)!r}")

    widths = new.cwdh[0][2]
    lines.append(f"cwdh entries={len(widths)} (need {len(new.charmap)})")
    open(os.path.join(outdir, "verify.txt"), "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
