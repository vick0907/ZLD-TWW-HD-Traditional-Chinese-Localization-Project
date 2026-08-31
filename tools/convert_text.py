"""Convert every MSBT in the tree from Simplified to Traditional Chinese (zh-TW).

Control codes are never touched: the MSBT reader hands back typed segments and
only ("t", ...) segments are passed through OpenCC.
"""
import json
import os
import re
import sys

import opencc

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import msbt  # noqa: E402

# Applied to the already-converted text. OpenCC gets the general vocabulary
# right but not Nintendo's official Traditional Chinese proper nouns, and it
# leaves Mainland-only wording alone because those words exist in both scripts.
TERMS = [
    # Nintendo's official Traditional Chinese names
    (re.compile("塞爾達"), "薩爾達"),
    (re.compile("海拉爾"), "海拉魯"),
    (re.compile("加農多夫"), "加儂多夫"),
    (re.compile("加農(?![砲炮])"), "加儂"),
    (re.compile("黃金聖三角"), "三角神力"),
    (re.compile("王者之劍"), "大師之劍"),
    (re.compile("迴旋鏢"), "迴力鏢"),

    # Mainland vocabulary that OpenCC leaves alone
    (re.compile("質量"), "品質"),
    (re.compile("服務員"), "服務生"),
    (re.compile("水平"), "水準"),
    (re.compile("撒手"), "放手"),
    (re.compile("頭兒"), "老大"),
    (re.compile("沒門兒"), "不行"),
    (re.compile("一塊兒"), "一起"),
    (re.compile("這塊兒"), "這附近"),

    # erhua - Taiwanese Mandarin drops it
    (re.compile("這兒"), "這裡"),
    (re.compile("那兒"), "那裡"),
    (re.compile("哪兒"), "哪裡"),
    (re.compile("玩意兒"), "玩意"),
    (re.compile("點兒"), "點"),
    (re.compile("事兒"), "事"),
    (re.compile("玩兒"), "玩"),
    (re.compile("活兒"), "活"),
    (re.compile("法兒"), "法"),
    (re.compile("彎兒"), "彎"),
    (re.compile("勁兒"), "勁"),
    (re.compile("信兒"), "信"),
    (re.compile("邊兒"), "邊"),
    (re.compile("樣兒"), "樣"),
    (re.compile("氣兒"), "氣"),
    (re.compile("招兒"), "招"),
    (re.compile("份兒"), "份"),

    # OCR slips in the original translation - it was OCR'd off the GameCube patch
    (re.compile("眼睹"), "眼睛"),
    (re.compile("眼哞"), "眼眸"),
    (re.compile("磨躇"), "磨蹭"),
    (re.compile("咋碎"), "砸碎"),
    (re.compile("初學乍到"), "初來乍到"),

    # OpenCC picked the wrong Traditional form for these
    (re.compile("丘位元"), "邱比特"),
    (re.compile("東西后"), "東西後"),
    (re.compile("制作"), "製作"),
    (re.compile("併為此"), "並為此"),
]


def convert_text(conv, text):
    out = conv.convert(text)
    for pattern, repl in TERMS:
        out = pattern.sub(repl, out)
    return out


def main():
    root, dest, report_path = sys.argv[1], sys.argv[2], sys.argv[3]
    config = sys.argv[4] if len(sys.argv) > 4 else "s2twp"
    conv = opencc.OpenCC(config)

    changed_files = 0
    total_msgs = 0
    changed_msgs = 0
    before_chars = set()
    after_chars = set()
    samples = []

    for dirpath, _, files in os.walk(root):
        for name in sorted(files):
            if not name.endswith(".msbt"):
                continue
            path = os.path.join(dirpath, name)
            data = open(path, "rb").read()
            messages, _ = msbt.read(data)
            new_messages = []
            file_changed = False
            for segs in messages:
                total_msgs += 1
                new_segs = []
                msg_changed = False
                for kind, val in segs:
                    if kind == "t":
                        before_chars.update(val)
                        conv_val = convert_text(conv, val)
                        after_chars.update(conv_val)
                        if conv_val != val:
                            msg_changed = True
                            if len(samples) < 40 and len(val) > 8:
                                samples.append((val, conv_val))
                        new_segs.append(("t", conv_val))
                    else:
                        new_segs.append((kind, val))
                if msg_changed:
                    changed_msgs += 1
                    file_changed = True
                new_messages.append(new_segs)

            rel = os.path.relpath(path, root)
            outpath = os.path.join(dest, rel)
            os.makedirs(os.path.dirname(outpath), exist_ok=True)
            with open(outpath, "wb") as f:
                f.write(msbt.write(data, new_messages))
            if file_changed:
                changed_files += 1

    cjk_before = {c for c in before_chars if "\u4e00" <= c <= "\u9fff"}
    cjk_after = {c for c in after_chars if "\u4e00" <= c <= "\u9fff"}
    report = {
        "opencc_config": config,
        "files_changed": changed_files,
        "messages": total_msgs,
        "messages_changed": changed_msgs,
        "unique_chars_before": len(before_chars),
        "unique_chars_after": len(after_chars),
        "cjk_before": len(cjk_before),
        "cjk_after": len(cjk_after),
        "cjk_new": len(cjk_after - cjk_before),
        "cjk_dropped": len(cjk_before - cjk_after),
        "chars_after": "".join(sorted(after_chars)),
        "samples": [{"before": a, "after": b} for a, b in samples[:20]],
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    for k, v in report.items():
        if k not in ("chars_after", "samples"):
            print(f"{k}: {v}")


if __name__ == "__main__":
    main()
