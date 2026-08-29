/**
 * 貪婪圖著色（greedy graph coloring）：給定相鄰關係圖跟可用色格數量，指派每個節點一個色格
 * 索引，保證相鄰節點不會拿到同一個色格。
 *
 * 這是通用演算法，不含任何實際顏色值——實際要用哪幾個色碼對應到色格索引，是「政權識別色」
 * 決定時才需要拍板的事，這裡刻意先擱置（見 design-tokens.scss 開頭說明、implementation
 * plan Phase 3 任務 3.5 補充說明）。
 *
 * 演算法本身不保證用到最少色格數（那是 NP-hard 的圖著色最佳化問題），但對地圖這種平面圖，
 * 四色定理保證 4 色一定夠用；`slotCount` 通常會設得比 4 大一些，換取多一點視覺變化空間，
 * 不是必要下限。
 *
 * 2026-08-29 拍板（同日補齊系統色 50-900 完整色階後修正）：實際接上分類色盤時，
 * `slotCount` 用分類色第 3-8 格（6 色）——第 1 格（藍）、第 2 格（橙）分別保留給
 * `design-tokens.scss` 的 UI 主色／次色（按鈕/連結/焦點框/次要強調）專用，避免疆域填色
 * 跟互動元件顏色混淆。6 色仍遠高於四色定理需要的下限。
 */
export function greedyColorAssignment(
  adjacency: Map<string, Set<string>>,
  slotCount: number,
  previousAssignment?: Map<string, number>,
): Map<string, number> {
  const assignment = new Map<string, number>();

  // 處理順序：優先保留「前一次已經有指派」的節點（穩定性——時間拉桿拖動造成疆域形狀微調時，
  // 不希望顏色無謂閃爍換來換去），其餘節點依相鄰數量從多到少處理（相鄰越多、可選色格越少，
  // 優先處理比較不容易在後面卡死找不到色格）。
  const ids = [...adjacency.keys()];
  ids.sort((a, b) => {
    const aHasPrevious = previousAssignment?.has(a) ? 0 : 1;
    const bHasPrevious = previousAssignment?.has(b) ? 0 : 1;
    if (aHasPrevious !== bHasPrevious) {
      return aHasPrevious - bHasPrevious;
    }
    return (adjacency.get(b)?.size ?? 0) - (adjacency.get(a)?.size ?? 0);
  });

  for (const id of ids) {
    const neighborSlots = new Set<number>();
    for (const neighborId of adjacency.get(id) ?? []) {
      const neighborSlot = assignment.get(neighborId);
      if (neighborSlot !== undefined) {
        neighborSlots.add(neighborSlot);
      }
    }

    // 優先沿用前一次的色格，只有真的跟目前已指派的相鄰節點衝突才換色。
    const preferred = previousAssignment?.get(id);
    if (preferred !== undefined && !neighborSlots.has(preferred)) {
      assignment.set(id, preferred);
      continue;
    }

    let chosen = -1;
    for (let slot = 0; slot < slotCount; slot++) {
      if (!neighborSlots.has(slot)) {
        chosen = slot;
        break;
      }
    }

    if (chosen === -1) {
      throw new Error(
        `greedyColorAssignment: 節點 "${id}" 的相鄰節點用滿了全部 ${slotCount} 個色格，` +
          '理論上不該發生在平面地圖上（四色定理保證 4 色就夠）——請檢查相鄰關係計算是否有誤。',
      );
    }

    assignment.set(id, chosen);
  }

  return assignment;
}
