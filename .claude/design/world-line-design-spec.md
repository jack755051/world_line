# World Line 設計規格（進 Stitch 之前）

> 版本：v0.2・2026-10-28（台北時間）・Tai 已拍板，決策見 §9 決策紀錄
> 範圍：只定義**地圖專用**的視覺規格；一般 UI 全部沿用 Sanring UI。
> 狀態：唯讀研究產出，**沒有改動任何 repo**。

**讀過的來源**

| 來源 | 版本 |
|---|---|
| `jack755051/world_line`：`.claude/constitutions/world-line.md`（status: active）、`.claude/prds/world-line.md`、`.claude/notes/world-line-tech-candidates.md`、`app/`（Angular 22 scaffold） | `main` @ `20ffd41`（2026-08-25 22:27 台北時間） |
| `sanringtech/ui`：`registry/shared/theme.css`、`registry/shared/theme-presets/{warm,slate,high-contrast}.css`、`registry/shared/component-styles.ts` | `main` @ `361b866`（2026-10-19 11:11 台北時間） |

`app/` 目前只有 CLI 預設 scaffold，沒有地圖或時間軸程式碼，也還沒裝 MapLibre 和 Tailwind，所以本規格以 PRD 和 notes 的描述為準。

---

## 0. 用語確認

Manager 原文寫的「爨議區」「疏域」是錯字。PRD 和 notes 的寫法是：

- **爭議區**：PRD §5「爭議控制區（notes §十）」、§9「斜線網底（爭議控制區）」；notes §十.3「爭議控制區用斜線網底／斑馬紋」。資料面是 `regime_territories.is_disputed`（憲法 I3「爭議並存」）。
- **疆域**：憲法 R2、PRD 全文都用「疆域」（`regime_territories`）。

政權狀態用憲法 §4 的四個詞：**存續／分裂／被取代（禪讓）／被滅亡**。

---

## 1. 主題預設建議：**Slate**（預設深色，另支援淺色）

Sanring 的四種主題比較（數值都來自 repo 原始檔）：

| Preset | 主色 50 | 圓角 xs/sm/base/lg | 其他變動 | 適不適合地圖 |
|---|---|---|---|---|
| Base（預設） | 青綠 `#8bd3dd` | 3/6/8/12 | — | 青綠容易和疆域色盤的青綠色相混淆，使用者可能把介面強調色誤認成某個政權 |
| **Slate** ✅ | 灰藍 `#64748b` | 3/6/8/12（沿用 base） | 只換 primary 色階 | **最適合**，原因見下方 |
| Warm | 琥珀 `#f59e0b` | 4/8/10/16 | 圓角放大 | 琥珀和橘黃系政權撞色；圓角也跟 Tai 指定的 3/6/8/12 不同 |
| High-contrast | 藍 `#3b82f6` | 2/2/4/4 | 背景改成純黑或純白 | 長時間看會刺眼，地圖半透明色塊在純黑上會顯得很髒；適合當無障礙切換選項，不建議當預設 |

**選 Slate 的理由**

1. **讓地圖上的顏色只代表政權**：Slate 的主色是低彩度灰藍，介面框架幾乎不帶色相。地圖上同時有十幾個政權的顏色，介面用色越中性，使用者越不容易誤讀。
2. **長時間閱讀**：Slate 沿用 base 的語意層，深色背景是 `--sanring-neutral-90 #202424`，不是純黑，前景是 `#edf1f2`，不是純白，對比 13.8:1，夠清楚又不刺眼。notes §八的毛玻璃抽屜原本就是深色設計，所以**預設用深色**。
3. **圓角維持 3/6/8/12**，和 Tai 指定的一致；Warm 和 High-contrast 都會改圓角。
4. **深淺色都支援**：Sanring 用 `:root` 當深色、`[data-theme='light']` 當淺色，地圖常數也照這兩種模式各做一份。
5. **High-contrast 當無障礙選項**：地圖色盤不需要另外做一份，只要把 `fillOpacity` 提高到 0.45、邊界加粗到 2px。**已決定：Phase 1 不做 High-contrast 地圖**，保留為之後的無障礙選項（見 §9 D7）。

**套用方式**：`sanring init --theme slate`，或在全域樣式中先引入 `theme.css`，再引入 `theme-presets/slate.css`。

### 1.1 必要的 3 項覆寫（Slate 本身沒通過 AA 的地方）

我用腳本實測，Slate 直接套用時有三組對比不夠：

| 問題 | 原值 | 實測對比 | 修正 | 修正後 |
|---|---|---|---|---|
| 主色按鈕的文字：`--sanring-primary-fg`（`neutral-90`）放在 Slate `primary-50 #64748b` 上 | `#202424` / `#64748b` | **3.30:1 ❌** | `--sanring-primary-fg: #ffffff` | 4.76:1 ✅ |
| 淺色模式的 `--sanring-border-strong`（Sanring 也拿它當 **focus ring** 顏色，見 `component-styles.ts`） | `#aebdc0` / `#f6f8f8` | **1.82:1 ❌** | 淺色模式改用 `#818e91`（= `neutral-60`） | 3.17:1 ✅ |
| `--sanring-active` 選取底色：深色模式是 Slate `primary-80 #1e293b`，淺色模式寫死成 `#d8eef1`（青綠，不會跟著 Slate 改） | 對背景 1.07 / 1.13 | ⚠️ | 不改 token；在 World Line 裡，選取狀態一律**另外加 2px 指示條**（`--sanring-control`），不能只靠底色區分 | 指示條 12.9 / 13.0 ✅ |

```css
/* app 全域樣式，接在 theme.css + slate.css 之後 */
:root { --sanring-primary-fg: #ffffff; }
:root[data-theme='light'] { --sanring-border-strong: #818e91; }
```

前兩項建議直接回報給 Sanring UI 上游修正；`#d8eef1` 寫死不跟主題變動，也算上游的不一致。

### 1.2 字型

`--sanring-font-sans` 是 `Ubuntu, ui-sans-serif, system-ui, …`，**Ubuntu 沒有中文字形**，中文會落到各系統的預設字型，Mac、Windows、Linux 顯示起來不一樣。建議在 app 層補上中文字型：

```css
:root { --sanring-font-sans: Ubuntu, "Noto Sans TC", "PingFang TC", "Microsoft JhengHei", ui-sans-serif, system-ui, sans-serif; }
```

MapLibre 的標籤字型和 CSS 分開處理：拉丁字用 Ubuntu 的 glyph PBF，中日韓字用 `localIdeographFontFamily` 交給瀏覽器的本機字型，就不用下載龐大的中文 glyph。

---

## 2. 沿用的 Sanring token（不新增）

| 用途 | Token |
|---|---|
| 頁面、面板、浮層 | `--sanring-background` / `--sanring-surface` / `--sanring-surface-strong` / `--sanring-elevated` |
| 文字 | `--sanring-foreground`、`--sanring-muted` |
| 邊框、焦點框 | `--sanring-border`、`--sanring-border-strong`（淺色模式依 §1.1 覆寫） |
| 時間軸播放頭、主要按鈕 | `--sanring-control` / `--sanring-control-foreground` |
| 圓角 | `--sanring-radius-xs 3px`（朝代帶、小徽章）、`--sanring-radius-sm 6px`（年份膠囊、圖示按鈕）、`--sanring-radius 8px`（地圖控制項、popover）、`--sanring-radius-lg 12px`（抽屜、時間軸面板） |
| 字級 | 沿用 Sanring 使用的 Tailwind 級距：`text-xs 12`、`text-sm 14`（預設）、`text-base 16`、`text-lg 18`（抽屜標題） |
| 間距 | Tailwind 4px 級距 |
| 狀態色 | `info` / `success` / `warn` / `error` / `sun` 色階（地圖 token 有直接引用其中幾階，見下方） |

---

## 3. 地圖專用 token

命名規則是 `map-<區塊>-<用途>`。程式碼裡集中放在**一個共用常數檔**（PRD §5 已決定），內容見 §8。表中標「= Sanring xxx」的值和 Sanring 色階完全相同，只是在地圖情境下另外取名。

### 3.1 底圖

| Token | 深色 | 淺色 | 說明 |
|---|---|---|---|
| `map-water` | `#151b1c` | `#d5e1e4` | 新值：比背景更深或更冷一點，讓陸地浮出來 |
| `map-land` | `#2a3132` | `#f4f5f1` | 新值：淺色模式帶一點紙張的暖色 |
| `map-coastline` | `#606b6d`（= `neutral-70`） | `#606b6d` | 海岸線 0.75px |
| `map-graticule` | `--sanring-border` | `--sanring-border` | 經緯網，純裝飾 |

### 3.2 疆域色盤（16 色，分類用）

**設計方式**：用 OKLCH 等距取 16 個色相（每 22.5° 一個），相鄰色相交錯分成兩階明度。A 階 8 色、B 階 8 色，讓相鄰色相的明度也不同，這樣色盲使用者也較容易分辨。陣列順序經過排列，相鄰索引的色相盡量拉開。

- 深色模式：A 階 L=0.85、B 階 L=0.68，C=0.12（超出色域時自動降低）
- 淺色模式：A 階 L=0.46、B 階 L=0.62，C=0.13

| ID | Token／名稱 | OKLCH 色相 | 階 | 深色描邊 | 淺色描邊 |
|---|---|---|---|---|---|
| T01 | `map-territory-01` rose／玫瑰 | 10° | A | `#feb8c1` | `#913147` |
| T02 | `map-territory-02` teal／青綠 | 190° | A | `#5ce7df` | `#056662` |
| T03 | `map-territory-03` olive／橄欖 | 100° | A | `#e0d06e` | `#655904` |
| T04 | `map-territory-04` periwinkle／長春花藍 | 280° | A | `#c4c9fe` | `#4c4c9e` |
| T05 | `map-territory-05` apricot／杏橘 | 55° | A | `#febe92` | `#874300` |
| T06 | `map-territory-06` sky／天藍 | 235° | A | `#95d7fe` | `#055f86` |
| T07 | `map-territory-07` green／綠 | 145° | A | `#9be39d` | `#186a23` |
| T08 | `map-territory-08` orchid／蘭紫 | 325° | A | `#f6b2f9` | `#7b3a7f` |
| T09 | `map-territory-09` terracotta／赭紅 | 32.5° | B | `#d87b68` | `#c86552` |
| T10 | `map-territory-10` ocean／海藍 | 212.5° | B | `#06abc3` | `#0297ac` |
| T11 | `map-territory-11` moss／苔綠 | 122.5° | B | `#8ba44a` | `#78922c` |
| T12 | `map-territory-12` violet／紫羅蘭 | 302.5° | B | `#a785d5` | `#9671c6` |
| T13 | `map-territory-13` ochre／赭黃 | 77.5° | B | `#c18e35` | `#b07a06` |
| T14 | `map-territory-14` cornflower／矢車菊藍 | 257.5° | B | `#689ae2` | `#5187d3` |
| T15 | `map-territory-15` jade／玉綠 | 167.5° | B | `#38b089` | `#029e77` |
| T16 | `map-territory-16` raspberry／覆盆子 | 347.5° | B | `#ce78a6` | `#bd6395` |

**一個政權由三層組成**

| Token | 深色 | 淺色 | 說明 |
|---|---|---|---|
| `map-territory-stroke` | 色盤色、1.5px 實線 | 同左 | 邊界 |
| `map-territory-fill-opacity` | **0.35** | **0.28** | 填色＝色盤色乘上這個透明度，疊在 `map-land` 上 |
| `map-territory-label` | `#edf1f2`（= `neutral-10`） | `#202424`（= `neutral-90`） | 標籤一律用中性色，不用色盤色 |
| `map-label-halo` | `#202424`，1.5px | `#ffffff`，1.5px | 標籤光暈 |

