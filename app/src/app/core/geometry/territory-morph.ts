import { interpolate } from 'flubber';
import type { Feature, FeatureCollection, MultiPolygon, Position } from 'geojson';
import type { TerritoryFeatureProperties } from './territory-styling';

type TerritoryFeature = Feature<MultiPolygon, TerritoryFeatureProperties>;

/** `sampleMorphPlan()` 輸出的 feature 額外帶：
    - `morphOpacity`（0-1）：動畫進行中，正在「出現」或「消失」的疆域用這個欄位控制
      淡入淡出透明度，`map.ts` 的 paint expression 讀這個欄位。
    - `morphRole`：只有 entering/leaving 的 feature 才有這個欄位（matched 的沒有）——
      `map.ts` 組疆域重疊區資料時要靠這個欄位判斷「entering 對 leaving」這種跨政權
      配對該不該算重疊，見 `territory-overlap.ts` 的 `TerritoryWithRegime.morphRole`
      說明。
    真正的（非動畫過場中）疆域資料不帶這兩個欄位，paint expression 用 `coalesce`
    預設回 1，不需要每個呼叫端都手動補這些屬性。 */
export type MorphedFeatureProperties = TerritoryFeatureProperties & {
  morphOpacity: number;
  morphRole?: 'entering' | 'leaving';
};

interface MatchedPair {
  to: TerritoryFeature;
  /** flubber 的 TypeScript 型別定義（`@types/flubber`）把 `Interpolator` 寫死成
      `(t: number) => string`，但那是只有 `options.string`（預設 true）情境下的行為；
      這裡呼叫時明確帶 `{ string: false }`，執行期實際回傳的是 `Position[]`（插值後的
      環狀點陣列），不是 SVG path 字串——型別定義沒有覆蓋這個分支，這裡用
      `unknown as (t: number) => Position[]` 轉型一次，繞開型別定義的落差，不是隨便亂轉。 */
  interpolator: (t: number) => Position[];
}

export interface MorphPlan {
  /** 兩個年份都有、同一個政權底下配對到的疆域列——用 flubber 插值連續變形。 */
  matched: MatchedPair[];
  /** 只在新年份出現的疆域列（政權新成立、或同一政權新增一筆快照，例如進入爭議期間新增
      的爭議地帶那筆）——沒有「從哪個形狀變過來」，用淡入處理，不做形狀插值。 */
  entering: TerritoryFeature[];
  /** 只在舊年份出現、新年份已經沒有的疆域列——用淡出處理。 */
  leaving: TerritoryFeature[];
}

/**
 * 疆域快照間的連續形變（任務 3.6，對應憲法 §9「疆域必須連續變化呈現，非離散跳轉」）。
 *
 * **配對策略**：先依 `regimeId` 分組，同一個政權底下的疆域列（`rows`）用「環的形心
 * 座標排序」排出固定順序後逐一配對——不是用資料庫 `id`（不同年份的快照是不同列，`id`
 * 本來就不會相同，沒辦法拿來配對），也不是用陣列原始順序（後端回傳順序不保證跨查詢
 * 穩定）。排序用形心座標而不是隨機/插入順序，確保同一批資料重複呼叫這個函式時，配對
 * 結果是決定性的（同一個政權有兩筆疆域列時，例如荊州爭議期間的核心區+爭議區，每次都
 * 配對到「同一個位置」的那一筆，不會因為呼叫時機不同而配對錯位、造成形變路徑跳來跳去）。
 * 政權底下疆域列數量在兩個年份不一致時（例如剛進入/離開爭議期間，從 1 筆變 2 筆），
 * 多出來的部分歸類到 `entering`／`leaving`，不強行配對插值——沒有形狀插值的「正確」
 * 對應關係可言（1 筆該怎麼插值成 2 筆？沒有唯一解），用淡入淡出至少維持「連續變化」
 * 而不是硬切換，這是刻意的 V1 範圍限制，見本模組其他函式的說明。
 *
 * **只讀每個 feature 的第一個 polygon、第一個環**（`geometry.coordinates[0][0]`）：
 * 目前種子資料的 `MultiPolygon` 一律只有單一 polygon、單一環（無洞、無多部分），見
 * `api/Data/SeedData.cs` 的 `Rect()`。之後若真的匯入有多部分/有洞的真實史料幾何，這裡
 * 需要跟著擴充（例如用 flubber 的 `combine`/`separate` 處理多環對多環），現在不先猜
 * 那個規格——目前資料形狀下這個簡化完全正確，不是偷懶漏掉。
 */
