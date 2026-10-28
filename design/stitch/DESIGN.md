---
name: World Line — Atlas Paper
# Stitch fills any missing Material role by deriving it from `primary`, which produces lavender.
# Every role is set here so nothing is derived.
# `primary` is vermilion (seal red): primary buttons, selected states, the timeline handle, focus rings.
# `secondary` is slate ink-blue: links and secondary emphasis.
# `tertiary` is brass: archival labels only (e.g. the 「史料快照」 stamp).
# Light theme only. There is no dark theme.
colors:
  primary: '#b23a26'
  on-primary: '#fffaf2'
  primary-container: '#f6ddd4'
  on-primary-container: '#5a1a0f'
  inverse-primary: '#f0a896'
  primary-fixed: '#f6ddd4'
  primary-fixed-dim: '#eab5a6'
  on-primary-fixed: '#3d1009'
  on-primary-fixed-variant: '#8a2b1b'
  secondary: '#34506b'
  on-secondary: '#fffaf2'
  secondary-container: '#dce4ec'
  on-secondary-container: '#1a2b3c'
  secondary-fixed: '#dce4ec'
  secondary-fixed-dim: '#b4c3d2'
  on-secondary-fixed: '#0f1c29'
  on-secondary-fixed-variant: '#2a4158'
  tertiary: '#8a6d2f'
  on-tertiary: '#fffaf2'
  tertiary-container: '#efe3c4'
  on-tertiary-container: '#3f3013'
  tertiary-fixed: '#efe3c4'
  tertiary-fixed-dim: '#dcc690'
  on-tertiary-fixed: '#2a1f0a'
  on-tertiary-fixed-variant: '#6b5323'
  error: '#8c1d40'
  on-error: '#fffaf2'
  error-container: '#f3d9e0'
  on-error-container: '#4a0c20'
  background: '#f4efe4'
  on-background: '#2a2620'
  surface: '#faf7f0'
  on-surface: '#2a2620'
  surface-variant: '#ebe4d5'
  on-surface-variant: '#6b6355'
  surface-tint: '#f4efe4'
  surface-dim: '#e6dfcf'
  surface-bright: '#fdfbf6'
  surface-container-lowest: '#fdfbf6'
  surface-container-low: '#faf7f0'
  surface-container: '#f6f1e6'
  surface-container-high: '#efe9dc'
  surface-container-highest: '#e8e1d1'
  inverse-surface: '#2a2620'
  inverse-on-surface: '#f4efe4'
  outline: '#a39985'
  outline-variant: '#d9d0bd'
  # extra roles
  placeholder: '#9a917f'
  success: '#4f7a4a'
  warning: '#a8741c'
  info: '#34506b'
  # map base (see "Map Styles")
  map-land: '#ece4d2'
  map-sea: '#cfdbe0'
  map-coast: '#9fb2ba'
  map-ink: '#3a2f28'
typography:
  display:
    fontFamily: Noto Serif TC
    fontSize: 30px
    fontWeight: '600'
    lineHeight: '1.2'
  title1:
    fontFamily: Noto Serif TC
    fontSize: 22px
    fontWeight: '600'
    lineHeight: '1.35'
  title2:
    fontFamily: Noto Serif TC
    fontSize: 17px
    fontWeight: '600'
    lineHeight: '1.4'
  sub-title:
    fontFamily: Noto Sans TC
    fontSize: 15px
    fontWeight: '600'
    lineHeight: '1.5'
  text1:
    fontFamily: Noto Sans TC
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.6'
  text2:
    fontFamily: Noto Sans TC
    fontSize: 12px
    fontWeight: '400'
    lineHeight: '1.5'
  # Stitch adds label styles in another font when none exist; these pin them to text2.
  label-sm:
    fontFamily: Noto Sans TC
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1.5'
  label-xs:
    fontFamily: Noto Sans TC
    fontSize: 12px
    fontWeight: '400'
    lineHeight: '1.5'
rounded:
  xs: 2px
  sm: 3px
  md: 4px
  lg: 6px
  xl: 8px
---

# World Line 設計系統（Atlas Paper）

World Line 自有的設計系統，**不屬於 sanring 產品家族，不沿用 sanring 色票與風格**。sanring UI 元件只取結構與行為，實作時顏色、字型、圓角一律用專案的 `--wl-*` token（M0 由本檔數值產生，見 `.claude/plans/world-line-ww2-plan.md` C7）。頁面規格是 PRD §8（`.claude/prds/world-line-ww2.md`），各畫面 prompt 在 `docs/ww2-stitch.md`。

> 色碼是 2026-10-28 風格訪談後的**第一版提案**（訪談拍板的是方向：地圖集／檔案館、標題襯線＋內文無襯線、朱紅強調色、紙色陸地＋灰藍海、陣營四色系）。數值待使用者看過校正卡後確認；地圖樣式的細節在 M1 用法國真實資料於 MapLibre 實測後定稿。

