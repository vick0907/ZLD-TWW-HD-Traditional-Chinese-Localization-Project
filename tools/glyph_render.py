"""Render new glyphs in the game's style (white core + grey outline) and
calibrate size/offset/outline against the existing glyphs."""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

CORE = 255
HALO = 128
SUPERSAMPLE = 4


class GlyphRenderer:
    def __init__(self, font_path, size, dx, dy, outline, variation=None, index=0):
        self.font_path = font_path
        self.size = size
        self.dx = dx
        self.dy = dy
        self.outline = outline
        self.variation = variation
        self.font = ImageFont.truetype(font_path, size * SUPERSAMPLE, index=index)
        if variation:
            try:
                self.font.set_variation_by_name(variation)
            except Exception:
                try:
                    self.font.set_variation_by_axes([float(variation)])
                except Exception:
                    pass

    def render(self, ch, cell_w, cell_h):
        big = Image.new("L", (cell_w * SUPERSAMPLE * 2, cell_h * SUPERSAMPLE * 2), 0)
        d = ImageDraw.Draw(big)
        d.text((big.width // 4, big.height // 4), ch, fill=255, font=self.font, anchor="lt")
        small = big.resize((big.width // SUPERSAMPLE, big.height // SUPERSAMPLE),
                           Image.LANCZOS)
        core = small.point(lambda v: 255 if v >= 110 else 0)
        halo = core
        if self.outline > 0:
            halo = core.filter(ImageFilter.MaxFilter(2 * self.outline + 1))
        a = np.asarray(core, dtype=np.uint8)
        b = np.asarray(halo, dtype=np.uint8)
        img = np.where(a > 0, CORE, np.where(b > 0, HALO, 0)).astype(np.uint8)

        ys, xs = np.nonzero(img)
        if len(xs) == 0:
            return np.zeros((cell_h, cell_w), dtype=np.uint8)
        crop = img[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        out = np.zeros((cell_h, cell_w), dtype=np.uint8)
        oy = (cell_h - crop.shape[0]) // 2 + self.dy
        ox = (cell_w - crop.shape[1]) // 2 + self.dx
        sy0, sx0 = max(0, oy), max(0, ox)
        cy0, cx0 = max(0, -oy), max(0, -ox)
        hh = min(crop.shape[0] - cy0, cell_h - sy0)
        ww = min(crop.shape[1] - cx0, cell_w - sx0)
        if hh > 0 and ww > 0:
            out[sy0:sy0 + hh, sx0:sx0 + ww] = crop[cy0:cy0 + hh, cx0:cx0 + ww]
        return out


def calibrate(font_path, refs, cell_w, cell_h, variation=None, index=0, log=None):
    """refs: dict char -> reference cell array. Returns the best GlyphRenderer."""
    best = None
    margin = 4   # neighbouring cells bleed a couple of pixels into every cell
    for size in range(32, 52):
        for outline in (1, 2):
            r = GlyphRenderer(font_path, size, 0, 0, outline, variation, index)
            rendered = {ch: r.render(ch, cell_w, cell_h) for ch in refs}
            for dy in range(-5, 6):
                for dx in range(-5, 6):
                    total = 0.0
                    for ch, ref in refs.items():
                        shifted = np.roll(np.roll(rendered[ch], dy, axis=0), dx, axis=1)
                        total += np.abs(
                            shifted[margin:cell_h - margin,
                                    margin:cell_w - margin].astype(np.int16) -
                            ref[margin:cell_h - margin,
                                margin:cell_w - margin].astype(np.int16)).mean()
                    score = total / max(1, len(refs))
                    if best is None or score < best[0]:
                        best = (score, size, dx, dy, outline)
    score, size, dx, dy, outline = best
    if log is not None:
        log.append(f"calibrated: size={size} dx={dx} dy={dy} outline={outline} "
                   f"mean_abs_err={score:.2f}")
    return GlyphRenderer(font_path, size, dx, dy, outline, variation, index), score
