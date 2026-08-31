"""List the rarest characters in the text with context.

The upstream translation was OCR'd from the GameCube patch (the author said so
when releasing v0.9), so misrecognised characters are the expected defect. They
show up as unusual characters that occur only once or twice.
"""
import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import msbt  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--max-count", type=int, default=2)
    ap.add_argument("--context", type=int, default=10)
    args = ap.parse_args()

    freq = collections.Counter()
    where = {}
    for dirpath, _, files in os.walk(args.root):
        for name in sorted(files):
            if not name.endswith(".msbt"):
                continue
            for i, segs in enumerate(msbt.read(open(os.path.join(dirpath, name), "rb").read())[0]):
                text = "".join(v for k, v in segs if k == "t")
                for pos, ch in enumerate(text):
                    if "\u4e00" <= ch <= "\u9fff":
                        freq[ch] += 1
                        where.setdefault(ch, (name, i, text, pos))

    rare = [c for c, n in freq.items() if n <= args.max_count]
    print(f"{len(freq)} distinct CJK characters; {len(rare)} occur <= {args.max_count} times\n")
    for ch in sorted(rare, key=lambda c: (freq[c], c)):
        name, idx, text, pos = where[ch]
        a, b = max(0, pos - args.context), min(len(text), pos + args.context + 1)
        snippet = text[a:b].replace("\r", "").replace("\n", " ")
        print(f"{ch}  x{freq[ch]}  {name}#{idx}: ...{snippet}...")


if __name__ == "__main__":
    main()
