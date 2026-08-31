"""Work out which characters the menu font must gain.

Any message whose characters are all inside the original menu font's repertoire
could have been drawn with it, so its converted form must be renderable too.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bffnt  # noqa: E402
import msbt  # noqa: E402


def text_of(segs):
    return "".join(v for k, v in segs if k == "t")


def main():
    font_path, old_root, new_root, out = sys.argv[1:5]
    font = bffnt.parse(open(font_path, "rb").read())
    repertoire = {chr(c) for c in font.charmap}

    needed = set()
    candidates = 0
    for dirpath, _, files in os.walk(old_root):
        for name in sorted(files):
            if not name.endswith(".msbt"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), old_root)
            new_path = os.path.join(new_root, rel)
            if not os.path.exists(new_path):
                continue
            old_msgs = msbt.read(open(os.path.join(dirpath, name), "rb").read())[0]
            new_msgs = msbt.read(open(new_path, "rb").read())[0]
            for old_segs, new_segs in zip(old_msgs, new_msgs):
                old_text = text_of(old_segs)
                if old_text and set(old_text) <= repertoire:
                    candidates += 1
                    needed.update(text_of(new_segs))

    extra = sorted(c for c in needed - repertoire
                   if ord(c) >= 0x20 and not (0xE000 <= ord(c) <= 0xF8FF))
    with open(out, "w", encoding="utf-8") as f:
        f.write("".join(extra))
    print(f"menu-renderable messages: {candidates}")
    print(f"font repertoire: {len(repertoire)}  needed extra glyphs: {len(extra)}")
    print(f"free slots: {font.tglp.capacity - len(font.charmap)}")
    print("wrote", out)


if __name__ == "__main__":
    main()
