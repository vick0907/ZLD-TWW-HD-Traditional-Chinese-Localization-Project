"""Compare the leaf files of two SARC archives and report what differs."""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sarc  # noqa: E402


def walk(blob, prefix, out):
    if blob[:4] == b"Yaz0":
        blob = sarc.yaz0_decompress(blob)
    if blob[:4] != b"SARC":
        return
    for name, sub in sarc.sarc_read(blob):
        path = f"{prefix}/{name}" if prefix else name
        if sub[:4] in (b"Yaz0", b"SARC"):
            walk(sub, path, out)
        else:
            out[path] = sub


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a", help="reference archive (e.g. the untouched game)")
    ap.add_argument("b", help="modified archive")
    ap.add_argument("--ext", help="only report leaves with this extension")
    args = ap.parse_args()

    A, B = {}, {}
    walk(open(args.a, "rb").read(), "", A)
    walk(open(args.b, "rb").read(), "", B)

    only_a = sorted(set(A) - set(B))
    only_b = sorted(set(B) - set(A))
    changed = sorted(p for p in set(A) & set(B) if A[p] != B[p])

    def keep(p):
        return not args.ext or p.endswith(args.ext)

    print(f"{len(A)} vs {len(B)} leaf files")
    for label, items in (("only in A", only_a), ("only in B", only_b)):
        items = [p for p in items if keep(p)]
        if items:
            print(f"\n{label}: {len(items)}")
            for p in items:
                print(f"    {p}")

    changed = [p for p in changed if keep(p)]
    print(f"\nchanged: {len(changed)}")
    for p in changed:
        print(f"  {len(A[p]):>9} -> {len(B[p]):>9}  {p}")


if __name__ == "__main__":
    main()
