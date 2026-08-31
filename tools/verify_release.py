"""End-to-end check of the rebuilt pack: text is Traditional and every character has a glyph."""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bffnt  # noqa: E402
import msbt  # noqa: E402
import sarc  # noqa: E402

SIMPLIFIED_PROBE = "国东车马门见贝页风飞长韦纟讠讥说这时会对开来们过学国乐买卖东丝"


def walk_archive(blob, prefix, out):
    if blob[:4] == b"Yaz0":
        blob = sarc.yaz0_decompress(blob)
    for name, sub in sarc.sarc_read(blob):
        path = f"{prefix}/{name}"
        if sub[:4] in (b"Yaz0", b"SARC"):
            walk_archive(sub, path, out)
        else:
            out[path] = sub


def main():
    pack_path, report = sys.argv[1], sys.argv[2]
    leaves = {}
    walk_archive(open(pack_path, "rb").read(), "pack", leaves)

    fonts = {}
    for path, blob in leaves.items():
        if path.endswith(".bffnt"):
            fonts[os.path.basename(path)] = bffnt.parse(blob)

    msg_font = fonts["CKingMsg.bffnt"]
    main_font = fonts["CKingMain.bffnt"]

    chars = collections.Counter()
    messages = 0
    for path, blob in leaves.items():
        if not path.endswith(".msbt"):
            continue
        for segs in msbt.read(blob)[0]:
            messages += 1
            for kind, val in segs:
                if kind == "t":
                    chars.update(val)

    lines = [f"leaf files: {len(leaves)}",
             f"fonts: {sorted(fonts)}",
             f"messages: {messages}  unique text chars: {len(chars)}"]
    for name, font in sorted(fonts.items()):
        lines.append(f"  {name}: {len(font.charmap)} glyphs / capacity {font.tglp.capacity}")

    missing_msg = sorted(c for c in chars if ord(c) not in msg_font.charmap
                         and ord(c) >= 0x20 and not (0xE000 <= ord(c) <= 0xF8FF))
    lines.append(f"chars missing from CKingMsg: {len(missing_msg)} {''.join(missing_msg)!r}")

    missing_main = sorted(c for c in chars if ord(c) not in main_font.charmap
                          and ord(c) >= 0x20 and not (0xE000 <= ord(c) <= 0xF8FF))
    lines.append(f"chars missing from CKingMain (menu font, expected - it only "
                 f"carries UI text): {len(missing_main)}")

    still_simplified = sorted(c for c in chars if c in SIMPLIFIED_PROBE)
    lines.append(f"simplified-only probe chars still present: {''.join(still_simplified)!r}")

    trad_probe = "國東車馬門見貝頁風飛長說這時會對開來們過學樂買賣絲"
    present = "".join(c for c in trad_probe if c in chars)
    lines.append(f"traditional probe chars present in text: {present!r}")

    open(report, "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
