"""Build the original English title with shared Traditional Chinese artwork."""
import argparse
from pathlib import Path
import struct

import numpy as np
from PIL import Image

from dump_bflim import to_image
from pack_bflim import encode_bflim
import sarc


def layout_sections(blob):
    if blob[:6] != b"FLYT\xfe\xff":
        raise ValueError("Expected a big-endian FLYT layout")
    header_size = struct.unpack_from(">H", blob, 6)[0]
    file_size, count = struct.unpack_from(">IH", blob, 12)
    if file_size != len(blob):
        raise ValueError("Layout file size does not match its header")
    offset = header_size
    sections = []
    for _ in range(count):
        length = struct.unpack_from(">I", blob, offset + 4)[0]
        if length < 8 or offset + length > len(blob):
            raise ValueError("Invalid layout section length")
        sections.append(blob[offset:offset + length])
        offset += length
    if offset != len(blob):
        raise ValueError("Unexpected data after layout sections")
    return blob[:header_size], sections


def pane_records(sections):
    records = {}
    parents = []
    last_name = None
    for index, section in enumerate(sections):
        kind = section[:4]
        if kind == b"pas1":
            if last_name is None:
                raise ValueError("Child panes have no parent")
            parents.append(last_name)
        elif kind == b"pae1":
            if not parents:
                raise ValueError("Unbalanced pane hierarchy")
            parents.pop()
        elif kind in (b"pan1", b"pic1", b"txt1", b"wnd1", b"bnd1", b"prt1"):
            last_name = section[12:36].split(b"\0")[0].decode("ascii")
            if last_name in records:
                raise ValueError(f"Duplicate pane: {last_name}")
            records[last_name] = (index, parents[-1] if parents else None)
    if parents:
        raise ValueError("Unclosed pane hierarchy")
    return records


def patch_layout(blob):
    header, sections = layout_sections(blob)
    records = pane_records(sections)
    pairs = (
        ("N_Windwaker_00", "N_WindwakerJ_00"),
        ("P_Windwaker_00", "P_WindwakerJ_00"),
        ("P_WindwakerMask_00", "P_WindwakerJMask_00"),
        ("P_TitleLogoHD_00", "P_TitleLogoHDJ_00"),
    )
    for target_name, reference_name in pairs:
        target_index = records[target_name][0]
        reference = sections[records[reference_name][0]]
        target = bytearray(sections[target_index])
        if target[:4] != reference[:4]:
            raise ValueError(f"Pane types differ: {target_name}, {reference_name}")
        target[8:12] = reference[8:12]
        target[0x2C:0x54] = reference[0x2C:0x54]
        sections[target_index] = bytes(target)

    ruby_index, ruby_parent = records["P_ZeldaRuby_00"]
    if ruby_parent == "N_TitleLogo_00_JpJa":
        parent_index, grandparent = records[ruby_parent]
        parent = sections[parent_index]
        if grandparent != "N_Logo_00":
            raise ValueError("Unexpected Japanese title hierarchy")
        if struct.unpack_from(">5f", parent, 0x38) != (0, 0, 0, 1, 1):
            raise ValueError("Cannot reparent a transformed Japanese title group")
        if sections[ruby_index + 1][:4] == b"pas1":
            raise ValueError("The ruby pane unexpectedly has children")
        ruby = bytearray(sections.pop(ruby_index))
        parent_position = struct.unpack_from(">3f", parent, 0x2C)
        ruby_position = struct.unpack_from(">3f", ruby, 0x2C)
        struct.pack_into(">3f", ruby, 0x2C, *(
            coordinate + parent_coordinate
            for coordinate, parent_coordinate in zip(ruby_position, parent_position)
        ))
        main_index = pane_records(sections)["P_TitleLogoZelda_00"][0]
        if sections[main_index + 1][:4] == b"pas1":
            raise ValueError("The main logo unexpectedly has children")
        sections.insert(main_index + 1, bytes(ruby))
    elif ruby_parent != "N_Logo_00":
        raise ValueError(f"Unexpected ruby parent: {ruby_parent}")

    updated = pane_records(sections)
    if updated.keys() != records.keys() or updated["P_ZeldaRuby_00"][1] != "N_Logo_00":
        raise ValueError("Title pane names or common ruby placement changed unexpectedly")
    return header + b"".join(sections)


