"""Wii U BFFNT (FFNT) reader/writer: FINF / TGLP / CWDH / CMAP."""
import struct
from dataclasses import dataclass, field

MAPPING_DIRECT = 0
MAPPING_TABLE = 1
MAPPING_SCAN = 2


@dataclass
class Tglp:
    cell_width: int
    cell_height: int
    sheet_count: int
    max_char_width: int
    sheet_size: int
    baseline: int
    fmt: int
    columns: int
    rows: int
    sheet_width: int
    sheet_height: int
    sheet_offset: int
    sheets: list = field(default_factory=list)

    @property
    def cell_w(self) -> int:
        """TGLP stores cell size minus one."""
        return self.cell_width + 1

    @property
    def cell_h(self) -> int:
        return self.cell_height + 1

    @property
    def per_sheet(self) -> int:
        return self.columns * self.rows

    @property
    def capacity(self) -> int:
        return self.per_sheet * self.sheet_count


@dataclass
class Bffnt:
    raw: bytes
    version: int
    finf_offset: int
    finf: dict
    tglp: Tglp
    cwdh: list          # list of (start, end, [(left, glyph, char), ...])
    cmap: list          # list of (begin, end, method, payload)
    charmap: dict       # codepoint -> glyph index


def _u8(b, o):
    return b[o]


def _u16(b, o):
    return struct.unpack_from(">H", b, o)[0]


def _u32(b, o):
    return struct.unpack_from(">I", b, o)[0]


def parse(data: bytes) -> Bffnt:
    assert data[:4] == b"FFNT", "not FFNT"
    assert _u16(data, 4) == 0xFEFF, "expected big endian"
    version = _u32(data, 8)

    finf_off = _u16(data, 6)
    assert data[finf_off:finf_off + 4] == b"FINF"
    finf = {
        "font_type": _u8(data, finf_off + 8),
        "height": _u8(data, finf_off + 9),
        "width": _u8(data, finf_off + 10),
        "ascent": _u8(data, finf_off + 11),
        "line_feed": _u16(data, finf_off + 12),
        "alter_index": _u16(data, finf_off + 14),
        "def_left": _u8(data, finf_off + 16),
        "def_glyph": _u8(data, finf_off + 17),
        "def_char": _u8(data, finf_off + 18),
        "encoding": _u8(data, finf_off + 19),
        "tglp_off": _u32(data, finf_off + 20),
        "cwdh_off": _u32(data, finf_off + 24),
        "cmap_off": _u32(data, finf_off + 28),
    }

    t = finf["tglp_off"] - 8
    assert data[t:t + 4] == b"TGLP"
    tglp = Tglp(
        cell_width=_u8(data, t + 8), cell_height=_u8(data, t + 9),
        sheet_count=_u8(data, t + 10), max_char_width=_u8(data, t + 11),
        sheet_size=_u32(data, t + 12), baseline=_u16(data, t + 16),
        fmt=_u16(data, t + 18), columns=_u16(data, t + 20), rows=_u16(data, t + 22),
        sheet_width=_u16(data, t + 24), sheet_height=_u16(data, t + 26),
        sheet_offset=_u32(data, t + 28),
    )
    for i in range(tglp.sheet_count):
        s = tglp.sheet_offset + i * tglp.sheet_size
        tglp.sheets.append(data[s:s + tglp.sheet_size])

    cwdh = []
    off = finf["cwdh_off"]
    while off:
        c = off - 8
        assert data[c:c + 4] == b"CWDH", f"CWDH missing at {c:#x}"
        start, end = _u16(data, c + 8), _u16(data, c + 10)
        nxt = _u32(data, c + 12)
        widths = []
        p = c + 16
        for _ in range(end - start + 1):
            widths.append((data[p], data[p + 1], struct.unpack_from(">b", data, p + 2)[0]))
            p += 3
        cwdh.append((start, end, widths))
        off = nxt

    cmap = []
    charmap = {}
    off = finf["cmap_off"]
    while off:
        c = off - 8
        assert data[c:c + 4] == b"CMAP", f"CMAP missing at {c:#x}"
        begin, end, method = _u16(data, c + 8), _u16(data, c + 10), _u16(data, c + 12)
        nxt = _u32(data, c + 16)
        p = c + 20
        if method == MAPPING_DIRECT:
            base = _u16(data, p)
            for i, code in enumerate(range(begin, end + 1)):
                charmap[code] = base + i
        elif method == MAPPING_TABLE:
            for i, code in enumerate(range(begin, end + 1)):
                idx = _u16(data, p + i * 2)
                if idx != 0xFFFF:
                    charmap[code] = idx
        else:
            count = _u16(data, p)
            for i in range(count):
                code = _u16(data, p + 2 + i * 4)
                idx = _u16(data, p + 4 + i * 4)
                if idx != 0xFFFF:
                    charmap[code] = idx
        cmap.append((begin, end, method, None))
        off = nxt

    return Bffnt(data, version, finf_off, finf, tglp, cwdh, cmap, charmap)


def build_cwdh(widths) -> bytes:
    """widths: list of (left, glyph, char)."""
    body = b"".join(struct.pack(">Bbb", left & 0xFF, glyph, char)
                    for left, glyph, char in widths)
    payload = struct.pack(">HHI", 0, len(widths) - 1, 0) + body
    size = 8 + len(payload)
    pad = (-size) % 4
    return b"CWDH" + struct.pack(">I", size + pad) + payload + b"\x00" * pad


def build_cmap_scan(chars) -> bytes:
    """Scan-type CMAP mapping each char in `chars` to its list index."""
    pairs = sorted((ord(c), i) for i, c in enumerate(chars))
    payload = struct.pack(">HHHHI", 0x0000, 0xFFFF, MAPPING_SCAN, 0, 0)
    payload += struct.pack(">H", len(pairs))
    payload += b"".join(struct.pack(">HH", code, idx) for code, idx in pairs)
    size = 8 + len(payload)
    pad = (-size) % 4
    return b"CMAP" + struct.pack(">I", size + pad) + payload + b"\x00" * pad