**配色策略**（`assignTerritoryColors()`，見 §8）

1. **一個政權一輩子只用一個顏色**：拖動時間軸時顏色不會跳動，符合憲法 §9 連續變化的要求。
2. **鄰接圖著色（DSatur）**：如果兩個政權在任一共存年份有共同邊界，或距離小於緩衝值，就視為鄰居。先處理已上色鄰居最多的政權，再處理鄰居最多的政權。
3. **鄰居相容矩陣 `TERRITORY_COMPAT`**：兩個顏色要在正常視覺下 OKLab ΔE×100 ≥ 15，而且在紅綠色盲模擬（Machado 2009 的 deutan 和 protan）下 ΔE ≥ 8，**深淺兩種模式都成立**，才能當鄰居。實測每個顏色可相容 9–13 色；彼此兩兩相容的 4 色組有 182 組，5 色組有 40 組，足以應付平面地圖最多 4 個政權互相接壤的情況。
4. **優先順序**：先沿用上次的顏色，其次是政權 ID 雜湊出來的偏好色，最後才依序找其他相容色；全部衝突時，選衝突最少的顏色。實測三國周邊 8 個政權、12 組鄰接：0 衝突，重算後顏色不變。
5. **繼承政權不沿用前身的顏色**：如果西晉沿用曹魏的顏色，等於在視覺上暗示正統。這違反 PRD §6 方案 D「核心政權圖保持中立，正統是史觀 preset 的事」。傳承關係改用 §3.4 的狀態徽章和時間軸端點表現。
6. **建議在前端計算並快取，不寫入資料庫**，避免增加 schema 欄位。**已決定**（§9 D6）：前端計算並快取，不寫入資料庫。

> 限制：16 個顏色不可能在色盲視覺下兩兩都分得清楚，所以**辨識政權靠的是邊界加標籤**，顏色只負責區分鄰居。這是刻意的設計。

### 3.3 爭議區斜線網底（Canvas Pattern）

PRD §5 和 §9 已決定 Phase 1 用 Canvas Pattern；notes §十.5 決定 MVP 用中立灰斜線。

| Token | 深色 | 淺色 | 說明 |
|---|---|---|---|
| `map-hatch-color` | `#c8d4d6`（= `neutral-30`） | `#606b6d`（= `neutral-70`） | 中立斜線 |
| `map-hatch-angle` | 45°（"/" 方向） | 同左 | 固定 45°，方形 tile 才能無縫平鋪；改角度要重新計算 tile |
| `map-hatch-tile` | 12px | 同左 | 斜線的垂直間距 ≈ 12/√2 ≈ **8.5px** |
| `map-hatch-line-width` | 2px | 同左 | 用 `devicePixelRatio` 產生，`addImage(..., { pixelRatio })` |
| `map-hatch-two-party` | tile 16px、線寬 2.5px | 同左 | 雙方的色盤色交替（notes §十.3「雙方代表色交替斜線」），同色線距 ≈ 11.3px |
| `map-disputed-outline` | `#c8d4d6`，1px 虛線 4/3 | `#404748`（= `neutral-80`），1px 虛線 4/3 | 爭議區外框 |
| 底色 | 先用 `map-land` 不透明填滿 | 同左 | 底下政權的填色不會透上來，斜線對比固定 |

圖層順序：疆域填色 → **爭議區底色（land）→ 斜線（`fill-pattern`）→ 爭議區外框** → 疆域邊界 → 標籤。切換深淺色時，用 `map.updateImage()` 重新產生斜線圖。

已知限制和 notes 說的一樣：Canvas Pattern 是固定螢幕像素，縮放地圖時線距不會跟著變。成熟階段再升級成 Shader（方案 ③）。

### 3.4 政權狀態（憲法 §4）：不只靠顏色區分

| 狀態 | 地圖邊界 | 填色 | 徽章圖示 | 標籤 | 時間軸端點 |
|---|---|---|---|---|---|
| **存續** | 原色、**實線** 1.5px | 原色 × 0.35／0.28 | （無，或實心點） | `曹魏` | 開放（持續延伸） |
| **分裂** | 原色、**短虛線** `[3,2]`×1.5px（殘影） | 無，由新政權接手填色 | **分叉 ⑂** | `東漢・分裂為 魏/蜀/吳` | **分叉**：色條末端拆成 3 條細線 |
| **被取代（禪讓）** | **保留原色**、**長虛線** `[6,2]`×1.5px | 原色 × 0.12／0.10（淡填） | **向右箭頭 →** | `曹魏・禪讓 → 西晉` | **箭頭**：色條末端是實心三角，指向繼承者 |
| **被滅亡** | **去飽和灰** `#a1b2b5` / `#606b6d`、**圓點線** `[0,2]`、2.2px、圓頭 | 無 | **叉號 ✕** | `蜀漢・亡於 曹魏` | **豎線加 ✕**：色條末端是灰色豎線 |

**「禪讓」和「被滅亡」用五種方式區分**，任何一種單獨看都分得出來，符合 PRD Story 4 的要求：
① 線型：長虛線或圓點線；② 色彩：保留色相，或去飽和成灰，兩者明度也不同，色盲使用者也分得出來；③ 徽章：箭頭或叉號；④ 文字：「禪讓 →」或「亡於」；⑤ 時間軸端點：三角箭頭或豎線加叉號。

**殘影時間** `GHOST_YEARS = 10`：政權終止後，殘影會在 10 年內線性淡出到透明，不會突然消失，呼應憲法 §9「連續變化、非離散跳轉」。**已決定**（§9 D5）：10 年。

**MapLibre 注意事項**：`line-dasharray` 的單位是線寬；`line-cap` 是 layout 屬性，不能依資料切換。所以**每種狀態各用一個 line layer**，用 `filter` 依狀態分開。

徽章用 MapLibre 的 `symbol` layer，`icon-image` 依狀態給 4 個 SDF 圖示，放在標籤左邊。圖示照 notes §十.3 的原則，用沒有情緒的中立符號。

### 3.5 聚焦模式、事件、互動

| Token | 值 | 說明 |
|---|---|---|
| `map-focus-line-width` | 3px | 被聚焦政權的邊界 |
| `map-focus-ring` | `--sanring-control`（`#edf1f2` / `#202424`），外圈 1.5px | 對每個色盤填色都 ≥ 3:1（實測至少 4.89:1） |
| `map-focus-others-fill-factor` | 0.4 | 其他政權的填色透明度乘以 0.4 |
| `map-focus-others-line-opacity` | 0.5 | 其他政權邊界變淡 |
| `map-event-marker` | `#e57373`（= `error-50`）/ `#b75c5c`（= `error-60`） | 事件點直徑 10px，外加 2px 背景色光環；起始點的脈動動畫要遵守 `prefers-reduced-motion`。**已決定**（§9 D8）：保留紅點，定位為**事件語意色**（標示「這裡發生了事件」），不代表對任何政權或事件的價值判斷；圖例須明寫「事件」，不得與政權色盤混用 |
| `map-event-icon` | 依類型使用中立圖示：交叉刀劍＝交戰，圓圈＝條約，虛線＝動線 | 同 notes §十.3，不用顏色表達立場 |
| `map-alias-label` | 他稱用斜體或加上「（他稱）」，hover 時顯示自稱 | 例：唐朝視角下顯示「大食」，可追溯到「阿拉伯帝國」（憲法 I4） |
| `map-place-label` | 12px／400；古名用 `label`，括號內的今名用 `label-muted` | `長安（西安）`，用 MapLibre 的 `format` 表達式分段上色 |

### 3.6 時間軸

| Token | 深色 | 淺色 | 說明 |
|---|---|---|---|
| `timeline-panel` | `--sanring-elevated`，圓角 `radius-lg` | 同左 | 底部面板 |
| `timeline-track` | `#78858a`（新值） | `#818e91`（= `neutral-60`） | 4px 高；`neutral-60` 在深色 elevated 上只有 2.97:1，所以深色模式調亮 |
| `timeline-tick-major` | `#a1b2b5`（= `neutral-50`），10px | `#606b6d`（= `neutral-70`），10px | 百年、五十年刻度 |
| `timeline-tick-minor` | `--sanring-border-strong`，5px | 同左 | 十年刻度，輔助用 |
| `timeline-label` | `--sanring-muted` `#b4c3c6` | `#606b6d` | 12px（`text-xs`） |
| `timeline-playhead` | `--sanring-control` `#edf1f2` | `#202424` | 2px 線；圓形握把 16px，外加 2px 背景色邊；觸控熱區 44px |
| `timeline-playhead-label` | 底色 `control`、文字 `control-foreground`、圓角 `radius-sm` | 同左 | `263 · 景元四年`：西元加年號（憲法 §9） |
| `timeline-era-band` | 色盤色 × **0.35** 疊在 surface 上，下緣 3px 色盤色色條 | × **0.22** | 高 20px、間距 4px、圓角 `radius-xs`；文字一律用 `foreground`，不放在純色上 |
| `timeline-era-band-end` | 依 §3.4 的狀態端點 | 同左 | 分叉、箭頭、豎線加 ✕ |
| `timeline-uncertain` | 不確定的區間用色條漸隱，色條改成虛線 `[4,3]`，標註「? 約 216」 | 同左 | 對應 EDTF 的 `?` 和 `~`（PRD Story 5），不能顯示得比史料更精確 |
| `timeline-keyframe` | `#fce08f`（= `sun-50`） | `#978656`（= `sun-70`） | 事件的活躍區間 pin（notes §八「Keyframe Pin」） |
| `timeline-focus-range` | `#64b5f6`（= `info-50`） | `#3c6d94`（= `info-70`） | 聚焦政權的存續區間 |
| 尺寸 | 主軸 64px；副軸（月／日）40px | 同左 | notes §六的雙層時間軸 |

### 3.7 地圖浮層：圓角、間距、字級、陰影、毛玻璃

**圓角**：全部沿用 Sanring 的 3/6/8/12，不新增。

**間距**（`MAP_LAYOUT`）

| Token | 值 |
|---|---|
| `map-overlay-inset` | 16px（桌機）／12px（行動裝置） |
| `map-control-gap` | 8px |
| `map-popover-padding` | 12px（比 Sanring popover 的 16px 緊湊，避免擋住地圖） |
| `map-popover-max-width` | 320px |
| `map-drawer-width` | 400px |

**字級**（地圖標籤）

| Token | 值 |
|---|---|
| `map-label-regime` | 依縮放插值：z2 12px → z4 14px → z6 18px；字重 500，聚焦時 700；光暈 1.5px |
| `map-label-place` | 12px／400；光暈 1.25px |
| `map-label-state-suffix` | 11px／400，用 `label` 或 `label-muted`（例：「亡於 曹魏」） |

**陰影**（地圖底下很雜，需要比 Sanring 預設的 `shadow-md`、`shadow-lg` 更重一點）

| Token | 深色 | 淺色 |
|---|---|---|
| `map-shadow-control` | `0 1px 2px rgb(0 0 0 / .40)` | `0 1px 2px rgb(16 24 26 / .16)` |
| `map-shadow-popover` | `0 8px 24px rgb(0 0 0 / .45)` | `0 8px 24px rgb(16 24 26 / .18)` |
| `map-shadow-drawer` | `0 16px 48px rgb(0 0 0 / .55)` | `0 16px 48px rgb(16 24 26 / .22)` |

地圖上的文字不用陰影，一律用光暈 halo。

**毛玻璃抽屜**（PRD §8、notes §八）

| Token | 深色 | 淺色 |
|---|---|---|
| `map-glass-bg` | `rgb(35 42 43 / .90)`（= `surface` 加 90% 不透明） | `rgb(255 255 255 / .92)` |
| `map-glass-blur` | 16px | 16px |
| `map-glass-border` | `--sanring-border` | `--sanring-border` |

