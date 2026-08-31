"""Decode / encode BFFNT sheets (Wii U, GX2-tiled BC4)."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bc4  # noqa: E402
import bffnt  # noqa: E402
import gx2_addr  # noqa: E402
import texture2ddecoder  # noqa: E402
from PIL import Image  # noqa: E402


def sheet_swizzle(slice_index: int, base: int = 0) -> int:
    """Each array slice rotates bank/pipe by `rotation` (=2 for 2D tiled thin1)."""
    return (base + 2 * slice_index) % 8


def sheet_to_image(sheet: bytes, w: int, h: int, tile_mode=4, swizzle=0):
    linear = gx2_addr.untile(sheet, w // 4, h // 4, 64, tile_mode, swizzle, 0)
    raw = texture2ddecoder.decode_bc4(linear, w, h)
    img = Image.frombytes("RGBA", (w, h), raw, "raw", "BGRA").getchannel("R")
    # BFFNT sheet data is stored bottom-up
    return img.transpose(Image.FLIP_TOP_BOTTOM)


def image_to_sheet(img: Image.Image, tile_mode=4, swizzle=0, keep_from=None,
                   rewrite_mask=None) -> bytes:
    """Inverse of sheet_to_image.

    keep_from / rewrite_mask let untouched blocks keep their original bytes so
    existing glyphs are not degraded by a re-encode.
    """
    w, h = img.size
    arr = np.asarray(img.transpose(Image.FLIP_TOP_BOTTOM), dtype=np.uint8)
    linear = bytearray(bc4.encode(arr))
    if keep_from is not None and rewrite_mask is not None:
        original = gx2_addr.untile(keep_from, w // 4, h // 4, 64, tile_mode, swizzle, 0)
        mask = np.asarray(rewrite_mask.transpose(Image.FLIP_TOP_BOTTOM), dtype=bool)
        block_mask = mask.reshape(h // 4, 4, w // 4, 4).any(axis=(1, 3)).ravel()
        blocks = np.frombuffer(bytes(linear), dtype=np.uint8).reshape(-1, 8).copy()
        orig_blocks = np.frombuffer(original, dtype=np.uint8).reshape(-1, 8)
        blocks[~block_mask] = orig_blocks[~block_mask]
        linear = bytearray(blocks.tobytes())
    return gx2_addr.tile(bytes(linear), w // 4, h // 4, 64, tile_mode, swizzle, 0)


def main():
    path, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    f = bffnt.parse(open(path, "rb").read())
    t = f.tglp
    for i, sheet in enumerate(t.sheets):
        img = sheet_to_image(sheet, t.sheet_width, t.sheet_height, 4, sheet_swizzle(i))
        img.save(os.path.join(outdir, f"sheet{i:02d}.png"))
        print(f"sheet {i} -> {outdir}\\sheet{i:02d}.png")


if __name__ == "__main__":
    main()