def archive_files(blob):
    compressed = blob[:4] == b"Yaz0"
    raw = sarc.yaz0_decompress(blob) if compressed else blob
    return dict(sarc.sarc_read(raw)), raw, compressed


def build_archive(blob, logo, ruby, subtitle):
    for name, image, size in (("main logo", logo, (500, 210)),
                              ("ruby", ruby, (174, 50)),
                              ("subtitle", subtitle, (326, 120))):
        if image.size != size or image.mode != "RGBA":
            raise ValueError(f"{name} must be {size[0]}x{size[1]} RGBA")
    original, raw, compressed = archive_files(blob)
    files = original.copy()
    layouts = [name for name in files if name.endswith("/Title_00.bflyt")]
    if len(layouts) != 1:
        raise ValueError("Expected exactly one Title_00.bflyt")
    layout_name = layouts[0]
    files[layout_name] = patch_layout(files[layout_name])
    by_basename = {Path(name).name: name for name in files}
    texture_changes = (
        ("TitleLogoZelda_00^l.bflim", "TitleLogoZelda_00^l.bflim", logo),
        ("TitleLogoZeldaRuby_00^l.bflim", "TitleLogoZeldaRuby_00^l.bflim", ruby),
        ("TitleLogoWindwakerJ_00^l.bflim", "TitleLogoWindwakerJ_00^l.bflim", subtitle),
        ("TitleLogoWindwaker_00^l.bflim", "TitleLogoWindwakerJ_00^l.bflim", subtitle),
        ("TitleLogoWindwakerJMask_00^s.bflim", "TitleLogoWindwakerJMask_00^s.bflim", subtitle.getchannel("A")),
        ("TitleLogoWindwakerMask_00^s.bflim", "TitleLogoWindwakerJMask_00^s.bflim", subtitle.getchannel("A")),
    )
    changed_paths = {layout_name}
    for target_name, template_name, image in texture_changes:
        target_path = by_basename[target_name]
        files[target_path] = encode_bflim(original[by_basename[template_name]], image)
        changed_paths.add(target_path)

    packed = sarc.sarc_write(list(files.items()), sarc.sarc_alignment(raw))
    result = sarc.yaz0_compress(packed) if compressed else packed
    checked, _, _ = archive_files(result)
    if checked != files:
        raise ValueError("Archive did not round-trip exactly")
    if patch_layout(checked[layout_name]) != checked[layout_name]:
        raise ValueError("Layout patch is not idempotent")
    for path, original_data in original.items():
        if path not in changed_paths and checked[path] != original_data:
            raise ValueError(f"Unexpected modification: {path}")
    for target_name, _, image in texture_changes:
        decoded, note = to_image(checked[by_basename[target_name]])
        if decoded is None or decoded.size != image.size:
            raise ValueError(f"Invalid output texture {target_name}: {note}")
        if image.mode == "RGBA" and not np.array_equal(np.asarray(decoded), np.asarray(image)):
            raise ValueError(f"Pixels changed while packing {target_name}")
    for english_name, japanese_name in (
        ("TitleLogoWindwaker_00^l.bflim", "TitleLogoWindwakerJ_00^l.bflim"),
        ("TitleLogoWindwakerMask_00^s.bflim", "TitleLogoWindwakerJMask_00^s.bflim"),
    ):
        if checked[by_basename[english_name]] != checked[by_basename[japanese_name]]:
            raise ValueError("English and Japanese subtitle assets differ")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--logo", type=Path, required=True)
    parser.add_argument("--ruby", type=Path, required=True)
    parser.add_argument("--subtitle", type=Path, required=True)
    args = parser.parse_args()
    images = [Image.open(path).convert("RGBA") for path in (args.logo, args.ruby, args.subtitle)]
    result = build_archive(args.archive.read_bytes(), *images)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(result)
    if args.out.read_bytes() != result:
        raise ValueError("Output file differs from the verified archive")
    print("PASS: archive round-trip; all RGBA pixels preserved")
    print("PASS: common ruby; matching English/Japanese subtitle layout and masks")
    print("PASS: existing animation files and unrelated resources unchanged")
    print(f"{args.out}: {len(result)} bytes")


if __name__ == "__main__":
    main()