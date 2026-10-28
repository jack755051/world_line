# World Line 二戰畫面設計（Google Stitch）

2026-10-28。設計稿只當版面參考，實作顏色、字型、圓角一律用 `--wl-*` token。設計系統是 `design/stitch/DESIGN.md`；頁面與四態的規格是 PRD §8（`.claude/prds/world-line-ww2.md`）。

## 為什麼是這 7 張

World Line 只有一個頁面（`/`），所有功能都是疊在地圖上的面板，沒有可以沿用的列表、表單或後台頁型，所以每種面板都要出稿。資料建置不做 UI（PRD §12 Q16），不出稿。

| # | 畫面 | 網址 | 畫面要包含 | 規則 |
|---|---|---|---|---|
| W1 | 主地圖・實際控制 | `/?date=1940-07-15` | 頂部列、法國德佔區＋維琪區、義大利區為資料缺、圖例展開、多戰區時間軸 | R2、R6、R9、§9 |
| W2 | 推估過渡與資料缺 | `/?date=1941-08-20` | 「推估過渡」chip 的 popover、中國戰區資料缺 popover | §9、R9 |
| W3 | 主權檢視＋地區主權詳情 | `/?date=1940-07-15&axis=sovereignty` | 並存主張、承認方／不承認方、「系統不裁判」文案 | R6、I3、I5 |
| W4 | 政權聚焦面板 | `/?date=1940-07-15&focus=etat-francais` | 名稱、狀態、狀態時間條、傳承、控制、主張、互動、紀年 | R3、§4、§6 |
| W5 | 事件詳情＋爭議點 | `/?date=1939-09-01&event=…` | 「第二次世界大戰」起點三張觀點卡並列 | R8、§9 |
| W6 | 來源 popover | 疊在 W1 上 | 圖集、出版者、圖號、授權 | I6、R7 |
| W7 | 全域與錯誤狀態 | — | 首次載入、地圖錯誤、無資料日期、API 離線、找不到頁面 | §8.2、§8.11 |

**範例資料**：法國 1940 案例取自 `docs/research/ww2-data-sources.md` §4（停戰協定、Paris Musées 分界線地圖 inv. 2015.3.1.230）。快照日期、東線日期在 W2 只是示意，實際由資料決定。爭議點只用「二戰起點」三種日期（PRD §8.8 特例），不在設計稿裡編造傷亡數字。

## 給 Stitch 的 prompt

### 先匯入設計系統

1. 開新的 Stitch 專案「World Line」，不跟 sanring 專案混用。
2. 匯入 `design/stitch/DESIGN.md`，在主題設定確認：淺色、字型 Noto Serif TC／Noto Sans TC、主色 `#b23a26`。
3. 先產生下方的「校正卡」，確認紙色背景、朱紅只出現在按鈕與選取狀態、襯線標題、陣營色塊都對，再產生 W1–W7。
4. 匯出後檢查：出現 `#bec2ff`（淡紫）、Plus Jakarta Sans、Inter、深色背景，代表 Stitch 又自己補值了，回到第 2 步。

### 共用條件（已包含在下面每一段裡，這裡只是列出來方便看）

1. 產品：二戰歷史地圖集，單一使用者拖動時間軸看全球政權的控制與主權，每筆資料可追到史料。
2. 照 DESIGN.md。
3. 介面文字繁體中文，引號內的中文照抄。
4. 1440px 桌機，單頁，地圖滿版，面板浮在地圖上。
5. 只有淺色，紙色背景 `#f4efe4`、面板 `#faf7f0`、墨色文字 `#2a2620`。
6. 朱紅 `#b23a26` 只用在主要按鈕、選取中的切換、時間軸指針、focus ring；不可用在地圖、錯誤訊息或大面積背景。錯誤用 `#8c1d40` 加圖示。
7. 標題 Noto Serif TC、內文 Noto Sans TC；字級只有 30／22／17／15／14／12；日期與數字用等寬數字；圓角 4px（面板 6px）；1px 細線框、幾乎沒有陰影、Lucide 線條圖示。
8. 頂部列只有：「World Line」、日期、紀年、推估提示 chip、「實際控制｜主權」、「中｜EN」、圖例開關。沒有側邊欄、頭像、搜尋、設定。
9. 不要加入下面沒描述的按鈕、分頁、統計、匯出或功能。

