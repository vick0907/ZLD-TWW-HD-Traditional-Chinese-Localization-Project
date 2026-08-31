"""Dump raw CMAP pairs and CWDH entries in file order."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bffnt  # noqa: E402


def main():
    path, out = sys.argv[1], sys.argv[2]
    data = open(path, "rb").read()
    f = bffnt.parse(data)
    lines = [f"cwdh_off={f.finf['cwdh_off']:#x} cmap_off={f.finf['cmap_off']:#x} "
             f"tglp_off={f.finf['tglp_off']:#x} sheetDataOff={f.tglp.sheet_offset:#x} "
             f"filesize={len(data)}"]

    inv = {}
    for code, idx in f.charmap.items():
        inv.setdefault(idx, []).append(chr(code))
    lines.append("index -> char(s), first 80:")
    lines.append("".join(f"[{i}:{''.join(inv.get(i, ['?']))}]" for i in range(80)))
    lines.append("index 360..420:")
    lines.append("".join(f"[{i}:{''.join(inv.get(i, ['?']))}]" for i in range(360, 420)))
    widths = f.cwdh[0][2]
    lines.append("cwdh[0:80]: " + " ".join(f"({a},{b},{c})" for a, b, c in widths[:80]))
    dup = {i: v for i, v in inv.items() if len(v) > 1}
    lines.append(f"indices with multiple chars: {len(dup)} -> {list(dup.items())[:10]}")
    missing = [i for i in range(max(inv) + 1) if i not in inv]
    lines.append(f"unmapped indices below max: {len(missing)} -> {missing[:20]}")
    open(out, "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines[:3]))


if __name__ == "__main__":
    main()
