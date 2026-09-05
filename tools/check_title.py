"""Render the packed title geometry and compare both languages with an approved preview."""
import argparse
from pathlib import Path
import struct

import numpy as np
from PIL import Image

from build_title import archive_files, layout_sections, pane_records
from dump_bflim import to_image


def render(files, japanese):
    layout = next(blob for name, blob in files.items() if name.endswith("/Title_00.bflyt"))
    _, sections = layout_sections(layout)
    records = pane_records(sections)
    if records["P_ZeldaRuby_00"][1] != "N_Logo_00":
        raise ValueError("Ruby is still hidden inside a language-specific group")
    textures = {Path(name).name: blob for name, blob in files.items() if name.endswith(".bflim")}
    pictures = (
        ("P_TitleLogoZelda_00", "TitleLogoZelda_00^l.bflim"),
        ("P_ZeldaRuby_00", "TitleLogoZeldaRuby_00^l.bflim"),
        ("P_WindwakerJ_00" if japanese else "P_Windwaker_00",
         "TitleLogoWindwakerJ_00^l.bflim" if japanese else "TitleLogoWindwaker_00^l.bflim"),
        ("P_TitleLogoHDJ_00" if japanese else "P_TitleLogoHD_00", "TitleLogoHD_00^l.bflim"),
    )
    canvas = Image.new("RGBA", (500, 296), (0, 0, 0, 0))
    occupied = np.zeros((296, 500), dtype=bool)
    for pane_name, texture_name in pictures:
        pane = sections[records[pane_name][0]]
        width, height = struct.unpack_from(">2f", pane, 0x4C)
        position_x, position_y, scale_x, scale_y = 0.0, 0.0, 1.0, 1.0
        current = pane_name
        while current != "N_Logo_00":
            index, parent = records[current]
            section = sections[index]
            if struct.unpack_from(">3f", section, 0x38) != (0, 0, 0):
                raise ValueError(f"Unsupported rotation on {current}")
            translate_x, translate_y, _ = struct.unpack_from(">3f", section, 0x2C)
            local_scale_x, local_scale_y = struct.unpack_from(">2f", section, 0x44)
            position_x = translate_x + position_x * local_scale_x
            position_y = translate_y + position_y * local_scale_y
            scale_x *= local_scale_x
            scale_y *= local_scale_y
            if parent is None:
                raise ValueError(f"{pane_name} is outside the logo group")
            current = parent
        image, note = to_image(textures[texture_name])
        if image is None:
            raise ValueError(note)
        display_size = (round(width * scale_x), round(height * scale_y))
        if image.size != display_size:
            image = image.resize(display_size, Image.Resampling.LANCZOS)
        left = round(250 + position_x - display_size[0] / 2)
        top = round(105 - position_y - display_size[1] / 2)
        layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        layer.alpha_composite(image, (left, top))
        visible = np.asarray(layer.getchannel("A")) > 8
        if (occupied & visible).any():
            raise ValueError(f"Visible artwork overlaps at {pane_name}")
        occupied |= visible
        canvas.alpha_composite(layer)
    return canvas


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("preview", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    files, _, _ = archive_files(args.archive.read_bytes())
    expected = Image.open(args.preview).convert("RGBA")
    for japanese in (False, True):
        actual = render(files, japanese)
        if not np.array_equal(np.asarray(actual), np.asarray(expected)):
            raise ValueError(f"{'Japanese' if japanese else 'English'} layout differs from approved preview")
        print(f"PASS: {'Japanese' if japanese else 'English'} packed layout matches approved preview exactly")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        render(files, False).save(args.out)
    print("PASS: no overlaps; common ruby visible in both layout branches")


if __name__ == "__main__":
    main()