### 校正卡

```text
Design a single calibration card for "World Line", a historical atlas web app of the Second World War. Follow the attached DESIGN.md design system exactly. Light theme only: paper background #f4efe4, card #faf7f0, ink text #2a2620, 1px hairline borders #d9d0bd, almost no shadow. All UI text is Traditional Chinese (zh-Hant); use the exact Chinese labels given in quotes.

Show on one 1440px canvas, in rows:
1. Typography: 「1940年7月15日」 in 30px Noto Serif TC 600; 「法蘭西國」 22px serif; 「傳承關係」 17px serif; 「持續關係」 15px Noto Sans TC 600; body text 「1940年7月10日國民議會授權貝當，第三共和改制為法蘭西國。」 14px; caption 「昭和15年・民國29年」 12px in #6b6355.
2. Buttons: primary 「跳到最近有資料的日期」 vermilion #b23a26 fill with #fffaf2 text, 4px radius; secondary 「重試」 transparent with 1px #a39985 border and ink text. Segmented toggle 「實際控制｜主權」 with 「實際控制」 selected (vermilion fill) and 「中｜EN」 with 「中」 selected.
3. Badges: 「存續」 ink outline, 「流亡」 slate #34506b outline, 「被併吞」 #a8741c outline, 「已終止」 grey fill. Stamp 「史料快照」 in brass #8a6d2f text with 1px brass border. Chip 「推估過渡・2 個戰區」 with 1px dashed slate border.
4. Map swatches, each 80×56px with a label below: 「直接統治」 solid #6f8fb0; 「軍事佔領」 #c8964a at 60% with a darker 2px inner edge; 「傀儡代管」 solid #9c7fa3 with dotted border in #c8964a; 「不完全控制」 45° hatch lines in #b8743d on paper #ece4d2; 「交戰中」 alternating hatch #b8743d and #5f9a8f; 「推估過渡」 #6f8fb0 at 50% with dashed border; 「控制資料缺」 paper #ece4d2 with fine ink dots; 「依主權推定」 #6f8fb0 at 35% no border; 「戰線」 a 2.5px #3a2f28 line.
5. An alert: crimson #8c1d40 icon and text on #f3d9e0 background: 「地圖資料載入失敗」 with a 「重試」 secondary button.

Do not add anything else. No dark mode.
```

### W1. 主地圖・實際控制

