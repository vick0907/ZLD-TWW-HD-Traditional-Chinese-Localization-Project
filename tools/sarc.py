"""SARC / Yaz0 reader + writer (Python 3 port of NWPlayer123's SARCExtract/SARCPack)."""
import os
import struct
import sys


def yaz0_decompress(data: bytes) -> bytes:
    assert data[:4] == b"Yaz0"
    size = struct.unpack_from(">I", data, 4)[0]
    src = 16
    out = bytearray()
    code = 0
    bits = 0
    while len(out) < size:
        if bits == 0:
            code = data[src]
            src += 1
            bits = 8
        if code & 0x80:
            out.append(data[src])
            src += 1
        else:
            rle = struct.unpack_from(">H", data, src)[0]
            src += 2
            dist = rle & 0xFFF
            start = len(out) - (dist + 1)
            read = rle >> 12
            if read == 0:
                read = data[src] + 0x12
                src += 1
            else:
                read += 2
            for i in range(read):
                out.append(out[start + i])
        code = (code << 1) & 0xFF
        bits -= 1
    return bytes(out)


def yaz0_compress(data: bytes, level: int = 6) -> bytes:
    try:
        import libyaz0
        return bytes(libyaz0.compress(data, 0, level))
    except ImportError:
        pass
    # store-only fallback: valid Yaz0, no compression
    out = bytearray(b"Yaz0" + struct.pack(">I", len(data)) + b"\x00" * 8)
    pos = 0
    while pos < len(data):
        out.append(0xFF)
        out += data[pos:pos + 8]
        pos += 8
    return bytes(out)


def calchash(name: str, multiplier: int = 0x65) -> int:
    result = 0
    for ch in name.encode("ascii"):
        result = (ch + result * multiplier) & 0xFFFFFFFF
    return result


def _cstr(data: bytes, pos: int) -> str:
    end = data.index(b"\x00", pos)
    return data[pos:end].decode("ascii")


def sarc_read(data: bytes):
    """Return (list of (name, bytes), data_offset_alignment_hint)."""
    assert data[:4] == b"SARC", "not a SARC"
    hdr_len, bom, file_size, data_off = struct.unpack_from(">HHII", data, 4)
    assert bom == 0xFEFF, "little endian SARC not supported"
    pos = hdr_len + 4  # skip version/reserved
    assert data[pos - 4:pos] == b"\x01\x00\x00\x00" or True
    pos = 0x14
    assert data[pos:pos + 4] == b"SFAT", "SFAT missing"
    node_count, multiplier = struct.unpack_from(">HI", data, pos + 6)
    pos += 0x0C
    nodes = []
    for _ in range(node_count):
        fhash, attrs, start, end = struct.unpack_from(">IIII", data, pos)
        pos += 16
        nodes.append((fhash, attrs, start, end))
    assert data[pos:pos + 4] == b"SFNT", "SFNT missing"
    name_base = pos + 8
    files = []
    for fhash, attrs, start, end in nodes:
        name_off = (attrs & 0xFFFFFF) * 4
        name = _cstr(data, name_base + name_off)
        files.append((name, data[data_off + start:data_off + end]))
    return files


def sarc_alignment(data: bytes, cap: int = 0x2000) -> int:
    """Largest power of two (<= cap) that divides dataStart and every file offset."""
    _, _, _, data_off = struct.unpack_from(">HHII", data, 4)
    node_count = struct.unpack_from(">H", data, 0x1A)[0]
    values = [data_off]
    for i in range(node_count):
        values.append(struct.unpack_from(">I", data, 0x20 + i * 16 + 8)[0])
    align = cap
    while align > 1 and any(v % align for v in values):
        align >>= 1
    return align


def sarc_write(files, padding: int = 0x100) -> bytes:
    """files: list of (name, bytes) - order is recomputed by hash, like the game tools."""
    entries = []
    for name, blob in files:
        namesize = len(name) + (4 - len(name) % 4)
        entries.append({"name": name, "data": blob, "namesize": namesize})
    entries.sort(key=lambda e: calchash(e["name"]))

    num = len(entries)
    lennames = sum(e["namesize"] for e in entries)
    header_size = 32 + 16 * num + 8 + lennames
    pad_sfat = padding - (header_size % padding) if header_size % padding else 0
    data_start = header_size + pad_sfat

    # file offsets: every file padded except the last
    filepos = 0
    for i, e in enumerate(entries):
        e["start"] = filepos
        e["end"] = filepos + len(e["data"])
        step = len(e["data"])
        if step % padding:
            step += padding - (step % padding)
        filepos += len(e["data"]) if i == num - 1 else step

    total = data_start + filepos

    out = bytearray()
    out += b"SARC\x00\x14\xFE\xFF"
    out += struct.pack(">I", total)
    out += struct.pack(">I", data_start)
    out += b"\x01\x00\x00\x00SFAT\x00\x0C"
    out += struct.pack(">H", num)
    out += struct.pack(">I", 0x65)
    strpos = 0
    for e in entries:
        out += struct.pack(">I", calchash(e["name"]))
        out += b"\x01" + struct.pack(">I", strpos // 4)[1:]
        strpos += e["namesize"]
        out += struct.pack(">I", e["start"])
        out += struct.pack(">I", e["end"])
    out += b"SFNT\x00\x08\x00\x00"
    for e in entries:
        out += e["name"].encode("ascii").ljust(e["namesize"], b"\x00")
    out += b"\x00" * pad_sfat
    for i, e in enumerate(entries):
        out += e["data"]
        if i != num - 1:
            step = len(e["data"])
            if step % padding:
                out += b"\x00" * (padding - (step % padding))
    return bytes(out)


def load_archive(path: str):
    data = open(path, "rb").read()
    compressed = data[:4] == b"Yaz0"
    if compressed:
        data = yaz0_decompress(data)
    return sarc_read(data), compressed


def extract(path: str, dest: str):
    files, compressed = load_archive(path)
    for name, blob in files:
        out = os.path.join(dest, name.replace("/", os.sep))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as f:
            f.write(blob)
    return files, compressed


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    got, comp = extract(src, dst)
    print(f"{len(got)} files, yaz0={comp}")
    for name, blob in got:
        print(f"{len(blob):>9}  {name}")
