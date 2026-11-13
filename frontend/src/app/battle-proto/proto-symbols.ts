import ms from 'milsymbol';
import type { ProtoSide, ProtoUnit } from './proto-data';

/** 陣營色（避開 Stitch 強調色 #8BD3DD／#22C3EE）：盟軍藍、軸心紅。 */
export const SIDE_COLOR: Record<ProtoSide, { fill: string; frame: string }> = {
  allied: { fill: '#3F6FD0', frame: '#BBD0FF' },
  axis: { fill: '#C24444', frame: '#FFC2C2' },
};

export const symbolId = (sidc: string, dashed: boolean) => `bp-sym:${sidc}:${dashed ? 'd' : 's'}`;
/** 狀態碼 'A'（anticipated）讓 milsymbol 畫虛線外框；'P' 為實線。 */
const withStatus = (sidc: string, dashed: boolean) => sidc.slice(0, 3) + (dashed ? 'A' : 'P') + sidc.slice(4);

export interface SymbolImage { id: string; image: ImageData; pixelRatio: number }

/** 啟動時一次產生所有 sidc × (實／虛框) 圖像；不在每幀產圖。 */
export function buildSymbolImages(units: ProtoUnit[]): SymbolImage[] {
  const seen = new Set<string>();
  const out: SymbolImage[] = [];
  for (const u of units) {
    for (const dashed of [false, true]) {
      const id = symbolId(u.sidc, dashed);
      if (seen.has(id)) continue;
      seen.add(id);
      const c = SIDE_COLOR[u.side];
      const sym = new ms.Symbol(withStatus(u.sidc, dashed), { size: u.echelon === 'corps' ? 30 : 26, fill: true, fillColor: c.fill, frameColor: { Civilian: c.frame, Friend: c.frame, Hostile: c.frame, Neutral: c.frame, Unknown: c.frame, Suspect: c.frame }, iconColor: '#FFFFFF', strokeWidth: 3, outlineColor: '#0B121B', outlineWidth: 2 });
      const canvas = sym.asCanvas(2);
      const ctx = canvas.getContext('2d')!;
      out.push({ id, image: ctx.getImageData(0, 0, canvas.width, canvas.height), pixelRatio: 2 });
    }
  }
  return out;
}

/** 推進箭頭頭部（朝上的三角形，icon-rotate 轉向）；每陣營一張。 */
export function buildArrowHead(side: ProtoSide): SymbolImage {
  const s = 32, canvas = document.createElement('canvas');
  canvas.width = canvas.height = s;
  const g = canvas.getContext('2d')!;
  g.fillStyle = SIDE_COLOR[side].fill; g.strokeStyle = '#FFFFFF'; g.lineWidth = 2;
  g.beginPath(); g.moveTo(s / 2, 3); g.lineTo(s - 5, s - 5); g.lineTo(5, s - 5); g.closePath(); g.fill(); g.stroke();
  return { id: `bp-arrowhead-${side}`, image: g.getImageData(0, 0, s, s), pixelRatio: 2 };
}