```text
Design the main screen of "World Line", a historical GIS atlas of the Second World War where a single user drags a timeline to any day and sees every regime's actual control and sovereignty on one world map, each record traceable to a cited historical map. It must feel like a scholarly printed atlas, not a game or a dashboard.
Follow the attached DESIGN.md design system exactly. All UI text is Traditional Chinese (zh-Hant); use the exact Chinese labels given in quotes.
Desktop 1440×900, one page, full-bleed map with floating paper panels.
Light theme only: page #f4efe4, panels #faf7f0 with 1px #d9d0bd border and a barely visible shadow, ink text #2a2620, secondary text #6b6355.
Vermilion #b23a26 is used ONLY for the primary button, the selected toggle segment, the timeline handle and focus rings. Never use vermilion on the map or for errors. Errors use crimson #8c1d40 with an icon.
Headings Noto Serif TC, body Noto Sans TC. Sizes only 30/22/17/15/14/12px. Tabular figures. Radius 4px, panels 6px. 1px hairlines, Lucide line icons.
Top bar contains exactly: 「World Line」, the date, the era line, the evidence chip, the 「實際控制｜主權」 toggle, the 「中｜EN」 toggle, a legend toggle icon. No sidebar, no avatar, no search, no settings.
Do not add buttons, tabs, stats, export actions or features that are not described below.

Screen: the world map on 1940-07-15, actual-control view.

Top bar (56px, panel color, bottom hairline), left to right:
- 「World Line」 in 17px serif.
- Date block: 「1940年7月15日」 30px serif; below it 12px caption 「昭和15年・民國29年」.
- Stamp 「史料快照」 (brass #8a6d2f text, 1px brass border).
- Right side: segmented toggle 「實際控制｜主權」 with 「實際控制」 selected; segmented toggle 「中｜EN」 with 「中」 selected; a legend icon button.

Map (centered on Europe, Atlantic to Urals, North Africa visible):
- Sea #cfdbe0, land #ece4d2, coastline #9fb2ba. No modern borders, no modern city labels.
- France split: northern and western France (Atlantic coast down to the Spanish border) filled with ochre #c8964a at 60% with a 2px darker inner edge (German military occupation); southern France filled solid mauve #9c7fa3 at 85% with a thin ink border (Vichy direct rule, co-belligerent camp). A small strip on the Italian border is bare paper with fine ink dots (no control data).
- Germany, Austria, Bohemia ochre/sienna tones #b8743d and #a5683f (Axis). Italy #d3ad6a. United Kingdom #6f8fb0 (Allies). Soviet Union #c9c2ad (neutral camp in 1940). Spain #d6cfba, Switzerland #b9b4a4, Sweden #c9c2ad (neutral).
- Do not draw front lines on this date.
- Serif place labels in ink at 80%: 「巴黎（Paris）」「維琪（Vichy）」「倫敦（London）」「柏林（Berlin）」「羅馬（Roma）」.
- Regime labels in 12px small caps style: 「德國」「法蘭西國」「義大利王國」「英國」「蘇聯」.
- A tooltip near the occupied zone: 「德國・軍事佔領」 / 「史料快照 1940-07-15」.

Legend (floating bottom-left, 280px, expanded), title 「圖例」 17px serif:
- Group 「控制類型」: 「直接統治」「軍事佔領」「傀儡代管」「不完全控制」「交戰中」 each with its small swatch.
- 「控制資料缺」 swatch with 12px note 「沒有合格來源可判斷實際控制，並非不完全控制」.
- 「戰線」 line swatch.
- Group 「史料狀態」: 「史料快照」 solid border swatch, 「推估過渡」 dashed border swatch.
- Group 「陣營」: four color chips 「軸心」「同盟」「共同交戰／合作」「中立／未結盟」.
- Group 「目前畫面中的政權」: a scrollable list with color chip + name: 「德國」「法蘭西國」「義大利王國」「英國」「蘇聯」「西班牙」.

Timeline (bottom, 112px, full width, panel color, top hairline):
- Left controls: 「上一個快照」 icon button, 「播放」 icon button, 「下一個快照」 icon button, speed text button 「1 週/秒」, a date input showing 「1940-07-15」.
- Scale 1937 … 1945 with year ticks in 12px serif and month hairlines.
- Five thin tracks labeled at left in 12px: 「西歐」「東線」「北非」「太平洋」「中國」. Small ink pills mark snapshots, denser in 「西歐」 around 1940-05 to 1940-07, sparse in 「中國」. The 「中國」 track has long stretches with the fine-dot no-data pattern.
- Vermilion handle line at 1940-07-15 crossing all tracks, with a small vermilion knob.

States to also show as separate frames:
1. Loading (first visit): basemap visible, centered spinner and text 「載入 1940-07-15 的資料…」, legend regime list as skeleton rows, timeline tracks as skeleton.
2. Empty date: centered paper card 「此日期尚無資料」 with primary button 「跳到最近有資料的日期」.
3. Error: crimson alert at top of map 「地圖資料載入失敗」 with secondary button 「重試」, previous layers still shown with caption 「顯示的是 1940-07-14 的資料」.
```

### W2. 推估過渡與資料缺

