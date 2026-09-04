"""Machine checks over the EN/zh alignment.

Each check exists because the same class of bug was found by hand at least once;
turning it into a detector is what makes "we read it" into "this class is clean".
Run after tools/align_en.py has written out/bilingual.tsv.
"""
import re
import sys
from collections import defaultdict

CODE = re.compile(r"\{[^{}]*\}")
CJK = r"\u4e00-\u9fff"


def plain(s):
    """Display string with control codes and escaped newlines removed."""
    return CODE.sub("", s.replace("\\n", "\n"))


def flat(s):
    return re.sub(r"\s+", " ", plain(s)).strip()


def load(path):
    rows = []
    for line in open(path, encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) == 4 and p[0] != "key":
            rows.append(p)
    return rows


CHECKS = []


def check(name, why):
    def deco(fn):
        CHECKS.append((name, why, fn))
        return fn
    return deco


@check("stray-latin", "中文句中夾雜孤立的英文字母，通常是打字殘留")
def stray_latin(key, en, zh):
    m = re.search(r"[%s][A-Za-z][%s]|[%s][A-Za-z][，。！？]" % (CJK, CJK, CJK), zh)
    return m.group(0) if m else None


@check("stray-brace", "文字裡出現裸露的大括號，會原樣顯示在遊戲中")
def stray_brace(key, en, zh):
    t = plain(zh)
    m = re.search(r"[{}]", t)
    return repr(t[max(0, m.start() - 8):m.start() + 8]) if m else None


@check("orphan-punct", "整行只有標點，通常是句號被換行擠到下一行")
def orphan_punct(key, en, zh):
    # a name insert or colour reset legitimately opens the line before the
    # sentence-final mark, so only flag a line that is punctuation and nothing else
    lines = zh.replace("\\n", "\n").split("\n")
    for i, ln in enumerate(lines[1:], 1):
        if not re.fullmatch(r"\s*[。，、！？；：]+\s*", ln):
            continue
        if re.search(r"[%s]\s*$" % CJK, lines[i - 1]):
            return ln.strip()
    return None


@check("latin-fullstop", "英文縮寫用了全形句號")
def latin_fullstop(key, en, zh):
    m = re.search(r"[A-Za-z]。[A-Za-z]", plain(zh))
    return m.group(0) if m else None


@check("punct-residue", "全形與半形標點疊在一起")
def punct_residue(key, en, zh):
    z = re.sub(r"\.\.\.", "\u2026", zh)          # a real ellipsis after ! or ? is fine
    m = re.search(r"[。！？，、][.!?,]|[.]。|，，|。。(?!。)", z)
    return m.group(0) if m else None


@check("dup-phrase", "相鄰重複的字串")
def dup_phrase(key, en, zh):
    t = re.sub(r"\s", "", plain(zh))
    m = re.search(r"([%s]{2,6})\1" % CJK, t)
    if m and m.group(1) not in ("哈哈", "呵呵", "嘿嘿", "喲喲", "嗬嗬", "啊啊", "呼呼",
                                "嗯嗯", "噢噢", "哦哦", "喔喔", "咯咯", "嘻嘻", "謝謝"):
        return m.group(0)
    m = re.search(r"([的了是在我你他也就都很不])\1", t)
    return m.group(0) if m else None


@check("truncated", "英文有句尾標點但中文沒有，可能被截斷")
def truncated(key, en, zh):
    e, z = flat(en), flat(zh)
    if len(z) < 4 or not re.search(r"[%s]" % CJK, z):
        return None
    if not re.search(r"[.!?\"'\u2026]\s*$", e):
        return None
    if re.search(r"[。！？…」』）\)\u2026.!?~]\s*$", z):
        return None
    return "ends with: " + z[-14:]


@check("too-short", "中文長度不到英文的五分之一，通常是漏譯或截斷")
def too_short(key, en, zh):
    e, z = flat(en), flat(zh)
    if len(e) < 70 or not re.search(r"[a-z]{3}", e):
        return None
    ratio = len(z) / len(e)
    return "%d/%d = %.2f" % (len(z), len(e), ratio) if ratio < 0.2 else None


