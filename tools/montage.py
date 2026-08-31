"""Tile RGBA images over a dark background for side-by-side review."""
import argparse
import glob
import os

from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("patterns", nargs="+")
    ap.add_argument("--scale", type=int, default=5)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--crop", help="x0,y0,x1,y1")
    args = ap.parse_args()

    files = []
    for p in args.patterns:
        files += sorted(glob.glob(p)) if any(c in p for c in "*?") else [p]

    crop = tuple(int(v) for v in args.crop.split(",")) if args.crop else None
    tiles = []
    for f in files:
        im = Image.open(f).convert("RGBA")
        if crop:
            im = im.crop(crop)
        bg = Image.new("RGBA", im.size, (20, 20, 28, 255))
        flat = Image.alpha_composite(bg, im).convert("RGB")
        tiles.append((os.path.basename(f)[:-4],
                      flat.resize((flat.width * args.scale, flat.height * args.scale),
                                  Image.NEAREST)))

    w, h = tiles[0][1].size
    rows = (len(tiles) + args.cols - 1) // args.cols
    sheet = Image.new("RGB", (w * min(args.cols, len(tiles)), (h + 22) * rows), (20, 20, 28))
    d = ImageDraw.Draw(sheet)
    for i, (name, img) in enumerate(tiles):
        x, y = (i % args.cols) * w, (i // args.cols) * (h + 22)
        sheet.paste(img, (x, y + 20))
        d.text((x + 6, y + 4), name, fill=(235, 235, 235))
    sheet.save(args.out)
    print(f"{len(tiles)} tiles -> {args.out} {sheet.size}")


if __name__ == "__main__":
    main()
