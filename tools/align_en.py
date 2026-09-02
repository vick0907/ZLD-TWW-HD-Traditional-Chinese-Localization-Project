"""Align the retail English script with the Chinese script, message by message.

The English and Chinese packs hold the same 68 MSBT files with the same message
counts and the same LBL1 labels, so message N of a file is a translation of
message N of the English file. That gives a reliable bilingual corpus to review
the Chinese wording against.

Outputs:
  bilingual.tsv       key, flags, English, Chinese - one row per message
  review_flagged.txt  only the messages a heuristic considers suspicious
  glossary.txt        every distinct Chinese rendering of a recurring English
                      proper noun, so inconsistent terminology stands out
"""
import argparse
import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import msbt  # noqa: E402

CJK = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]{2,}")
NUMBER = re.compile(r"\d+")
PROPER = re.compile(r"\b[A-Z][a-z]{2,}\b")
SENTENCE_START = re.compile(r"[.!?\"'\u2019\u201c\u2014:;\-\u3000]\s*$|^\s*$|\n\s*$")
CODE_TOKEN = re.compile(r"\{(?:[0-9A-F]{4}|0E:[^{}]*)\}")


def find_msbt(root):
    out = {}
    for dirpath, _, files in os.walk(root):
        for name in files:
            if name.endswith(".msbt"):
                out[name] = os.path.join(dirpath, name)
    return out


def load(path):
    data = open(path, "rb").read()
    messages, _ = msbt.read(data)
    return messages, msbt.read_labels(data) or {}


def message_key(stem, index, labels):
    label = labels.get(index)
    return f"{stem}#{label}" if label else f"{stem}#idx{index}"


def plain(segs):
    return "".join(v for k, v in segs if k == "t")


def inserts(segs):
    """Multiset of data-carrying control codes (player name, counts, items...)."""
    return collections.Counter(
        val[2:6] for kind, val in segs if kind == "c" and len(val) > 2)


def classify(en_segs, zh_segs):
    en, zh = plain(en_segs), plain(zh_segs)
    en_s, zh_s = en.strip(), zh.strip()
    en_words = len(LATIN_WORD.findall(en))
    flags = []
    if en_s and not zh_s:
        flags.append("empty")
    if en_words and zh_s and not CJK.search(zh_s):
        flags.append("untranslated")
    if inserts(en_segs) != inserts(zh_segs):
        flags.append("inserts")
    if set(NUMBER.findall(en)) != set(NUMBER.findall(zh)):
        flags.append("numbers")
    zh_chars = len(CJK.findall(zh))
    if en_words >= 12 and zh_chars:
        ratio = zh_chars / en_words
        if ratio < 0.7:
            flags.append("short")
        elif ratio > 3.4:
            flags.append("long")
    return flags


def escape(text):
    return text.replace("\\", "\\\\").replace("\t", "\\t").replace(
        "\r", "").replace("\n", "\\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("english_root", help="tree unpacked from the retail English pack")
    ap.add_argument("chinese_root", help="tree holding the Chinese MSBTs")
    ap.add_argument("--tsv", default="out/bilingual.tsv")
    ap.add_argument("--flagged", default="out/review_flagged.txt")
    ap.add_argument("--glossary", default="out/glossary.txt")
    ap.add_argument("--min-term-hits", type=int, default=4)
    args = ap.parse_args()

    en_files = find_msbt(args.english_root)
    zh_files = find_msbt(args.chinese_root)
    shared = sorted(set(en_files) & set(zh_files))
    missing = sorted(set(en_files) ^ set(zh_files))
    if missing:
        print("warning: unpaired MSBT files:", ", ".join(missing))

    rows = []
    skipped = []
    for name in shared:
        stem = os.path.splitext(name)[0]
        en_msgs, en_labels = load(en_files[name])
        zh_msgs, _ = load(zh_files[name])
        if len(en_msgs) != len(zh_msgs):
            skipped.append(f"{name}: {len(en_msgs)} English vs {len(zh_msgs)} Chinese")
            continue
        for i, (e, z) in enumerate(zip(en_msgs, zh_msgs)):
            rows.append((message_key(stem, i, en_labels), classify(e, z),
                         msbt.to_display(e), msbt.to_display(z)))

    for line in skipped:
        print("skipped", line)

    os.makedirs(os.path.dirname(args.tsv) or ".", exist_ok=True)
    with open(args.tsv, "w", encoding="utf-8") as f:
        f.write("key\tflags\tenglish\tchinese\n")
        for key, flags, en, zh in rows:
            f.write(f"{key}\t{','.join(flags)}\t{escape(en)}\t{escape(zh)}\n")

    flagged = [r for r in rows if r[1]]
    with open(args.flagged, "w", encoding="utf-8") as f:
        counts = collections.Counter(fl for _, flags, _, _ in rows for fl in flags)
        f.write(f"{len(flagged)} of {len(rows)} messages flagged\n")
        for flag, n in counts.most_common():
            f.write(f"  {flag}: {n}\n")
        for key, flags, en, zh in flagged:
            f.write(f"\n======== {key}  [{','.join(flags)}]\n")
            f.write(f"EN: {en}\n")
            f.write(f"ZH: {zh}\n")

    write_glossary(args.glossary, rows, args.min_term_hits)
    print(f"{len(rows)} aligned messages -> {args.tsv}")
    print(f"{len(flagged)} flagged -> {args.flagged}")


def write_glossary(path, rows, min_hits):
    hits = collections.defaultdict(list)
    for key, _, en, zh in rows:
        for term in proper_nouns(strip_codes(en)):
            hits[term].append((key, " ".join(strip_codes(zh).split())))

    lines = [f"proper nouns appearing in at least {min_hits} messages, with the "
             "aligned Chinese line - scan for inconsistent renderings"]
    for term in sorted(hits, key=lambda t: (-len(hits[t]), t)):
        appearances = hits[term]
        if len(appearances) < min_hits:
            continue
        lines.append(f"\n==== {term}  ({len(appearances)} messages)")
        for key, zh in appearances[:6]:
            lines.append(f"  {key}: {zh[:88]}")
    open(path, "w", encoding="utf-8").write("\n".join(lines))


def proper_nouns(text):
    """Capitalised words that are not sentence-initial, i.e. names and places."""
    return {m.group() for m in PROPER.finditer(text)
            if not SENTENCE_START.search(text[max(0, m.start() - 24):m.start()])}


def strip_codes(display):
    return CODE_TOKEN.sub("", display)


if __name__ == "__main__":
    main()