@check("long-line", "單行超過 34 個全形字，文字框可能爆版")
def long_line(key, en, zh):
    if not re.search(r"[%s]" % CJK, plain(zh)):     # untranslated Miiverse samples
        return None
    for ln in plain(zh).split("\n"):
        w = sum(2 if ord(c) > 0x2000 else 1 for c in ln.strip())
        if w > 68:
            return "%d cols: %s" % (w // 2, ln.strip()[:40])
    return None


NEG_EN = re.compile(r"\b(?:don't|doesn't|didn't|won't|can't|cannot|never|no one|"
                    r"nobody|nothing|isn't|aren't|wasn't|weren't|shouldn't|"
                    r"mustn't|couldn't|wouldn't|neither)\b", re.I)
NEG_ZH = re.compile(r"[不沒別勿莫甀無非未少難]")


@check("negation-flip", "英文有強否定、中文沒有，語意可能顫倒")
def negation_flip(key, en, zh):
    e, z = flat(en), flat(zh)
    # only the dangerous direction, and only when the sentence is short enough
    # that the negation has to map one-to-one
    if not (25 < len(e) < 130):
        return None
    if not NEG_EN.search(e) or NEG_ZH.search(z):
        return None
    return "EN neg, zh none"


@check("question-flip", "英文是問句、中文不是問句（或相反）")
def question_flip(key, en, zh):
    e, z = flat(en), flat(zh)
    if len(e) < 25 or "\n" in flat(en):
        return None
    qe, qz = e.rstrip().endswith("?"), bool(re.search(r"[？?]\s*$", z))
    return "EN ?, zh none" if qe and not qz else ("zh ?, EN none" if qz and not qe else None)


CLASSIFIER = {
    "棵": "歌|曲|花|劍|人|信", "顆": "樹|苗|歌|曲|劍", "隻": "歌|曲|花|樹|劍",
    "首": "花|樹|劍|人", "朵": "樹|劍|人|歌", "把": "花|樹(?!葉)|人",
    "張": "花|樹|劍", "面": "花|樹|歌",
}


@check("classifier", "量詞與名詞不搭")
def classifier(key, en, zh):
    t = re.sub(r"\s", "", plain(zh))
    for cl, bad in CLASSIFIER.items():
        m = re.search(r"[一二三四五六七八九十兩這那每幾]%s(%s)" % (cl, bad), t)
        if m:
            return m.group(0)
    return None


def main():
    rows = load(sys.argv[1] if len(sys.argv) > 1 else "out/bilingual.tsv")
    out = open(sys.argv[2] if len(sys.argv) > 2 else "out/qa_report.txt", "w", encoding="utf-8")
    counts = {}
    for name, why, fn in CHECKS:
        hits = []
        for key, _, en, zh in rows:
            try:
                r = fn(key, en, zh)
            except Exception as exc:            # a broken detector must not hide the rest
                r = "detector error: %r" % (exc,)
            if r:
                hits.append((key, r, flat(en), flat(zh)))
        counts[name] = len(hits)
        if not hits:
            continue
        print("### %s  (%d)  -- %s" % (name, len(hits), why), file=out)
        for key, r, e, z in hits:
            print("  %-22s [%s]" % (key, r), file=out)
            print("      EN: %s" % e[:110], file=out)
            print("      ZH: %s" % z[:110], file=out)
        print(file=out)

    # proper nouns rendered more than one way
    terms = defaultdict(lambda: defaultdict(list))
    NAMES = ["Deku Tree", "Great Sea", "Forsaken Fortress", "Master Sword", "Wind Waker",
             "Triforce", "Great Fairy", "Rito", "Korok", "Zora", "Moblin", "Bokoblin",
             "ChuChu", "Picto Box", "Grappling Hook", "Hookshot", "Deku Leaf", "Boomerang",
             "Joy Pendant", "Skull Necklace", "Knight's Crest", "Golden Feather",
             "Tingle", "Beedle", "Medli", "Makar", "Valoo", "Jabun", "Ganondorf", "Zelda",
             "Sea Chart", "Treasure Chart", "Bait Bag", "Delivery Bag", "Spoils Bag",
             "sky spirit", "water spirit", "spirit of the earth", "attendant", "chieftain"]
    for key, _, en, zh in rows:
        e, z = flat(en), flat(zh)
        for n in NAMES:
            if re.search(re.escape(n), e, re.I):
                terms[n][z].append(key)
    print("### glossary spread (manual read)", file=out)
    for n in NAMES:
        variants = terms.get(n)
        if variants:
            print("  %s: %d messages" % (n, sum(len(v) for v in variants.values())), file=out)
    out.close()
    for name, why, _ in CHECKS:
        print("%-16s %d" % (name, counts[name]))


if __name__ == "__main__":
    main()