## Brand & Style

World Line is a historical GIS atlas of the Second World War (1937–1945). The user drags a timeline to any day and sees every regime's territory, sovereignty claims and actual control on one world map, side by side, each record traceable to a cited historical map. Phase 1 has one user, the developer; later it is for education.

- **Feels like a historical atlas or an archive folder**: warm paper background, ink-black text, hairline rules, serif headings. Calm, scholarly, neutral. Never a game, never a "war room" HUD, never a dashboard.
- **The map is the only colorful thing on screen.** UI chrome stays paper and ink so regime colors read clearly. Panels float over the map as paper cards.
- **Honesty about evidence is a visual feature.** Attested data, interpolated transitions, missing data and presumed control must always look different (constitution R9, §9). Never make interpolated or missing areas look like attested ones.
- **Neutral tone for atrocities.** Massacres and genocide are shown with the same sober styling as other events: no red splashes, no skulls, no dramatic imagery.
- Component style: 1px hairline borders, almost no shadow, no gradients, Lucide line icons at 1.5px stroke.
- Light theme only. Desktop only, minimum width 1024px; design at 1440px.
- Bilingual: Traditional Chinese (zh-Hant) default, English switch 「中｜EN」. Original-language names (e.g. 「État français」) appear as small secondary text.

## Colors

- **Vermilion `primary` `#b23a26`** is used only for: primary buttons, the selected segment of toggles, the timeline handle and the current-date line, focus rings, the active tab underline. **Never** use vermilion on the map, for error messages, for warning text or as a large background.
- **Slate `secondary` `#34506b`** is for links and the 「推估過渡」 chip outline.
- **Brass `tertiary` `#8a6d2f`** is only for the 「史料快照」 stamp label and archival metadata (catalog numbers, plate numbers).
- **Error `#8c1d40`** (deep crimson) is always paired with an alert icon and an `error-container` tinted box, so it is never confused with vermilion.
- **Text**: `on-surface` `#2a2620` for main text, `on-surface-variant` `#6b6355` for secondary text, original-language names and dates in captions.
- **Surfaces**: page and map frame `background` `#f4efe4`; floating panels and cards `surface` `#faf7f0` with a 1px `outline-variant` border.

## Typography

Headings use **Noto Serif TC** (Chinese) with **Noto Serif** for Latin; body and UI use **Noto Sans TC** with **Noto Sans**. Never use Plus Jakarta Sans, Inter or any other font. Only these sizes exist:

| Token | Size / weight | Use |
|---|---|---|
| `display` | 30px / 600 serif | The current date in the top bar 「1940年7月15日」 |
| `title1` | 22px / 600 serif | Panel title: regime name, event title |
| `title2` | 17px / 600 serif | Section headings inside panels |
| `sub-title` | 15px / 600 sans | Group labels, card titles |
| `text1` | 14px / 400 sans | Body, buttons, inputs, list items |
| `text2` | 12px / 400 sans | Captions, era names 「昭和15年・民國29年」, sources, legend notes |

All dates and numbers use tabular figures. Dates are written `1940-07-15` in data contexts and 「1940年7月15日」 in the top bar display.

## Layout & Spacing

- Full-bleed map. Over it: a top bar (56px, `surface`, bottom hairline), a right panel (400px, collapsible), a bottom timeline (112px), a floating legend at bottom-left (280px, collapsible).
- No sidebar navigation, no avatar, no settings page, no search page. One page only (`/`).
- 4px grid. 16px panel padding, 12px between list items, 24px between panel sections.
- Section dividers inside panels are hairlines with the section title in `title2` serif, like chapter headings.

## Elevation & Depth

Flat paper. Floating panels use a 1px `outline-variant` border plus a very soft shadow `0 1px 2px rgba(42,38,32,0.08)` only to lift them from the map. No other shadows.

## Shapes

Small, crisp radii like cut paper: buttons, inputs, tags `md` 4px; panels and popovers `lg` 6px; badges `sm` 3px. No pill shapes except the snapshot markers on the timeline.

## Components

Only: button, segmented toggle, badge, tag, collapsible, popover, tooltip, input (text and date), alert, skeleton, spinner, toast, and the custom timeline. No tables, no dropdown menus, no dialogs, no tabs other than those described, no charts.

- Primary button: vermilion fill, `on-primary` text. Secondary button: transparent with 1px `outline` border, ink text.
- Segmented toggle 「實際控制｜主權」 and 「中｜EN」: selected segment vermilion fill; unselected paper with ink text.
- Badges for regime status: 「存續」 ink outline; 「流亡」 slate outline; 「被併吞」 warning-brown outline; 「已終止」 grey fill. Each status uses a different shape of text, never color alone.
- 「史料快照」 stamp: brass text, 1px brass border, uppercase-like letter spacing, like a rubber stamp. 「推估過渡」 chip: slate dashed 1px border.
- Citation button: small ledger icon + 「來源」, opens a popover listing atlas, publisher, plate/page number, license.
- Viewpoint cards (event controversies): equal width side by side, never ranked, each with its own source list.

