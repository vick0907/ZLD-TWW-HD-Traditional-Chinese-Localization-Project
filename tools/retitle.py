"""Rebuild the 风之杖 title logo as 風之杖.

The outer 几 frame (with its spiral flourish) is identical in both forms, so only
the inner component is replaced: erase the 乂 stroke group and draw 虫 in its
place, reusing the artwork's own gradient / outline / shadow colours.
"""
import argparse
import os
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SUPERSAMPLE = 4


def blue_components(a):
    """Label the saturated-blue fill regions (the actual brush strokes)."""
    al, r, b = a[..., 3], a[..., 0], a[..., 2]
    blue = (al > 128) & (b - r > 40)
    h, w = blue.shape
    lab = np.zeros((h, w), int)
    n = 0
    for y in range(h):
        for x in range(w):
            if blue[y, x] and lab[y, x] == 0:
                n += 1
                q = deque([(y, x)])
                lab[y, x] = n
                while q:
                    cy, cx = q.popleft()
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < h and 0 <= nx < w and blue[ny, nx] and lab[ny, nx] == 0:
                                lab[ny, nx] = n
                                q.append((ny, nx))
    return lab, n


def ownership(lab, alpha):
    """Assign every visible pixel (outline + shadow included) to the nearest stroke."""
    h, w = lab.shape
    own = lab.copy()
    q = deque(zip(*np.nonzero(lab)))
    visible = alpha > 8
    while q:
        cy, cx = q.popleft()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < h and 0 <= nx < w and visible[ny, nx] and own[ny, nx] == 0:
                    own[ny, nx] = own[cy, cx]
                    q.append((ny, nx))
    return own


def sample_style(a, lab, comp_ids):
    """Fill gradient per row, taken from the character's own artwork."""
    sel = np.isin(lab, comp_ids)
    ys, xs = np.nonzero(sel)
    y0, y1 = ys.min(), ys.max()
    grad = np.zeros((y1 - y0 + 1, 3))
    for i, y in enumerate(range(y0, y1 + 1)):
        row = a[y][sel[y]][:, :3]
        grad[i] = row.mean(axis=0) if len(row) else grad[max(0, i - 1)]
    return grad, y0, y1


def label_mask(mask):
    h, w = mask.shape
    lab = np.zeros((h, w), int)
    n = 0
    for y in range(h):
        for x in range(w):
            if mask[y, x] and lab[y, x] == 0:
                n += 1
                q = deque([(y, x)])
                lab[y, x] = n
                while q:
                    cy, cx = q.popleft()
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and lab[ny, nx] == 0:
                                lab[ny, nx] = n
                                q.append((ny, nx))
    return lab, n