> notes 原本寫的是 `rgba(20,20,25,0.75)`。我實測：底下是白色時，`muted` 文字只有 **4.49:1**，沒過 AA，所以把不透明度提高到 0.90。

---

## 4. MapLibre 圖層順序（建議）

1. `water`（background）→ `land` → `coastline`
2. `territory-fill`（依 `color_index` 用 `match`，透明度依狀態）
3. `disputed-base`（land 色）→ `disputed-hatch`（`fill-pattern`）→ `disputed-outline`
4. `territory-line-existing` / `-split` / `-abdicated` / `-destroyed`（4 個 line layer，各自 `filter`）
5. `focus-casing`（聚焦時才顯示）
6. `relations`（Phase 1 先不做，留給 Deck.gl）→ `events`
7. `state-badge`（symbol）→ `regime-label` → `place-label`

---

## 5. 預覽圖

`/workspace/world-line-design/preview.png`（1440×1600，上半部深色、下半部淺色）包含：16 色色塊（填色、描邊、標籤）、兩種斜線網底、四種狀態圖例、三國時期的時間軸示意（東漢分叉、曹魏禪讓箭頭、蜀漢與東吳 ✕、匈奴的不確定漸隱、赤壁 pin、蜀漢聚焦區間、播放頭「263 · 景元四年」）。我已經看過圖，確認可以正常判讀。

---

## 6. WCAG AA 對比驗證（實際計算）

**方法**：用 `scripts/contrast.py` 依 WCAG 2.x 相對亮度公式計算。半透明顏色先依 alpha 混合到實際底色，再算對比。門檻是一般文字 4.5:1，UI 元件和圖形 3:1。毛玻璃取最壞情況，分別假設底下是純白、純黑和最亮的描邊色。總共 **260 組，全部通過**；另外 2 組是 Sanring 的 `active` 底色，屬於建議項目，已經用指示條補足（§1.1）。

**修正過程**：第一輪有 29 組沒過，包括 Slate 的主色文字、淺色模式強邊框、淺色模式殘影標籤、淺色模式朝代帶白字、時間軸軌道、淺色毛玻璃的次要文字。修正方式：覆寫 2 個 Sanring 值、淺色模式殘影標籤改用 `neutral-80`、朝代帶改成淡填色加色條並一律用前景色文字、調整軌道顏色、淺色毛玻璃不透明度從 0.90 提高到 0.92、色盤改成兩階明度。

### 6.1 色盤彙整（16 色取最小值和最大值）

| 模式 | 檢查項目 | 對比範圍 | 門檻 | 結果 |
|---|---|---|---|---|
| dark | stroke / land（最低 T16／最高 T02） | 4.33:1 ~ 8.81:1 | 3:1 | ✅ |
| dark | label / fill（最低 T02／最高 T16） | 4.89:1 ~ 6.94:1 | 4.5:1 | ✅ |
| dark | ghost label / ghost fill（最低 T02／最高 T09） | 5.46:1 ~ 6.17:1 | 4.5:1 | ✅ |
| dark | era band label / band tint（最低 T07／最高 T09） | 5.21:1 ~ 7.48:1 | 4.5:1 | ✅ |
| dark | era band stripe / timeline surface（最低 T16／最高 T02） | 4.77:1 ~ 9.70:1 | 3:1 | ✅ |
| dark | focus ring / fill（最低 T02／最高 T16） | 4.89:1 ~ 6.94:1 | 3:1 | ✅ |
| light | stroke / land（最低 T15／最高 T01） | 3.11:1 ~ 7.01:1 | 3:1 | ✅ |
| light | label / fill（最低 T01／最高 T11） | 9.00:1 ~ 10.71:1 | 4.5:1 | ✅ |
| light | ghost label / ghost fill（最低 T01／最高 T11） | 7.39:1 ~ 7.84:1 | 4.5:1 | ✅ |
| light | era band label / band tint（最低 T01／最高 T11） | 10.90:1 ~ 12.36:1 | 4.5:1 | ✅ |
| light | era band stripe / timeline surface（最低 T15／最高 T01） | 3.41:1 ~ 7.68:1 | 3:1 | ✅ |
| light | focus ring / fill（最低 T01／最高 T11） | 9.00:1 ~ 10.71:1 | 3:1 | ✅ |

### 6.2 其他配對

| 模式 | 配對 | 前景 | 背景 | 對比 | 門檻 | 結果 |
|---|---|---|---|---|---|---|
| dark | foreground / background | `#edf1f2` | `#202424` | 13.79:1 | 4.5:1 | ✅ |
| dark | muted / background | `#b4c3c6` | `#202424` | 8.63:1 | 4.5:1 | ✅ |
| dark | muted / surface | `#b4c3c6` | `#232a2b` | 8.04:1 | 4.5:1 | ✅ |
| dark | foreground / elevated | `#edf1f2` | `#2b3334` | 11.36:1 | 4.5:1 | ✅ |
| dark | border-strong / background | `#818e91` | `#202424` | 4.64:1 | 3:1 | ✅ |
| dark | control / background (playhead, primary btn) | `#edf1f2` | `#202424` | 13.79:1 | 3:1 | ✅ |
| dark | control-foreground / control | `#202424` | `#edf1f2` | 13.79:1 | 4.5:1 | ✅ |
| dark | primary-fg / primary (slate 50) | `#ffffff` | `#64748b` | 4.76:1 | 4.5:1 | ✅ |
| dark | active / background（選取底色，非唯一指示） | `#1e293b` | `#202424` | 1.07:1 | 3:1 | ⚠️ 以指示條補足 |
| dark | 選取指示條 control / active | `#edf1f2` | `#1e293b` | 12.86:1 | 3:1 | ✅ |
| dark | coastline / water | `#606b6d` | `#151b1c` | 3.17:1 | 3:1 | ✅ |
| dark | coastline / land | `#606b6d` | `#2a3132` | 2.41:1 | 1.0:1 | 參考 |
| dark | label / land (no fill) | `#edf1f2` | `#2a3132` | 11.66:1 | 4.5:1 | ✅ |
| dark | label / water | `#edf1f2` | `#151b1c` | 15.32:1 | 4.5:1 | ✅ |
| dark | label muted / land | `#b4c3c6` | `#2a3132` | 7.30:1 | 4.5:1 | ✅ |
| dark | hatch neutral / land | `#c8d4d6` | `#2a3132` | 8.74:1 | 3:1 | ✅ |
| dark | disputed outline / land | `#c8d4d6` | `#2a3132` | 8.74:1 | 3:1 | ✅ |
| dark | destroyed outline / land | `#a1b2b5` | `#2a3132` | 6.03:1 | 3:1 | ✅ |
| dark | event marker / land | `#e57373` | `#2a3132` | 4.44:1 | 3:1 | ✅ |
| dark | event marker / water | `#e57373` | `#151b1c` | 5.83:1 | 3:1 | ✅ |
| dark | timeline track / panel(elevated) | `#78858a` | `#2b3334` | 3.40:1 | 3:1 | ✅ |
| dark | timeline major tick / surface | `#a1b2b5` | `#232a2b` | 6.64:1 | 3:1 | ✅ |
| dark | timeline label / surface | `#b4c3c6` | `#232a2b` | 8.04:1 | 4.5:1 | ✅ |
| dark | timeline playhead / surface | `#edf1f2` | `#232a2b` | 12.85:1 | 3:1 | ✅ |
| dark | timeline playhead / track | `#edf1f2` | `#78858a` | 3.34:1 | 3:1 | ✅ |
| dark | keyframe pin / surface | `#fce08f` | `#232a2b` | 11.27:1 | 3:1 | ✅ |
| dark | focus range / surface | `#64b5f6` | `#232a2b` | 6.60:1 | 3:1 | ✅ |
| dark | glass drawer text / glass over white | `#edf1f2` | `#393f40` | 9.43:1 | 4.5:1 | ✅ |
| dark | glass drawer muted / glass over white | `#b4c3c6` | `#393f40` | 5.90:1 | 4.5:1 | ✅ |
| dark | glass drawer text / glass over black | `#edf1f2` | `#202627` | 13.50:1 | 4.5:1 | ✅ |
| dark | glass drawer muted / glass over black | `#b4c3c6` | `#202627` | 8.45:1 | 4.5:1 | ✅ |
| dark | glass drawer text / glass over brightest stroke | `#edf1f2` | `#293d3d` | 10.09:1 | 4.5:1 | ✅ |
| dark | glass drawer muted / glass over brightest stroke | `#b4c3c6` | `#293d3d` | 6.32:1 | 4.5:1 | ✅ |
| dark | popover muted / elevated | `#b4c3c6` | `#2b3334` | 7.11:1 | 4.5:1 | ✅ |
| light | foreground / background | `#202424` | `#f6f8f8` | 14.71:1 | 4.5:1 | ✅ |
| light | muted / background | `#606b6d` | `#f6f8f8` | 5.16:1 | 4.5:1 | ✅ |
| light | muted / surface | `#606b6d` | `#ffffff` | 5.50:1 | 4.5:1 | ✅ |
| light | foreground / elevated | `#202424` | `#ffffff` | 15.68:1 | 4.5:1 | ✅ |
| light | border-strong / background | `#818e91` | `#f6f8f8` | 3.17:1 | 3:1 | ✅ |
| light | control / background (playhead, primary btn) | `#202424` | `#f6f8f8` | 14.71:1 | 3:1 | ✅ |
| light | control-foreground / control | `#ffffff` | `#202424` | 15.68:1 | 4.5:1 | ✅ |
| light | primary-fg / primary (slate 50) | `#ffffff` | `#64748b` | 4.76:1 | 4.5:1 | ✅ |
| light | active / background（選取底色，非唯一指示） | `#d8eef1` | `#f6f8f8` | 1.13:1 | 3:1 | ⚠️ 以指示條補足 |
| light | 選取指示條 control / active | `#202424` | `#d8eef1` | 13.01:1 | 3:1 | ✅ |
| light | coastline / water | `#606b6d` | `#d5e1e4` | 4.11:1 | 3:1 | ✅ |
| light | coastline / land | `#606b6d` | `#f4f5f1` | 5.02:1 | 1.0:1 | 參考 |
| light | label / land (no fill) | `#202424` | `#f4f5f1` | 14.32:1 | 4.5:1 | ✅ |
| light | label / water | `#202424` | `#d5e1e4` | 11.74:1 | 4.5:1 | ✅ |
| light | label muted / land | `#404748` | `#f4f5f1` | 8.67:1 | 4.5:1 | ✅ |
| light | hatch neutral / land | `#606b6d` | `#f4f5f1` | 5.02:1 | 3:1 | ✅ |
| light | disputed outline / land | `#404748` | `#f4f5f1` | 8.67:1 | 3:1 | ✅ |
| light | destroyed outline / land | `#606b6d` | `#f4f5f1` | 5.02:1 | 3:1 | ✅ |
| light | event marker / land | `#b75c5c` | `#f4f5f1` | 4.08:1 | 3:1 | ✅ |
| light | event marker / water | `#b75c5c` | `#d5e1e4` | 3.35:1 | 3:1 | ✅ |
| light | timeline track / panel(elevated) | `#818e91` | `#ffffff` | 3.38:1 | 3:1 | ✅ |
| light | timeline major tick / surface | `#606b6d` | `#ffffff` | 5.50:1 | 3:1 | ✅ |
| light | timeline label / surface | `#606b6d` | `#ffffff` | 5.50:1 | 4.5:1 | ✅ |
| light | timeline playhead / surface | `#202424` | `#ffffff` | 15.68:1 | 3:1 | ✅ |
| light | timeline playhead / track | `#202424` | `#818e91` | 4.64:1 | 3:1 | ✅ |
| light | keyframe pin / surface | `#978656` | `#ffffff` | 3.58:1 | 3:1 | ✅ |
| light | focus range / surface | `#3c6d94` | `#ffffff` | 5.52:1 | 3:1 | ✅ |
| light | glass drawer text / glass over white | `#202424` | `#ffffff` | 15.68:1 | 4.5:1 | ✅ |
| light | glass drawer muted / glass over white | `#606b6d` | `#ffffff` | 5.50:1 | 4.5:1 | ✅ |
| light | glass drawer text / glass over black | `#202424` | `#ebebeb` | 13.15:1 | 4.5:1 | ✅ |
| light | glass drawer muted / glass over black | `#606b6d` | `#ebebeb` | 4.61:1 | 4.5:1 | ✅ |
| light | glass drawer text / glass over brightest stroke | `#202424` | `#ebf7f4` | 14.29:1 | 4.5:1 | ✅ |
| light | glass drawer muted / glass over brightest stroke | `#606b6d` | `#ebf7f4` | 5.01:1 | 4.5:1 | ✅ |
| light | popover muted / elevated | `#606b6d` | `#ffffff` | 5.50:1 | 4.5:1 | ✅ |

