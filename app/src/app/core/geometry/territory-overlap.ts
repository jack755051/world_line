import { bbox, featureCollection, intersect } from '@turf/turf';
import type { MultiPolygon, Polygon } from 'geojson';

export interface TerritoryWithRegime {
  id: string;
  regimeId: string;
  geometry: MultiPolygon;
  /** 形變過場動畫中（任務 3.6）正在淡入/淡出的疆域列的目前透明度（0-1），沒有動畫時
      省略即可，視同 1。用來讓重疊區網底也跟著淡入淡出，而不是在來源政權自己都還沒
      「完全出現」時就先以滿版強度顯示重疊斜線——見下方 `overlap.opacity` 的說明。 */
  morphOpacity?: number;
  /** 形變過場動畫中，這筆疆域列是不是正在「出現」或「消失」（不是動畫時省略）——用來
      擋下「entering 對 leaving」這種跨政權配對被誤判成重疊爭議，見下方
      `computeTerritoryOverlaps` 文件註解的「政權更迭不是政權衝突」說明。 */
  morphRole?: 'entering' | 'leaving';
}

export interface TerritoryOverlap {
  geometry: Polygon | MultiPolygon;
  /** 這塊重疊區的顯示透明度——取兩個來源政權疆域列各自 `morphOpacity` 的較小值。
      重疊區的存在本身依附在兩個疆域主張都要「看得見」才有意義，任一邊還在淡入/淡出，
      重疊斜線也該跟著淡，不能無視動畫狀態直接以滿版強度顯示。沒有傳 `morphOpacity`
      的一般情況（兩邊都當作 1）維持原本行為，值是 1。 */
  opacity: number;
}

/**
 * 計算一批疆域裡，**不同政權之間**實際幾何重疊的區域，回傳交集多邊形陣列——不是「有
 * 沒有相鄰」（那是 territory-adjacency.ts 的 `computeAdjacency()`，只回答 true/false，
 * 邊界接觸也算相鄰，服務對象是圖著色演算法），這裡回傳真正有面積的交集，給疆域重疊區
 * 斜線網底用。
 *
 * **規則就是這麼簡單（2026-08-29 使用者定案）**：政權掌控區用顏色表示，**兩個不同
 * 政權的疆域重疊區域才用斜線**——同一個政權自己底下多筆疆域記錄（例如 I3 史觀分歧的
 * 兩個並存版本）彼此重疊，不算「政權重疊」，不畫斜線；那是同一個政權，一律用顏色
 * 表示，不需要另外標記。這也是為什麼這個函式需要 `regimeId`，不能只看 `id`——純幾何
 * 相交測試分不出「這是同政權自己的版本分歧」還是「這是跟別的政權搶地盤」，只有比對
 * `regimeId` 才分得出來。
 *
 * **2026-08-29 拍板，取代原本「靠 `regime_territories.is_disputed` 整筆記錄畫網底」的
 * 做法**：使用者指出「一整筆爭議記錄就整塊畫斜線」邏輯上站不住腳——例如蜀漢在 208-215
 * 年借荊州期間，西邊（跟東吳完全不重疊的部分）從沒被任何人質疑過，只有跟東吳宣稱重疊
 * 的那一小塊才是真正的爭議地帶；若整筆記錄都畫網底，類比到二戰後英法美蘇瓜分德國，
 * 佔領區邊界是條約明訂、沒有史料分歧，套用同一套判斷會荒謬地把整個佔領區都畫成爭議。
 * 改成即時算幾何交集，斜線只出現在真正重疊的地方，不管未來匯入任何真實史料、任兩個
 * 政權疆域重疊，都會自動正確顯示，不需要再手動判斷或標記哪一筆該標 `is_disputed`。
 *
 * 效能：先用 bounding box 粗篩，只對 bbox 有重疊的候選對呼叫真正的幾何交集運算
 * （`turf.intersect()` 比 `booleanIntersects()` 貴很多），避免 O(n²) 全對全都跑。
 * 邊界只是接觸（不是真的有面積重疊）的情況，`turf.intersect()` 本身就會回傳 `null`
 * （已用測試驗證），不需要另外過濾。
 *
 * **「政權更迭」不是「政權衝突」（2026-08-30，使用者實機回報：漢禪魏、魏禪晉這種和平
 * 交接，換年份的形變動畫過程中會閃過一整塊紅色斜線衝突區，看起來像在打仗）**。根因：
 * 這個專案的既有設計刻意讓禪讓/滅國前後兩個政權的疆域座標完全一致（例如魏建國疆域＝
 * 曹操禪讓前的漢朝實際控制地盤，見 `api/Data/SeedData.cs` 的說明）——形變動畫換年份
 * 跨過這種交接的那一刻，舊政權那筆疆域列正在淡出（`morphRole: 'leaving'`）、新政權那筆
 * 正在淡入（`morphRole: 'entering'`），兩者座標完全相同，幾何交集自然是整塊疆域，被
 * 這個函式判定成「政權重疊」畫上爭議紅色斜線——但這不是真的政權衝突，是**同一塊地換了
 * 主人**（不管是和平禪讓還是被滅國攻佔，土地本身沒有「同時被兩個政權宣稱」的意思，只是
 * 換手的瞬間畫面上剛好兩邊都在淡入淡出而已）。真正的政權衝突（例如蜀漢/東吳的荊州爭議）
 * 是兩個政權在同一個「已經定案」的年份**同時且持續**宣稱同一塊地，不是動畫過場中純粹
 * 因為淡入淡出時機重疊造成的視覺假象。**因此：entering 跟 leaving 這兩種角色互相配對
 * 時直接跳過，不算重疊**——matched（持續存在）對 entering/leaving，或 entering 對
 * entering、leaving 對 leaving，這些配對都還是正常計算（例如一個新政權誕生時剛好跟
 * 一個持續存在的政權有真正的地盤衝突，這種情況仍然該顯示爭議），只有 entering×leaving
 * 這一種組合被排除。
 */
