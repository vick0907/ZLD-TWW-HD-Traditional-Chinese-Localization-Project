# 譯名查核與修正：2026-09-07

本次修正納入 `tw-v1.0.11`。相較 `tw-v1.0.10`，九組名稱影響 95 則訊息、113 處用詞，分布於 9 個 MSBT 檔案；不是另一次全文重譯。

## 修正內容

| 原用詞 | 本版用詞 | 訊息數／替換處數 | 依據 |
| --- | --- | --- | --- |
| 魔頭鑰匙 | 大鑰匙 | 1／1 | 《智慧的再現》Big Key 繁中轉錄 |
| 鏈鉤 | 鉤索 | 5／7 | 任天堂台灣系列道具圖卡 |
| 古基利 | 科奇里 | 2／3 | 任天堂台灣「科奇里族」圖卡 |
| 卓拉地區 | 卓拉領地 | 1／1 | 《王國之淚》Zora's Domain 繁中轉錄 |
| 蝶蟲怪 | 加摩斯 | 1／1 | 《智慧的再現》Mothula 繁中轉錄 |
| 飄飄鬼 | 魄 | 2／3 | 《智慧的再現》Poe 繁中轉錄 |
| 詐屍者 | 死亡殭屍 | 1／1 | 《智慧的再現》ReDead 繁中轉錄 |
| 庭格爾 | 汀空 | 60／74 | 《曠野之息／王國之淚》同名裝備及遊戲取得提示 |
| 幸福耳墜 | 幸福墜飾 | 22／22 | Joy Pendant／幸せのペンダント 指墜飾，不是耳飾 |

修訂使用逐句精確替換，保留文字控制碼、數字與其他內容。「繩鉤」是不同於 Hookshot 的另一件道具，沒有改為「鉤索」；「魂豬羅」的頭目名也未隨其下屬改名。

## 來源與界線

- 直接官方文字：[鉤索圖卡](https://www.nintendo.com/tw/character/zelda/img/keywords/pc/22/block_02.jpg)、[科奇里族圖卡](https://www.nintendo.com/tw/character/zelda/img/keywords/pc/07/block_02.jpg)。
- Wiki 對官方繁中遊戲的二手轉錄：[EoW 道具](https://zeldawiki.wiki/wiki/Data:Translations/EoW/Items/A-F)、[EoW 敵人 A-M](https://zeldawiki.wiki/w/index.php?title=Data:Translations/EoW/Enemies/A-M&oldid=1373053)、[EoW 敵人 N-Z](https://zeldawiki.wiki/w/index.php?title=Data:Translations/EoW/Enemies/N-Z&oldid=1273745)、[TotK 地名](https://zeldawiki.wiki/w/index.php?title=Data:Translations/TotK/Locations/T-Z&oldid=1344812)。社群轉錄不是任天堂官網；本次比對了作品、語言欄位與對象身分。
- 汀空：[BotW 裝備名稱轉錄](https://zeldawiki.wiki/w/index.php?title=Data:Translations/BotW/Items/N-Z&oldid=1344589)、[TotK 繁中取得提示](https://annygames.com/wp-content/uploads/2023/06/16-10-1024x576.jpg)。角色與裝備詞幹的日文同為 `チンクル`。
- 「科奇里森林」「汀空瓶／島／雕像」是沿用已確認詞幹的本專案完整譯名，不宣稱每個完整名稱都有官方逐字出處。
- 「幸福墜飾」依[物件與原文資料](https://zeldawiki.wiki/wiki/Joy_Pendant#Nomenclature)修正語意，是本專案譯法，不冒稱已有官方繁中名稱。

## 保留項目

另選查 38 項非歌曲名稱，不包含六首歌曲；這不是全遊戲所有專有名詞的窮盡查核。

- 赤獅子王維持現譯：《王國之淚》[赤獅子王的布料](https://zeldawiki.wiki/w/index.php?title=Data:Translations/TotK/Items/A-M&oldid=1359885)繁中轉錄可支持同一詞幹。
- 風之杖、鳳凰王維持原名。玩家攻略中的「風之指揮棒／吉克洛克」尚未核實為官方繁中名稱。
- 瓦魯已定位到《大亂鬥》第 252 號命魂，但未取得足以確認其繁中名稱的依據。
- 力量／勇氣／智慧寶珠仍保留；其他作品的女神名稱不能直接當成三件物品完整名稱的官譯。
- 未找到可用來源不等於官方從未翻譯，也不表示現譯必然有誤。不同人物、道具或敵人不因英文同名就合併。
- `message#02209` 的觸發情境及部分陶罐用詞仍待後續處理，本版沒有猜測性改寫。

## 建置與驗證

字型先重現並核對已發布的 `tw-v1.0.10` 字型，再追加必要字形；固定先前字集，避免因名稱增刪重排舊索引。對話字重保持 500，標題檔保持不變。

發布前檢查全部 5,040 則訊息、68 個 MSBT 的標籤與回存一致性、控制碼順序、數字、必要字形的實際像素，以及 9 項動作提示回歸測試；另核對新舊封包差異與兩種 ZIP 的內容及雜湊。

本次是文字資料、字型與套件驗證，未部署裝置或重新實機試玩；不代表已完成所有場景的排版檢查或全遊戲通關驗收。