`coastline / land` 只是參考值。海岸線的作用是區分海和陸，不要求和陸地有 3:1 對比。

完整 260 組的明細在附錄 A，也在 `scripts/contrast-table.md`。

**驗證範圍外**：WCAG 的對比公式不涵蓋**色盲辨識度**，這部分改用 §3.2 的 ΔE 加 CVD 模擬矩陣檢查。**斜線網底疊在政權填色上**的情況不存在，因為爭議區底下先用 land 色蓋住了。

---

## 7. 貼進 Google Stitch 的內容

> 直接整段複製。顏色寫在文字裡，Stitch 才會照用；它不會讀 CSS 變數。

```text
【產品】World Line：歷史 GIS 地圖網頁（Angular + MapLibre）。全螢幕地圖為主角，底部是可拖曳的時間軸，讓人「縱覽世界」：同一年份同時看到多個政權的疆域，像氣象雲圖一樣隨時間連續變化。介面語言：繁體中文。

【風格】沉穩、學術、可長時間閱讀。介面框架用低彩度灰藍，把色彩留給地圖上的政權。預設深色主題，另做一份淺色版。字體 Ubuntu，中文用 Noto Sans TC。圓角 3／6／8／12px。陰影克制，地圖上的文字用 1.5px 底色光暈取代陰影。所有文字對比符合 WCAG AA。

【畫面】
1. 主地圖：多個政權以半透明色塊、實線邊界和置中名稱標籤呈現。左上是搜尋和圖層切換，右上是縮放和深淺色切換，左下是圖例（政權狀態、爭議區）。
2. 底部時間軸面板（主軸高 64px，圓角 12px）：4px 細軌道、每 50 年一個大刻度、每 10 年一個小刻度，圓形播放頭搭配年份膠囊（西元加年號，例如「263 · 景元四年」）。軌道上方是一列列朝代帶，高 20px，淡色底加下緣 3px 色條，文字用前景色。事件以黃色小 pin 標出活躍區間。
3. 政權聚焦：點擊某個政權後，它的邊界加粗為 3px，外圈加亮色描邊，其他政權變淡。右側 400px 毛玻璃抽屜列出同時期的周邊政權和互動：戰爭、條約是離散事件；貿易、朝貢是持續關係。
4. 事件詳情抽屜：毛玻璃效果（blur 16px，背景 90% 不透明），三層手風琴（背景起因／關鍵轉折／歷史影響），另有多重視角分頁。

【關鍵視覺規則】
- 爭議區不填任何國家色，改用 45° 斜線網底（中立灰，或兩方顏色交替）加 1px 虛線外框。
- 政權狀態不能只靠顏色區分：
  · 存續：實線邊界加半透明填色。
  · 分裂：原邊界變成短虛線殘影，加分叉圖示，裡面是分裂出的新政權。
  · 被取代（禪讓）：長虛線，保留原色，淡填色，加向右箭頭圖示，標「禪讓 → 西晉」。
  · 被滅亡：灰色圓點線，無填色，加叉號圖示，標「亡於 曹魏」。
  時間軸上的朝代帶結尾也要對應：分叉、三角箭頭、豎線加叉號。
- 年代不確定時（例如「? 約 216」），朝代帶尾端漸隱，色條改成虛線。
- 政權名稱顯示自稱；切換觀察視角時改顯示他稱（例如「大食」），hover 時顯示自稱。地名顯示「長安（西安）」，括號內用次要文字色。

【色彩 token：深色／淺色】
背景 #202424／#f6f8f8；面板 #232a2b／#ffffff；浮層 #2b3334／#ffffff
文字 #edf1f2／#202424；次要文字 #b4c3c6／#606b6d
邊框 #354042／#d9e1e2；強邊框 #818e91／#818e91
主色 #64748b（主色上的文字用 #ffffff）
海 #151b1c／#d5e1e4；陸地 #2a3132／#f4f5f1；海岸線 #606b6d
政權色盤（深色，描邊用原色，填色用原色的 35%）：T01 #feb8c1, T02 #5ce7df, T03 #e0d06e, T04 #c4c9fe, T05 #febe92, T06 #95d7fe, T07 #9be39d, T08 #f6b2f9, T09 #d87b68, T10 #06abc3, T11 #8ba44a, T12 #a785d5, T13 #c18e35, T14 #689ae2, T15 #38b089, T16 #ce78a6
政權色盤（淺色，描邊用原色，填色用原色的 28%）：T01 #913147, T02 #056662, T03 #655904, T04 #4c4c9e, T05 #874300, T06 #055f86, T07 #186a23, T08 #7b3a7f, T09 #c86552, T10 #0297ac, T11 #78922c, T12 #9671c6, T13 #b07a06, T14 #5187d3, T15 #029e77, T16 #bd6395
斜線網底 #c8d4d6／#606b6d；被滅亡的邊界 #a1b2b5／#606b6d；事件點 #e57373／#b75c5c
時間軸：軌道 #78858a／#818e91；大刻度 #a1b2b5／#606b6d；播放頭 #edf1f2／#202424；事件 pin #fce08f／#978656；聚焦區間 #64b5f6／#3c6d94
```

---

## 8. 共用常數檔（TS）

PRD §5 的決策是「Phase 1 用單一共用常數檔」，所以不做 token pipeline，也不做 Figma 同步。建議路徑是 `app/src/app/map/map-colors.ts`。PRD 舉的檔名是 `neutral-map-colors.ts`，但這個檔已經不只放中立色，所以改名。**已決定**（§9 D4）：檔名為 `map-colors.ts`。

這段程式碼已經用 TypeScript `--strict` 通過型別檢查；`assignTerritoryColors()` 用三國案例實際跑過：0 衝突，重算後顏色不變。檔案在 `/workspace/world-line-design/map-colors.ts`。