def render_glyph(ch, font_path, box_w, box_h, index=0, variation=None, drop_outer=False):
    """Draw a character as a coverage mask scaled into the given box.

    drop_outer keeps only the enclosed strokes, i.e. the 虫 inside 風.
    """
    size = max(box_w, box_h) * SUPERSAMPLE
    font = ImageFont.truetype(font_path, size, index=index)
    if variation:
        font.set_variation_by_name(variation)
    big = Image.new("L", (size * 2, size * 2), 0)
    ImageDraw.Draw(big).text((size // 2, size // 2), ch, fill=255, font=font, anchor="lt")
    arr = np.asarray(big) > 40

    if drop_outer:
        lab, n = label_mask(arr[::2, ::2])
        counts = [(int((lab == i).sum()), i) for i in range(1, n + 1)]
        if n < 2:
            print(f"  warning: {os.path.basename(font_path)} draws {ch} as one "
                  f"connected shape, using it whole")
        else:
            outer = max(counts)[1]
            keep = np.kron((lab != outer) & (lab != 0), np.ones((2, 2), bool))
            keep = keep[:arr.shape[0], :arr.shape[1]]
            arr = arr & np.pad(keep, ((0, arr.shape[0] - keep.shape[0]),
                                      (0, arr.shape[1] - keep.shape[1])))

    ys, xs = np.nonzero(arr)
    crop = Image.fromarray((arr * 255).astype(np.uint8)).crop(
        (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    scale = min(box_w / crop.width, box_h / crop.height)
    return crop.resize((max(1, round(crop.width * scale)),
                        max(1, round(crop.height * scale))), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--inner", default="風")
    ap.add_argument("--drop-outer", action="store_true", default=True)
    ap.add_argument("--whole", dest="drop_outer", action="store_false")
    ap.add_argument("--font", default=r"C:\Windows\Fonts\NotoSansTC-VF.ttf")
    ap.add_argument("--font-index", type=int, default=0)
    ap.add_argument("--variation")
    ap.add_argument("--weight", type=int, default=0)
    ap.add_argument("--outline", type=int, default=2)
    ap.add_argument("--shadow", type=int, default=3)
    ap.add_argument("--box", help="x0,y0,x1,y1 placement box; defaults to the removed stroke's bbox")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--dx", type=int, default=0)
    ap.add_argument("--dy", type=int, default=0)
    ap.add_argument("--debug")
    args = ap.parse_args()

    im = Image.open(args.src).convert("RGBA")
    a = np.asarray(im).astype(int)
    lab, n = blue_components(a)
    sizes = [(int((lab == i).sum()), i) for i in range(1, n + 1)]
    sizes.sort(reverse=True)
    frame_id = sizes[0][1]
    fys, fxs = np.nonzero(lab == frame_id)
    inner_id = None
    for _, i in sizes:
        if i == frame_id:
            continue
        ys, xs = np.nonzero(lab == i)
        if xs.min() > fxs.min() and xs.max() < fxs.max() and ys.min() > fys.min():
            inner_id = i
            break
    print(f"components={n} frame=#{frame_id} inner=#{inner_id}")

    own = ownership(lab, a[..., 3])
    out = np.asarray(im).copy()
    out[own == inner_id] = (0, 0, 0, 0)

    iys, ixs = np.nonzero(lab == inner_id)
    if args.box:
        bx0, by0, bx1, by1 = (int(v) for v in args.box.split(","))
    else:
        bx0, bx1, by0, by1 = ixs.min(), ixs.max(), iys.min(), iys.max()
    print(f"replacing box: x{bx0}-{bx1} y{by0}-{by1}")

    box_w = int((bx1 - bx0 + 1) * args.scale)
    box_h = int((by1 - by0 + 1) * args.scale)
    glyph = render_glyph(args.inner, args.font, box_w, box_h, args.font_index,
                         args.variation, args.drop_outer)
    gx = bx0 + (bx1 - bx0 + 1 - glyph.width) // 2 + args.dx
    gy = by0 + (by1 - by0 + 1 - glyph.height) // 2 + args.dy

    grad, gy0, gy1 = sample_style(a, lab, [frame_id, inner_id])

    layer = Image.new("L", im.size, 0)
    layer.paste(glyph, (gx, gy))
    cov = np.asarray(layer).astype(np.float32) / 255.0
    core = cov > 0.45
    if args.weight:
        core = np.asarray(Image.fromarray((core * 255).astype(np.uint8)).filter(
            ImageFilter.MaxFilter(2 * args.weight + 1))) > 0

    halo = Image.fromarray((core * 255).astype(np.uint8)).filter(
        ImageFilter.MaxFilter(2 * args.outline + 1))
    halo = np.asarray(halo) > 0

    shadow = Image.fromarray((halo * 255).astype(np.uint8))
    shadow = np.asarray(shadow.transform(
        im.size, Image.AFFINE, (1, 0, -args.shadow, 0, 1, -args.shadow),
        resample=Image.NEAREST)) > 0

    shadow_rgb = np.array([12, 20, 40])
    outline_rgb = np.array([255, 255, 255])

    h, w = core.shape
    yy = np.clip(np.arange(h) - gy0, 0, len(grad) - 1)
    fill_rgb = grad[yy][:, None, :].repeat(w, axis=1)

    res = out.astype(np.float32)
    for mask, rgb in ((shadow, shadow_rgb), (halo, outline_rgb)):
        m = mask & (res[..., 3] < 8)
        res[m] = np.concatenate([np.broadcast_to(rgb, (m.sum(), 3)),
                                 np.full((m.sum(), 1), 255.0)], axis=1)
    res[halo] = np.concatenate([np.broadcast_to(outline_rgb, (halo.sum(), 3)),
                                np.full((halo.sum(), 1), 255.0)], axis=1)
    res[core] = np.concatenate([fill_rgb[core], np.full((core.sum(), 1), 255.0)], axis=1)

    Image.fromarray(res.astype(np.uint8)).save(args.out)
    print("wrote", args.out)

    if args.debug:
        os.makedirs(args.debug, exist_ok=True)
        bg = Image.new("RGBA", im.size, (20, 20, 28, 255))
        for tag, img in (("orig", im),
                         ("erased", Image.fromarray(out)),
                         ("final", Image.fromarray(res.astype(np.uint8)))):
            c = Image.alpha_composite(bg, img).convert("RGB")
            c.resize((c.width * 4, c.height * 4), Image.NEAREST).save(
                os.path.join(args.debug, f"{tag}.png"))


if __name__ == "__main__":
    main()
