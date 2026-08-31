"""Write PNGs back into the BFLIM textures of an SZS/SARC archive.

RGBA8 and BC4 surfaces are re-encoded; the original tiled bytes supply
everything outside the visible width x height so padding stays intact.
"""
import argparse
import os
import struct
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bc4  # noqa: E402
import gx2_addr  # noqa: E402
import sarc  # noqa: E402
from dump_bflim import BC4, RGBA8, align, decode_bc4, to_image  # noqa: E402


def encode_bflim(blob: bytes, img: Image.Image) -> bytes:
    footer = blob[-0x28:]
    width, height, _a, fmt, tile_byte = struct.unpack_from(">HHHBB", footer, 0x1C)
    if img.size != (width, height):
        raise ValueError(f"image is {img.size}, texture is {width}x{height}")

    tile_mode, swizzle = tile_byte & 0x1F, (tile_byte >> 5) & 7
    data = blob[:-0x28]

    if fmt in RGBA8:
        pitch, rows = align(width, 32), align(height, 16)
        linear = np.frombuffer(
            gx2_addr.untile(data, pitch, rows, 32, tile_mode, swizzle << 8),
            dtype=np.uint8).reshape(rows, pitch, 4).copy()
        linear[:height, :width] = np.asarray(img.convert("RGBA"), dtype=np.uint8)
        tiled = gx2_addr.tile(linear.tobytes(), pitch, rows, 32, tile_mode, swizzle << 8)
    elif fmt in BC4:
        bw, bh = align(align(width, 4) // 4, 32), align(align(height, 4) // 4, 16)
        old = decode_bc4(gx2_addr.untile(data, bw, bh, 64, tile_mode, swizzle << 8), bw, bh)
        plane = np.frombuffer(old, dtype=np.uint8).reshape(bh * 4, bw * 4).copy()
        plane[:height, :width] = np.asarray(img.convert("L"), dtype=np.uint8)
        tiled = gx2_addr.tile(bc4.encode(plane), bw, bh, 64, tile_mode, swizzle << 8)
    else:
        raise ValueError(f"format 0x{fmt:02x} is not supported for encoding")

    if len(tiled) != len(data):
        raise ValueError(f"re-tiled {len(tiled)} bytes, original was {len(data)}")
    return tiled + footer


def rebuild(blob: bytes, pngs: dict, prefix: str, stats: list) -> bytes:
    was_yaz0 = blob[:4] == b"Yaz0"
    raw = sarc.yaz0_decompress(blob) if was_yaz0 else blob
    if raw[:4] != b"SARC":
        return blob

    files, changed = [], False
    for name, sub in sarc.sarc_read(raw):
        path = f"{prefix}/{name}"
        key = os.path.basename(name).replace("^", "_")[:-6]
        if sub[:4] in (b"Yaz0", b"SARC"):
            new = rebuild(sub, pngs, path, stats)
            changed |= new is not sub
        elif name.endswith(".bflim") and key in pngs:
            new = encode_bflim(sub, Image.open(pngs[key]))
            changed = True
            stats.append((path, len(sub), len(new)))
        else:
            new = sub
        files.append((name, new))

    if not changed:
        return blob
    out = sarc.sarc_write(files, sarc.sarc_alignment(raw))
    return sarc.yaz0_compress(out) if was_yaz0 else out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("archive")
    ap.add_argument("out")
    ap.add_argument("--png-dir", required=True)
    args = ap.parse_args()

    pngs = {os.path.splitext(f)[0]: os.path.join(args.png_dir, f)
            for f in os.listdir(args.png_dir) if f.endswith(".png")}
    print(f"{len(pngs)} replacement images: {sorted(pngs)}")

    stats = []
    blob = open(args.archive, "rb").read()
    out = rebuild(blob, pngs, "", stats)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    open(args.out, "wb").write(out)
    for path, before, after in stats:
        print(f"  {before} -> {after}  {path}")
    print(f"{args.archive} {len(blob)} -> {args.out} {len(out)} bytes")

    # read the result back and make sure every replaced texture decodes to its PNG
    check = {}
    def walk(b, p):
        if b[:4] == b"Yaz0":
            b = sarc.yaz0_decompress(b)
        if b[:4] != b"SARC":
            return
        for name, sub in sarc.sarc_read(b):
            if sub[:4] in (b"Yaz0", b"SARC"):
                walk(sub, f"{p}/{name}")
            else:
                check[os.path.basename(name).replace("^", "_")[:-6]] = sub
    walk(open(args.out, "rb").read(), "")
    for key, path in sorted(pngs.items()):
        got, _ = to_image(check[key])
        want = Image.open(path).convert(got.mode)
        diff = np.abs(np.asarray(got, int) - np.asarray(want, int)).max()
        print(f"  round-trip {key}: max channel diff = {diff}")


if __name__ == "__main__":
    main()
