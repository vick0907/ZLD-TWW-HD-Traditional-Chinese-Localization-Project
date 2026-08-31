"""Render a real converted message using the rebuilt font, exactly as the game would
look it up: CMAP -> glyph index -> atlas cell, advancing by the CWDH char width."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bffnt  # noqa: E402
import msbt  # noqa: E402
import sarc  # noqa: E402
from atlas import Atlas  # noqa: E402
from PIL import Image  # noqa: E402


def walk(blob, prefix, out):
    if blob[:4] == b"Yaz0":
        blob = sarc.yaz0_decompress(blob)
    for name, sub in sarc.sarc_read(blob):
        path = f"{prefix}/{name}"
        if sub[:4] in (b"Yaz0", b"SARC"):
            walk(sub, path, out)
        else:
            out[path] = sub


def render_line(font, atlas, text, scale=1):
    widths = font.cwdh[0][2]
    t = font.tglp
    total = 0
    for ch in text:
        idx = font.charmap.get(ord(ch))
        total += widths[idx][2] if idx is not None and idx < len(widths) else t.cell_w
    img = Image.new("L", (max(1, total), t.cell_h), 0)
    pen = 0
    for ch in text:
        idx = font.charmap.get(ord(ch))
        if idx is None:
            pen += t.cell_w
            continue
        left, glyph_w, adv = widths[idx]
        left = left - 256 if left > 127 else left
        cell = Image.fromarray(atlas.cell(idx))
        base = Image.new("L", img.size, 0)
        base.paste(cell, (pen + left, 0))
        img = Image.fromarray(np.maximum(np.asarray(img), np.asarray(base)))
        pen += adv
    return img


def main():
    pack_path, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    leaves = {}
    walk(open(pack_path, "rb").read(), "pack", leaves)
    font = bffnt.parse(next(v for k, v in leaves.items() if k.endswith("CKingMsg.bffnt")))
    atlas = Atlas(font)

    lines = []
    for path in sorted(leaves):
        if not path.endswith("message.msbt"):
            continue
        for segs in msbt.read(leaves[path])[0]:
            text = "".join(v for k, v in segs if k == "t").replace("\n", "")
            if 12 <= len(text) <= 26:
                lines.append(text)
            if len(lines) >= 12:
                break
        break

    rendered = [render_line(font, atlas, t) for t in lines]
    width = max(r.width for r in rendered)
    sheet = Image.new("L", (width, sum(r.height + 4 for r in rendered)), 0)
    y = 0
    for r in rendered:
        sheet.paste(r, (0, y))
        y += r.height + 4
    sheet.save(os.path.join(outdir, "preview.png"))
    open(os.path.join(outdir, "preview.txt"), "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(f"  {t}" for t in lines))
    print("wrote", os.path.join(outdir, "preview.png"))


if __name__ == "__main__":
    main()
