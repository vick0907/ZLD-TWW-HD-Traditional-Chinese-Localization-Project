"""Extract reference glyph cells from a BFFNT."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decode_font import sheet_swizzle, sheet_to_image  # noqa: E402


class Atlas:
    def __init__(self, font, y_origin=0, x_origin=0):
        self.f = font
        self.t = font.tglp
        self.y_origin = y_origin
        self.x_origin = x_origin
        self._cache = {}

    def sheet(self, index):
        if index not in self._cache:
            self._cache[index] = sheet_to_image(
                self.t.sheets[index], self.t.sheet_width, self.t.sheet_height,
                4, sheet_swizzle(index))
        return self._cache[index]

    def cell_box(self, glyph_index):
        t = self.t
        s, rem = divmod(glyph_index, t.per_sheet)
        row, col = divmod(rem, t.columns)
        x0 = self.x_origin + col * t.cell_w
        y0 = self.y_origin + row * t.cell_h
        return s, (x0, y0, x0 + t.cell_w, y0 + t.cell_h)

    def cell(self, glyph_index):
        s, box = self.cell_box(glyph_index)
        return np.asarray(self.sheet(s).crop(box))

    def cell_for_char(self, ch):
        idx = self.f.charmap.get(ord(ch))
        return None if idx is None else self.cell(idx)
