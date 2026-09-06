# 薩爾達傳說 風之律動 HD 繁體中文化 (zh-TW)

Wii U《The Legend of Zelda: The Wind Waker HD》的非官方**繁體中文（台灣用語）**語言包。
以 [原簡體中文專案](https://github.com/wmltogether/ZLD-TWW-HD-Chinese-Localization-Project)
為基礎，包含文字校訂、繁中字型，以及保留原版英文主標的繁中標題美術。

## 下載

**[下載最新版](https://github.com/vick0907/ZLD-TWW-HD-Traditional-Chinese-Localization-Project/releases/latest)**
｜[更新紀錄與舊版](https://github.com/vick0907/ZLD-TWW-HD-Traditional-Chinese-Localization-Project/releases)

| 檔案 | 用途 |
|---|---|
| `TWWHD_zhTW_CemuGraphicPack-*.zip` | Cemu 外掛式安裝，不修改遊戲本體 |
| `ZLD-TWW-HD-zhTW-*.zip` | 覆蓋已解壓的遊戲資料夾 |

## 安裝

**僅適用美版（WUP-P-BCZE，title ID `0005000010143500`），主機語言必須設為 English。**
歐版與日版不適用。以下兩種方式擇一即可。

### Cemu 外掛式安裝

1. 下載 Cemu graphic pack 版，解壓後將 `TWWHD_zhTW` 放進 Cemu 的 `graphicPacks\`。
2. 重開 Cemu，在 `The Legend of Zelda: The Wind Waker HD → Mods → Traditional Chinese` 勾選啟用。

取消勾選即可恢復英文。**不要放進 `downloadedGraphicPacks\`**，以免被 Cemu 更新覆蓋。
使用 `.wud` / `.wux` / `.iso` 時，仍需自行提供合法取得的光碟金鑰。

### 覆蓋遊戲資料夾

1. 關閉遊戲，備份以下兩個原始檔案。
2. 下載鬆散檔案版，將其中的 `content\` 合併到遊戲資料夾，覆蓋同名檔案。

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
- 校對方法與待確認項目見 [審查報告](docs/semantic-review-2026-09-06.md)。

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
