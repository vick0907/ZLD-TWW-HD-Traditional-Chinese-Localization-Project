"""Copy the built language pack into a loose-file game dump."""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ["content/Common/Pack/permanent_2d_UsEnglish.pack",
         "content/Common/Layout/Title_00.szs"]


def main():
    game = sys.argv[1]
    for rel in FILES:
        src = os.path.join(ROOT, "out", "release", *rel.split("/"))
        dst = os.path.join(game, *rel.split("/"))
        if not os.path.exists(dst):
            raise SystemExit(f"not a Wii U dump - missing {dst}")
        shutil.copyfile(src, dst)
        print(f"{os.path.getsize(dst):>10}  {rel}")


if __name__ == "__main__":
    main()
