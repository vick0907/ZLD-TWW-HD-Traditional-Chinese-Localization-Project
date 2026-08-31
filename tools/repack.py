"""Rebuild permanent_2d_UsEnglish.pack with the converted MSBT files and new fonts."""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sarc  # noqa: E402


def rebuild_inner(blob: bytes, replacements: dict, path_prefix: str, stats: list) -> bytes:
    """Recursively replace leaf files inside a SARC / Yaz0-SARC blob."""
    was_yaz0 = blob[:4] == b"Yaz0"
    raw = sarc.yaz0_decompress(blob) if was_yaz0 else blob
    if raw[:4] != b"SARC":
        return blob

    files = sarc.sarc_read(raw)
    new_files = []
    changed = False
    for name, sub in files:
        vpath = f"{path_prefix}/{name}"
        if sub[:4] in (b"Yaz0", b"SARC"):
            new_sub = rebuild_inner(sub, replacements, vpath, stats)
            changed |= new_sub is not sub
        elif vpath in replacements:
            new_sub = replacements[vpath]
            changed = True
            stats.append((vpath, len(sub), len(new_sub)))
        else:
            new_sub = sub
        new_files.append((name, new_sub))

    if not changed:
        return blob
    out = sarc.sarc_write(new_files, sarc.sarc_alignment(raw))
    return sarc.yaz0_compress(out) if was_yaz0 else out


def collect_replacements(pack_name, msbt_root, font_dir):
    repl = {}
    for dirpath, _, files in os.walk(msbt_root):
        for name in files:
            if not name.endswith(".msbt"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), msbt_root)
            repl[rel.replace(os.sep, "/")] = open(os.path.join(dirpath, name), "rb").read()
    if font_dir and os.path.isdir(font_dir):
        for name in os.listdir(font_dir):
            if name.endswith(".bffnt"):
                key = f"{pack_name}/{os.path.splitext(name)[0]}_bffnt.szs/{name}"
                repl[key] = open(os.path.join(font_dir, name), "rb").read()
    return repl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pack")
    ap.add_argument("out")
    ap.add_argument("--msbt-root", required=True)
    ap.add_argument("--font-dir")
    args = ap.parse_args()

    pack_name = os.path.splitext(os.path.basename(args.pack))[0]
    repl = collect_replacements(pack_name, args.msbt_root, args.font_dir)
    print(f"{len(repl)} replacement files")

    blob = open(args.pack, "rb").read()
    stats = []
    out = rebuild_inner(blob, repl, pack_name, stats)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "wb") as f:
        f.write(out)

    print(f"replaced {len(stats)} files")
    for vpath, before, after in sorted(stats, key=lambda s: -s[2])[:8]:
        print(f"  {before:>9} -> {after:>9}  {vpath}")
    print(f"pack {len(blob)} -> {len(out)} bytes")


if __name__ == "__main__":
    main()
