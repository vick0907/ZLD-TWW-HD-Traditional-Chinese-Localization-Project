"""Scan the converted text for mainland-register wording that reads wrong in Taiwan.

Semantic review compares against English; this pass is orthogonal - it looks for
phrases that are correct in meaning but wrong in register.
"""
import re
import sys

# (pattern, why) - deliberately broad; every hit gets judged by hand.
PATTERNS = [
    # farewells / politeness
    ("走好", "台灣是對往生者說的；應為 慢走"),
    ("您呐|您哪", "京腔"),
    ("回頭見", "陸腔，台灣說 待會見/再見"),
    # kinship / address
    ("姥姥|姥爺", "台灣說 外婆/外公"),
    ("大爺|大媽", "台灣說 阿伯/阿姨"),
    ("哥們|爺們|老鐵|老鄉", "陸語"),
    ("師傅(?!們)", "大陸對司機／工人的稱呼"),
    ("同志", "陸語"),
    ("丫頭", "陸語"),
    # northern colloquialisms
    ("咋", "陸語，台灣說 怎麼"),
    ("甭|俺|忒", "陸語"),
    ("賊(?!人|寇|窩|船)", "東北話的「很」"),
    ("嘚瑟|顯擺|拾掇|磨嘰|墨跡|尋思|合計|嘮嗑", "陸語"),
    ("忽悠|靠譜|給力|牛逼|牛掰", "陸語"),
    ("沒轍|拉倒|得嘞|敢情", "陸語"),
    ("不好使", "東北話"),
    ("擱這|擱那|擱著", "陸語"),
    ("整個(?!人|世界|鎮|島|大陸|過程|房間)", "東北話的「弄」"),
    ("挺.{1,3}的呢", "語感偏陸"),
    ("小伙子", "台灣多寫 小伙子/年輕人，可接受"),
    ("媳婦", "陸語，台灣說 老婆/太太"),
    ("對象(?!是)", "大陸指交往對象"),
    ("愛人", "大陸指配偶"),
    # register words
    ("質量|水平(?!線)|服務員|郵遞員|自行車|土豆|公交", "陸語詞彙"),
    ("信息", "台灣說 訊息/資訊"),
    ("概率|幾率", "台灣說 機率"),
    ("渠道", "台灣說 管道"),
    ("激光", "台灣說 雷射"),
    ("視頻|音頻", "台灣說 影片/音訊"),
    ("屏幕", "台灣說 螢幕"),
    ("軟件|硬件|網絡", "陸語"),
    ("單位(?!是|時間|面積)", "大陸指工作單位"),
    ("警惕", "台灣多說 警覺/提防"),
    ("鬧騰|折騰(?!人)", "偏陸"),
    ("憋屈|窩囊", "偏陸"),
    ("噁心", "台灣寫 噁心（正確）"),
    ("倒騰", "陸語"),
    ("差不離", "陸語"),
    ("怎麼著", "台灣說 怎樣"),
    ("有戲|沒戲", "陸語"),
    ("到位", "陸語"),
    ("上檔次|夠嗆", "陸語"),
    ("貓膩", "陸語"),
    ("下崗|打的", "陸語"),
    ("這會兒|那會兒", "兒化殘留"),
    ("兒(?=[，。！？、\\s])", "兒化殘留"),
    # OpenCC s2twp over-conversions
    ("透過(?!窗|玻璃|縫|水|樹|雲)", "s2twp 把 通过 一律轉成 透過；考試/門檻要用 通過"),
    ("資訊|訊息", "確認該處是 information 還是 news；後者台灣說 消息"),
    ("影片|檔案|網路", "s2twp 資訊術語，奇幻對白裡要檢查"),
    # Taiwanese orthography
    ("幹嗎", "台灣寫 幹嘛"),
    ("其它", "台灣多寫 其他"),
    ("窩心", "陸台意思相反，台灣是「溫暖」"),
    ("摳門|找茬|較真|合算(?!的)|立馬", "陸語"),
    ("特別棒|賊好|老好", "陸語程度副詞"),
    ("嘮|唄|咧咧", "陸語語尾"),
    # s2twp also swaps in Taiwanese *computing* jargon, which is absurd in a
    # fantasy script. Each of these is a word s2twp produces from a perfectly
    # ordinary Simplified word.
    ("分割槽", "分区 -> 分割槽（磁碟分割）；應為 區域/分區"),
    ("區域性", "局部 -> 區域性"),
    ("最佳化", "优化 -> 最佳化"),
    ("解除安裝", "卸载 -> 解除安裝"),
    ("重灌", "重装 -> 重灌"),
    ("全域性", "全局 -> 全域性"),
    ("佇列", "队列 -> 佇列"),
    ("影格", "帧 -> 影格"),
    ("相容", "兼容 -> 相容"),
    ("整合", "集成 -> 整合"),
    ("啟用", "激活 -> 啟用"),
    ("列印", "打印 -> 列印"),
    ("預設", "缺省/默认 -> 預設"),
    ("游標", "光标 -> 游標"),
    ("螢幕", "屏幕 -> 螢幕"),
    ("位元|位址|快取|陣列|變數|函式|指標|點陣", "程式術語"),
    ("解析度|畫素", "分辨率/像素"),
    ("伺服器|網域|連線埠|閘道", "網路術語"),
    ("記憶體|硬碟|軟體|韌體", "硬體術語"),
    ("復原(?!了)|還原", "撤销/恢复 -> 復原/還原"),
    ("元件|外掛|巨集", "组件/插件/宏"),
]

c = lambda s: re.sub(r"\s+", " ", re.sub(r"\{[^}]*\}", " ", s.replace("\\n", " "))).strip()

rows = []
for line in open(sys.argv[1] if len(sys.argv) > 1 else "out/bilingual.tsv", encoding="utf-8"):
    p = line.rstrip("\n").split("\t")
    if len(p) == 4 and p[0] != "key":
        rows.append(p)

total = 0
out = open(sys.argv[2] if len(sys.argv) > 2 else "out/register_audit.txt", "w", encoding="utf-8")
for pat, why in PATTERNS:
    rx = re.compile(pat)
    hits = [(p[0], c(p[2]), c(p[3])) for p in rows if rx.search(c(p[3]))]
    if not hits:
        continue
    total += len(hits)
    print("### %s  (%d)  -- %s" % (pat, len(hits), why), file=out)
    for key, en, zh in hits:
        print("   %-18s ZH: %s" % (key, zh[:100]), file=out)
        print("   %-18s EN: %s" % ("", en[:100]), file=out)
    print(file=out)
print("total hits:", total, file=out)
out.close()
print("total hits:", total)
