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
    (re.compile("綠色藥水"), "綠藥水"),
    (re.compile("藍色藥水"), "藍藥水"),
    (re.compile("紅果凍"), "紅丘丘膠"),
    (re.compile("綠果凍"), "綠丘丘膠"),
    (re.compile("藍果凍"), "藍丘丘膠"),
    (re.compile("號令之曲"), "號令之歌"),
    (re.compile("降魔之力"), "退魔之力"),
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
    (re.compile("手辦"), "模型"),
    (re.compile("如閒庭信步"), "站得穩穩的"),
    (re.compile("感謝技術的進步"), "多虧製帆師傅的手藝"),
    (re.compile("愛好羽毛的女孩"), "長翅膀的女孩"),
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
    (re.compile("加滿卷"), "加滿券"),
    (re.compile("析求"), "祈求"),
    (re.compile("磨磨蹭躇"), "磨磨蹭蹭"),
    (re.compile("摩獸島"), "魔獸島"),
    (re.compile("封閒"), "封閉"),
    (re.compile("醉得很好"), "做得很好"),
    (re.compile("視南"), "視角"),
    (re.compile("左上南"), "左上角"),
    (re.compile("最多隻能"), "最多只能"),
    (re.compile("十二張張"), "十二張"),
    (re.compile("一顆大樹"), "一棵大樹"),
    (re.compile("那顆德庫樹"), "那棵德庫樹"),
    (re.compile("這隻包"), "這個包"),
    (re.compile("這隻特殊的口袋"), "這個特殊的口袋"),
    (re.compile("這隻嬌豔欲滴的花"), "這朵嬌豔欲滴的花"),
    (re.compile("回覆生命力"), "恢復生命力"),
    (re.compile("回覆魔力"), "恢復魔力"),
    (re.compile("回覆生命值"), "恢復生命值"),
    (re.compile("回覆它的"), "恢復它的"),
    (re.compile("自動為你回覆"), "自動為你恢復"),
    (re.compile("一般沁人心脾"), "一股沁人心脾"),
    (re.compile("透著一般"), "透著一股"),
    (re.compile("散發出一般"), "散發出一股"),
    (re.compile("一般氣團來刮向物體"), "一陣強風吹向物體"),
    (re.compile("日月如梭"), "歲月如梭"),
    (re.compile("地圖示示"), "地圖標示"),
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

    (re.compile("而是隻有"), "而是只有"),
    (re.compile("不是隻會"), "不是只會"),
    (re.compile("但是隻要"), "但是只要"),
    (re.compile("別隻拍我"), "別只拍我"),
    (re.compile("練一隻新歌"), "練一首新歌"),
    (re.compile("聰明瞭"), "聰明了"),
    (re.compile("黃金三南碎片"), "三角神力碎片"),
    (re.compile("密制濃湯"), "特製濃湯"),
    (re.compile("遙個彎"), "溜個彎"),
    (re.compile("斬殺惡摩"), "斬殺惡魔"),
    (re.compile("受益非淺"), "受益匪淺"),
    (re.compile("旋風斬"), "大迴旋斬"),
    (re.compile("想象"), "想像"),
    (re.compile("過的真"), "過得真"),
    (re.compile("讀書使人明知"), "讀書使人明智"),
    (re.compile("磨磨躇躇"), "磨磨蹭蹭"),
    (re.compile("想要只小豬"), "想養隻小豬"),
    (re.compile("寄包裡"), "寄包裹"),
    (re.compile("這個包裡"), "這個包裹"),
    (re.compile("包裡已"), "包裹已"),
    (re.compile("或者包裡"), "或者包裹"),
    (re.compile("成結也達不到"), "成績也達不到"),
    (re.compile("把提機會"), "趁這機會"),
    (re.compile("閒上眼睛"), "閉上眼睛"),
    (re.compile("一副引以為傲"), "一張引以為傲"),
    (re.compile("魚餌袋"), "餌包"),
    (re.compile("餌袋"), "餌包"),
    (re.compile("混身是傷"), "渾身是傷"),
    (re.compile("在在海盜"), "在海盜"),
    (re.compile("從我視前消失"), "從我眼前消失"),
    (re.compile("通關某個考驗"), "通過某個考驗"),
    (re.compile("有機會在回來"), "有機會再回來"),
    (re.compile("小小新意"), "小小心意"),
    (re.compile("登入地點"), "登陸地點"),
    (re.compile("我的第0位好顧客"), "我最要好的顧客"),
    (re.compile("消除此照片"), "刪除此照片"),
    (re.compile("被髮射"), "被發射"),
    (re.compile("瞭如何"), "了如何"),
    (re.compile("把提"), "把握"),
    (re.compile("草團裡"), "草叢裡"),
    (re.compile("一隻新歌"), "一首新歌"),
    (re.compile("古羅克"), "克洛格"),
    (re.compile("回覆魔力"), "恢復魔力"),
    (re.compile("回覆活力"), "恢復活力"),
    (re.compile("能回覆"), "能恢復"),
    (re.compile("回覆所有的枯樹"), "救活所有的枯樹"),
    (re.compile("再下名叫"), "在下名叫"),
    (re.compile("一定會會"), "一定會"),
    (re.compile("要你你在"), "要是你在"),
    (re.compile("家庭雜物"), "家務雜事"),
    (re.compile("那副樹葉大提琴"), "那把樹葉大提琴"),
    (re.compile("他談的樂曲"), "他彈的樂曲"),
    (re.compile("藥水把。"), "藥水吧。"),
    (re.compile("向我資訊"), "向我詢問"),
    (re.compile("壞訊息"), "壞消息"),
    (re.compile("好訊息"), "好消息"),
    (re.compile("湍湍的清泉"), "潺潺的清泉"),
    (re.compile("助理研修"), "侍從研修"),
    (re.compile("瓦魯的一名助理"), "瓦魯的一名侍從"),
    (re.compile("這是似乎"), "這似乎"),
    (re.compile("你們個有沒有"), "你們倆有沒有"),
    (re.compile("北方的 的"), "北方的"),
    (re.compile("太吵吵了"), "太亂了"),
    (re.compile("！!"), "！"),
    (re.compile("。\\."), "。"),
    (re.compile("隨侍"), "侍從"),
    (re.compile("鳥翼族"), "利特族"),
    (re.compile("太醅了"), "太棒了"),
    (re.compile("真得很累"), "真的很累"),
    (re.compile("才能說的說的過去啊"), "這樣才說得過去啊"),
    (re.compile("別在吊兒浪當的了"), "別再吊兒郎當了"),
    (re.compile("待會在說"), "待會再說"),
    (re.compile("進步阿"), "進步啊"),
    (re.compile("我也是在過意不去"), "我也實在過意不去"),
    (re.compile("那些你認識 那些需要工作的人"), "那些你認識、需要工作的人"),
    (re.compile("多高的記錄"), "多高的紀錄"),
    (re.compile("馬力的祖母"), "克馬力的奶奶"),
    (re.compile("他的祖母逝世"), "他的奶奶過世"),
    (re.compile("完全不需要我的知道"), "完全不需要我的指導"),
    (re.compile("P像這樣演奏"), "像這樣演奏"),
    (re.compile("普通的助理"), "普通的侍從"),
    (re.compile("指定席"), "專屬位置"),
    (re.compile("卑鄱"), "卑鄙"),
    (re.compile("冷醅"), "冷酷"),
    (re.compile("麵板"), "面板"),
    (re.compile("給我閒嘴"), "給我閉嘴"),
    (re.compile("為-什-嗎"), "為-什-麼"),
    (re.compile("毛頭未乾"), "乳臭未乾"),
    (re.compile("加儂彈丸"), "加農彈丸"),
    (re.compile("創記錄了"), "創紀錄了"),
    (re.compile("回覆果汁"), "恢復果汁"),
    (re.compile("魚雷"), "烏賊"),
    (re.compile("從 從 一根繩索"), "從一根繩索"),
    (re.compile("遠遠超它"), "遠遠超過它"),
    (re.compile("你可就這樣打破"), "你可以就這樣打破"),
    (re.compile("殘醅"), "殘酷"),
    (re.compile("最醅的"), "最棒的"),
    (re.compile("不敢興趣"), "不感興趣"),
    (re.compile("好成結"), "好成績"),
    (re.compile("零花錢"), "零用錢"),
    (re.compile("小男孩兒"), "小男孩"),
    (re.compile("小孩兒"), "小孩"),
    (re.compile("描迷"), "描述"),
    (re.compile("定睹"), "定睛"),
    (re.compile("烏鴉外套"), "連帽外套"),
    (re.compile("顛波"), "顛簸"),
    (re.compile("？\\?"), "？"),
    (re.compile("成結是"), "成績是"),
    (re.compile("這成結"), "這成績"),
    (re.compile("表琪"), "麥琪"),
    (re.compile("閒著眼睛"), "閉著眼睛"),
    (re.compile("菜鳥兒"), "菜鳥"),
    (re.compile("給給我看"), "給我看"),
    (re.compile("即沒有離得太近"), "既沒有離得太近"),
    (re.compile("嚇成會成"), "會嚇成"),
    (re.compile("你真是個 you\\.好人"), "你真是個好人"),
    (re.compile("不要向撒魚餌"), "不要向它撒魚餌"),
    (re.compile("你現在的記錄是"), "你現在的紀錄是"),
    (re.compile("\\.\\.。"), "..."),
    (re.compile("閒嘴"), "閉嘴"),
    (re.compile("重灌上陣"), "重新開張"),
    (re.compile("花悄"), "花俏"),
    (re.compile("想國離開"), "想過離開"),
    (re.compile("在這的鎮裡"), "這鎮裡"),
    (re.compile("四馬難追"), "駟馬難追"),
    (re.compile("暸望島"), "瞭望島"),
    (re.compile("30個炸彈30盧比"), "30個炸彈60盧比"),
    (re.compile("30支箭30盧比"), "30支箭60盧比"),
    (re.compile("很醅"), "很棒"),
    (re.compile("蘭藥水"), "藍藥水"),
    (re.compile("伽裡克森"), "伽里克森"),
    (re.compile("就時帶著"), "就是帶著"),
    (re.compile("什麼樣的個傻子"), "什麼樣的傻子"),
    (re.compile("你這幅死相"), "你這副表情"),
    (re.compile("輕易與人"), "輕易給人"),
    (re.compile("這也東西不對"), "這東西也不對"),
    (re.compile("很腦殘"), "很愚蠢"),
    (re.compile("孃的！"), "混蛋！"),
    (re.compile("室息"), "窒息"),
    (re.compile("真醅"), "真棒"),
    (re.compile("醅必了"), "酷斃了"),
    (re.compile("醅啊"), "酷啊"),
    (re.compile("任飯"), "任天堂迷"),
    (re.compile("沒沒那麼多"), "沒那麼多"),
    (re.compile("帶去去樓上"), "帶你去樓上"),
    (re.compile("悄皮"), "俏皮"),
    (re.compile("參見拍賣會"), "參加拍賣會"),
    (re.compile("煙黴"), "煙霧"),
    (re.compile("攝影師家"), "攝影師"),
    (re.compile("但確實個"), "但確實是個"),
    (re.compile("夢想去儘快長大"), "夢想是儘快長大"),
    (re.compile("英俊瀟灑他深受"), "英俊瀟灑，深受"),
    (re.compile("我們的真是目的"), "我們真正的目的"),
    (re.compile("小道訊息"), "小道消息"),
    (re.compile("沉默在海底"), "沉沒在海底"),
    (re.compile("考研偉大"), "考驗偉大"),
    (re.compile("庫伯裡"), "庫伯里"),
    (re.compile("行走商人"), "旅行商人"),
    (re.compile("瓦魯的服務生"), "瓦魯的侍從"),
    (re.compile("他的服務生，梅德麗"), "他的侍從，梅德麗"),
    (re.compile("回覆劑"), "恢復劑"),
    (re.compile("大的好一夜暴富"), "大的，好一夜致富"),
    (re.compile("大地之魂"), "大地精靈"),

    # Taiwanese register: wording that is correct in meaning but reads mainland
    (re.compile("您走好！今後常來啊！"), "慢走！歡迎再來喔！"),
    (re.compile("走好！常來啊！"), "慢走！再來喔！"),
    (re.compile("走好！有空常來！"), "慢走！有空再來！"),
    (re.compile("哥們"), "老兄"),
    (re.compile("鑑賞家同志"), "鑑賞家同好"),
    (re.compile("放鬆警惕"), "放鬆戒心"),
    (re.compile("還是怎麼著"), "還是怎樣"),
    (re.compile("好女孩兒"), "好女孩"),
    (re.compile("小寶貝兒"), "小寶貝"),
    (re.compile("幹嗎"), "幹嘛"),
    (re.compile("其它"), "其他"),
    (re.compile("它人"), "他人"),


    # s2twp turns every 通过 into 透過; passing a test or a gap needs 通過
    (re.compile("你可以透過呢"), "你可以通過呢"),
    (re.compile("都要透過的考驗"), "都要通過的考驗"),
    (re.compile("要透過的試煉"), "要通過的試煉"),
    (re.compile("你透過了"), "你通過了"),
    (re.compile("沒有透過這個測試"), "沒有通過這個測試"),
    (re.compile("透過了第一場測試"), "通過了第一場測試"),
    (re.compile("透過了我的第二場測試"), "通過了我的第二場測試"),

    # message = 訊息, news = 消息, information = 資訊
    (re.compile("回來的訊息"), "回來的消息"),
    (re.compile("任何的訊息"), "任何的消息"),
    (re.compile("編寫後的資訊"), "編寫後的訊息"),
    (re.compile("收到你的資訊"), "收到你的訊息"),
    (re.compile("把資訊送進漂流瓶"), "把訊息送進漂流瓶"),
    (re.compile("閱讀他人的資訊"), "閱讀他人的訊息"),
    # OpenCC picked the wrong Traditional form for these
    (re.compile("丘位元"), "邱比特"),
    (re.compile("東西后"), "東西後"),
    (re.compile("制作"), "製作"),
    (re.compile("併為此"), "並為此"),
    (re.compile("洋麵向上伸展"), "海平面向上伸展"),
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