```text
Design a screen of "World Line", a historical GIS atlas of the Second World War where a single user drags a timeline to any day and sees every regime's actual control and sovereignty on one world map, each record traceable to a cited historical map. It must feel like a scholarly printed atlas, not a game or a dashboard.
Follow the attached DESIGN.md design system exactly. All UI text is Traditional Chinese (zh-Hant); use the exact Chinese labels given in quotes.
Desktop 1440×900, one page, full-bleed map with floating paper panels.
Light theme only: page #f4efe4, panels #faf7f0 with 1px #d9d0bd border and a barely visible shadow, ink text #2a2620, secondary text #6b6355.
Vermilion #b23a26 is used ONLY for the primary button, the selected toggle segment, the timeline handle and focus rings. Never use vermilion on the map or for errors. Errors use crimson #8c1d40 with an icon.
Headings Noto Serif TC, body Noto Sans TC. Sizes only 30/22/17/15/14/12px. Tabular figures. Radius 4px, panels 6px. 1px hairlines, Lucide line icons.
Top bar contains exactly: 「World Line」, the date, the era line, the evidence chip, the 「實際控制｜主權」 toggle, the 「中｜EN」 toggle, a legend toggle icon. No sidebar, no avatar, no search, no settings.
Do not add buttons, tabs, stats, export actions or features that are not described below.

Screen: the world map on 1941-08-20, between two attested snapshots, actual-control view. Same top bar, legend (collapsed to a small 「圖例」 button) and timeline layout as the main screen.

Top bar: date 「1941年8月20日」, caption 「昭和16年・民國30年」. Instead of the 「史料快照」 stamp, show a chip with 1px dashed slate #34506b border: 「推估過渡・2 個戰區」. The chip is open, showing a popover under it:
- Title 「推估過渡，非史料」 15px.
- Row 1: 「東線：介於 1941-07-09 與 1941-09-26 史料快照之間」 with two small secondary buttons 「跳到前一快照」「跳到後一快照」.
- Row 2: 「中國：介於 1941-03-01 與 1941-12-01 史料快照之間」 with the same two buttons.
(These dates are placeholders.)

Map centered on Eurasia (Europe to China):
- Eastern Front area: German-controlled area ochre #c8964a at 33% opacity with dashed borders (interpolated), Soviet area slate-blue #4f7d99 at 47% with dashed borders. A 2.5px ink front line between them, also dashed.
- Western Europe: solid fills, solid borders (attested).
- China: Japanese-occupied coastal and railway zones in sienna #a5683f solid; the area under China #5f9a8f in the southwest solid; between and around them large areas of bare paper with fine ink dots (no control data).
- A small popover is open over the dotted area in China:
  - Title 「控制資料缺」 17px serif.
  - Text 「此區此時沒有合格來源可判斷實際控制。這不代表「不完全控制」。」
  - Caption 「原因：已調查，佔領區以外無公有領域來源（見史料調查報告）」.
  - Secondary button 「切到主權檢視」.

Timeline: handle at 1941-08-20. The 「東線」 track shows pills at 1941-07-09 and 1941-09-26 with the handle between them.

States to also show as separate frames:
1. Evidence info failed: the chip shows a warning icon and 「無法判斷史料或推估」 in #a8741c, and all control areas on the map use the interpolated (dashed, faded) style.
2. All attested: the chip is replaced by the 「史料快照」 brass stamp.
```

### W3. 主權檢視＋地區主權詳情

```text
Design a screen of "World Line", a historical GIS atlas of the Second World War where a single user drags a timeline to any day and sees every regime's actual control and sovereignty on one world map, each record traceable to a cited historical map. It must feel like a scholarly printed atlas, not a game or a dashboard.
Follow the attached DESIGN.md design system exactly. All UI text is Traditional Chinese (zh-Hant); use the exact Chinese labels given in quotes.
Desktop 1440×900, one page, full-bleed map with floating paper panels.
Light theme only: page #f4efe4, panels #faf7f0 with 1px #d9d0bd border and a barely visible shadow, ink text #2a2620, secondary text #6b6355.
Vermilion #b23a26 is used ONLY for the primary button, the selected toggle segment, the timeline handle and focus rings. Never use vermilion on the map or for errors. Errors use crimson #8c1d40 with an icon.
Headings Noto Serif TC, body Noto Sans TC. Sizes only 30/22/17/15/14/12px. Tabular figures. Radius 4px, panels 6px. 1px hairlines, Lucide line icons.
Top bar contains exactly: 「World Line」, the date, the era line, the evidence chip, the 「實際控制｜主權」 toggle, the 「中｜EN」 toggle, a legend toggle icon. No sidebar, no avatar, no search, no settings.
Do not add buttons, tabs, stats, export actions or features that are not described below.

Screen: sovereignty view on 1940-07-15, the user clicked a point near Paris. Same top bar (date 「1940年7月15日」, 「主權」 selected in the toggle), timeline at the bottom, legend collapsed.

Map: all of metropolitan France in one mauve tone #9c7fa3 (the effective claimant), with a 1px double inner edge marking 「多重主張」. No front lines in this view. A small ink pin at Paris.

Right panel (400px, full height between top bar and timeline), close icon at top right:
- Header: 「地區主權」 22px serif; 「巴黎（Paris）・1940-07-15」 14px.
- Note in 12px secondary text: 「並列所有主張；系統不裁判主權正當性。」
- Section 「並存主張」 17px serif with two claim cards:
  1. 「法蘭西國」 with badge 「實際生效」, period 「1940-07-10 起」, sub-list 「承認方」: 「美國（至 1942-11）」「蘇聯（至 1941-06）」; 「不承認方」: 「英國」. A small 「來源」 button with a ledger icon.
  2. 「自由法國」 without badge, period 「1940-06-18 起」, 「承認方」: 「英國（承認為自由法國人領袖）」; 「不承認方」: 「法蘭西國」. A 「來源」 button.
- Link at the bottom: 「修正歷程（2 個版本）」.

States to also show as separate frames:
1. Empty: 「此地點此日期尚無已建置的主權資料」 with a small caption 「建置缺口」.
2. Loading: two skeleton claim cards.
3. Error: crimson alert 「主權資料載入失敗」 and 「重試」.
```

