# 薩爾達傳說 風之律動 HD 繁體中文化 (zh-TW)

Wii U《The Legend of Zelda: The Wind Waker HD》的非官方**繁體中文（台灣用語）**語言包。
以 [原簡體中文專案](https://github.com/wmltogether/ZLD-TWW-HD-Chinese-Localization-Project)
為基礎，包含文字校訂、繁中字型，以及保留原版英文主標的繁中標題美術。

## 下載

**[下載最新版](https://github.com/vick0907/ZLD-TWW-HD-Traditional-Chinese-Localization-Project/releases/latest)**
｜[更新紀錄與舊版](https://github.com/vick0907/ZLD-TWW-HD-Traditional-Chinese-Localization-Project/releases)

**tw-v1.0.12：全文校對收尾。** 本次預計是最後一輪大規模文字修訂，
後續以影響閱讀或遊玩的必要修正為主，不再為同義措辭頻繁改版。
可從任一舊版直接更新，不需逐版安裝或重新開始遊戲。

| 檔案 | 用途 |
|---|---|
| `TWWHD_zhTW_CemuGraphicPack-*.zip` | Cemu 外掛式安裝，不修改遊戲本體 |
| `ZLD-TWW-HD-zhTW-*.zip` | 覆蓋已解壓的遊戲資料夾 |

## 安裝

**僅適用美版（WUP-P-BCZE，title ID `0005000010143500`），主機語言必須設為 English。**
歐版與日版不適用。以下兩種方式擇一即可。

### Cemu 外掛式安裝（電腦版）

1. 關閉遊戲與 Cemu，下載 `TWWHD_zhTW_CemuGraphicPack-*.zip` 並解壓縮。
2. 將解壓後的整個 `TWWHD_zhTW` 資料夾放進 Cemu 的 `graphicPacks\`，確認檔案層級為 `graphicPacks\TWWHD_zhTW\rules.txt`。
3. 重新開啟 Cemu，**先不要啟動遊戲**。在主畫面的遊戲清單中，對《The Legend of Zelda: The Wind Waker HD》**按滑鼠右鍵**。
4. 點選「編輯圖形包」（`Edit graphic packs`），開啟圖形包設定視窗。
5. 在清單中依序展開 `The Legend of Zelda: The Wind Waker HD`、`Mods`，**勾選 `Traditional Chinese` 前方的方框**。
6. 關閉圖形包視窗，確認主機語言設為 `English`，再從遊戲清單啟動遊戲。

若找不到 `Traditional Chinese`，先確認 ZIP 已解壓、資料夾沒有多包一層，且遊戲為美版。
取消勾選並重新啟動遊戲即可停用外掛。**不要放進 `downloadedGraphicPacks\`**，以免被 Cemu 更新覆蓋。
使用 `.wud` / `.wux` / `.iso` 時，仍需自行提供合法取得的光碟金鑰。

### 覆蓋遊戲資料夾

1. 關閉遊戲，備份以下兩個原始檔案。
2. 下載 `ZLD-TWW-HD-zhTW-*.zip` 並解壓縮。
3. 開啟遊戲資料夾中可看到 `code`、`content`、`meta` 的那一層，將補丁內的 `content` 資料夾合併到這裡，確認取代同名檔案。**不要再放進原有的 `content` 裡，變成 `content\content\`。**

```text
content\Common\Pack\permanent_2d_UsEnglish.pack
content\Common\Layout\Title_00.szs
```

還原備份即可移除補丁。Android 使用已解壓的遊戲資料夾時也可採此方式；
實機 Loadiine 使用此方式。

## 畫面

<img src="docs/screenshot-title.png" width="100%" alt="標題畫面：薩爾達傳說 風之律動 HD">

<details>
<summary>查看對話與選單畫面</summary>

<img src="docs/screenshot-dialogue.png" width="100%" alt="遊戲內對話：注視操作說明">

<img src="docs/screenshot-dialogue-2.png" width="100%" alt="遊戲內對話：搬起與放下水缸">

<img src="docs/screenshot-dialogue-3.png" width="100%" alt="遊戲內對話：時間與歲月">

<img src="docs/screenshot-menu.png" width="100%" alt="道具說明：望遠鏡">

</details>

## 注意事項

- **謎題密碼沿用英文版**，卡關請參考英文攻略。
- 5,040 則文字已與美版英文逐句核對，但仍可能有錯字、誤譯或版面問題，**尚未經完整通關測試**。
- 譯名優先參考任天堂官方繁中用語；未確認者暫沿用既有譯名，仍持續查核。
- 校對方法與待確認項目見 [語意審查](docs/semantic-review-2026-09-06.md)及[譯名查核](docs/terminology-review-2026-09-07.md)。
- 本輪套用範圍與驗證見[文字校訂收尾](docs/text-final-review-2026-09-08.md)。

## 自行建置

<details>
<summary>環境與指令</summary>

需求：Python 3.11+；請先建立 `.venv`，並安裝 `pillow`、`numpy`、
`opencc-python-reimplemented`、`libyaz0`。

自行取得上游 v1.0.2 語言包，解壓至 `work\pack102\`，使
`work\pack102\release\content\` 存在，再展開原版美版英文封包並建置：

```powershell
.\.venv\Scripts\python.exe tools\expand_tree.py "<美版 pack 完整路徑>" work\tree_en out\inventory_en.txt
.\build.ps1
```

兩種安裝包會產生於 `out\`。流程見 [build.ps1](build.ps1)，
工具與文字修正分別位於 [tools/](tools/) 和 [text/](text/)，
[art/texture/](art/texture/) 為標題美術輸入。

</details>

## 出處

- **NGC 原始簡體中文補丁**：鼯鼠工作室 / 漫遊漢化組（2007-2008）
- **WiiU HD 版移植**：[wmltogether](https://github.com/wmltogether) 及數名匿名玩家
- **繁體化與標題重繪**：本分支

原始專案說明保留於 [README.upstream.md](README.upstream.md)。
本專案不提供遊戲本體或金鑰，僅供個人研究與自有遊戲片使用；請勿商用或散布遊戲本體。