```ts
/**
 * World Line — 地圖專用設計常數（單一共用常數檔，PRD §5「斜線網底配色」決策）
 *
 * - 只放「地圖專用」的值；一般 UI 一律用 Sanring UI 的 CSS 變數（--sanring-*）。
 * - 不是 token pipeline：沒有建置步驟、沒有 Figma 同步，改值就直接改這個檔。
 * - 色值已用 scripts/contrast.py 驗證 WCAG AA（見 design-spec.md §6）。
 * - 主題：Sanring slate preset；深色 = :root 預設，淺色 = <html data-theme="light">。
 */

export type MapThemeMode = 'dark' | 'light';

/** 16 色疆域分類色盤。索引固定（0–15），兩種模式同一索引 = 同一色相，切換深淺色時政權不會換色。 */
export const TERRITORY_HUE_NAMES = ["rose", "teal", "olive", "periwinkle", "apricot", "sky", "green", "orchid", "terracotta", "ocean", "moss", "violet", "ochre", "cornflower", "jade", "raspberry"] as const;

export const MAP_COLORS = {
  dark: {
    water: '#151b1c',
    land: '#2a3132',
    coastline: '#606b6d', // = --sanring-neutral-70
    territory: [
    '#feb8c1', // T01 rose (A)
    '#5ce7df', // T02 teal (A)
    '#e0d06e', // T03 olive (A)
    '#c4c9fe', // T04 periwinkle (A)
    '#febe92', // T05 apricot (A)
    '#95d7fe', // T06 sky (A)
    '#9be39d', // T07 green (A)
    '#f6b2f9', // T08 orchid (A)
    '#d87b68', // T09 terracotta (B)
    '#06abc3', // T10 ocean (B)
    '#8ba44a', // T11 moss (B)
    '#a785d5', // T12 violet (B)
    '#c18e35', // T13 ochre (B)
    '#689ae2', // T14 cornflower (B)
    '#38b089', // T15 jade (B)
    '#ce78a6', // T16 raspberry (B)
  ],
    fillOpacity: 0.35,
    ghostFillOpacity: 0.12,
    label: '#edf1f2', // = --sanring-neutral-10
    labelMuted: '#b4c3c6', // = --sanring-neutral-40
    labelHalo: '#202424', // = --sanring-neutral-90
    focusRing: '#edf1f2', // = --sanring-control
    hatch: '#c8d4d6', // = --sanring-neutral-30
    disputedOutline: '#c8d4d6', // = --sanring-neutral-30
    destroyedOutline: '#a1b2b5', // = --sanring-neutral-50
    eventMarker: '#e57373', // = --sanring-error-50；事件語意色，非政權價值判斷
  },
  light: {
    water: '#d5e1e4',
    land: '#f4f5f1',
    coastline: '#606b6d', // = --sanring-neutral-70
    territory: [
    '#913147', // T01 rose (A)
    '#056662', // T02 teal (A)
    '#655904', // T03 olive (A)
    '#4c4c9e', // T04 periwinkle (A)
    '#874300', // T05 apricot (A)
    '#055f86', // T06 sky (A)
    '#186a23', // T07 green (A)
    '#7b3a7f', // T08 orchid (A)
    '#c86552', // T09 terracotta (B)
    '#0297ac', // T10 ocean (B)
    '#78922c', // T11 moss (B)
    '#9671c6', // T12 violet (B)
    '#b07a06', // T13 ochre (B)
    '#5187d3', // T14 cornflower (B)
    '#029e77', // T15 jade (B)
    '#bd6395', // T16 raspberry (B)
  ],
    fillOpacity: 0.28,
    ghostFillOpacity: 0.1,
    label: '#202424', // = --sanring-neutral-90
    labelMuted: '#404748', // = --sanring-neutral-80
    labelHalo: '#ffffff',
    focusRing: '#202424', // = --sanring-control
    hatch: '#606b6d', // = --sanring-neutral-70
    disputedOutline: '#404748', // = --sanring-neutral-80
    destroyedOutline: '#606b6d', // = --sanring-neutral-70
    eventMarker: '#b75c5c', // = --sanring-error-60；事件語意色，非政權價值判斷
  },
} as const;

/**
 * 色盤相容矩陣：bit j = 1 代表 T(i+1) 與 T(j+1) 可以當鄰居。
 * 條件（兩種模式都要成立）：OKLab ΔE×100 ≥ 15，且紅綠色盲模擬（Machado 2009 deutan/protan）ΔE ≥ 8。
 */
export const TERRITORY_COMPAT: readonly number[] = [0xff20, 0xff10, 0xffa8, 0xff54, 0xffaa, 0xff15, 0xff88, 0xff54, 0x2aff, 0x15ff, 0xaaff, 0x55ff, 0xeaff, 0xd5ff, 0x38ff, 0x34ff];

/** 爭議區斜線網底（Canvas Pattern）。尺寸為 CSS px，產生時乘上 devicePixelRatio。 */
export const HATCH = {
  angleDeg: 45, // 固定 45°（"/" 方向）：方形 tile 可無縫平鋪；其他角度需另算 tile
  neutral: { tile: 12, lineWidth: 2 }, // 垂直線距 = 12/√2 ≈ 8.5px
  twoParty: { tile: 16, lineWidth: 2.5 }, // 雙方顏色交替，同色線距 ≈ 11.3px
  outlineDash: [4, 3] as const, // 爭議區外框（px，line-dasharray 需除以線寬 1）
} as const;

/**
 * 產生 MapLibre 可用的斜線 tile：map.addImage(id, img, { pixelRatio })。
 * colors 給 1 色 = 中立網底；給 2 色 = 雙方交替。換主題時用 map.updateImage() 重產。
 */
export function createHatchImage(
  colors: readonly string[],
  tile: number,
  lineWidth: number,
  pixelRatio = globalThis.devicePixelRatio ?? 1,
): ImageData {
  const size = Math.round(tile * pixelRatio);
  const canvas = new OffscreenCanvas(size, size);
  const ctx = canvas.getContext('2d')!;
  ctx.lineWidth = lineWidth * pixelRatio;
  ctx.lineCap = 'butt';
  const n = colors.length;
  // 直線 x + y = c，c 每 size/n 一條；多畫幾條把四角補滿，平鋪時才不會斷線
  for (let i = -2 * n; i < 4 * n; i++) {
    const c = (i * size) / n;
    ctx.strokeStyle = colors[((i % n) + n) % n];
    ctx.beginPath();
    ctx.moveTo(c + size, -size);
    ctx.lineTo(c - 2 * size, 2 * size);
    ctx.stroke();
  }
  return ctx.getImageData(0, 0, size, size);
}

/** 政權狀態（憲法 §4）。顏色以外至少還有線型＋徽章＋文字三種編碼。 */
export type PolityState = 'existing' | 'split' | 'abdicated' | 'destroyed';

export const POLITY_STATE_STYLE = {
  existing: {
    labelZh: '存續', lineWidth: 1.5, dash: null, lineCap: 'butt',
    stroke: 'hue', fill: 'hue', fillOpacity: 'fillOpacity', badge: null, labelSuffix: null,
    timelineEnd: 'open',
  },
  split: {
    labelZh: '分裂', lineWidth: 1.5, dash: [3, 2], lineCap: 'butt', // dash 單位 = 線寬
    stroke: 'hue', fill: null, fillOpacity: 0, badge: 'fork', labelSuffix: '分裂為 {successors}',
    timelineEnd: 'fork',
  },
  abdicated: {
    labelZh: '被取代（禪讓）', lineWidth: 1.5, dash: [6, 2], lineCap: 'butt',
    stroke: 'hue', fill: 'hue', fillOpacity: 'ghostFillOpacity', badge: 'arrow-right', labelSuffix: '禪讓 → {successor}',
    timelineEnd: 'chevron',
  },
  destroyed: {
    labelZh: '被滅亡', lineWidth: 2.2, dash: [0, 2], lineCap: 'round', // 0 長度 + 圓頭 = 圓點線
    stroke: 'destroyedOutline', fill: null, fillOpacity: 0, badge: 'cross', labelSuffix: '亡於 {destroyer}',
    timelineEnd: 'bar-cross',
  },
} as const;

/** 終止後「殘影」顯示多久（年），期間透明度線性淡出到 0；呼應憲法 §9 連續變化。 */
export const GHOST_YEARS = 10;

/** 聚焦模式（PRD Story 2） */
export const FOCUS_STYLE = {
  focusedLineWidth: 3,
  focusRingWidth: 1.5, // 外圈 casing，用 focusRing 色
  othersFillOpacityFactor: 0.4,
  othersLineOpacity: 0.5,
} as const;

export const TIMELINE = {
  dark: {
    track: '#78858a',
    tickMajor: '#a1b2b5', // = --sanring-neutral-50
    tickMinor: 'var(--sanring-border-strong)',
    label: '#b4c3c6', // = --sanring-muted
    playhead: '#edf1f2', // = --sanring-control
    keyframe: '#fce08f', // = --sanring-sun-50
    focusRange: '#64b5f6', // = --sanring-info-50
    eraBandOpacity: 0.35,
  },
  light: {
    track: '#818e91', // = --sanring-neutral-60
    tickMajor: '#606b6d', // = --sanring-neutral-70
    tickMinor: 'var(--sanring-border-strong)',
    label: '#606b6d', // = --sanring-muted
    playhead: '#202424', // = --sanring-control
    keyframe: '#978656', // = --sanring-sun-70
    focusRange: '#3c6d94', // = --sanring-info-70
    eraBandOpacity: 0.22,
  },
  size: {
    mainAxisHeight: 64, subAxisHeight: 40, trackHeight: 4,
    tickMajor: 10, tickMinor: 5, bandHeight: 20, bandGap: 4, bandStripe: 3,
    playheadLine: 2, playheadHandle: 16, hitTarget: 44, uncertainFade: 'gradient+dash',
  },
} as const;

export const MAP_TYPE = {
  /** MapLibre text-size 依 zoom 插值：[zoom, px] */
  regimeLabel: { stops: [[2, 12], [4, 14], [6, 18]] as const, weight: 500, focusedWeight: 700, haloWidth: 1.5 },
  placeLabel: { size: 12, weight: 400, haloWidth: 1.25 }, // 「長安（西安）」括號內用 labelMuted
  stateSuffix: { size: 11, weight: 400 },
  /** CJK 交給瀏覽器本機字型，避免下載 CJK glyph PBF */
  localIdeographFontFamily: '"Noto Sans TC", "PingFang TC", "Microsoft JhengHei", sans-serif',
} as const;

export const MAP_LAYOUT = {
  overlayInset: 16, overlayInsetMobile: 12, controlGap: 8,
  popoverPadding: 12, popoverMaxWidth: 320, drawerWidth: 400,
} as const;

export const MAP_SHADOW = {
  dark: {
    control: '0 1px 2px rgb(0 0 0 / 0.40)',
    popover: '0 8px 24px rgb(0 0 0 / 0.45)',
    drawer: '0 16px 48px rgb(0 0 0 / 0.55)',
  },
  light: {
    control: '0 1px 2px rgb(16 24 26 / 0.16)',
    popover: '0 8px 24px rgb(16 24 26 / 0.18)',
    drawer: '0 16px 48px rgb(16 24 26 / 0.22)',
  },
} as const;

export const GLASS_DRAWER = {
  dark: { background: 'rgb(35 42 43 / 0.9)', border: 'var(--sanring-border)', blur: 16 },
  light: { background: 'rgb(255 255 255 / 0.92)', border: 'var(--sanring-border)', blur: 16 },
} as const;

/**
 * 疆域配色：同一政權一生只用一個色（跨年份穩定），曾經相鄰的政權必須相容。
 * adjacency：在任何共存年份有共同邊界（或距離 < 緩衝值）的政權配對，預先計算。
 * 不讓繼承者沿用前身的色（避免暗示正統；對應 PRD §6 方案 D 中立原則）。
 */
export function assignTerritoryColors(
  regimeIds: readonly string[],
  adjacency: ReadonlyMap<string, ReadonlySet<string>>,
  previous: ReadonlyMap<string, number> = new Map(),
): Map<string, number> {
  const N = TERRITORY_COMPAT.length;
  const result = new Map<string, number>();
  const hash = (s: string) => {
    let h = 2166136261;
    for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
    return (h >>> 0) % N;
  };
  const neighbors = (id: string) => adjacency.get(id) ?? new Set<string>();
  const ok = (c: number, id: string) =>
    [...neighbors(id)].every((n) => !result.has(n) || ((TERRITORY_COMPAT[c] >> result.get(n)!) & 1) === 1);
  // DSatur：先處理「已上色鄰居最多」→「鄰居最多」的政權
  const pending = new Set(regimeIds);
  while (pending.size) {
    let pick = '';
    let best = [-1, -1];
    for (const id of pending) {
      const sat = new Set([...neighbors(id)].filter((n) => result.has(n)).map((n) => result.get(n))).size;
      const deg = neighbors(id).size;
      if (sat > best[0] || (sat === best[0] && deg > best[1])) { best = [sat, deg]; pick = id; }
    }
    const prefer = [previous.get(pick), hash(pick)].filter((c): c is number => c !== undefined);
    const candidates = [...prefer, ...Array.from({ length: N }, (_, k) => (hash(pick) + k) % N)];
    // 找不到完全相容的色時（極少見），退而求其次：與最少鄰居衝突的色
    const chosen =
      candidates.find((c) => ok(c, pick)) ??
      candidates.reduce((a, c) => {
        const bad = (x: number) => [...neighbors(pick)].filter((n) => result.has(n) && !((TERRITORY_COMPAT[x] >> result.get(n)!) & 1)).length;
        return bad(c) < bad(a) ? c : a;
      });
    result.set(pick, chosen);
    pending.delete(pick);
  }
  return result;
}
```

CSS 端只需要 §1.1 的三行覆寫和 §1.2 的字型；地圖專用值不需要寫成 CSS 變數。

---

## 9. 決策紀錄（2026-10-28）

以下由 Tai 於 2026-10-28 拍板（本次仍為唯讀，未改動任何 repo）。

| # | 議題 | 決定 |
|---|---|---|
| D1 | 深淺色兩套值 | **接受**。深色、淺色兩套值放在同一個常數檔，不建 token pipeline，也不做 Figma 同步 |
| D2 | `app/` 前置套件 | **安裝 Tailwind v4 和 MapLibre GL JS**。由另一個 agent 執行，本規格只記錄 |
| D3 | 毛玻璃抽屜不透明度 | **核准** 深色 0.90／淺色 0.92（取代 notes §八的 0.75） |
| D4 | 常數檔名稱 | **核准** `map-colors.ts`（建議路徑 `app/src/app/map/map-colors.ts`），取代 PRD 舉例的 `neutral-map-colors.ts` |
| D5 | 政權終止殘影 | `GHOST_YEARS = 10`，10 年內線性淡出 |
| D6 | 政權色號 | 前端計算＋快取，**不寫入資料庫**，不改 schema |
| D7 | High-contrast 地圖 | Phase 1 不做，保留為之後的無障礙選項（屆時：填色 0.45、邊界 2px、斜線線寬 2.5px） |
| D8 | 事件紅點 | 保留 `error-50`／`error-60` 紅點，定位為**事件語意色**，不是對政權的價值判斷 |
| D9 | 「依史觀主線上色」模式 | 做成選用模式，**預設關閉** |
| D10 | Sanring 上游問題 | 現在**不回報**；先用 §1.1 的 app 層覆寫處理 |
| D11 | Stitch 提示語言 | 維持**中文**版（§7） |

### 9.1 PRD 待回填項目

這些項目要回填到 `.claude/prds/world-line.md`（本次未改檔，由後續流程處理）：

1. **§8 UI 元件庫**：「既有 UI 元件庫（待選型）」改為 **Sanring UI**（Angular 22、Tailwind v4、`@angular/aria`，主題用 slate preset，預設深色並支援淺色）。notes 第 313 行的「Radix/shadcn」開放問題也一併結案。
2. **§5 深色模式升級條件已觸發**：PRD 原文是「待深色模式……出現再升級」。現在已經有深色模式，處理方式是**在單一常數檔內放深淺兩套值，仍然不建 token pipeline**（D1）。
3. **毛玻璃不透明度**：§8 和 notes §八的 `rgba(20,20,25,0.75)` 改成深色 `rgb(35 42 43 / .90)`、淺色 `rgb(255 255 255 / .92)`，理由是原值沒過 WCAG AA（見 §3.7）。
4. **常數檔名稱**：§5「斜線網底配色」列的檔名從 `neutral-map-colors.ts` 改為 `map-colors.ts`（D4）。
5. （附帶）M3 前置工作加入「`app/` 安裝 Tailwind v4 和 MapLibre GL JS」（D2）。