export function computeTerritoryOverlaps(territories: TerritoryWithRegime[]): TerritoryOverlap[] {
  const boxes = territories.map((t) => bbox(t.geometry));
  const overlaps: TerritoryOverlap[] = [];

  for (let i = 0; i < territories.length; i++) {
    for (let j = i + 1; j < territories.length; j++) {
      if (territories[i].regimeId === territories[j].regimeId) {
        continue; // 同一個政權自己的疆域記錄，不算「政權重疊」，用顏色表示就好
      }
      if (isHandoverPair(territories[i].morphRole, territories[j].morphRole)) {
        continue; // entering 對 leaving：政權更迭的交接瞬間，不是真的政權衝突，見上方說明
      }
      if (!bboxesOverlap(boxes[i], boxes[j])) {
        continue;
      }

      const a = { type: 'Feature' as const, properties: {}, geometry: territories[i].geometry };
      const b = { type: 'Feature' as const, properties: {}, geometry: territories[j].geometry };
      const result = intersect(featureCollection([a, b]));
      if (result) {
        const opacityA = territories[i].morphOpacity ?? 1;
        const opacityB = territories[j].morphOpacity ?? 1;
        overlaps.push({ geometry: result.geometry, opacity: Math.min(opacityA, opacityB) });
      }
    }
  }

  return overlaps;
}

function bboxesOverlap(a: number[], b: number[]): boolean {
  // [minX, minY, maxX, maxY]
  return a[0] <= b[2] && b[0] <= a[2] && a[1] <= b[3] && b[1] <= a[3];
}

/** 一個是 entering、另一個是 leaving（順序不拘）——見 `computeTerritoryOverlaps`
    文件註解的「政權更迭不是政權衝突」說明。matched（`undefined`）不算在內。 */
function isHandoverPair(roleA: TerritoryWithRegime['morphRole'], roleB: TerritoryWithRegime['morphRole']): boolean {
  return (roleA === 'entering' && roleB === 'leaving') || (roleA === 'leaving' && roleB === 'entering');
}
