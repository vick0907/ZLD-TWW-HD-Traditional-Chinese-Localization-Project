"""Find corrections that were applied to one message but not to its twins.

Every entry in the override files targets a single key, so a wording fix only
lands where it was aimed. This re-scans the finished corpus for each `find`
string and reports the messages that still carry it, which are the instances
the reviewer probably meant to catch as well.

    audit_overrides.py out\\bilingual.tsv text\\overrides.json text\\review_pass2.json out\\report.txt
"""
import json
import sys
from pathlib import Path

# Fragments below this length, or made only of punctuation and control-code
# syntax, match everywhere and say nothing about a missed instance.
MIN_LEN = 3
NOISE = set("　 、。，；：！？「」『』（）…—·\r\n\\{}:0123456789ABCDEF")


def load_corpus(tsv):
    rows = {}
    with open(tsv, encoding="utf-8") as f:
        next(f)
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 4:
                rows[parts[0]] = parts[3]
    return rows


def interesting(find):
    return len(find) >= MIN_LEN and not set(find) <= NOISE


def main(argv):
    if len(argv) < 4:
        print(__doc__)
        return 2
    tsv, *patches, report = argv[1:]
    corpus = load_corpus(tsv)

    findings = []
    for patch in patches:
        for entry in json.loads(Path(patch).read_text(encoding="utf-8")):
            find = entry.get("find")
            if not find or entry.get("all") or not interesting(find):
                continue
            others = [k for k, text in corpus.items()
                      if k != entry["key"] and find in text]
            if others:
                findings.append((Path(patch).name, entry["key"], find,
                                 entry.get("replace", ""), others))

    with open(report, "w", encoding="utf-8") as out:
        for patch, key, find, replace, others in findings:
            out.write(f"[{patch}] {key}\n  find    {find!r}\n"
                      f"  replace {replace!r}\n"
                      f"  still in {len(others)}: {', '.join(others[:12])}\n\n")
        out.write(f"total {len(findings)}\n")

    print(f"overrides whose original wording survives elsewhere: {len(findings)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
