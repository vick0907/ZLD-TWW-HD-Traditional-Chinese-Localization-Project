"""Drop hand-drawn logo artwork onto a game texture, keying out its black background.

Used to put a redrawn 薩爾達傳說 back into TitleLogoZelda while keeping the
original English wordmark that sits above it.
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image


def key_black(img, lo, hi):
    """Turn a black-backed RGB image into RGBA, ramping alpha between lo and hi."""
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    lum = a.max(axis=2)
    alpha = np.clip((lum - lo) / max(1, hi - lo), 0, 1)
    # undo the black matte so semi-transparent edges keep their colour
    rgb = np.where(alpha[..., None] > 0.02, a / np.maximum(alpha[..., None], 0.02), 0)
    out = np.concatenate([np.clip(rgb, 0, 255), alpha[..., None] * 255], axis=2)
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def trim(img):
    a = np.asarray(img)
    ys, xs = np.nonzero(a[..., 3] > 8)
    return img.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("art")
    ap.add_argument("base", help="texture to composite onto (already has the parts to keep)")
    ap.add_argument("out")
    ap.add_argument("--box", required=True, help="x0,y0,x1,y1 area to fit the artwork into")
    ap.add_argument("--key-lo", type=float, default=6)
    ap.add_argument("--key-hi", type=float, default=26)
    ap.add_argument("--anchor", default="center", choices=["center", "top", "bottom"])
    args = ap.parse_args()

    art = trim(key_black(Image.open(args.art), args.key_lo, args.key_hi))
    base = Image.open(args.base).convert("RGBA")

    x0, y0, x1, y1 = (int(v) for v in args.box.split(","))
    bw, bh = x1 - x0 + 1, y1 - y0 + 1
    s = min(bw / art.width, bh / art.height)
    w, h = max(1, round(art.width * s)), max(1, round(art.height * s))
    art = art.resize((w, h), Image.LANCZOS)

    ox = x0 + (bw - w) // 2
    oy = {"center": y0 + (bh - h) // 2, "top": y0, "bottom": y1 - h + 1}[args.anchor]

    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    layer.paste(art, (ox, oy))
    Image.alpha_composite(base, layer).save(args.out)
    print(f"art {art.width}x{art.height} at ({ox},{oy}) -> {args.out} {base.size}")


if __name__ == "__main__":
    main()
