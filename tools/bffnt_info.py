"""Print BFFNT header/TGLP/CWDH/CMAP summary."""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bffnt  # noqa: E402

FORMATS = {0: "RGBA8", 1: "RGB8", 2: "RGBA5551", 3: "RGB565", 4: "RGBA4",
           5: "LA8", 6: "HILO8", 7: "L8", 8: "A8", 9: "LA4", 10: "L4",
           11: "A4", 12: "ETC1", 13: "ETC1A4", 14: "BC1", 15: "BC2",
           16: "BC3", 17: "BC4", 18: "BC5"}


def report(path, out):
    f = bffnt.parse(open(path, "rb").read())
    t = f.tglp
    out.write(f"=== {os.path.basename(path)} ===\n")
    out.write(f"version      : {f.version:#010x}   filesize={len(f.raw)}\n")
    out.write(f"FINF         : height={f.finf['height']} width={f.finf['width']} "
              f"ascent={f.finf['ascent']} linefeed={f.finf['line_feed']} "
              f"alter={f.finf['alter_index']} encoding={f.finf['encoding']}\n")
    out.write(f"               default (left,glyph,char)="
              f"({f.finf['def_left']},{f.finf['def_glyph']},{f.finf['def_char']})\n")
    out.write(f"TGLP cell    : {t.cell_width}x{t.cell_height}  maxCharW={t.max_char_width}"
              f"  baseline={t.baseline}\n")
    out.write(f"TGLP sheets  : {t.sheet_count} x {t.sheet_width}x{t.sheet_height}"
              f"  size={t.sheet_size} ({t.sheet_size:#x})"
              f"  fmt={t.fmt}={FORMATS.get(t.fmt, '?')}\n")
    out.write(f"TGLP grid    : {t.columns} cols x {t.rows} rows = {t.per_sheet}/sheet"
              f"  -> capacity {t.capacity} glyphs\n")
    out.write(f"TGLP dataoff : {t.sheet_offset:#x}\n")
    total = 0
    for start, end, widths in f.cwdh:
        total += len(widths)
        out.write(f"CWDH         : {start}..{end} ({len(widths)} entries)\n")
    out.write(f"CWDH total   : {total}\n")
    for begin, end, method, _ in f.cmap:
        out.write(f"CMAP         : {begin:#06x}..{end:#06x} method={method}\n")
    out.write(f"CMAP entries : {len(f.charmap)}\n")
    idx = sorted(f.charmap.values())
    out.write(f"glyph index  : min={idx[0]} max={idx[-1]}\n")
    codes = sorted(f.charmap)
    sample = "".join(chr(c) for c in codes[:80])
    out.write(f"first chars  : {sample!r}\n")
    cjk = [c for c in codes if 0x4E00 <= c <= 0x9FFF]
    out.write(f"CJK unified  : {len(cjk)}\n")
    out.write("\n")


if __name__ == "__main__":
    buf = io.StringIO()
    for p in sys.argv[1:-1]:
        try:
            report(p, buf)
        except Exception as e:
            buf.write(f"=== {p} === FAILED: {e!r}\n\n")
    open(sys.argv[-1], "w", encoding="utf-8").write(buf.getvalue())
    print(f"wrote {sys.argv[-1]}")
