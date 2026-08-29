import { greedyColorAssignment } from './graph-coloring';

function assertNoAdjacentConflict(adjacency: Map<string, Set<string>>, assignment: Map<string, number>): void {
  for (const [id, neighbors] of adjacency) {
    for (const neighborId of neighbors) {
      expect(assignment.get(id)).not.toBe(assignment.get(neighborId));
    }
  }
}

describe('greedyColorAssignment', () => {
  it('相鄰節點永遠拿到不同色格', () => {
    // 三角形相鄰關係（三者兩兩相鄰）：a-b-c-a，至少需要 3 色格才能滿足。
    const adjacency = new Map<string, Set<string>>([
      ['a', new Set(['b', 'c'])],
      ['b', new Set(['a', 'c'])],
      ['c', new Set(['a', 'b'])],
    ]);

    const assignment = greedyColorAssignment(adjacency, 8);

    assertNoAdjacentConflict(adjacency, assignment);
    expect(new Set(assignment.values()).size).toBe(3); // 三角形確實需要 3 個不同色格
  });

  it('不相鄰的節點可以重複使用同一個色格（四色定理精神：不強迫每個節點都要不同色）', () => {
    // 一字排開的鏈：a-b-c，a 只跟 b 相鄰，c 只跟 b 相鄰，a 跟 c 不相鄰。
    const adjacency = new Map<string, Set<string>>([
      ['a', new Set(['b'])],
      ['b', new Set(['a', 'c'])],
      ['c', new Set(['b'])],
    ]);

    const assignment = greedyColorAssignment(adjacency, 8);

    assertNoAdjacentConflict(adjacency, assignment);
    // a 跟 c 不相鄰，允許（不強制）共用同一個色格。
    expect(assignment.get('a')).toBe(assignment.get('c'));
  });

  it('色格數量不足以滿足相鄰關係時會拋出例外，而不是靜默指派錯誤的顏色', () => {
    // 4 個節點兩兩相鄰（完全圖 K4），需要 4 個色格，只給 3 個應該失敗。
    const adjacency = new Map<string, Set<string>>([
      ['a', new Set(['b', 'c', 'd'])],
      ['b', new Set(['a', 'c', 'd'])],
      ['c', new Set(['a', 'b', 'd'])],
      ['d', new Set(['a', 'b', 'c'])],
    ]);

    expect(() => greedyColorAssignment(adjacency, 3)).toThrow();
  });

  it('提供前一次的指派時，優先沿用舊色格以維持穩定（沒有衝突就不換色）', () => {
    const adjacency = new Map<string, Set<string>>([
      ['a', new Set(['b'])],
      ['b', new Set(['a'])],
    ]);
    const previous = new Map<string, number>([
      ['a', 5],
      ['b', 2],
    ]);

    const assignment = greedyColorAssignment(adjacency, 8, previous);

    expect(assignment.get('a')).toBe(5);
    expect(assignment.get('b')).toBe(2);
  });

  it('前一次的指派互相衝突時，至少一個節點被迫換色，換色後仍保證跟相鄰節點不同色', () => {
    // a、b 都跟 c 相鄰，三者前一次卻都用同一個色格 0——這組舊指派本身不合法，
    // 代表疆域形狀在拖拉桿拖動間改變出了新的相鄰關係，一定要有人讓步換色。
    const adjacency = new Map<string, Set<string>>([
      ['a', new Set(['c'])],
      ['b', new Set(['c'])],
      ['c', new Set(['a', 'b'])],
    ]);
    const previous = new Map<string, number>([
      ['a', 0],
      ['b', 0],
      ['c', 0],
    ]);

    const assignment = greedyColorAssignment(adjacency, 8, previous);

    assertNoAdjacentConflict(adjacency, assignment);
    // 三者不可能維持全部都是色格 0（那樣 c 會跟 a、b 衝突），至少有節點的色格跟前一次不同。
    const changed = [...previous.keys()].filter((id) => assignment.get(id) !== previous.get(id));
    expect(changed.length).toBeGreaterThan(0);
  });
});