### W4. 政權聚焦面板

```text
Design a screen of "World Line", a historical GIS atlas of the Second World War where a single user drags a timeline to any day and sees every regime's actual control and sovereignty on one world map, each record traceable to a cited historical map. It must feel like a scholarly printed atlas, not a game or a dashboard.
Follow the attached DESIGN.md design system exactly. All UI text is Traditional Chinese (zh-Hant); use the exact Chinese labels given in quotes.
Desktop 1440×900, one page, full-bleed map with floating paper panels.
Light theme only: page #f4efe4, panels #faf7f0 with 1px #d9d0bd border and a barely visible shadow, ink text #2a2620, secondary text #6b6355.
Vermilion #b23a26 is used ONLY for the primary button, the selected toggle segment, the timeline handle and focus rings. Never use vermilion on the map or for errors. Errors use crimson #8c1d40 with an icon.
Headings Noto Serif TC, body Noto Sans TC. Sizes only 30/22/17/15/14/12px. Tabular figures. Radius 4px, panels 6px. 1px hairlines, Lucide line icons.
Top bar contains exactly: 「World Line」, the date, the era line, the evidence chip, the 「實際控制｜主權」 toggle, the 「中｜EN」 toggle, a legend toggle icon. No sidebar, no avatar, no search, no settings.
Do not add buttons, tabs, stats, export actions or features that are not described below.

Screen: actual-control view on 1940-07-15 with the regime 「法蘭西國」 focused. Same top bar and timeline. On the map, Vichy France and Germany stay fully colored; all other regimes fade to 35% opacity.

Right panel (400px, scrollable), top row: a filter input with placeholder 「篩選當日政權」, a text button 「退出聚焦」, a close icon.

Sections, each with a 17px serif heading and a hairline above:
1. Names: 「法蘭西國」 22px serif, below in 12px 「État français」. Collapsible 「其他名稱（2）」 showing 「維琪法國・後世史學視角」「Vichy France・英語通稱」.
2. Status: badge 「存續」 and caption 「1940-07-10 起」.
3. 「狀態時間條」: a thin horizontal bar 1937–1945; the regime exists only from 1940-07 to 1944-08; one marker at the start labeled 「政體更替」.
4. 「傳承關係」: 「前身：法蘭西第三共和（政體更替，1940-07-10）」 as a link.
5. 「當日控制」: row 「直接統治：法國南部（非佔領區）」 with a 「來源」 button.
6. 「主權主張」: 「法國本土・實際生效・美國等承認」 and 「並存主張：自由法國」.
7. 「互動」 with two sub-groups:
   - 「持續關係」: 「德國・停戰協定約束（1940-06-22 起）」, 「英國・斷交（1940-07-08 起）」. Each regime name is a link.
   - 「事件（前後 3 個月）」: 「1940-06-22 德法停戰協定」, 「1940-07-03 米爾斯克比爾港事件」, 「1940-07-10 國民議會授予貝當全權」.
8. 「紀年」: 「使用西曆，無其他紀年」.
9. A switch row: 「以此政權視角稱呼其他政權」, on.

States to also show as separate frames:
1. Loading: name shown, other sections as skeletons.
2. Section empty: under 「互動」 show 「此時段尚無已建置的互動紀錄」.
3. Section error: only the 「互動」 section shows 「互動紀錄載入失敗」 with 「重試」; other sections normal.
```

