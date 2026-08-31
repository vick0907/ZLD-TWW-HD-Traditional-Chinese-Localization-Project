"""Dump pane names, sizes and positions from a Wii U BFLYT layout."""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dump_bflim import walk  # noqa: E402


def panes(blob):
    magic, bom, header_size, version, file_size, section_count = struct.unpack_from(
        ">4sHHIIH", blob, 0)
    assert magic == b"FLYT", magic
    pos = header_size
    out = []
    for _ in range(section_count):
        if pos + 8 > len(blob):
            break
        kind, size = struct.unpack_from(">4sI", blob, pos)
        if kind in (b"pic1", b"pan1", b"txt1", b"wnd1", b"bnd1", b"prt1"):
            name = blob[pos + 8 + 4:pos + 8 + 4 + 24].split(b"\x00")[0].decode("latin-1")
            tx, ty, tz = struct.unpack_from(">3f", blob, pos + 8 + 0x24)
            w, h = struct.unpack_from(">2f", blob, pos + 8 + 0x44)
            out.append((kind.decode(), name, w, h, tx, ty))
        pos += size
        if size == 0:
            break
    return out


def main():
    archive, target = sys.argv[1], sys.argv[2]
    leaves = {}
    walk(open(archive, "rb").read(), "", leaves)
    blob = next(v for k, v in leaves.items() if k.endswith(target))
    print(f"{'type':<6}{'pane':<26}{'size':>18}   translate")
    for kind, name, w, h, tx, ty in panes(blob):
        print(f"{kind:<6}{name:<26}{w:>8.1f} x{h:>7.1f}   ({tx:.1f}, {ty:.1f})")


if __name__ == "__main__":
    main()
