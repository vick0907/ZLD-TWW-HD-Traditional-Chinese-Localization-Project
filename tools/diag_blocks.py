"""Diagnostics: block emptiness maps, to validate untiling without ETC1 decoding."""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bffnt  # noqa: E402
import gx2_addr  # noqa: E402
from PIL import Image  # noqa: E402


EMPTY = bytes.fromhex("0100499224499224")


def block_map_image(data, bw, bh, addrs=None):
    img = Image.new("L", (bw, bh))
    px = img.load()
    for i in range(bw * bh):
        addr = addrs[i] if addrs else i * 8
        blk = data[addr:addr + 8]
        px[i % bw, i // bw] = 0 if blk == EMPTY else 255
    return img


def main():
    path, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    f = bffnt.parse(open(path, "rb").read())
    t = f.tglp
    bw, bh = t.sheet_width // 4, t.sheet_height // 4

    for idx, sheet in enumerate(t.sheets):
        zero = sum(1 for i in range(0, len(sheet), 8) if sheet[i:i + 8] == EMPTY)
        print(f"sheet {idx}: empty blocks {zero}/{len(sheet)//8} ({zero*100//(len(sheet)//8)}%)")

    c = Counter(t.sheets[0][i:i + 8] for i in range(0, len(t.sheets[0]), 8))
    print("most common blocks sheet0:", [(b.hex(), n) for b, n in c.most_common(4)])

    # raw (tiled) emptiness map
    block_map_image(t.sheets[0], bw, bh).resize((512, 512), Image.NEAREST).save(
        os.path.join(outdir, "empty_raw_s0.png"))
    last = len(t.sheets) - 1
    block_map_image(t.sheets[9], bw, bh).resize((512, 512), Image.NEAREST).save(
        os.path.join(outdir, "empty_raw_s9.png"))
    print("last sheet index", last)

    for tile_mode in (2, 4):
        for swizzle in range(8):
            addrs, _ = gx2_addr.build_address_map(bw, bh, 64, tile_mode, swizzle)
            block_map_image(t.sheets[9], bw, bh, addrs).resize((512, 512), Image.NEAREST).save(
                os.path.join(outdir, f"empty_s9_tm{tile_mode}_sw{swizzle}.png"))


if __name__ == "__main__":
    main()