### W5. 事件詳情＋爭議點

```text
Design a screen of "World Line", a historical GIS atlas of the Second World War where a single user drags a timeline to any day and sees every regime's actual control and sovereignty on one world map, each record traceable to a cited historical map. It must feel like a scholarly printed atlas, not a game or a dashboard.
Follow the attached DESIGN.md design system exactly. All UI text is Traditional Chinese (zh-Hant); use the exact Chinese labels given in quotes.
Desktop 1440×900, one page, full-bleed map with floating paper panels.
Light theme only: page #f4efe4, panels #faf7f0 with 1px #d9d0bd border and a barely visible shadow, ink text #2a2620, secondary text #6b6355.
Vermilion #b23a26 is used ONLY for the primary button, the selected toggle segment, the timeline handle and focus rings. Never use vermilion on the map or for errors. Errors use crimson #8c1d40 with an icon.
Headings Noto Serif TC, body Noto Sans TC. Sizes only 30/22/17/15/14/12px. Tabular figures. Radius 4px, panels 6px. 1px hairlines, Lucide line icons.
Top bar contains exactly: 「World Line」, the date, the era line, the evidence chip, the 「實際控制｜主權」 toggle, the 「中｜EN」 toggle, a legend toggle icon. No sidebar, no avatar, no search, no settings.
Do not add buttons, tabs, stats, export actions or features that are not described below.

Screen: date 1939-09-01, the event 「第二次世界大戰」 is open in the right panel. Same top bar (「1939年9月1日」, 「昭和14年・民國28年」) and timeline; map shows Europe and East Asia.

Right panel (400px, scrollable), close icon:
1. Title 「第二次世界大戰」 22px serif; collapsible 「其他命名（2）」: 「大東亞戰爭・日本當時官方稱呼」「Second World War」.
2. Date row: 「起點有爭議（見下方）～ 1945-09-02」.
3. Badge 「戰爭」; participants as links: 「德國」「日本」「義大利王國」「英國」「美國」「蘇聯」「中華民國」 and 「…等」.
4. Summary paragraph 14px (2–3 lines of neutral narrative text).
5. Section 「爭議點：起點」 17px serif. Three viewpoint cards of EQUAL width side by side (or stacked equally), not ranked, no "main" or "minor" labels:
   - 「1931-09-18」 caption 「九一八事變」, holder 「部分中國史學觀點」, 「來源（1）」 button.
   - 「1937-07-07」 caption 「盧溝橋事變」, holder 「中國與部分亞洲史觀點」, 「來源（1）」.
   - 「1939-09-01」 caption 「德國入侵波蘭」, holder 「歐美通行觀點」, 「來源（1）」.
6. A boxed note in 12px secondary text: 「僅列出有合格史料支撐的觀點；已由史料確立的事實不開放並列。」
7. Section 「事件來源」 with 2 citation rows.
8. Buttons at the bottom: secondary 「在地圖上定位」 and secondary 「跳到事件日期」.

States to also show as separate frames:
1. Loading skeleton.
2. Event with no controversy: no controversy section at all (do not show any 「無爭議」 text).
3. Error: crimson alert 「事件載入失敗」 and 「重試」.
```

### W6. 來源 popover

