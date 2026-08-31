"""Structurally validate MSBT files.

Version 1.0.0 of the upstream Simplified Chinese pack shipped with a "TXT2 chunk
size error" that v1.0.1 had to fix, so every size/offset field our writer
produces is checked against the actual bytes here.
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import msbt  # noqa: E402


def validate(data: bytes):
    errors = []
    if data[:8] != msbt.MAGIC:
        return ["bad magic"]

    declared_size = struct.unpack_from(">I", data, 0x12)[0]
    if declared_size != len(data):
        errors.append(f"header size field {declared_size} != actual {len(data)}")

    declared_sections = struct.unpack_from(">H", data, 0x0E)[0]

    pos = 0x20
    seen = 0
    while pos + 16 <= len(data):
        magic = data[pos:pos + 4]
        if not magic.isalnum():
            errors.append(f"section {seen} at {pos:#x}: bad magic {magic!r}")
            break
        size = struct.unpack_from(">I", data, pos + 4)[0]
        body = pos + 16
        if body + size > len(data):
            errors.append(f"{magic.decode()} claims {size} bytes but only "
                          f"{len(data) - body} remain")
            break
        if magic == b"TXT2":
            block = data[body:body + size]
            count = struct.unpack_from(">I", block, 0)[0]
            if 4 + count * 4 > size:
                errors.append(f"TXT2 offset table ({count} entries) overruns the block")
            else:
                for i in range(count):
                    off = struct.unpack_from(">I", block, 4 + i * 4)[0]
                    if off >= size:
                        errors.append(f"TXT2 string {i} offset {off} outside block ({size})")
                        continue
                    # walk it with the real decoder; a naive 0x0000 search would trip
                    # over control-code payloads and UTF-16 byte pairs
                    try:
                        _, end = msbt.decode_string(block, off)
                    except Exception as e:
                        errors.append(f"TXT2 string {i} failed to decode: {e!r}")
                        continue
                    if end > size:
                        errors.append(f"TXT2 string {i} runs past the end of the block")
        seen += 1
        pos = body + size
        if size % 0x10:
            pos += 0x10 - size % 0x10

    if pos != len(data):
        errors.append(f"sections end at {pos:#x}, file is {len(data):#x}")
    if declared_sections != seen:
        errors.append(f"header says {declared_sections} sections, walked {seen}")
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    args = ap.parse_args()

    total = bad = 0
    for dirpath, _, files in os.walk(args.root):
        for name in sorted(files):
            if not name.endswith(".msbt"):
                continue
            total += 1
            errs = validate(open(os.path.join(dirpath, name), "rb").read())
            if errs:
                bad += 1
                print(f"FAIL {name}")
                for e in errs:
                    print(f"       {e}")
    print(f"\n{total} MSBT files checked, {bad} with structural errors")


if __name__ == "__main__":
    main()
