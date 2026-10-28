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
