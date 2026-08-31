"""Fit an oversized logo artwork into a game texture's canvas.

The artwork is trimmed to its alpha bounds, scaled to fit the target box while
keeping its aspect ratio, and centred there. An optional overlay (e.g. the
original English wordmark) is composited on top afterwards.
"""
import argparse

from PIL import Image


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("art")
    ap.add_argument("out")
    ap.add_argument("--canvas", required=True, help="WxH of the target texture")
    ap.add_argument("--box", required=True, help="x0,y0,x1,y1 area the art must fit inside")
    ap.add_argument("--overlay", help="PNG drawn on top at full canvas size")
    args = ap.parse_args()

    cw, ch = (int(v) for v in args.canvas.lower().split("x"))
    x0, y0, x1, y1 = (int(v) for v in args.box.split(","))
    bw, bh = x1 - x0 + 1, y1 - y0 + 1

    art = Image.open(args.art).convert("RGBA")
    art = art.crop(art.getbbox())
    scale = min(bw / art.width, bh / art.height)
    art = art.resize((max(1, round(art.width * scale)), max(1, round(art.height * scale))),
                     Image.LANCZOS)

    canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    px = x0 + (bw - art.width) // 2
    py = y0 + (bh - art.height) // 2
    canvas.alpha_composite(art, (px, py))

    if args.overlay:
        canvas.alpha_composite(Image.open(args.overlay).convert("RGBA"))

    canvas.save(args.out)
    print(f"{args.out}: art {art.width}x{art.height} at ({px},{py}) on {cw}x{ch}")


if __name__ == "__main__":
    main()
