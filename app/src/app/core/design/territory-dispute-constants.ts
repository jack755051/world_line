/**
 * 疆域重疊區斜線網底的顏色/間距常數（PRD §5「斜線網底配色」已拍板方案，任務 3.15
 * 抽成共用常數檔）——原本 tile 尺寸/線寬/加深比例寫死在
 * `core/geometry/territory-dispute-pattern.ts`，MapLibre 圖層/圖片/來源 id 字串則
 * 寫死在 `map.ts`，兩處各自硬編碼，其中一處調整時容易忘記同步改另一處（例如改了圖層
 * id 卻漏改測試裡對應的字串）。集中在這裡，兩邊都改成讀這個檔案。
 *
 * **顏色本身（`--wl-dispute-*` 色階）刻意不在這裡**：那是 `design-tokens.scss` 已經
 * 拍板的 CSS 自訂屬性，是唯一真相來源（見該檔案該色階區塊的說明）。這個檔案只收「CSS
 * 沒有對應 token 的純 TS 端渲染參數」（tile 尺寸、線寬、加深比例）跟「MapLibre 圖層/
 * 圖片/來源 id 字串」——顏色改 `design-tokens.scss`，網底繪製參數/圖層命名改這裡，
 * 不是同一份檔案身兼兩種不相干的責任。
 */

/** 45 度斜線 tile 邊長（px）——`createDiagonalHatchImageData()` 用來畫可無縫拼接的
    網底圖樣，見 `territory-dispute-pattern.ts`。 */
export const DISPUTE_HATCH_TILE_SIZE = 8;

/** 斜線本身的線寬（px）。 */
export const DISPUTE_HATCH_LINE_WIDTH = 1.5;

/** 網底斜線相對底色的加深比例（0-1），見 `darkenHex()`。 */
export const DISPUTE_HATCH_DARKEN_AMOUNT = 0.35;

/** `design-tokens.scss` 的 `--wl-dispute-500` 讀不到時的 JS fallback——理論上不該
    發生，只有 CSS 還沒載入完成的極端時序才會走到這個分支，跟 `map.ts` 讀
    `--wl-territory-border`/`--wl-focus-ring` 的 fallback 字串同一個既有慣例。這裡
    只收斜線網底專屬的這一個，不是把所有 CSS token 的 fallback 都集中在這裡（那些
    不是「斜線網底」的常數，見上方檔案文件說明）。 */
export const DISPUTE_COLOR_FALLBACK_HEX = '#b83333';

/** MapLibre GeoJSON source id——`territory-overlap.ts` 即時算出來的重疊區資料掛在
    這個 source 上，`DISPUTE_FILL_LAYER_ID`/`DISPUTE_HATCH_LAYER_ID` 兩個圖層都讀
    同一個 source。 */
export const DISPUTE_OVERLAP_SOURCE_ID = 'territory-overlaps';

/** 重疊區底色圖層 id（先鋪不透明爭議紅底色，蓋掉底下兩個政權各自的顏色，見 map.ts
    `addTerritoryLayers()` 的說明）。 */
export const DISPUTE_FILL_LAYER_ID = 'territory-overlaps-fill';

/** 重疊區斜線網底圖層 id（疊在 `DISPUTE_FILL_LAYER_ID` 之上）。 */
export const DISPUTE_HATCH_LAYER_ID = 'territory-overlaps-hatch';

/** `map.addImage()` 註冊的網底圖樣 id，`DISPUTE_HATCH_LAYER_ID` 的 `fill-pattern`
    引用這個 id。 */
export const DISPUTE_HATCH_IMAGE_ID = 'territory-overlap-hatch';
