"""Add Traditional Chinese glyphs to a Wii U BFFNT without disturbing existing ones.

New glyphs are appended to the free slots at the end of the atlas, so every
existing glyph index, width and pixel stays exactly as it was.
"""
import argparse
import json
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bffnt  # noqa: E402
import glyph_render  # noqa: E402
import msbt  # noqa: E402
from atlas import Atlas  # noqa: E402
from decode_font import image_to_sheet, sheet_swizzle  # noqa: E402
from PIL import Image  # noqa: E402

CALIB = "日月山川人大中小天王正方五百千文本立平田目口"
FULLWIDTH_CJK = (1, 40, 42)


def is_fullwidth(ch):
    o = ord(ch)
    return (0x3000 <= o <= 0x303F or 0x3400 <= o <= 0x4DBF or
            0x4E00 <= o <= 0x9FFF or 0xF900 <= o <= 0xFAFF or
            0xFF00 <= o <= 0xFF60 or 0xFFE0 <= o <= 0xFFE6)


def chars_from_msbt(root):
    chars = set()
    for dirpath, _, files in os.walk(root):
        for name in files:
            if not name.endswith(".msbt"):
                continue
            messages, _ = msbt.read(open(os.path.join(dirpath, name), "rb").read())
            for segs in messages:
                for kind, val in segs:
                    if kind == "t":
                        chars.update(val)
    return chars


def build_cmap_scan(pairs):
    payload = struct.pack(">HHHHI", 0x0000, 0xFFFF, bffnt.MAPPING_SCAN, 0, 0)
    payload += struct.pack(">H", len(pairs))
    payload += b"".join(struct.pack(">HH", code, idx) for code, idx in pairs)
    size = 8 + len(payload)
    pad = (-size) % 4
    return b"CMAP" + struct.pack(">I", size + pad) + payload + b"\x00" * pad


def build_cwdh(widths):
    body = b"".join(bytes((left & 0xFF, glyph & 0xFF, char & 0xFF))
                    for left, glyph, char in widths)
    payload = struct.pack(">HHI", 0, len(widths) - 1, 0) + body
    size = 8 + len(payload)
    pad = (-size) % 4
    return b"CWDH" + struct.pack(">I", size + pad) + payload + b"\x00" * pad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bffnt")
    ap.add_argument("out")
    ap.add_argument("--text-root", help="MSBT tree supplying the required characters")
    ap.add_argument("--convert-existing", action="store_true",
                    help="also add the Traditional form of every CJK glyph already present")
    ap.add_argument("--chars-file", help="UTF-8 file listing extra characters to add")
    ap.add_argument("--ttf", default=r"C:\Windows\Fonts\NotoSansTC-VF.ttf")
    ap.add_argument("--variation", default="Bold")
    ap.add_argument("--index", type=int, default=0)
    ap.add_argument("--report")
    args = ap.parse_args()

    data = open(args.bffnt, "rb").read()
    f = bffnt.parse(data)
    t = f.tglp
    existing = {chr(c) for c in f.charmap}
    next_index = max(f.charmap.values()) + 1

    needed = set()
    if args.text_root:
        needed |= chars_from_msbt(args.text_root)
    if args.chars_file:
        needed |= set(open(args.chars_file, encoding="utf-8").read())
    if args.convert_existing:
        import opencc
        conv = opencc.OpenCC("s2twp")
        for ch in list(existing):
            if "\u4e00" <= ch <= "\u9fff":
                needed.add(conv.convert(ch))

    # private-use symbols live in CKingPic, control codes are not glyphs
    new_chars = sorted(c for c in needed - existing
                       if ord(c) >= 0x20 and not (0xE000 <= ord(c) <= 0xF8FF))

    log = {"font": os.path.basename(args.bffnt),
           "existing_glyphs": len(f.charmap),
           "capacity": t.capacity,
           "free_slots": t.capacity - next_index,
           "new_chars_requested": len(new_chars)}

    if len(new_chars) > t.capacity - next_index:
        raise SystemExit(f"not enough slots: need {len(new_chars)}, "
                         f"have {t.capacity - next_index}")

    atlas = Atlas(f)
    refs = {ch: atlas.cell_for_char(ch) for ch in CALIB
            if atlas.cell_for_char(ch) is not None}
    calib_log = []
    renderer, score = glyph_render.calibrate(args.ttf, refs, t.cell_w, t.cell_h,
                                             args.variation, args.index, calib_log)
    log["calibration"] = calib_log[0] if calib_log else None

    sheets = {}
    masks = {}
    widths = list(f.cwdh[0][2])
    while len(widths) < next_index:
        widths.append(FULLWIDTH_CJK)

    added = []
    skipped = []
    for ch in new_chars:
        glyph = renderer.render(ch, t.cell_w, t.cell_h)
        if not glyph.any():
            skipped.append(ch)
            continue
        idx = next_index + len(added)
        s, box = atlas.cell_box(idx)
        if s not in sheets:
            sheets[s] = atlas.sheet(s).copy()
            masks[s] = Image.new("L", sheets[s].size, 0)
        sheets[s].paste(Image.fromarray(glyph), (box[0], box[1]))
        masks[s].paste(255, (box[0], box[1], box[2], box[3]))
        if is_fullwidth(ch):
            widths.append(FULLWIDTH_CJK)
        else:
            xs = np.nonzero(glyph.max(axis=0))[0]
            adv = int(xs.max() - xs.min() + 3)
            widths.append(((t.cell_w - adv) // 2, adv, adv))
        added.append(ch)

    log["added"] = len(added)
    log["skipped_missing_glyph"] = "".join(skipped)
    log["sheets_rewritten"] = sorted(sheets)

    new_sheets = list(t.sheets)
    for s, img in sheets.items():
        new_sheets[s] = image_to_sheet(img, 4, sheet_swizzle(s),
                                       keep_from=t.sheets[s], rewrite_mask=masks[s])

    out = bytearray(data[:f.finf["cwdh_off"] - 8])
    for i, sheet in enumerate(new_sheets):
        start = t.sheet_offset + i * t.sheet_size
        out[start:start + t.sheet_size] = sheet

    charmap = dict(f.charmap)
    for i, ch in enumerate(added):
        charmap[ord(ch)] = next_index + i

    cwdh = build_cwdh(widths)
    cwdh_pos = len(out)
    out += cwdh
    cmap_pos = len(out)
    out += build_cmap_scan(sorted(charmap.items()))

    struct.pack_into(">I", out, f.finf_offset + 24, cwdh_pos + 8)
    struct.pack_into(">I", out, f.finf_offset + 28, cmap_pos + 8)
    struct.pack_into(">I", out, 0x0C, len(out))
    struct.pack_into(">H", out, 0x10, 4)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "wb") as fp:
        fp.write(bytes(out))
    log["output"] = args.out
    log["output_size"] = len(out)
    log["total_glyphs"] = len(charmap)

    if args.report:
        with open(args.report, "w", encoding="utf-8") as fp:
            json.dump(log, fp, ensure_ascii=False, indent=2)
    for k, v in log.items():
        if k != "skipped_missing_glyph" or v:
            print(f"{k}: {v}")


if __name__ == "__main__":
    main()
