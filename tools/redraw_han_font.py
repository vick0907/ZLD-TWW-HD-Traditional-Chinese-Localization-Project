"""Redraw every existing Han glyph in a BFFNT with a selected font weight."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bffnt  # noqa: E402
import msbt  # noqa: E402
from atlas import Atlas  # noqa: E402
from decode_font import image_to_sheet, sheet_swizzle  # noqa: E402
from glyph_render import GlyphRenderer  # noqa: E402


def is_han(codepoint):
    return (0x3400 <= codepoint <= 0x9FFF or
            0xF900 <= codepoint <= 0xFAFF)


def required_han_codes(root):
    required = set()
    for path in Path(root).rglob("*.msbt"):
        messages, _ = msbt.read(path.read_bytes())
        for segments in messages:
            for kind, value in segments:
                if kind == "t":
                    required.update(ord(character) for character in value
                                    if is_han(ord(character)))
    return required


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    required_source = parser.add_mutually_exclusive_group(required=True)
    required_source.add_argument("--text-root")
    required_source.add_argument("--chars-file", type=Path)
    parser.add_argument("--ttf", default=r"C:\Windows\Fonts\NotoSansTC-VF.ttf")
    parser.add_argument("--variation", default="500")
    parser.add_argument("--size", type=int, default=36)
    parser.add_argument("--dx", type=int, default=-1)
    parser.add_argument("--dy", type=int, default=3)
    parser.add_argument("--outline", type=int, default=2)
    parser.add_argument("--blur", type=float, default=0.5)
    parser.add_argument("--report")
    args = parser.parse_args()

    if args.source.resolve() == args.output.resolve():
        raise ValueError("Source and output must be different files")
    original = args.source.read_bytes()
    font = bffnt.parse(original)
    atlas = Atlas(font)
    if args.chars_file:
        required = {ord(character) for character in args.chars_file.read_text(encoding="utf-8")
                    if is_han(ord(character))}
    else:
        required = required_han_codes(args.text_root)
    missing_mappings = sorted(required - font.charmap.keys())
    if missing_mappings:
        raise ValueError("Required Han characters are not mapped: " +
                         "".join(chr(codepoint) for codepoint in missing_mappings))

    glyph_codes = defaultdict(list)
    for codepoint, glyph_index in font.charmap.items():
        glyph_codes[glyph_index].append(codepoint)

    renderer = GlyphRenderer(
        args.ttf, args.size, args.dx, args.dy, args.outline,
        args.variation, blur=args.blur,
    )
    missing_shape = renderer.render("\uffff", font.tglp.cell_w, font.tglp.cell_h)
    sheets = {}
    masks = {}
    targets = {}
    for glyph_index, codepoints in sorted(glyph_codes.items()):
        han_codes = [codepoint for codepoint in codepoints if is_han(codepoint)]
        if not han_codes:
            continue
        if len(han_codes) != len(codepoints):
            raise ValueError(
                f"Han glyph shares a non-Han cell: {glyph_index}, {codepoints}"
            )
        glyph = renderer.render(chr(han_codes[0]), font.tglp.cell_w,
                                font.tglp.cell_h)
        if not glyph.any() or np.array_equal(glyph, missing_shape):
            if required.intersection(han_codes):
                raise ValueError(f"Font lacks required glyph U+{han_codes[0]:04X}")
            continue
        for codepoint in han_codes[1:]:
            alternate = renderer.render(chr(codepoint), font.tglp.cell_w,
                                        font.tglp.cell_h)
            if not np.array_equal(glyph, alternate):
                raise ValueError(
                    f"Aliased Han glyphs render differently: {glyph_index}, {codepoints}"
                )
        edges = (glyph[0], glyph[-1], glyph[:, 0], glyph[:, -1])
        if any((edge >= 220).any() for edge in edges):
            raise ValueError(f"White strokes reach cell boundary: U+{han_codes[0]:04X}")

        sheet_index, box = atlas.cell_box(glyph_index)
        if sheet_index not in sheets:
            sheets[sheet_index] = atlas.sheet(sheet_index).copy()
            masks[sheet_index] = Image.new("L", sheets[sheet_index].size, 0)
        sheets[sheet_index].paste(Image.fromarray(glyph), (box[0], box[1]))
        masks[sheet_index].paste(255, box)
        targets[glyph_index] = han_codes

    # BC4 blocks cross cell boundaries. Preserve every block touching a cell
    # that is not being redrawn so non-Han characters remain pixel-identical.
    for glyph_index in glyph_codes.keys() - targets.keys():
        sheet_index, box = atlas.cell_box(glyph_index)
        if sheet_index not in masks:
            continue
        left, top, right, bottom = box
        protected = (left // 4 * 4, top // 4 * 4,
                     (right + 3) // 4 * 4, (bottom + 3) // 4 * 4)
        masks[sheet_index].paste(0, protected)

    candidate = bytearray(original)
    for sheet_index, image in sorted(sheets.items()):
        encoded = image_to_sheet(
            image, 4, sheet_swizzle(sheet_index),
            keep_from=font.tglp.sheets[sheet_index],
            rewrite_mask=masks[sheet_index],
        )
        if len(encoded) != font.tglp.sheet_size:
            raise ValueError(f"Unexpected sheet length: {sheet_index}")
        start = font.tglp.sheet_offset + sheet_index * font.tglp.sheet_size
        candidate[start:start + len(encoded)] = encoded
    result = bytes(candidate)

    checked = bffnt.parse(result)
    checked_atlas = Atlas(checked)
    if checked.charmap != font.charmap or checked.cwdh != font.cwdh:
        raise ValueError("Glyph lookup or character widths changed")
    sheet_start = font.tglp.sheet_offset
    sheet_end = sheet_start + font.tglp.sheet_count * font.tglp.sheet_size
    if (result[:sheet_start] != original[:sheet_start] or
            result[sheet_end:] != original[sheet_end:]):
        raise ValueError("Non-atlas font data changed")

    changed_other = []
    for glyph_index, codepoints in sorted(glyph_codes.items()):
        decoded = checked_atlas.cell(glyph_index)
        if glyph_index in targets:
            if not (decoded >= 220).any():
                raise ValueError(f"Redrawn Han glyph is empty: {codepoints}")
        elif not np.array_equal(atlas.cell(glyph_index), decoded):
            changed_other.append(codepoints)
    if changed_other:
        raise ValueError(
            f"Untouched glyph pixels changed in {len(changed_other)} cells"
        )

    rewritten_codes = {
        codepoint for codepoints in targets.values() for codepoint in codepoints
    }
    missing_redraws = sorted(required - rewritten_codes)
    if missing_redraws:
        raise ValueError("Required Han characters were not redrawn: " +
                         "".join(chr(codepoint) for codepoint in missing_redraws))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(result)
    report = {
        "font": args.source.name,
        "variation": args.variation,
        "size": args.size,
        "dx": args.dx,
        "dy": args.dy,
        "outline": args.outline,
        "blur": args.blur,
        "glyph_count": len(font.charmap),
        "han_codepoints_redrawn": len(rewritten_codes),
        "han_cells_redrawn": len(targets),
        "required_han_codepoints_covered": len(required),
        "other_cells_unchanged": len(glyph_codes) - len(targets),
        "sheets_rewritten": sorted(sheets),
        "source_sha256": digest(original),
        "output_sha256": digest(result),
    }
    if args.report:
        Path(args.report).write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(f"PASS: redrew {len(rewritten_codes)} Han codepoints at weight {args.variation}")
    print(f"PASS: all {len(required)} Han codepoints used by the text are covered")
    print(f"PASS: {report['other_cells_unchanged']} other glyph cells are pixel-identical")
    print(f"output_sha256: {report['output_sha256']}")


if __name__ == "__main__":
    main()