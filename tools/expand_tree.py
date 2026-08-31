"""Recursively expand a SARC/Yaz0 tree into work/tree and write an inventory."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sarc import sarc_read, yaz0_decompress  # noqa: E402

ARCHIVE_EXT = (".szs", ".pack", ".sarc")
inventory = []


def looks_like_archive(blob: bytes) -> bool:
    return blob[:4] in (b"Yaz0", b"SARC")


def walk(blob: bytes, virt: str, dest: str, depth: int = 0):
    if blob[:4] == b"Yaz0":
        blob = yaz0_decompress(blob)
    for name, sub in sarc_read(blob):
        vpath = f"{virt}/{name}"
        if looks_like_archive(sub):
            walk(sub, vpath, dest, depth + 1)
        else:
            outpath = os.path.join(dest, vpath.replace("/", os.sep))
            os.makedirs(os.path.dirname(outpath), exist_ok=True)
            with open(outpath, "wb") as f:
                f.write(sub)
            inventory.append((vpath, len(sub), sub[:4].decode("latin-1")))


def main():
    src, dest, report = sys.argv[1], sys.argv[2], sys.argv[3]
    blob = open(src, "rb").read()
    walk(blob, os.path.splitext(os.path.basename(src))[0], dest)
    inventory.sort()
    with open(report, "w", encoding="utf-8") as f:
        for vpath, size, magic in inventory:
            f.write(f"{size:>9}  {magic!r:<10} {vpath}\n")
    print(f"{len(inventory)} leaf files -> {report}")


if __name__ == "__main__":
    main()