export function buildMorphPlan(
  from: FeatureCollection<MultiPolygon, TerritoryFeatureProperties>,
  to: FeatureCollection<MultiPolygon, TerritoryFeatureProperties>,
): MorphPlan {
  const fromByRegime = groupByRegime(from.features);
  const toByRegime = groupByRegime(to.features);

  const matched: MatchedPair[] = [];
  const entering: TerritoryFeature[] = [];
  const leaving: TerritoryFeature[] = [];

  const regimeIds = new Set([...fromByRegime.keys(), ...toByRegime.keys()]);
  for (const regimeId of regimeIds) {
    const fromRows = sortRowsByCentroid(fromByRegime.get(regimeId) ?? []);
    const toRows = sortRowsByCentroid(toByRegime.get(regimeId) ?? []);
    const pairCount = Math.min(fromRows.length, toRows.length);

    for (let i = 0; i < pairCount; i++) {
      const fromRing = outerRing(fromRows[i]);
      const toRing = outerRing(toRows[i]);
      matched.push({ to: toRows[i], interpolator: buildRingInterpolator(fromRing, toRing) });
    }
    for (let i = pairCount; i < toRows.length; i++) {
      entering.push(toRows[i]);
    }
    for (let i = pairCount; i < fromRows.length; i++) {
      leaving.push(fromRows[i]);
    }
  }

  return { matched, entering, leaving };
}

/**
 * 取某個時間點 `t`（0-1）的插值結果，組回一個可以直接餵給 `source.setData()` 的
 * `FeatureCollection`。**呼叫端負責邊界值**：`t=0`／`t=1` 這裡不特別處理成「完全等於
 * 原始資料」——flubber 內部會先把 from/to 兩個環重新取樣成點數相同才插值，`t=0`／`t=1`
 * 的輸出點數/精確度跟原始資料不會完全一致（已用真實矩形資料實測驗證過），動畫開始前
 * 畫面上本來就是還沒換的舊資料（不需要呼叫這個函式），動畫結束時 `map.ts` 直接改用
 * 目標年份的原始 `FeatureCollection`（`morphOpacity` 全部視為 1），不呼叫
 * `interpolator(1)`，避免每次拖桿都疊加一次取樣誤差。
 */
export function sampleMorphPlan(
  plan: MorphPlan,
  t: number,
): FeatureCollection<MultiPolygon, MorphedFeatureProperties> {
  const features: Feature<MultiPolygon, MorphedFeatureProperties>[] = [];

  for (const { to, interpolator } of plan.matched) {
    const ring = closeRing(interpolator(t));
    features.push({
      type: 'Feature',
      properties: { ...to.properties, morphOpacity: 1 },
      geometry: { type: 'MultiPolygon', coordinates: [[ring]] },
    });
  }
  for (const feature of plan.entering) {
    features.push({ ...feature, properties: { ...feature.properties, morphOpacity: t, morphRole: 'entering' } });
  }
  for (const feature of plan.leaving) {
    features.push({ ...feature, properties: { ...feature.properties, morphOpacity: 1 - t, morphRole: 'leaving' } });
  }

  return { type: 'FeatureCollection', features };
}

/** ease-in-out cubic 緩動函式——動畫開頭/結尾慢、中段快，比線性插值視覺上更自然（業界
    動畫慣用曲線之一，不是這個專案發明的公式）。純函式，跟這個模組其他函式一樣不碰
    RAF／時間，由 `map.ts` 的動畫迴圈每一幀呼叫，把原始進度 t 轉成實際拿去插值的 t。 */
