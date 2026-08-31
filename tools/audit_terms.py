"""Audit converted text for wording that still reads as Mainland Chinese.

Reports only candidates that actually occur, with a sample line each, so the
suggestions can be reviewed before being added to convert_text.TERMS.
"""
import argparse
import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import msbt  # noqa: E402

# (pattern, suggested Taiwan wording, note)
CANDIDATES = [
    # Zelda terminology (Nintendo's official zh-TW names)
    (r"黃金聖三角|金聖三角|聖三角", "三角神力", "Triforce"),
    (r"迴旋鏢|回旋鏢", "迴力鏢", "boomerang"),
    (r"庭格爾", "庭格爾", "Tingle - no official zh-TW name, left alone"),
    # computing / UI vocabulary
    (r"界面", "介面", "interface"),
    (r"信息", "訊息", "message/information"),
    (r"默認", "預設", "default"),
    (r"設置", "設定", "setting"),
    (r"菜單", "選單", "menu"),
    (r"用戶", "使用者", "user"),
    (r"手柄", "手把", "controller"),
    (r"存儲", "儲存", "storage"),
    (r"文件", "檔案", "file"),
    (r"程序", "程式", "program"),
    (r"數據", "資料", "data"),
    (r"視頻", "影片", "video"),
    (r"質量", "品質", "quality"),
    (r"激活", "啟動", "activate"),
    (r"打印", "列印", "print"),
    (r"拷貝", "複製", "copy"),
    (r"光盤", "光碟", "disc"),
    (r"軟件", "軟體", "software"),
    (r"硬件", "硬體", "hardware"),
    (r"網絡", "網路", "network"),
    # everyday vocabulary
    (r"土豆", "馬鈴薯", "potato"),
    (r"西紅柿", "番茄", "tomato"),
    (r"自行車", "腳踏車", "bicycle"),
    (r"出租車", "計程車", "taxi"),
    (r"服務員", "服務生", "waiter"),
    (r"姥姥", "外婆", "grandma"),
    (r"方便麵", "泡麵", "instant noodles"),
    (r"冰棍", "冰棒", "popsicle"),
    (r"水平", "水準", "level/standard - check context, 水平 can mean horizontal"),
    (r"通過", "透過", "via - check context, 通過 is fine for 'pass through'"),
    # Mainland colloquialisms
    (r"這兒", "這裡", "here"),
    (r"那兒", "那裡", "there"),
    (r"哪兒", "哪裡", "where"),
    (r"點兒", "點", "erhua"),
    (r"事兒", "事", "erhua"),
    (r"味兒", "味", "erhua"),
    (r"勁兒", "勁", "erhua"),
    (r"玩兒", "玩", "erhua"),
    (r"個兒", "個", "erhua"),
    (r"咋", "怎麼", "how (northern dialect)"),
    (r"甭", "別", "don't (northern dialect)"),
    (r"俺", "我", "I (northern dialect)"),
    (r"倆", "兩個", "the two of them"),
    (r"仨", "三個", "the three of them"),
    (r"忽悠", "唬弄", "to fool someone"),
    (r"靠譜", "可靠", "reliable"),
    (r"沒轍", "沒辦法", "no way out"),
    (r"起碼", "至少", "at least - also used in Taiwan"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--samples", type=int, default=1)
    args = ap.parse_args()

    texts = []
    for dirpath, _, files in os.walk(args.root):
        for name in sorted(files):
            if name.endswith(".msbt"):
                for segs in msbt.read(open(os.path.join(dirpath, name), "rb").read())[0]:
                    texts.append((name, "".join(v for k, v in segs if k == "t")))

    print(f"scanned {len(texts)} messages\n")
    for pattern, suggestion, note in CANDIDATES:
        rx = re.compile(pattern)
        hits = [(n, t) for n, t in texts if rx.search(t)]
        if not hits:
            continue
        counts = collections.Counter(m for _, t in hits for m in rx.findall(t))
        found = ", ".join(f"{k}x{v}" for k, v in counts.most_common())
        print(f"[{len(hits):>3}] {found:<22} -> {suggestion:<10} ({note})")
        for name, t in hits[:args.samples]:
            s = t.replace("\r", "").replace("\n", " ")
            m = rx.search(s)
            a, b = max(0, m.start() - 16), min(len(s), m.end() + 16)
            print(f"        {name}: ...{s[a:b]}...")


if __name__ == "__main__":
    main()
