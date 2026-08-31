"""Dump all MSBT messages to a readable UTF-8 file."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import msbt  # noqa: E402


def iter_msbt(root):
    for dirpath, _, files in os.walk(root):
        for name in sorted(files):
            if name.endswith(".msbt"):
                yield os.path.join(dirpath, name)


def main():
    root, out = sys.argv[1], sys.argv[2]
    with open(out, "w", encoding="utf-8") as f:
        for path in sorted(iter_msbt(root)):
            data = open(path, "rb").read()
            messages, _ = msbt.read(data)
            f.write(f"\n======== {os.path.basename(path)}  ({len(messages)} msgs) ========\n")
            for i, segs in enumerate(messages):
                f.write(f"---- {i} ----\n{msbt.to_display(segs)}\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