```text
Design a popover component for "World Line", a historical GIS atlas of the Second World War where every territory record must cite a historical map. It must feel like an archive catalog card.
Follow the attached DESIGN.md design system exactly. All UI text is Traditional Chinese (zh-Hant); use the exact Chinese labels given in quotes.
Show it over the main map screen at 1440px, anchored to a small 「來源」 button in a right panel row 「軍事佔領：法國北部」.
Light theme only: popover #faf7f0, 1px #d9d0bd border, 6px radius, ink text #2a2620, secondary text #6b6355. Archival metadata (catalog numbers, plate numbers) in brass #8a6d2f. Links in slate #34506b.
Headings Noto Serif TC, body Noto Sans TC. Sizes only 17/15/14/12px. Tabular figures.
Do not add buttons or features that are not described below.

Popover (360px wide), title 「來源（2）」 17px serif. Two catalog entries separated by a hairline:
1. 「Ligne de démarcation（分界線地圖）」 15px; 「出版者：Leconte」「1940–1943」; brass 「館藏號 Paris Musées inv. 2015.3.1.230」; 「引用角色：主要」; 「依據說明：以圖中分界線描繪佔領區南界」 12px; 「授權：CC0」 with link 「授權依據」; links 「原始連結」「存檔連結」.
2. 「德法停戰協定（1940-06-22）」 15px; 「美國政府出版品」; 「引用角色：日期核對」; 「授權：公有領域」; link 「原始連結」.

Also show two variants:
1. Missing citation: crimson #8c1d40 warning with icon 「此紀錄缺少來源（資料錯誤）」.
2. Loading: small spinner.
```

### W7. 全域與錯誤狀態

```text
Design five full-screen states for "World Line", a historical GIS atlas of the Second World War. It must feel like a scholarly printed atlas.
Follow the attached DESIGN.md design system exactly. All UI text is Traditional Chinese (zh-Hant); use the exact Chinese labels given in quotes.
Desktop 1440×900. Light theme only: page #f4efe4, panels #faf7f0, ink text #2a2620. Vermilion #b23a26 only for the primary button. Errors crimson #8c1d40 with icon. Headings Noto Serif TC, body Noto Sans TC; sizes only 30/22/17/15/14/12px. Radius 4px.
Do not add anything not described.

Frames:
1. First load: skeleton of the top bar, a paper-colored map area with faint coastline, and the timeline frame.
2. API offline: centered card, crimson icon, 「無法連線到 World Line API」 22px serif, caption 「服務狀態：無回應」, primary button 「重試」.
3. Not found: centered 「找不到頁面」 22px serif, secondary button 「回主地圖」.
4. Invalid date in URL: the main map at the default date with a toast at bottom-center above the timeline: 「網址中的日期格式無效，已回到預設日期」.
5. Early period hint: map on 1935-05-01 with a small corner note 「本時段資料不保證完整」 and the timeline's pre-1937 segment shaded slightly darker.
```

### 修正已產生的畫面

```text
Apply the current design system to this screen without changing the page layout or content:
- Light theme only: page #f4efe4, panels #faf7f0, ink text #2a2620, 1px #d9d0bd hairlines, no heavy shadows.
- Vermilion #b23a26 only on the primary button, selected toggle segment, timeline handle and focus rings. Remove vermilion anywhere else, especially on the map.
- Headings Noto Serif TC, body Noto Sans TC; sizes only 30/22/17/15/14/12px. Remove Plus Jakarta Sans, Inter and any other font.
- Top bar only: 「World Line」, date, era, evidence chip, 「實際控制｜主權」, 「中｜EN」, legend icon. No sidebar, avatar, search or settings.
- Remove any buttons, stats, tabs, badges or text that the original prompt did not describe.
```

## 交付與實作

- 稿件匯出後放 `design/stitch/<id>-<slug>/`（例：`w1-main-control/`），`.html`＋`.png`；校正卡放 `design/stitch/w0-calibration/`。由我整理 `design/stitch/README.md`（計畫 A9）。
- 實作時只參考版面：元件用 sanring UI 結構＋`--wl-*` token 重組，時間軸自建於 `shared/timeline`，地圖樣式照 DESIGN.md「Map Styles」寫成 MapLibre style，不照抄 Stitch 的 Tailwind 設定與 CDN。
- 地圖色塊在 Stitch 裡只是示意；「控制資料缺」與「依主權推定」的兩種候選樣式、控制類型樣式在 M1 以真實資料於 MapLibre 實測後定稿，回寫 DESIGN.md。
- 做完一個畫面就跟設計稿對照，中文、英文各看一次。