### 9.2 仍未決定

目前沒有。之後如果要做 High-contrast 地圖（D7）或向 Sanring 上游回報（D10），再重新評估。

## 附錄 A：完整對比明細（260 組）

| 模式 | 配對 | 前景 | 背景 | 對比 | 門檻 | 類型 | 結果 |
|---|---|---|---|---|---|---|---|
| dark | foreground / background | `#edf1f2` | `#202424` | 13.79:1 | 4.5:1 | text | ✅ |
| dark | muted / background | `#b4c3c6` | `#202424` | 8.63:1 | 4.5:1 | text | ✅ |
| dark | muted / surface | `#b4c3c6` | `#232a2b` | 8.04:1 | 4.5:1 | text | ✅ |
| dark | foreground / elevated | `#edf1f2` | `#2b3334` | 11.36:1 | 4.5:1 | text | ✅ |
| dark | border-strong / background | `#818e91` | `#202424` | 4.64:1 | 3:1 | ui | ✅ |
| dark | control / background (playhead, primary btn) | `#edf1f2` | `#202424` | 13.79:1 | 3:1 | ui | ✅ |
| dark | control-foreground / control | `#202424` | `#edf1f2` | 13.79:1 | 4.5:1 | text | ✅ |
| dark | primary-fg / primary (slate 50) | `#ffffff` | `#64748b` | 4.76:1 | 4.5:1 | text | ✅ |
| dark | active / background（選取底色，非唯一指示） | `#1e293b` | `#202424` | 1.07:1 | 3:1 | advisory | ⚠️ 以指示條補足 |
| dark | 選取指示條 control / active | `#edf1f2` | `#1e293b` | 12.86:1 | 3:1 | ui | ✅ |
| dark | coastline / water | `#606b6d` | `#151b1c` | 3.17:1 | 3:1 | graphic | ✅ |
| dark | coastline / land | `#606b6d` | `#2a3132` | 2.41:1 | 1.0:1 | info | ✅ |
| dark | T01 stroke / land | `#feb8c1` | `#2a3132` | 8.11:1 | 3:1 | graphic | ✅ |
| dark | T01 label / fill | `#edf1f2` | `#746064` | 5.13:1 | 4.5:1 | text | ✅ |
| dark | T01 ghost label / ghost fill | `#b4c3c6` | `#434143` | 5.57:1 | 4.5:1 | text | ✅ |
| dark | T01 era band label / band tint | `#edf1f2` | `#705c60` | 5.45:1 | 4.5:1 | text | ✅ |
| dark | T01 era band stripe / timeline surface | `#feb8c1` | `#232a2b` | 8.93:1 | 3:1 | graphic | ✅ |
| dark | T01 focus ring / fill | `#edf1f2` | `#746064` | 5.13:1 | 3:1 | graphic | ✅ |
| dark | T02 stroke / land | `#5ce7df` | `#2a3132` | 8.81:1 | 3:1 | graphic | ✅ |
| dark | T02 label / fill | `#edf1f2` | `#3b716f` | 4.89:1 | 4.5:1 | text | ✅ |
| dark | T02 ghost label / ghost fill | `#b4c3c6` | `#304747` | 5.46:1 | 4.5:1 | text | ✅ |
| dark | T02 era band label / band tint | `#edf1f2` | `#376c6a` | 5.25:1 | 4.5:1 | text | ✅ |
| dark | T02 era band stripe / timeline surface | `#5ce7df` | `#232a2b` | 9.70:1 | 3:1 | graphic | ✅ |
| dark | T02 focus ring / fill | `#edf1f2` | `#3b716f` | 4.89:1 | 3:1 | graphic | ✅ |
| dark | T03 stroke / land | `#e0d06e` | `#2a3132` | 8.47:1 | 3:1 | graphic | ✅ |
| dark | T03 label / fill | `#edf1f2` | `#6a6947` | 4.96:1 | 4.5:1 | text | ✅ |
| dark | T03 ghost label / ghost fill | `#b4c3c6` | `#404439` | 5.50:1 | 4.5:1 | text | ✅ |
| dark | T03 era band label / band tint | `#edf1f2` | `#656442` | 5.34:1 | 4.5:1 | text | ✅ |
| dark | T03 era band stripe / timeline surface | `#e0d06e` | `#232a2b` | 9.33:1 | 3:1 | graphic | ✅ |
| dark | T03 focus ring / fill | `#edf1f2` | `#6a6947` | 4.96:1 | 3:1 | graphic | ✅ |
| dark | T04 stroke / land | `#c4c9fe` | `#2a3132` | 8.29:1 | 3:1 | graphic | ✅ |
| dark | T04 label / fill | `#edf1f2` | `#606679` | 5.03:1 | 4.5:1 | text | ✅ |
| dark | T04 ghost label / ghost fill | `#b4c3c6` | `#3c434a` | 5.52:1 | 4.5:1 | text | ✅ |
| dark | T04 era band label / band tint | `#edf1f2` | `#5b6275` | 5.35:1 | 4.5:1 | text | ✅ |
| dark | T04 era band stripe / timeline surface | `#c4c9fe` | `#232a2b` | 9.14:1 | 3:1 | graphic | ✅ |
| dark | T04 focus ring / fill | `#edf1f2` | `#606679` | 5.03:1 | 3:1 | graphic | ✅ |
| dark | T05 stroke / land | `#febe92` | `#2a3132` | 8.20:1 | 3:1 | graphic | ✅ |
| dark | T05 label / fill | `#edf1f2` | `#746254` | 5.10:1 | 4.5:1 | text | ✅ |
| dark | T05 ghost label / ghost fill | `#b4c3c6` | `#43423e` | 5.54:1 | 4.5:1 | text | ✅ |
| dark | T05 era band label / band tint | `#edf1f2` | `#705e4f` | 5.43:1 | 4.5:1 | text | ✅ |
| dark | T05 era band stripe / timeline surface | `#febe92` | `#232a2b` | 9.04:1 | 3:1 | graphic | ✅ |
| dark | T05 focus ring / fill | `#edf1f2` | `#746254` | 5.10:1 | 3:1 | graphic | ✅ |
| dark | T06 stroke / land | `#95d7fe` | `#2a3132` | 8.48:1 | 3:1 | graphic | ✅ |
| dark | T06 label / fill | `#edf1f2` | `#4f6b79` | 4.97:1 | 4.5:1 | text | ✅ |
| dark | T06 ghost label / ghost fill | `#b4c3c6` | `#37454a` | 5.47:1 | 4.5:1 | text | ✅ |
| dark | T06 era band label / band tint | `#edf1f2` | `#4b6775` | 5.28:1 | 4.5:1 | text | ✅ |
| dark | T06 era band stripe / timeline surface | `#95d7fe` | `#232a2b` | 9.34:1 | 3:1 | graphic | ✅ |
| dark | T06 focus ring / fill | `#edf1f2` | `#4f6b79` | 4.97:1 | 3:1 | graphic | ✅ |
| dark | T07 stroke / land | `#9be39d` | `#2a3132` | 8.76:1 | 3:1 | graphic | ✅ |
| dark | T07 label / fill | `#edf1f2` | `#526f57` | 4.90:1 | 4.5:1 | text | ✅ |
| dark | T07 ghost label / ghost fill | `#b4c3c6` | `#38463f` | 5.46:1 | 4.5:1 | text | ✅ |
| dark | T07 era band label / band tint | `#edf1f2` | `#4d6b53` | 5.21:1 | 4.5:1 | text | ✅ |
| dark | T07 era band stripe / timeline surface | `#9be39d` | `#232a2b` | 9.65:1 | 3:1 | graphic | ✅ |
| dark | T07 focus ring / fill | `#edf1f2` | `#526f57` | 4.90:1 | 3:1 | graphic | ✅ |
| dark | T08 stroke / land | `#f6b2f9` | `#2a3132` | 7.99:1 | 3:1 | graphic | ✅ |
| dark | T08 label / fill | `#edf1f2` | `#715e78` | 5.17:1 | 4.5:1 | text | ✅ |
| dark | T08 ghost label / ghost fill | `#b4c3c6` | `#42404a` | 5.60:1 | 4.5:1 | text | ✅ |
| dark | T08 era band label / band tint | `#edf1f2` | `#6d5a73` | 5.50:1 | 4.5:1 | text | ✅ |
| dark | T08 era band stripe / timeline surface | `#f6b2f9` | `#232a2b` | 8.80:1 | 3:1 | graphic | ✅ |
| dark | T08 focus ring / fill | `#edf1f2` | `#715e78` | 5.17:1 | 3:1 | graphic | ✅ |
| dark | T09 stroke / land | `#d87b68` | `#2a3132` | 4.39:1 | 3:1 | graphic | ✅ |
| dark | T09 label / fill | `#edf1f2` | `#674b45` | 6.92:1 | 4.5:1 | text | ✅ |
| dark | T09 ghost label / ghost fill | `#b4c3c6` | `#3f3a38` | 6.17:1 | 4.5:1 | text | ✅ |
| dark | T09 era band label / band tint | `#edf1f2` | `#624640` | 7.48:1 | 4.5:1 | text | ✅ |
| dark | T09 era band stripe / timeline surface | `#d87b68` | `#232a2b` | 4.84:1 | 3:1 | graphic | ✅ |
| dark | T09 focus ring / fill | `#edf1f2` | `#674b45` | 6.92:1 | 3:1 | graphic | ✅ |
| dark | T10 stroke / land | `#06abc3` | `#2a3132` | 4.81:1 | 3:1 | graphic | ✅ |
| dark | T10 label / fill | `#edf1f2` | `#1d5c65` | 6.66:1 | 4.5:1 | text | ✅ |
| dark | T10 ghost label / ghost fill | `#b4c3c6` | `#264043` | 6.10:1 | 4.5:1 | text | ✅ |
| dark | T10 era band label / band tint | `#edf1f2` | `#195760` | 7.18:1 | 4.5:1 | text | ✅ |
| dark | T10 era band stripe / timeline surface | `#06abc3` | `#232a2b` | 5.30:1 | 3:1 | graphic | ✅ |
| dark | T10 focus ring / fill | `#edf1f2` | `#1d5c65` | 6.66:1 | 3:1 | graphic | ✅ |
| dark | T11 stroke / land | `#8ba44a` | `#2a3132` | 4.74:1 | 3:1 | graphic | ✅ |
| dark | T11 label / fill | `#edf1f2` | `#4c593a` | 6.60:1 | 4.5:1 | text | ✅ |
| dark | T11 ghost label / ghost fill | `#b4c3c6` | `#363f35` | 6.02:1 | 4.5:1 | text | ✅ |
| dark | T11 era band label / band tint | `#edf1f2` | `#475536` | 7.05:1 | 4.5:1 | text | ✅ |
| dark | T11 era band stripe / timeline surface | `#8ba44a` | `#232a2b` | 5.22:1 | 3:1 | graphic | ✅ |
| dark | T11 focus ring / fill | `#edf1f2` | `#4c593a` | 6.60:1 | 3:1 | graphic | ✅ |
| dark | T12 stroke / land | `#a785d5` | `#2a3132` | 4.39:1 | 3:1 | graphic | ✅ |
| dark | T12 label / fill | `#edf1f2` | `#564e6b` | 6.84:1 | 4.5:1 | text | ✅ |
| dark | T12 ghost label / ghost fill | `#b4c3c6` | `#393b46` | 6.12:1 | 4.5:1 | text | ✅ |
| dark | T12 era band label / band tint | `#edf1f2` | `#514a66` | 7.32:1 | 4.5:1 | text | ✅ |
| dark | T12 era band stripe / timeline surface | `#a785d5` | `#232a2b` | 4.84:1 | 3:1 | graphic | ✅ |
| dark | T12 focus ring / fill | `#edf1f2` | `#564e6b` | 6.84:1 | 3:1 | graphic | ✅ |
| dark | T13 stroke / land | `#c18e35` | `#2a3132` | 4.54:1 | 3:1 | graphic | ✅ |
| dark | T13 label / fill | `#edf1f2` | `#5f5233` | 6.74:1 | 4.5:1 | text | ✅ |
| dark | T13 ghost label / ghost fill | `#b4c3c6` | `#3c3c32` | 6.14:1 | 4.5:1 | text | ✅ |
| dark | T13 era band label / band tint | `#edf1f2` | `#5a4d2f` | 7.28:1 | 4.5:1 | text | ✅ |
| dark | T13 era band stripe / timeline surface | `#c18e35` | `#232a2b` | 5.00:1 | 3:1 | graphic | ✅ |
| dark | T13 focus ring / fill | `#edf1f2` | `#5f5233` | 6.74:1 | 3:1 | graphic | ✅ |
| dark | T14 stroke / land | `#689ae2` | `#2a3132` | 4.61:1 | 3:1 | graphic | ✅ |
| dark | T14 label / fill | `#edf1f2` | `#405670` | 6.63:1 | 4.5:1 | text | ✅ |
| dark | T14 ghost label / ghost fill | `#b4c3c6` | `#313e47` | 6.05:1 | 4.5:1 | text | ✅ |
| dark | T14 era band label / band tint | `#edf1f2` | `#3b516b` | 7.17:1 | 4.5:1 | text | ✅ |
| dark | T14 era band stripe / timeline surface | `#689ae2` | `#232a2b` | 5.08:1 | 3:1 | graphic | ✅ |
| dark | T14 focus ring / fill | `#edf1f2` | `#405670` | 6.63:1 | 3:1 | graphic | ✅ |
| dark | T15 stroke / land | `#38b089` | `#2a3132` | 4.89:1 | 3:1 | graphic | ✅ |
| dark | T15 label / fill | `#edf1f2` | `#2f5d50` | 6.59:1 | 4.5:1 | text | ✅ |
| dark | T15 ghost label / ghost fill | `#b4c3c6` | `#2c403c` | 6.07:1 | 4.5:1 | text | ✅ |
| dark | T15 era band label / band tint | `#edf1f2` | `#2a594c` | 7.02:1 | 4.5:1 | text | ✅ |
| dark | T15 era band stripe / timeline surface | `#38b089` | `#232a2b` | 5.38:1 | 3:1 | graphic | ✅ |
| dark | T15 focus ring / fill | `#edf1f2` | `#2f5d50` | 6.59:1 | 3:1 | graphic | ✅ |
| dark | T16 stroke / land | `#ce78a6` | `#2a3132` | 4.33:1 | 3:1 | graphic | ✅ |
| dark | T16 label / fill | `#edf1f2` | `#634a5b` | 6.94:1 | 4.5:1 | text | ✅ |
| dark | T16 ghost label / ghost fill | `#b4c3c6` | `#3e3a40` | 6.14:1 | 4.5:1 | text | ✅ |
| dark | T16 era band label / band tint | `#edf1f2` | `#5f4556` | 7.47:1 | 4.5:1 | text | ✅ |
| dark | T16 era band stripe / timeline surface | `#ce78a6` | `#232a2b` | 4.77:1 | 3:1 | graphic | ✅ |
| dark | T16 focus ring / fill | `#edf1f2` | `#634a5b` | 6.94:1 | 3:1 | graphic | ✅ |
| dark | label / land (no fill) | `#edf1f2` | `#2a3132` | 11.66:1 | 4.5:1 | text | ✅ |
| dark | label / water | `#edf1f2` | `#151b1c` | 15.32:1 | 4.5:1 | text | ✅ |
| dark | label muted / land | `#b4c3c6` | `#2a3132` | 7.30:1 | 4.5:1 | text | ✅ |
| dark | hatch neutral / land | `#c8d4d6` | `#2a3132` | 8.74:1 | 3:1 | graphic | ✅ |
| dark | disputed outline / land | `#c8d4d6` | `#2a3132` | 8.74:1 | 3:1 | graphic | ✅ |
| dark | destroyed outline / land | `#a1b2b5` | `#2a3132` | 6.03:1 | 3:1 | graphic | ✅ |
| dark | event marker / land | `#e57373` | `#2a3132` | 4.44:1 | 3:1 | graphic | ✅ |
| dark | event marker / water | `#e57373` | `#151b1c` | 5.83:1 | 3:1 | graphic | ✅ |
| dark | timeline track / panel(elevated) | `#78858a` | `#2b3334` | 3.40:1 | 3:1 | ui | ✅ |
| dark | timeline major tick / surface | `#a1b2b5` | `#232a2b` | 6.64:1 | 3:1 | graphic | ✅ |
| dark | timeline label / surface | `#b4c3c6` | `#232a2b` | 8.04:1 | 4.5:1 | text | ✅ |
| dark | timeline playhead / surface | `#edf1f2` | `#232a2b` | 12.85:1 | 3:1 | ui | ✅ |
| dark | timeline playhead / track | `#edf1f2` | `#78858a` | 3.34:1 | 3:1 | ui | ✅ |
| dark | keyframe pin / surface | `#fce08f` | `#232a2b` | 11.27:1 | 3:1 | graphic | ✅ |
| dark | focus range / surface | `#64b5f6` | `#232a2b` | 6.60:1 | 3:1 | graphic | ✅ |
| dark | glass drawer text / glass over white | `#edf1f2` | `#393f40` | 9.43:1 | 4.5:1 | text | ✅ |
| dark | glass drawer muted / glass over white | `#b4c3c6` | `#393f40` | 5.90:1 | 4.5:1 | text | ✅ |
| dark | glass drawer text / glass over black | `#edf1f2` | `#202627` | 13.50:1 | 4.5:1 | text | ✅ |
| dark | glass drawer muted / glass over black | `#b4c3c6` | `#202627` | 8.45:1 | 4.5:1 | text | ✅ |
| dark | glass drawer text / glass over brightest stroke | `#edf1f2` | `#293d3d` | 10.09:1 | 4.5:1 | text | ✅ |
| dark | glass drawer muted / glass over brightest stroke | `#b4c3c6` | `#293d3d` | 6.32:1 | 4.5:1 | text | ✅ |
| dark | popover muted / elevated | `#b4c3c6` | `#2b3334` | 7.11:1 | 4.5:1 | text | ✅ |
| light | foreground / background | `#202424` | `#f6f8f8` | 14.71:1 | 4.5:1 | text | ✅ |
| light | muted / background | `#606b6d` | `#f6f8f8` | 5.16:1 | 4.5:1 | text | ✅ |
| light | muted / surface | `#606b6d` | `#ffffff` | 5.50:1 | 4.5:1 | text | ✅ |
| light | foreground / elevated | `#202424` | `#ffffff` | 15.68:1 | 4.5:1 | text | ✅ |
| light | border-strong / background | `#818e91` | `#f6f8f8` | 3.17:1 | 3:1 | ui | ✅ |
| light | control / background (playhead, primary btn) | `#202424` | `#f6f8f8` | 14.71:1 | 3:1 | ui | ✅ |
| light | control-foreground / control | `#ffffff` | `#202424` | 15.68:1 | 4.5:1 | text | ✅ |
| light | primary-fg / primary (slate 50) | `#ffffff` | `#64748b` | 4.76:1 | 4.5:1 | text | ✅ |
| light | active / background（選取底色，非唯一指示） | `#d8eef1` | `#f6f8f8` | 1.13:1 | 3:1 | advisory | ⚠️ 以指示條補足 |
| light | 選取指示條 control / active | `#202424` | `#d8eef1` | 13.01:1 | 3:1 | ui | ✅ |
| light | coastline / water | `#606b6d` | `#d5e1e4` | 4.11:1 | 3:1 | graphic | ✅ |
| light | coastline / land | `#606b6d` | `#f4f5f1` | 5.02:1 | 1.0:1 | info | ✅ |
| light | T01 stroke / land | `#913147` | `#f4f5f1` | 7.01:1 | 3:1 | graphic | ✅ |
| light | T01 label / fill | `#202424` | `#d8bec1` | 9.00:1 | 4.5:1 | text | ✅ |
| light | T01 ghost label / ghost fill | `#404748` | `#eae1e0` | 7.39:1 | 4.5:1 | text | ✅ |
| light | T01 era band label / band tint | `#202424` | `#e7d2d7` | 10.90:1 | 4.5:1 | text | ✅ |
| light | T01 era band stripe / timeline surface | `#913147` | `#ffffff` | 7.68:1 | 3:1 | graphic | ✅ |
| light | T01 focus ring / fill | `#202424` | `#d8bec1` | 9.00:1 | 3:1 | graphic | ✅ |
| light | T02 stroke / land | `#056662` | `#f4f5f1` | 6.22:1 | 3:1 | graphic | ✅ |
| light | T02 label / fill | `#202424` | `#b1cdc9` | 9.29:1 | 4.5:1 | text | ✅ |
| light | T02 ghost label / ghost fill | `#404748` | `#dce7e3` | 7.49:1 | 4.5:1 | text | ✅ |
| light | T02 era band label / band tint | `#202424` | `#c8dddc` | 11.07:1 | 4.5:1 | text | ✅ |
| light | T02 era band stripe / timeline surface | `#056662` | `#ffffff` | 6.81:1 | 3:1 | graphic | ✅ |
| light | T02 focus ring / fill | `#202424` | `#b1cdc9` | 9.29:1 | 3:1 | graphic | ✅ |
| light | T03 stroke / land | `#655904` | `#f4f5f1` | 6.43:1 | 3:1 | graphic | ✅ |
| light | T03 label / fill | `#202424` | `#ccc9af` | 9.36:1 | 4.5:1 | text | ✅ |
| light | T03 ghost label / ghost fill | `#404748` | `#e6e5d9` | 7.49:1 | 4.5:1 | text | ✅ |
| light | T03 era band label / band tint | `#202424` | `#dddac8` | 11.15:1 | 4.5:1 | text | ✅ |
| light | T03 era band stripe / timeline surface | `#655904` | `#ffffff` | 7.04:1 | 3:1 | graphic | ✅ |
| light | T03 focus ring / fill | `#202424` | `#ccc9af` | 9.36:1 | 3:1 | graphic | ✅ |
| light | T04 stroke / land | `#4c4c9e` | `#f4f5f1` | 6.77:1 | 3:1 | graphic | ✅ |
| light | T04 label / fill | `#202424` | `#c5c6da` | 9.31:1 | 4.5:1 | text | ✅ |
| light | T04 ghost label / ghost fill | `#404748` | `#e3e4e9` | 7.47:1 | 4.5:1 | text | ✅ |
| light | T04 era band label / band tint | `#202424` | `#d8d8ea` | 11.15:1 | 4.5:1 | text | ✅ |
| light | T04 era band stripe / timeline surface | `#4c4c9e` | `#ffffff` | 7.41:1 | 3:1 | graphic | ✅ |
| light | T04 focus ring / fill | `#202424` | `#c5c6da` | 9.31:1 | 3:1 | graphic | ✅ |
| light | T05 stroke / land | `#874300` | `#f4f5f1` | 6.77:1 | 3:1 | graphic | ✅ |
| light | T05 label / fill | `#202424` | `#d5c3ae` | 9.14:1 | 4.5:1 | text | ✅ |
| light | T05 ghost label / ghost fill | `#404748` | `#e9e3d9` | 7.44:1 | 4.5:1 | text | ✅ |
| light | T05 era band label / band tint | `#202424` | `#e5d6c7` | 11.03:1 | 4.5:1 | text | ✅ |
| light | T05 era band stripe / timeline surface | `#874300` | `#ffffff` | 7.41:1 | 3:1 | graphic | ✅ |
| light | T05 focus ring / fill | `#202424` | `#d5c3ae` | 9.14:1 | 3:1 | graphic | ✅ |
| light | T06 stroke / land | `#055f86` | `#f4f5f1` | 6.42:1 | 3:1 | graphic | ✅ |
| light | T06 label / fill | `#202424` | `#b1cbd3` | 9.22:1 | 4.5:1 | text | ✅ |
| light | T06 ghost label / ghost fill | `#404748` | `#dce6e6` | 7.46:1 | 4.5:1 | text | ✅ |
| light | T06 era band label / band tint | `#202424` | `#c8dce4` | 11.06:1 | 4.5:1 | text | ✅ |
| light | T06 era band stripe / timeline surface | `#055f86` | `#ffffff` | 7.03:1 | 3:1 | graphic | ✅ |
| light | T06 focus ring / fill | `#202424` | `#b1cbd3` | 9.22:1 | 3:1 | graphic | ✅ |
| light | T07 stroke / land | `#186a23` | `#f4f5f1` | 6.14:1 | 3:1 | graphic | ✅ |
| light | T07 label / fill | `#202424` | `#b6ceb7` | 9.33:1 | 4.5:1 | text | ✅ |
| light | T07 ghost label / ghost fill | `#404748` | `#dee7dc` | 7.49:1 | 4.5:1 | text | ✅ |
| light | T07 era band label / band tint | `#202424` | `#ccdecf` | 11.14:1 | 4.5:1 | text | ✅ |
| light | T07 era band stripe / timeline surface | `#186a23` | `#ffffff` | 6.72:1 | 3:1 | graphic | ✅ |
| light | T07 focus ring / fill | `#202424` | `#b6ceb7` | 9.33:1 | 3:1 | graphic | ✅ |
| light | T08 stroke / land | `#7b3a7f` | `#f4f5f1` | 6.96:1 | 3:1 | graphic | ✅ |
| light | T08 label / fill | `#202424` | `#d2c1d1` | 9.18:1 | 4.5:1 | text | ✅ |
| light | T08 ghost label / ghost fill | `#404748` | `#e8e2e6` | 7.43:1 | 4.5:1 | text | ✅ |
| light | T08 era band label / band tint | `#202424` | `#e2d4e3` | 11.02:1 | 4.5:1 | text | ✅ |
| light | T08 era band stripe / timeline surface | `#7b3a7f` | `#ffffff` | 7.63:1 | 3:1 | graphic | ✅ |
| light | T08 focus ring / fill | `#202424` | `#d2c1d1` | 9.18:1 | 3:1 | graphic | ✅ |
| light | T09 stroke / land | `#c86552` | `#f4f5f1` | 3.53:1 | 3:1 | graphic | ✅ |
| light | T09 label / fill | `#202424` | `#e8cdc4` | 10.42:1 | 4.5:1 | text | ✅ |
| light | T09 ghost label / ghost fill | `#404748` | `#f0e7e1` | 7.78:1 | 4.5:1 | text | ✅ |
| light | T09 era band label / band tint | `#202424` | `#f3ddd9` | 12.06:1 | 4.5:1 | text | ✅ |
| light | T09 era band stripe / timeline surface | `#c86552` | `#ffffff` | 3.86:1 | 3:1 | graphic | ✅ |
| light | T09 focus ring / fill | `#202424` | `#e8cdc4` | 10.42:1 | 3:1 | graphic | ✅ |
| light | T10 stroke / land | `#0297ac` | `#f4f5f1` | 3.18:1 | 3:1 | graphic | ✅ |
| light | T10 label / fill | `#202424` | `#b0dbde` | 10.48:1 | 4.5:1 | text | ✅ |
| light | T10 ghost label / ghost fill | `#404748` | `#dcecea` | 7.79:1 | 4.5:1 | text | ✅ |
| light | T10 era band label / band tint | `#202424` | `#c7e8ed` | 12.09:1 | 4.5:1 | text | ✅ |
| light | T10 era band stripe / timeline surface | `#0297ac` | `#ffffff` | 3.49:1 | 3:1 | graphic | ✅ |
| light | T10 focus ring / fill | `#202424` | `#b0dbde` | 10.48:1 | 3:1 | graphic | ✅ |
| light | T11 stroke / land | `#78922c` | `#f4f5f1` | 3.23:1 | 3:1 | graphic | ✅ |
| light | T11 label / fill | `#202424` | `#d1d9ba` | 10.71:1 | 4.5:1 | text | ✅ |
| light | T11 ghost label / ghost fill | `#404748` | `#e8ebdd` | 7.84:1 | 4.5:1 | text | ✅ |
| light | T11 era band label / band tint | `#202424` | `#e1e7d1` | 12.36:1 | 4.5:1 | text | ✅ |
| light | T11 era band stripe / timeline surface | `#78922c` | `#ffffff` | 3.53:1 | 3:1 | graphic | ✅ |
| light | T11 focus ring / fill | `#202424` | `#d1d9ba` | 10.71:1 | 3:1 | graphic | ✅ |
| light | T12 stroke / land | `#9671c6` | `#f4f5f1` | 3.50:1 | 3:1 | graphic | ✅ |
| light | T12 label / fill | `#202424` | `#dad0e5` | 10.55:1 | 4.5:1 | text | ✅ |
| light | T12 ghost label / ghost fill | `#404748` | `#ebe8ed` | 7.82:1 | 4.5:1 | text | ✅ |
| light | T12 era band label / band tint | `#202424` | `#e8e0f2` | 12.23:1 | 4.5:1 | text | ✅ |
| light | T12 era band stripe / timeline surface | `#9671c6` | `#ffffff` | 3.84:1 | 3:1 | graphic | ✅ |
| light | T12 focus ring / fill | `#202424` | `#dad0e5` | 10.55:1 | 3:1 | graphic | ✅ |
| light | T13 stroke / land | `#b07a06` | `#f4f5f1` | 3.40:1 | 3:1 | graphic | ✅ |
| light | T13 label / fill | `#202424` | `#e1d3af` | 10.56:1 | 4.5:1 | text | ✅ |
| light | T13 ghost label / ghost fill | `#404748` | `#ede9da` | 7.80:1 | 4.5:1 | text | ✅ |
| light | T13 era band label / band tint | `#202424` | `#eee2c8` | 12.21:1 | 4.5:1 | text | ✅ |
| light | T13 era band stripe / timeline surface | `#b07a06` | `#ffffff` | 3.73:1 | 3:1 | graphic | ✅ |
| light | T13 focus ring / fill | `#202424` | `#e1d3af` | 10.56:1 | 3:1 | graphic | ✅ |
| light | T14 stroke / land | `#5187d3` | `#f4f5f1` | 3.33:1 | 3:1 | graphic | ✅ |
| light | T14 label / fill | `#202424` | `#c6d6e9` | 10.60:1 | 4.5:1 | text | ✅ |
| light | T14 ghost label / ghost fill | `#404748` | `#e4eaee` | 7.82:1 | 4.5:1 | text | ✅ |
| light | T14 era band label / band tint | `#202424` | `#d9e5f5` | 12.30:1 | 4.5:1 | text | ✅ |
| light | T14 era band stripe / timeline surface | `#5187d3` | `#ffffff` | 3.65:1 | 3:1 | graphic | ✅ |
| light | T14 focus ring / fill | `#202424` | `#c6d6e9` | 10.60:1 | 3:1 | graphic | ✅ |
| light | T15 stroke / land | `#029e77` | `#f4f5f1` | 3.11:1 | 3:1 | graphic | ✅ |
| light | T15 label / fill | `#202424` | `#b0ddcf` | 10.52:1 | 4.5:1 | text | ✅ |
| light | T15 ghost label / ghost fill | `#404748` | `#dcece5` | 7.76:1 | 4.5:1 | text | ✅ |
| light | T15 era band label / band tint | `#202424` | `#c7eae1` | 12.16:1 | 4.5:1 | text | ✅ |
| light | T15 era band stripe / timeline surface | `#029e77` | `#ffffff` | 3.41:1 | 3:1 | graphic | ✅ |
| light | T15 focus ring / fill | `#202424` | `#b0ddcf` | 10.52:1 | 3:1 | graphic | ✅ |
| light | T16 stroke / land | `#bd6395` | `#f4f5f1` | 3.56:1 | 3:1 | graphic | ✅ |
| light | T16 label / fill | `#202424` | `#e5ccd7` | 10.42:1 | 4.5:1 | text | ✅ |
| light | T16 ghost label / ghost fill | `#404748` | `#eee6e8` | 7.74:1 | 4.5:1 | text | ✅ |
| light | T16 era band label / band tint | `#202424` | `#f0dde8` | 12.11:1 | 4.5:1 | text | ✅ |
| light | T16 era band stripe / timeline surface | `#bd6395` | `#ffffff` | 3.90:1 | 3:1 | graphic | ✅ |
| light | T16 focus ring / fill | `#202424` | `#e5ccd7` | 10.42:1 | 3:1 | graphic | ✅ |
| light | label / land (no fill) | `#202424` | `#f4f5f1` | 14.32:1 | 4.5:1 | text | ✅ |
| light | label / water | `#202424` | `#d5e1e4` | 11.74:1 | 4.5:1 | text | ✅ |
| light | label muted / land | `#404748` | `#f4f5f1` | 8.67:1 | 4.5:1 | text | ✅ |
| light | hatch neutral / land | `#606b6d` | `#f4f5f1` | 5.02:1 | 3:1 | graphic | ✅ |
| light | disputed outline / land | `#404748` | `#f4f5f1` | 8.67:1 | 3:1 | graphic | ✅ |
| light | destroyed outline / land | `#606b6d` | `#f4f5f1` | 5.02:1 | 3:1 | graphic | ✅ |
| light | event marker / land | `#b75c5c` | `#f4f5f1` | 4.08:1 | 3:1 | graphic | ✅ |
| light | event marker / water | `#b75c5c` | `#d5e1e4` | 3.35:1 | 3:1 | graphic | ✅ |
| light | timeline track / panel(elevated) | `#818e91` | `#ffffff` | 3.38:1 | 3:1 | ui | ✅ |
| light | timeline major tick / surface | `#606b6d` | `#ffffff` | 5.50:1 | 3:1 | graphic | ✅ |
| light | timeline label / surface | `#606b6d` | `#ffffff` | 5.50:1 | 4.5:1 | text | ✅ |
| light | timeline playhead / surface | `#202424` | `#ffffff` | 15.68:1 | 3:1 | ui | ✅ |
| light | timeline playhead / track | `#202424` | `#818e91` | 4.64:1 | 3:1 | ui | ✅ |
| light | keyframe pin / surface | `#978656` | `#ffffff` | 3.58:1 | 3:1 | graphic | ✅ |
| light | focus range / surface | `#3c6d94` | `#ffffff` | 5.52:1 | 3:1 | graphic | ✅ |
| light | glass drawer text / glass over white | `#202424` | `#ffffff` | 15.68:1 | 4.5:1 | text | ✅ |
| light | glass drawer muted / glass over white | `#606b6d` | `#ffffff` | 5.50:1 | 4.5:1 | text | ✅ |
| light | glass drawer text / glass over black | `#202424` | `#ebebeb` | 13.15:1 | 4.5:1 | text | ✅ |
| light | glass drawer muted / glass over black | `#606b6d` | `#ebebeb` | 4.61:1 | 4.5:1 | text | ✅ |
| light | glass drawer text / glass over brightest stroke | `#202424` | `#ebf7f4` | 14.29:1 | 4.5:1 | text | ✅ |
| light | glass drawer muted / glass over brightest stroke | `#606b6d` | `#ebf7f4` | 5.01:1 | 4.5:1 | text | ✅ |
| light | popover muted / elevated | `#606b6d` | `#ffffff` | 5.50:1 | 4.5:1 | text | ✅ |

