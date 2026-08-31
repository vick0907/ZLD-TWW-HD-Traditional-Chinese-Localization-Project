"""Decode Wii U BFLIM textures out of an SZS/SARC archive into PNGs."""
import os
import struct
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gx2_addr  # noqa: E402
import sarc  # noqa: E402

RGBA8 = (0x14, 0x09)
BC4 = (0x10,)


def walk(blob, prefix, out):
    if blob[:4] == b"Yaz0":
        blob = sarc.yaz0_decompress(blob)
    if blob[:4] != b"SARC":
        return
    for name, sub in sarc.sarc_read(blob):
        path = f"{prefix}/{name}"
        if sub[:4] in (b"Yaz0", b"SARC"):
            walk(sub, path, out)
        else:
            out[path] = sub


def align(v, a):
    return (v + a - 1) // a * a


def decode_bc4(data, bw, bh):
    """Single-channel BC4 -> greyscale bytes, bw/bh in blocks."""
    out = bytearray(bw * 4 * bh * 4)
    row_px = bw * 4
    for by in range(bh):
        for bx in range(bw):
            off = (by * bw + bx) * 8
            r0, r1 = data[off], data[off + 1]
            bits = int.from_bytes(data[off + 2:off + 8], "little")
            if r0 > r1:
                lut = [r0, r1] + [((7 - i) * r0 + i * r1) // 7 for i in range(1, 7)]
            else:
                lut = [r0, r1] + [((5 - i) * r0 + i * r1) // 5 for i in range(1, 5)] + [0, 255]
            for py in range(4):
                for px in range(4):
                    out[(by * 4 + py) * row_px + bx * 4 + px] = lut[(bits >> (3 * (py * 4 + px))) & 7]
    return bytes(out)


def to_image(blob):
    footer = blob[-0x28:]
    width, height, _align, fmt, tile_byte = struct.unpack_from(">HHHBB", footer, 0x1C)
    tile_mode, swizzle = tile_byte & 0x1F, (tile_byte >> 5) & 7
    data = blob[:-0x28]

    if fmt in RGBA8:
        pitch, rows = align(width, 32), align(height, 16)
        linear = gx2_addr.untile(data, pitch, rows, 32, tile_mode, swizzle << 8)
        img = Image.frombytes("RGBA", (pitch, rows), linear)
    elif fmt in BC4:
        bw, bh = align(align(width, 4) // 4, 32), align(align(height, 4) // 4, 16)
        linear = gx2_addr.untile(data, bw, bh, 64, tile_mode, swizzle << 8)
        img = Image.frombytes("L", (bw * 4, bh * 4), decode_bc4(linear, bw, bh))
    else:
        return None, f"unsupported format 0x{fmt:02x}"
    return img.crop((0, 0, width, height)), f"{width}x{height} fmt=0x{fmt:02x} tile={tile_mode} swz={swizzle}"


def main():
    archive, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    leaves = {}
    walk(open(archive, "rb").read(), "", leaves)
    for path, blob in sorted(leaves.items()):
        if not path.endswith(".bflim"):
            continue
        name = os.path.basename(path).replace("^", "_")[:-6]
        img, note = to_image(blob)
        if img is None:
            print(f"{name}: {note}")
            continue
        img.save(os.path.join(outdir, name + ".png"))
        print(f"{name}: {note}")


if __name__ == "__main__":
    main()
