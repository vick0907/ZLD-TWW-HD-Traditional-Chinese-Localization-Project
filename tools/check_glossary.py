"""Check the Chinese script against Nintendo's official Traditional Chinese terms.

For every glossary term that appears in the retail English script, look at the
aligned Chinese message and report the ones that do not use the official name.
Run tools/fetch_glossary.py first to build the glossary.
"""
import argparse
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import align_en  # noqa: E402
import msbt  # noqa: E402


def aligned_messages(english_root, chinese_root):
    en_files = align_en.find_msbt(english_root)
    zh_files = align_en.find_msbt(chinese_root)
    for name in sorted(set(en_files) & set(zh_files)):
        stem = os.path.splitext(name)[0]
        en_msgs, labels = align_en.load(en_files[name])
        zh_msgs, _ = align_en.load(zh_files[name])
        if len(en_msgs) != len(zh_msgs):
            continue
        for i, (e, z) in enumerate(zip(en_msgs, zh_msgs)):
            yield (align_en.message_key(stem, i, labels),
                   align_en.plain(e), align_en.plain(z))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("english_root")
    ap.add_argument("chinese_root")
    ap.add_argument("--glossary", default="text/glossary_official.json")
    ap.add_argument("--out", default="out/glossary_check.txt")
    ap.add_argument("--min-hits", type=int, default=2)
    ap.add_argument("--samples", type=int, default=3)
    args = ap.parse_args()

    glossary = {term: entry for term, entry in
                json.load(open(args.glossary, encoding="utf-8")).items()
                if entry["zhT"] and len(term) >= 3}
    patterns = {term: re.compile(r"\b" + re.escape(term) + r"\b")
                for term in glossary}

    messages = list(aligned_messages(args.english_root, args.chinese_root))
    hits = collections.defaultdict(list)
    for key, en, zh in messages:
        for term, pattern in patterns.items():
            if pattern.search(en):
                hits[term].append((key, zh))

    rows = []
    for term, appearances in hits.items():
        if len(appearances) < args.min_hits:
            continue
        entry = glossary[term]
        official = list(entry["zhT"])
        accepted = official + list(entry["zhS"])
        missing = [(key, zh) for key, zh in appearances
                   if not any(name in zh for name in accepted)]
        if missing:
            rows.append((len(missing), len(appearances), term, entry, missing))

    rows.sort(reverse=True, key=lambda r: (r[0], r[2]))
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(f"{len(messages)} aligned messages, {len(glossary)} glossary terms\n")
        f.write(f"{len(rows)} terms where the Chinese script does not use the "
                "official Traditional Chinese name\n")
        for missing_count, total, term, entry, missing in rows:
            names = ", ".join(f"{name} ({'/'.join(sorted(set(games)))})"
                              for name, games in entry["zhT"].items())
            f.write(f"\n==== {term}  -  official: {names}\n")
            f.write(f"     {missing_count} of {total} messages do not use it\n")
            for key, zh in missing[:args.samples]:
                f.write(f"     {key}: {' '.join(zh.split())[:88]}\n")
    print(f"{len(rows)} terms to review -> {args.out}")


if __name__ == "__main__":
    main()
