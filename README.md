# 薩爾達傳說 風之律動 HD — 繁體中文化 (zh-TW)

> Fork 自 [wmltogether/ZLD-TWW-HD-Chinese-Localization-Project](https://github.com/wmltogether/ZLD-TWW-HD-Chinese-Localization-Project)
> 原專案是 WiiU《The Legend of Zelda: The Wind Waker HD》的非官方**簡體**中文語言包。
> 本分支把它轉成**繁體中文（台灣用語）**，並重繪標題畫面。
> 原始說明保留於 [README.upstream.md](README.upstream.md)。

原專案的工具是 Python 2 寫的，本分支保留原檔（`fontBuilder.py`、`repack_text.py`、
`unpack_text.py`、`Cafe/`、`NGC/`、`Patch/`）作為出處，另外在 `tools/` 提供一套
可重現的 Python 3 建置流程。

---

## 畫面

<img src="docs/screenshot-title.png" width="100%" alt="標題畫面：薩爾達傳說 風之律動 HD">

<img src="docs/screenshot-dialogue.png" width="100%" alt="遊戲內對話">

對話字型 `CKingMsg`，5,371 字，缺字 0。

<img src="docs/screenshot-menu.png" width="100%" alt="道具選單">

選單字型 `CKingMain`，731 字。

---

## 成果

| 項目 | 內容 |
|---|---|
| 文字 | 5,040 句全數轉繁，4,275 句有變動 |
| 字型 | `CKingMsg` 4,390 → 5,371 字；`CKingMain`/`MainL` 569 → 731 字 |
| 標題畫面 | 「薩爾達傳說 風之律動」重繪，並修復原簡中版被抹平的光掃遮罩 |
| 譯名 | 採任天堂官方繁中譯名：薩爾達、海拉魯、加儂多夫、三角神力、大師之劍、迴力鏢 |
| 缺字 | 0 |

---

## 做法

### 1. 容器層

語言包 `permanent_2d_UsEnglish.pack` 是 SARC（外層對齊 0x2000），內含
`*_msbt.szs` / `*_bffnt.szs` 等 Yaz0 + SARC 巢狀封存，共 2,085 個葉節點檔案。

`tools/sarc.py` 讀寫 SARC 與 Yaz0。重打包後的位元組與原檔完全相同
（`tools/check_repack.py` 驗證）。

### 2. 文字層

MSBT 的 `TXT2` 區塊是 UTF-16BE，中間夾雜控制碼（`0x000E` 帶長度欄位、`0xE0xx` 兩位元組）。

`tools/msbt.py` 把訊息拆成 typed segment：

```python
("t", "純文字")          # 只有這種會送進 OpenCC
("c", b"\x00\x0e...")   # 控制碼原封不動複製
```

**控制碼絕對不會被轉換工具碰到**，這是不讓遊戲當掉的關鍵。

轉換用 OpenCC `s2twp`，再套用 `tools/convert_text.py` 的 `TERMS` 詞表補正。

> ⚠️ **取代字串一律等長或更短。** MSBT 內含手動換行符，字串變長會爆版。

### 3. 字型層

BFFNT 的字圖頁是 **BC4 壓縮 + Wii U GX2 2D tiling（tileMode 4）**。

`tools/gx2_addr.py` 是 AMD R600 家族 address library 的重實作（2 pipes / 4 banks /
256-byte interleave）。實測踩到的坑：**bpp=64（BC4）的 micro-tile bit order 必須是
`x0,y0,x1,x2,y1,y2`** —— 這是拿遊戲自己的字圖反覆比對出來的。

`tools/build_font.py` 只把新字寫進字圖頁末端的**空白格位**：

- 既有字元的字圖索引、字寬（CWDH）完全不動
- 沒用到的字圖頁維持位元組相同
- CMAP 改用 scan 型對照表容納新增碼位

`tools/verify_font.py` 會確認「既有字元索引改變數 = 0」。

**字圖必須反鋸齒。** 遊戲原本的字圖是 `0 →(漸變)→ 128 →(漸變)→ 255` 的連續灰階，
把算繪結果二值化再加一圈平坦灰邊，放大看就是明顯的毛邊：

```
原版「一」： 0  0  99 126 128 147 227 255 ... 255 149 127 127  21  0
二值化版本： 0  0   0   0   0 145 145 255 ... 128 128 128 128   0  0
```

所以 `tools/glyph_render.py` 全程以浮點覆蓋率運算，而且**在超取樣解析度下做描邊膨脹**
再一起降取樣，最後 `128 * halo + 127 * core`，自然得到三個平台與其間的漸變。

`tools/glyph_quality.py` 可以量測：修正前新增字只有 4 個灰階，修正後 80–149，
與原版的 33–165 同級。

### 4. 貼圖層

`tools/dump_bflim.py` / `tools/pack_bflim.py` 解碼與編碼 BFLIM（RGBA8 與 BC4）。

BFLIM 的中繼資料在**檔尾 0x28 bytes**：

```
0x1C  width  (u16)
0x1E  height (u16)
0x22  format (u8)      0x14 = RGBA8(sRGB), 0x10 = BC4
0x23  tile   (u8)      tileMode = v & 0x1F,  swizzle = (v >> 5) & 7
```

pitch = `align(width, 32)`、rows = `align(height, 16)`（bpp32 / tileMode 4）。

`tools/dump_bflyt.py` 可讀版面的 pane 尺寸。實測 **quad 尺寸 = 貼圖尺寸（1:1 不縮放）**，
所以圖在貼圖裡的位置就等於螢幕上的位置：

```
pic1  P_TitleLogoZelda_00   500 x 210
pic1  P_Windwaker_00        340 x  60   ← 美版顯示這張
pic1  P_WindwakerJ_00       326 x 120   ← 日版分支
```

---

## 建置

需求：Python 3.11+、`pillow` `numpy` `opencc-python-reimplemented` `libyaz0`

```powershell
# 前提：把上游 v1.0.2 語言包解壓到 work\pack102\，
#       使 work\pack102\release\content\ 存在
.\build.ps1
```

九個步驟：解包 → 轉繁 → 算選單缺字 → 補字型 → 套用標題美術 → 重打包 →
驗證 → 打包 zip → 產生 Cemu graphic pack。

產物：

```
out\ZLD-TWW-HD-zhTW-*.zip            鬆散檔案版
out\TWWHD_zhTW_CemuGraphicPack.zip   Cemu graphic pack 版
```

`art/` 是**建置的輸入**（手繪標題美術），不是產出。

---

## 安裝

部署方式有兩種，擇一即可。

### 方式一　外掛式：不動到遊戲本體（限 Cemu）

中文以 graphic pack 的形式疊在遊戲上，**原始遊戲檔案不會被修改**，
取消勾選就切回英文。

把 `TWWHD_zhTW` 放進 `graphicPacks\`（**不要**放 `downloadedGraphicPacks\`，
那個資料夾會被 Cemu 更新覆蓋），重開 Cemu 後在
`The Legend of Zelda: The Wind Waker HD → Mods → Traditional Chinese` 打勾。

這個方式可以直接疊在 `.wud` / `.wux` 上，但那些格式**需要光碟金鑰**才讀得到。

### 方式二　整合式：直接覆蓋遊戲檔案

把 `content\` 覆蓋到遊戲資料的相同路徑，做出一份「本來就是中文」的
遊戲資料，之後不需要任何外掛。實機（Loadiine）只能用這種方式。

```
content\Common\Pack\permanent_2d_UsEnglish.pack
content\Common\Layout\Title_00.szs
```

會改寫遊戲檔案，請先備份上面這兩個檔。

Android 掌機屬於這一種：整個遊戲資料夾複製過去即可，補丁已經在檔案裡。
`tools/compare_device.py` 可以比對 PC 與裝置，只推送有變動的檔案。

---

## ⚠️ 注意事項

### 版本限制

- **只適用美版（WUP-P-BCZE，title ID `0005000010143500`）**
- 歐版是 `permanent_2d_EuEnglish.pack`、日版是 `permanent_2d_JpJapanese.pack`，檔名對不上
- **主機語言必須設為 English**，否則遊戲會去讀 `UsFrench` / `UsSpanish` 語言包

### 檔案格式與金鑰

Cemu 的格式支援（見其原始碼 `TitleInfo.h`）：

| 格式 | 需要金鑰 |
|---|---|
| `code`/`content`/`meta` 資料夾 | ❌ |
| `.wua` | ❌ |
| `.wud` / `.wux` / `.iso` | ✅ 光碟金鑰 |
| NUS `.app` | ✅ `title.tik` |

金鑰不足時 Cemu 會**靜默略過**該遊戲，遊戲清單空白且不跳錯誤。

### 譯文品質

上游作者說明文本是**用 OCR 從 GameCube 版漢化掃出來的**，因此原文就有辨識錯字。
本分支已修正找到的部分：

| 錯 | 對 |
|---|---|
| 眼**睹** | 眼**睛**（6 處以上） |
| 眼**哞** | 眼**眸** |
| 磨**躇** | 磨**蹭** |
| **咋**碎 | **砸**碎 |
| 初**學**乍到 | 初**來**乍到 |

`tools/rare_chars.py` 會列出只出現一兩次的罕用字，可以用來繼續獵捕同類錯誤。

另外修正了 OpenCC 轉錯的地方，例如 **愛神丘比特 → 丘位元**（詞表把「比特」
當成電腦術語 bit，台灣譯「位元」）。

### 已知問題

- 上游作者註明：**謎題密碼沿用英文版**，卡關請查英文攻略
- 譯文未逐句校潤，可能仍有殘留錯字
- 標題美術以字型算繪，筆形與原版手繪字不完全相同
- 未經完整通關測試

---

## 工具

| 檔案 | 用途 |
|---|---|
| `sarc.py` | SARC / Yaz0 讀寫 |
| `msbt.py` | MSBT 讀寫（控制碼隔離） |
| `bffnt.py` `gx2_addr.py` `bc4.py` `atlas.py` | 字型與 Wii U 貼圖 tiling |
| `glyph_render.py` `build_font.py` | 算繪並附加新字圖 |
| `convert_text.py` | 簡→繁 + 詞表 |
| `dump_bflim.py` `pack_bflim.py` | BFLIM 解碼 / 編碼 |
| `dump_bflyt.py` | 版面 pane 尺寸 |
| `fit_logo.py` `retitle.py` `retitle_word.py` | 標題美術處理 |
| `repack.py` `install.py` | 重打包與安裝 |
| `verify_release.py` `verify_font.py` `validate_msbt.py` `check_repack.py` | 驗證 |
| `glyph_quality.py` | 量測字圖灰階層數，抓出沒反鋸齒的字 |
| `audit_terms.py` `find_text.py` `rare_chars.py` | 用語稽核 |
| `diff_sarc.py` `compare_device.py` | 比對封存 / 裝置 |
| `audit_tools.py` | 列出哪些腳本是 `build.ps1` 真正會用到的 |
| `scan_privacy.py` `png_metadata.py` `strip_png_metadata.py` | 發布前檢查個資與圖片中繼資料 |

`validate_msbt.py` 特別針對上游 v1.0.0 出現過的 **"TXT2 chunk size error"**
（v1.0.1 才修掉）做結構驗證：檔頭尺寸、區段銜接、TXT2 偏移表越界、字串終止。

---

## 出處

- **NGC 原始簡體中文補丁**：鼯鼠工作室 / 漫遊漢化組（2007–2008）
- **WiiU HD 版移植**：[wmltogether](https://github.com/wmltogether) 及數名匿名玩家
- **繁體化與標題重繪**：本分支

本專案僅供個人研究與自有遊戲片使用，請勿用於任何商業用途，亦請勿散布遊戲本體檔案。
本倉庫**不包含**任何遊戲資料，建置所需的上游語言包請自行取得。
