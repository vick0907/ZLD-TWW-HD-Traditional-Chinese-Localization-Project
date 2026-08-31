"""List the newest images in a folder with their alpha bounding box and aspect."""
import glob
import os
import sys
import time

import numpy as np
from PIL import Image

pattern = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(r"~\Downloads\*.png")
count = int(sys.argv[2]) if len(sys.argv) > 2 else 6

for f in sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)[:count]:
    im = Image.open(f)
    a = np.asarray(im.convert("RGBA"))
    ys, xs = np.nonzero(a[..., 3] > 16)
    w, h = xs.max() - xs.min() + 1, ys.max() - ys.min() + 1
    stamp = time.strftime("%m-%d %H:%M:%S", time.localtime(os.path.getmtime(f)))
    print(f"{stamp}  {im.size[0]}x{im.size[1]} {im.mode:<5} "
          f"bbox {w}x{h} aspect {w / h:.2f}  {os.path.basename(f)}")
