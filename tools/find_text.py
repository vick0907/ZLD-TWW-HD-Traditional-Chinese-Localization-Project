"""Search the MSBT text of a tree for a pattern and show where it occurs."""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import msbt  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("pattern")
    ap.add_argument("--context", type=int, default=14)
    ap.add_argument("--limit", type=int, default=40)
    args = ap.parse_args()

    rx = re.compile(args.pattern)
    hits = 0
    for dirpath, _, files in os.walk(args.root):
        for name in sorted(files):
            if not name.endswith(".msbt"):
                continue
            path = os.path.join(dirpath, name)
            for i, segs in enumerate(msbt.read(open(path, "rb").read())[0]):
                text = "".join(v for k, v in segs if k == "t")
                for m in rx.finditer(text):
                    a = max(0, m.start() - args.context)
                    b = min(len(text), m.end() + args.context)
                    snippet = text[a:b].replace("\r", "").replace("\n", "\\n")
                    print(f"{name}#{i}: ...{snippet}...")
                    hits += 1
                    if hits >= args.limit:
                        print("(truncated)")
                        return
    print(f"{hits} match(es)")


if __name__ == "__main__":
    main()
