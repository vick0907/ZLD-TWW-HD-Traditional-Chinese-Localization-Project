"""Calibrate the glyph renderer against the game font and dump a comparison strip."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bffnt  # noqa: E402
import glyph_render  # noqa: E402
from atlas import Atlas  # noqa: E402
from PIL import Image  # noqa: E402

CALIB = "日月山川人大中小天王正方五百千文本立平田目口"


def reference_cells(f, chars):
    a = Atlas(f)
    return {ch: a.cell_for_char(ch) for ch in chars if a.cell_for_char(ch) is not None}


def main():
    font_bffnt, ttf, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    variation = sys.argv[4] if len(sys.argv) > 4 else None
    index = int(sys.argv[5]) if len(sys.argv) > 5 else 0
    os.makedirs(outdir, exist_ok=True)
    f = bffnt.parse(open(font_bffnt, "rb").read())
    t = f.tglp
    refs = reference_cells(f, CALIB)
    log = []
    renderer, score = glyph_render.calibrate(ttf, refs, t.cell_w, t.cell_h,
                                             variation, index, log)
    print("\n".join(log))

    chars = CALIB + "風國來說們這時會對開"
    strip = Image.new("L", (t.cell_w * len(chars), t.cell_h * 2 + 4))
    for i, ch in enumerate(chars):
        if ch in refs:
            strip.paste(Image.fromarray(refs[ch]), (i * t.cell_w, 0))
        strip.paste(Image.fromarray(renderer.render(ch, t.cell_w, t.cell_h)),
                    (i * t.cell_w, t.cell_h + 4))
    strip.resize((strip.width * 3, strip.height * 3), Image.NEAREST).save(
        os.path.join(outdir, "calibration.png"))
    print("wrote", os.path.join(outdir, "calibration.png"))


if __name__ == "__main__":
    main()
