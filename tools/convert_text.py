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
# Names marked "official" are attested in a Nintendo release with an official
# Traditional Chinese localisation - see tools/fetch_glossary.py. Everything
# else keeps the rendering the fan translation has always used.
TERMS = [
    # Nintendo's official Traditional Chinese names
    (re.compile("塞爾達"), "薩爾達"),
    (re.compile("海拉爾"), "海拉魯"),
    (re.compile("加農多夫"), "加儂多夫"),
    (re.compile("加農(?![砲炮])"), "加儂"),
    (re.compile("黃金聖三角"), "三角神力"),
    (re.compile("王者之劍"), "大師之劍"),
    (re.compile("迴旋鏢|迴力鏢"), "飛旋鏢"),
    (re.compile("海拉魯城(?!堡)"), "海拉魯城堡"),
    (re.compile("地之神殿"), "大地神殿"),
    (re.compile("紅色藥水"), "紅藥水"),
    (re.compile("藍色藥水"), "藍藥水"),
    (re.compile("大精靈"), "大妖精"),
    (re.compile("精靈女王"), "妖精女王"),
    (re.compile("精靈島"), "妖精島"),

    # official character, race and enemy names
    (re.compile("蒂拉"), "特托拉"),
    (re.compile("梅麗"), "梅德麗"),
    (re.compile("艾瑞兒"), "阿利爾"),
    (re.compile("比多"), "特里"),
    (re.compile("德古大樹"), "德庫樹"),
    (re.compile("德古"), "德庫"),
    (re.compile("瑞託"), "利特"),
    (re.compile("古洛克"), "克洛格"),
    (re.compile("佐拉"), "卓拉"),
    (re.compile("大豬怪"), "莫力布林"),
    (re.compile("惡鼠怪"), "波克布林"),
    (re.compile("啾啾果凍"), "丘丘膠"),
    (re.compile("啾啾怪"), "丘丘"),
    (re.compile("啾啾"), "丘丘"),
    (re.compile("黑騎士"), "黑甲武士"),
    (re.compile("阿莫斯"), "阿默斯"),
    (re.compile("觸手怪"), "八爪投石怪"),
    (re.compile("豆妖"), "匹哈特"),
    (re.compile("火山巨蟲"), "哥馬"),

    # s2twp swaps in Taiwanese computing jargon, which reads absurdly in a
    # fantasy script - put ordinary wording back.
    (re.compile("任務選單介面"), "任務畫面"),
    (re.compile("介面"), "畫面"),
    (re.compile("型別"), "類型"),
    (re.compile("遠端武器"), "遠距離武器"),
    (re.compile("專案"), "項目"),
    (re.compile("支援"), "支持"),
    (re.compile("訊號燈"), "信號燈"),
    (re.compile("教匯出"), "教導出"),
    (re.compile("物件"), "物品"),
    (re.compile("血液迴圈"), "血液循環"),
    (re.compile("無資訊"), "無資料"),
    (re.compile("傳送資訊"), "傳送訊息"),
    (re.compile("使用者的內心"), "持劍者的內心"),
    (re.compile("檢視四周"), "環顧四周"),

    # "進行 + verb" is Mainland officialese; Taiwanese Mandarin just uses the verb
    (re.compile("進行品籤"), "品鑑"),
    (re.compile("進行埋身戰"), "徒手攻擊"),
    (re.compile(r"進行\s*(安置|對比|設定|解讀|更改|注視|投擲|戰鬥|防禦|調製|交談|破壞|調查|拍照|攻擊|瞬移)"), r"\1"),
    (re.compile("品籤"), "品鑑"),

    # Mainland vocabulary that OpenCC leaves alone
    (re.compile("質量"), "品質"),
    (re.compile("品質過硬"), "品質可靠"),
    (re.compile("服務員"), "服務生"),
    (re.compile("郵遞員"), "郵差"),
    (re.compile("水平"), "水準"),
    (re.compile("撒手"), "放手"),
    (re.compile("頭兒"), "老大"),
    (re.compile("沒門兒"), "不行"),
    (re.compile("一塊兒"), "一起"),
    (re.compile("這塊兒"), "這附近"),
    (re.compile("咱們"), "我們"),
    (re.compile("咱倆"), "我們倆"),
    (re.compile("外婆"), "奶奶"),
    (re.compile("抓緊時間"), "趕快"),
    (re.compile(r"是不\?"), "對吧?"),
    (re.compile("倒黴"), "倒楣"),
    (re.compile("溜達"), "閒晃"),
    (re.compile("愛人"), "心上人"),
    (re.compile("小夥子"), "小伙子"),
    (re.compile("菜地"), "菜園"),
    (re.compile("牛皮哄哄"), "吹牛"),
    (re.compile("爍爍放光"), "閃閃發亮"),
    (re.compile("十年怕井繩"), "十年怕草繩"),
    (re.compile("海拉魯語"), "海利亞語"),
    # a sentence-final 麼 is the Mainland form of the question particle 嗎
    (re.compile(r"(?<![什怎那這多要甚])麼(?=[!?！？。，\n]|$)"), "嗎"),

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
    (re.compile("好象"), "好像"),
    (re.compile("黴氣"), "霧氣"),
    (re.compile("打裡打水"), "打水"),
    (re.compile("口口相傳"), "口耳相傳"),
    (re.compile("掌提"), "掌握"),
    (re.compile("風之仗"), "風之杖"),
    (re.compile("渲洩"), "宣洩"),
    (re.compile("析禱"), "祈禱"),
    (re.compile("學好它把"), "學好它吧"),
    (re.compile("被叫羅斯的女人"), "被一個叫羅斯的女人"),
    (re.compile("粘"), "黏"),
    (re.compile("的的"), "的"),
    (re.compile("，，"), "，"),
    (re.compile("黏乎乎"), "黏呼呼"),
    (re.compile("溼嗒嗒"), "溼答答"),
    (re.compile(r"\.。"), "。"),

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