## Timeline (custom component)

- Year ticks 1937–1945 in serif `text2`, month ticks as hairlines.
- Handle: vermilion vertical line with a small vermilion knob; the selected date appears above it.
- Snapshot tracks: one thin track per theater (「西歐」「東線」「太平洋」「中國」…), labeled at the left in `text2`. Each attested snapshot is a small ink pill; interval snapshots are ink bars spanning their period. A track with no snapshots shows the control-gap pattern.
- The period before 1937-07 (when data exists) has a faint paper-dim background and the caption 「資料不保證完整」.
- Controls at left: 「上一個快照」「播放」「下一個快照」, speed, a date input.

## Map Styles

Rendered in MapLibre. These are the first proposal; finalize in M1 with real France 1940 data.

### Base

- Land `map-land` `#ece4d2`, sea `map-sea` `#cfdbe0`, coastline `map-coast` `#9fb2ba` 0.75px. No modern borders, no modern city labels, no terrain shading.
- Place labels: serif, ink `#3a2f28` at 80%, format 「當時名稱（現代名稱）」.

### Camp colors (constitution §6 「陣營」)

Regime fill color comes from its camp on the selected date; within a camp, graph coloring picks a tone so that neighbors differ. Moderate chroma, watercolor-like, fill opacity 0.85 on paper.

| Camp | Tones |
|---|---|
| 軸心 Axis | `#c8964a` `#b8743d` `#d3ad6a` `#a5683f` `#c98a5e` `#8f6a3a` |
| 同盟 Allies | `#6f8fb0` `#5f9a8f` `#8aa7c4` `#4f7d99` `#7fae9a` `#9bb3a0` |
| 共同交戰／合作 Co-belligerent | `#9c7fa3` `#b394a8` `#85738f` `#a88aa0` |
| 中立／未結盟 Neutral | `#c9c2ad` `#b9b4a4` `#d6cfba` `#aaa596` |

No camp tone may be close to vermilion `#b23a26` or error `#8c1d40`.

### Control types (constitution R6)

| Type | Style |
|---|---|
| 直接統治 direct rule | Solid camp tone, 0.85 opacity, 0.75px ink border at 40% |
| 軍事佔領 military occupation | Occupier's tone at 0.6 opacity + 2px solid inner edge in the same tone darkened 25% |
| 傀儡代管 puppet administration | Puppet regime's tone, solid, + 1.5px dotted border in the patron's tone |
| 不完全控制 partial | 45° hatch in the controller's tone on paper: 1.5px lines every 6px, no fill |
| 交戰中 contested | Alternating 45° hatch in both parties' tones |

### Evidence states (constitution §9, R9)

| State | Style |
|---|---|
| 史料快照 attested | As above, solid borders |
| 推估過渡 interpolated | Fill opacity ×0.55, borders dashed 4–3 |
| 控制資料缺 no control data | **Two candidates, decide in M1**: (A) bare paper + fine ink dots on a 6px grid at 35%; (B) neutral grey `#b5b0a5` overlay at 0.7 |
| 依主權推定 presumed from sovereignty | **Two candidates, decide in M1**: (A) camp tone at 0.35 opacity, no border; (B) camp tone at 0.5 with a 0.75px dotted border |

Rule: control-gap and presumed styles must never resemble any control type, especially the partial-control hatch.

### Lines and markers

- 戰線 front line: 2.5px solid `map-ink` `#3a2f28`. Never red.
- Sovereignty view: multiple or disputed claims get a 1px double inner edge.
- Event markers: 14px ink line icons on a paper disc; atrocity events use the same disc with a neutral icon.
- Focus mode: non-focused regimes drop to 0.35 opacity.

## Screens

One page with panels; prompts and Chinese copy in `docs/ww2-stitch.md`.

1. **主地圖・實際控制** — 1940-07-15, France split into German occupation and Vichy, legend open, timeline with theater tracks (PRD §8.0–8.4).
2. **推估過渡與資料缺** — date between two snapshots, 「推估過渡」 chip popover open; China area showing the control-gap style and its popover (§8.4, §8.5).
3. **主權檢視＋地區主權詳情** — sovereignty view, right panel listing concurrent claims and recognizers (§8.7).
4. **政權聚焦面板** — 「法蘭西國」 focused: names, status badge, status timeline, lineage from 「法蘭西第三共和」 via 「政體更替」, control, claims, relations, era (§8.6).
5. **事件詳情＋爭議點** — an event with side-by-side viewpoint cards, R8 note, sources (§8.8).
6. **來源 popover** — citation details (§8.9).
7. **全域狀態** — first-load skeleton, map error with retry, empty date, API offline, not found (§8.2, §8.11).
