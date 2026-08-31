import sys, io, os, unicodedata

DEFAULT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "Cafe", "charlist.txt")
path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
raw = open(path, "rb").read()
out = io.StringIO()
out.write("bytes: %d\n" % len(raw))
out.write("first16: %s\n" % raw[:16].hex(" "))

for enc in ("utf-16", "utf-8", "gbk"):
    try:
        s = raw.decode(enc)
    except Exception as e:
        out.write("%-8s FAIL %s\n" % (enc, e))
        continue
    out.write("%-8s ok  chars=%d uniq=%d\n" % (enc, len(s), len(set(s))))
    out.write("    head: %r\n" % s[:60])
    out.write("    tail: %r\n" % s[-40:])

s = raw.decode("utf-16")
cats = {}
for ch in s:
    cats[unicodedata.category(ch)] = cats.get(unicodedata.category(ch), 0) + 1
out.write("categories: %s\n" % sorted(cats.items(), key=lambda kv: -kv[1]))
dupes = [c for c in set(s) if s.count(c) > 1]
out.write("duplicate chars: %d %r\n" % (len(dupes), dupes[:20]))
cjk = [c for c in s if "\u4e00" <= c <= "\u9fff"]
out.write("cjk count: %d\n" % len(cjk))

open(sys.argv[2] if len(sys.argv) > 2 else "charlist_report.txt", "w", encoding="utf-8").write(out.getvalue())