export function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t ** 3 : 1 - (-2 * t + 2) ** 3 / 2;
}

function groupByRegime(features: TerritoryFeature[]): Map<string, TerritoryFeature[]> {
  const byRegime = new Map<string, TerritoryFeature[]>();
  for (const feature of features) {
    const regimeId = feature.properties.regimeId;
    const rows = byRegime.get(regimeId);
    if (rows) {
      rows.push(feature);
    } else {
      byRegime.set(regimeId, [feature]);
    }
  }
  return byRegime;
}

/** 用環的形心座標（先比經度、再比緯度）排出決定性順序，見 `buildMorphPlan` 開頭說明。 */
function sortRowsByCentroid(features: TerritoryFeature[]): TerritoryFeature[] {
  return [...features].sort((a, b) => {
    const [ax, ay] = centroidOf(outerRing(a));
    const [bx, by] = centroidOf(outerRing(b));
    return ax - bx || ay - by;
  });
}

function outerRing(feature: TerritoryFeature): Position[] {
  return feature.geometry.coordinates[0][0];
}

/**
 * 建立一個環對環的插值函式。**頂點數相同時，直接逐點線性插值，不透過 flubber**
 * （2026-08-30，使用者實機回報：疆域明明只是單邊往內縮/往外擴的矩形，形變過程卻看起來
 * 像在旋轉或不對稱拉伸）。根因：flubber 的 `interpolate()` 是設計給「不知道兩個形狀
 * 頂點對應關係」的一般情況用的——它會先把兩個環重新取樣成更密的點集，再嘗試幾種不同的
 * 起點位移，挑「總移動量最小」的那個當對應關係。這個專案的疆域資料目前一律是 `Rect()`
 * 產生的矩形，**相鄰年份快照之間頂點數永遠相同、順序永遠一致**（永遠是同一個
 * min/min→min/max→max/max→max/min 建構順序），對應關係其實是已知的、不需要用演算法猜；
 * 讓 flubber 猜反而在「只有一條邊移動、其餘角完全沒動」這種簡單情況下，因為重新取樣後
 * 的密集點集，最小總移動量搜尋可能選到一個跟直覺不符的對應關係，看起來像整塊疆域在
 * 旋轉/歪斜，不是單純一條邊平移。
 *
 * 頂點數相同時逐點線性插值，保證每個頂點走最短直線路徑，不會有這個問題。頂點數不同
 * 時（例如之後匯入的真實史料，形狀被重新繪製、增刪了頂點）才真的沒有已知對應關係，
 * 這時才需要 flubber 的形狀比對演算法去猜——這個分支維持原本的做法。
 */
function buildRingInterpolator(fromRing: Position[], toRing: Position[]): (t: number) => Position[] {
  if (fromRing.length === toRing.length) {
    return (t: number) =>
      fromRing.map(([fromX, fromY], i) => {
        const [toX, toY] = toRing[i];
        return [fromX + (toX - fromX) * t, fromY + (toY - fromY) * t] as Position;
      });
  }

  // `string: false` 讓 flubber 回傳插值後的點陣列而不是 SVG path 字串（見
  // MatchedPair 的型別轉型註解）。
  return interpolate(fromRing as unknown as string, toRing as unknown as string, {
    string: false,
  }) as unknown as (t: number) => Position[];
}

function centroidOf(ring: Position[]): [number, number] {
  let sumX = 0;
  let sumY = 0;
  for (const [x, y] of ring) {
    sumX += x;
    sumY += y;
  }
  return [sumX / ring.length, sumY / ring.length];
}

/** flubber 回傳的點陣列不保留「首尾同一點」的閉環格式（已用真實矩形資料實測驗證），
    但 GeoJSON `Polygon`/`MultiPolygon` 的環規範要求首尾座標相同——這裡補上閉合點。 */
function closeRing(points: Position[]): Position[] {
  const [firstX, firstY] = points[0];
  const [lastX, lastY] = points[points.length - 1];
  if (firstX === lastX && firstY === lastY) {
    return points;
  }
  return [...points, [firstX, firstY]];
}
