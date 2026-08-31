"""Report metadata chunks embedded in the PNG files a repository tracks."""
import os
import struct
import subprocess
import sys

INTERESTING = {b"tEXt", b"iTXt", b"zTXt", b"eXIf", b"caBX", b"iCCP", b"pHYs", b"tIME"}

root = sys.argv[1]
files = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True,
                       text=True, check=True).stdout.split()

for rel in files:
    if not rel.lower().endswith(".png"):
        continue
    data = open(os.path.join(root, rel), "rb").read()
    pos, found = 8, []
    while pos + 8 <= len(data):
        length = struct.unpack_from(">I", data, pos)[0]
        kind = data[pos + 4:pos + 8]
        if kind in INTERESTING:
            body = data[pos + 8:pos + 8 + min(length, 200)]
            # keep the console happy on non-UTF-8 code pages
            text = "".join(c if 32 <= ord(c) < 127 else "." for c in body.decode("latin-1"))
            found.append(f"{kind.decode()} ({length} bytes): {text[:150]}")
        if kind == b"IEND":
            break
        pos += 12 + length
    print(rel)
    for f in found:
        print(f"    {f}")
    if not found:
        print("    no metadata chunks")
