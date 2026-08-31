"""Validate the SARC writer: re-writing an untouched archive must reproduce it byte-for-byte."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sarc  # noqa: E402


def check(blob: bytes, label: str, lines: list):
    was_yaz0 = blob[:4] == b"Yaz0"
    raw = sarc.yaz0_decompress(blob) if was_yaz0 else blob
    if raw[:4] != b"SARC":
        return
    files = sarc.sarc_read(raw)
    align = sarc.sarc_alignment(raw)
    rebuilt = sarc.sarc_write(files, align)
    status = "OK  " if rebuilt == raw else "DIFF"
    lines.append(f"{status} {label}: align={align:#x} {len(raw)} -> {len(rebuilt)} "
                 f"({len(files)} files)")
    if rebuilt != raw:
        first = next((i for i in range(min(len(raw), len(rebuilt)))
                      if raw[i] != rebuilt[i]), None)
        lines.append(f"     first diff at {first} ({first:#x})" if first is not None
                     else "     length differs only")


def main():
    pack = sys.argv[1]
    lines = []
    blob = open(pack, "rb").read()
    check(blob, os.path.basename(pack), lines)
    files = sarc.sarc_read(blob if blob[:4] == b"SARC" else sarc.yaz0_decompress(blob))
    for name, sub in files[:12]:
        check(sub, name, lines)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
