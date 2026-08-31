"""Survey proper nouns / frequent terms in the extracted text."""
import collections
import re
import sys

src, out = sys.argv[1], sys.argv[2]
s = open(src, encoding="utf-8").read()
s = re.sub(r"\{[^}]*\}", "", s)
s = re.sub(r"-+ \d+ -+", "", s)
s = re.sub(r"=+ \S+ +\(\d+ msgs\) =+", "", s)

names = ["塞尔达", "林克", "海拉尔", "加农", "三角神力", "风之杖", "德库", "卢比",
         "阿丽尔", "特朗", "梅德利", "马库", "庭格尔", "大妖精", "格利姆", "瓦尔",
         "红狮", "伐尔", "妖精", "火山", "要塞", "神庙", "公主", "王国", "勇者",
         "海盗", "船长", "回旋镖", "炸弹", "弓箭", "勾爪", "铁锤", "船帆", "宝箱"]
lines = ["== known name counts =="]
for n in names:
    c = s.count(n)
    if c:
        lines.append(f"{n}\t{c}")

cjk = re.findall(r"[\u4e00-\u9fff]+", s)
cnt = collections.Counter()
for w in cjk:
    for i in range(len(w) - 2):
        cnt[w[i:i + 3]] += 1
lines.append("\n== top 3-grams ==")
for w, c in cnt.most_common(60):
    lines.append(f"{w}\t{c}")

chars = collections.Counter(c for c in s if "\u4e00" <= c <= "\u9fff")
lines.append(f"\nunique CJK in text: {len(chars)}")
open(out, "w", encoding="utf-8").write("\n".join(lines))
print("wrote", out)
