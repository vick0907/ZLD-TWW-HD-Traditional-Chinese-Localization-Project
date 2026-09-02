"""MSBT (MsgStdBn) text section reader/writer for The Wind Waker HD.

Strings are represented as a list of segments so that control codes are never
exposed to text processing:
    ("t", "some text")   plain UTF-16 text
    ("c", b"\\x00\\x0e...")  raw control-code bytes, copied through verbatim
"""
import re
import struct

MAGIC = b"MsgStdBn"


def _sections(data: bytes):
    pos = 0x20
    while pos + 8 <= len(data):
        magic = data[pos:pos + 4]
        if len(magic) < 4 or not magic.isalnum():
            break
        size = struct.unpack_from(">I", data, pos + 4)[0]
        body = pos + 16
        yield magic, pos, size, body
        pos = body + size
        if size % 0x10:
            pos += 0x10 - size % 0x10


def find_txt2(data: bytes):
    for magic, start, size, body in _sections(data):
        if magic == b"TXT2":
            return start, size, body
    raise ValueError("TXT2 section not found")


def decode_string(buf: bytes, pos: int):
    segs = []
    text = []
    while True:
        code = struct.unpack_from(">H", buf, pos)[0]
        if code == 0:
            pos += 2
            break
        if code == 0x000E:
            if text:
                segs.append(("t", "".join(text)))
                text = []
            arg_len = struct.unpack_from(">H", buf, pos + 6)[0]
            segs.append(("c", buf[pos:pos + 8 + arg_len]))
            pos += 8 + arg_len
        elif code >> 8 == 0xE0:
            if text:
                segs.append(("t", "".join(text)))
                text = []
            segs.append(("c", buf[pos:pos + 2]))
            pos += 2
        else:
            text.append(buf[pos:pos + 2].decode("utf-16be"))
            pos += 2
    if text:
        segs.append(("t", "".join(text)))
    return segs, pos


def encode_string(segs) -> bytes:
    out = bytearray()
    for kind, val in segs:
        if kind == "t":
            out += val.encode("utf-16be")
        else:
            out += val
    out += b"\x00\x00"
    return bytes(out)


def read(data: bytes):
    """Return (list of message segment-lists, txt2 start offset)."""
    start, size, body = find_txt2(data)
    count = struct.unpack_from(">I", data, body)[0]
    offsets = [struct.unpack_from(">I", data, body + 4 + i * 4)[0] for i in range(count)]
    messages = []
    for off in offsets:
        segs, _ = decode_string(data, body + off)
        messages.append(segs)
    return messages, start


def write(data: bytes, messages) -> bytes:
    """Rebuild the file with a new TXT2 section, keeping earlier sections intact."""
    start, _, _ = find_txt2(data)
    out = bytearray(data[:start])

    count = len(messages)
    body = bytearray(struct.pack(">I", count) + b"\x00" * (4 * count))
    for i, segs in enumerate(messages):
        struct.pack_into(">I", body, 4 + i * 4, len(body))
        body += encode_string(segs)

    out += b"TXT2" + struct.pack(">I", len(body)) + b"\x00" * 8 + body
    if len(out) % 0x10:
        out += b"\xAB" * (0x10 - len(out) % 0x10)

    struct.pack_into(">I", out, 0x12, len(out))
    section_count = sum(1 for _ in _sections(bytes(out)))
    struct.pack_into(">H", out, 0x0E, section_count)
    return bytes(out)


def to_display(segs) -> str:
    parts = []
    for kind, val in segs:
        if kind == "t":
            parts.append(val)
        elif len(val) == 2:
            parts.append("{%04X}" % struct.unpack(">H", val)[0])
        else:
            group, typ, ln = struct.unpack_from(">HHH", val, 2)
            args = val[8:].hex().upper()
            parts.append("{0E:%X:%X:%X%s}" % (group, typ, ln, ":" + args if args else ""))
    return "".join(parts)


_SHORT_CODE = re.compile(r"^[0-9A-F]{4}$")
_LONG_CODE = re.compile(r"^0E:([0-9A-F]+):([0-9A-F]+):([0-9A-F]+)(?::([0-9A-F]*))?$")


def from_display(text: str):
    """Inverse of to_display. A '{' that is not a valid code stays literal text."""
    segs = []
    buf = []
    pos = 0
    while pos < len(text):
        ch = text[pos]
        if ch == "{":
            end = text.find("}", pos)
            token = text[pos + 1:end] if end != -1 else None
            code = _parse_code(token) if token is not None else None
            if code is not None:
                if buf:
                    segs.append(("t", "".join(buf)))
                    buf = []
                segs.append(("c", code))
                pos = end + 1
                continue
        buf.append(ch)
        pos += 1
    if buf:
        segs.append(("t", "".join(buf)))
    return segs


def _parse_code(token: str):
    if _SHORT_CODE.match(token):
        return struct.pack(">H", int(token, 16))
    m = _LONG_CODE.match(token)
    if not m:
        return None
    group, typ, ln = (int(m.group(i), 16) for i in (1, 2, 3))
    args = bytes.fromhex(m.group(4) or "")
    if len(args) != ln:
        return None
    return struct.pack(">HHHH", 0x000E, group, typ, ln) + args


def read_labels(data: bytes):
    """Return {message index: label} from LBL1, or None when the file has none."""
    for magic, _, _, body in _sections(data):
        if magic != b"LBL1":
            continue
        groups = struct.unpack_from(">I", data, body)[0]
        out = {}
        for i in range(groups):
            count, offset = struct.unpack_from(">II", data, body + 4 + i * 8)
            pos = body + offset
            for _ in range(count):
                ln = data[pos]
                name = data[pos + 1:pos + 1 + ln].decode("ascii", "replace")
                out[struct.unpack_from(">I", data, pos + 1 + ln)[0]] = name
                pos += 1 + ln + 4
        return out
    return None

