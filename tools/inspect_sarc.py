"""Dump SARC header + node layout to infer the original packer's alignment rules."""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sarc  # noqa: E402


def describe(raw: bytes, label: str, lines: list):
    hdr_len, bom, file_size, data_off = struct.unpack_from(">HHII", raw, 4)
    node_count, mult = struct.unpack_from(">HI", raw, 0x1A)
    lines.append(f"--- {label}: len={len(raw)} fileSize={file_size} dataStart={data_off} "
                 f"nodes={node_count} mult={mult:#x}")
    pos = 0x20
    prev_end = None
    for i in range(node_count):
        fhash, attrs, start, end = struct.unpack_from(">IIII", raw, pos)
        pos += 16
        name_off = (attrs & 0xFFFFFF) * 4
        name_base = 0x20 + node_count * 16 + 8
        nul = raw.index(b"\x00", name_base + name_off)
        name = raw[name_base + name_off:nul].decode()
        gap = "" if prev_end is None else f" gapFromPrev={start - prev_end}"
        lines.append(f"    {name:<28} start={start:>8} end={end:>8} "
                     f"size={end - start:>8} absStart={data_off + start:>8}{gap}")
        prev_end = end
    lines.append(f"    tail padding = {len(raw) - (data_off + prev_end)}")


def main():
    pack = sys.argv[1]
    out = sys.argv[2]
    lines = []
    blob = open(pack, "rb").read()
    raw = blob if blob[:4] == b"SARC" else sarc.yaz0_decompress(blob)
    describe(raw, os.path.basename(pack) + " (outer)", lines)
    files = sarc.sarc_read(raw)
    for name, sub in files:
        if name in ("SaveData_00_msbt.szs", "FadeWipe_01.szs", "CKingMsg_bffnt.szs",
                    "message_msbt.szs", "Cursor_00.szs"):
            inner = sarc.yaz0_decompress(sub) if sub[:4] == b"Yaz0" else sub
            describe(inner, name, lines)
    open(out, "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines[:60]))


if __name__ == "__main__":
    main()
