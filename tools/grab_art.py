"""Copy the user's latest logo artwork out of Downloads under ASCII names."""
import glob
import os
import shutil

WANTED = {(2079, 756): "src_zelda.png", (1976, 796): "src_wind.png"}
DEST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "out", "title_user")

from PIL import Image  # noqa: E402

os.makedirs(DEST, exist_ok=True)
for f in glob.glob(os.path.expanduser("~/Downloads/*.png")):
    try:
        size = Image.open(f).size
    except Exception:
        continue
    if size in WANTED:
        out = os.path.join(DEST, WANTED[size])
        shutil.copyfile(f, out)
        print(f"{size} -> {out}")
