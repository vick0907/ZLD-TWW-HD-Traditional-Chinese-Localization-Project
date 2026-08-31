"""Replace whole characters in a title-logo texture, keeping the artwork's style.

Used for 塞尔达传说 -> 薩爾達傳說: the strokes to remove are found by colour, the
replacements are drawn from a font and coloured with the logo's own row gradient.
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retitle import label_mask, ownership  # noqa: E402

SUPERSAMPLE = 4


def fill_mask(a, hue):
    al, r, g, b = a[..., 3], a[..., 0], a[..., 1], a[..., 2]
    if hue == "red":
        return (al > 128) & (r - g > 50) & (r - b > 50)
    return (al > 128) & (b - r > 40)


def render(ch, font_path, box, index=0, variation=None, weight=0):
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0 + 1, y1 - y0 + 1
    size = max(bw, bh) * SUPERSAMPLE
    font = ImageFont.truetype(font_path, size, index=index)
    if variation:
        font.set_variation_by_name(variation)
    big = Image.new("L", (size * 2, size * 2), 0)
    ImageDraw.Draw(big).text((size // 2, size // 2), ch, fill=255, font=font, anchor="lt")
    arr = np.asarray(big) > 40
    ys, xs = np.nonzero(arr)
    crop = Image.fromarray((arr * 255).astype(np.uint8)).crop(
        (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    small = crop.resize((bw, bh), Image.LANCZOS)
    m = np.asarray(small) > 115
    if weight:
        m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(
            ImageFilter.MaxFilter(2 * weight + 1))) > 0
    return m


def depth_from_top(mask):
    """For each pixel, how many mask pixels sit directly above it in the same run."""
    d = np.zeros(mask.shape, int)
    for y in range(1, mask.shape[0]):
        d[y] = np.where(mask[y], np.where(mask[y - 1], d[y - 1] + 1, 0), 0)
    return d


def shading_model(a, sel, dcut=6, dmax=14):
    """Learn the artwork's shading: a per-row base colour times a top-edge ramp."""
    d = np.clip(depth_from_top(sel), 0, dmax)
    interior = sel & (d >= dcut)
    base_mean = a[..., :3][interior].mean(axis=0)

    ramp = np.tile(base_mean, (dmax + 1, 1))
    for k in range(dmax + 1):
        px = a[..., :3][sel & (d == k)]
        if len(px) >= 20:
            ramp[k] = px.mean(axis=0)
    ramp /= base_mean

    rows = np.nonzero(sel.any(axis=1))[0]
    base = np.tile(base_mean, (len(rows), 1))
    for i, y in enumerate(rows):
        px = a[y, :, :3][interior[y]]
        if len(px) >= 4:
            base[i] = px.mean(axis=0)
        elif i:
            base[i] = base[i - 1]
    return ramp, base, rows.min(), dmax


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--chars", required=True)
    ap.add_argument("--boxes", required=True,
                    help="x0,y0,x1,y1 per character, separated by ';'")
    ap.add_argument("--erase-only", action="store_true",
                    help="just remove the old characters, don't draw replacements")
    ap.add_argument("--hue", default="red", choices=["red", "blue"])
    ap.add_argument("--erase-x", type=int, default=0)
    ap.add_argument("--erase-y", type=int, default=0)
    ap.add_argument("--font", default=r"C:\Windows\Fonts\NotoSansTC-VF.ttf")
    ap.add_argument("--font-index", type=int, default=0)
    ap.add_argument("--variation")
    ap.add_argument("--variations", help="per-character variation names, comma separated")
    ap.add_argument("--weight", type=int, default=0)
    ap.add_argument("--outline", type=int, default=3)
    ap.add_argument("--extrude", type=int, default=3)
    ap.add_argument("--shadow", type=int, default=4)
    ap.add_argument("--shadow-rgb", default="24,4,8")
    args = ap.parse_args()

    im = Image.open(args.src).convert("RGBA")
    a = np.asarray(im).astype(int)
    lab, n = label_mask(fill_mask(a, args.hue))

    doomed = set()
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        if len(xs) >= 40 and xs.mean() >= args.erase_x and ys.mean() >= args.erase_y:
            doomed.add(i)
    print(f"{n} stroke groups, removing {len(doomed)}")

    own = ownership(lab, a[..., 3])
    res = np.asarray(im).copy().astype(np.float32)
    gone = np.isin(own, list(doomed))
    res[gone] = 0

    if args.erase_only:
        Image.fromarray(res.astype(np.uint8)).save(args.out)
        print("wrote", args.out, "(erase only)")
        return

    sel = np.isin(lab, list(doomed))
    ramp, base, gy0, dmax = shading_model(a, sel)

    boxes = [tuple(int(v) for v in b.split(",")) for b in args.boxes.split(";")]
    assert len(boxes) == len(args.chars), "one box per character"
    variations = (args.variations.split(",") if args.variations
                  else [args.variation] * len(args.chars))
    assert len(variations) == len(args.chars), "one variation per character"

    core = np.zeros(a.shape[:2], bool)
    for ch, box, var in zip(args.chars, boxes, variations):
        m = render(ch, args.font, box, args.font_index, var, args.weight)
        x0, y0, x1, y1 = box
        ox = x0 + (x1 - x0 + 1 - m.shape[1]) // 2
        oy = y0 + (y1 - y0 + 1 - m.shape[0]) // 2
        core[oy:oy + m.shape[0], ox:ox + m.shape[1]] |= m

    def shift(mask, d):
        return np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).transform(
            im.size, Image.AFFINE, (1, 0, -d, 0, 1, -d), resample=Image.NEAREST)) > 0

    extrude = shift(core, args.extrude) & ~core if args.extrude else np.zeros_like(core)
    halo = np.asarray(Image.fromarray(((core | extrude) * 255).astype(np.uint8)).filter(
        ImageFilter.MaxFilter(2 * args.outline + 1))) > 0
    shadow = shift(halo, args.shadow)

    h, w = core.shape
    yy = np.clip(np.arange(h) - gy0, 0, len(base) - 1)
    fill = base[yy][:, None, :].repeat(w, axis=1) * ramp[np.clip(depth_from_top(core), 0, dmax)]
    shadow_rgb = np.array([float(v) for v in args.shadow_rgb.split(",")])
    dark = base.min(axis=0) * 0.62

    empty = res[..., 3] < 8
    for mask, rgb in ((shadow & empty, shadow_rgb), (halo, np.array([255.0, 255, 255]))):
        res[mask, :3] = rgb
        res[mask, 3] = 255
    res[extrude, :3] = dark
    res[extrude, 3] = 255
    res[core, :3] = np.clip(fill[core], 0, 255)
    res[core, 3] = 255

    Image.fromarray(res.astype(np.uint8)).save(args.out)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
