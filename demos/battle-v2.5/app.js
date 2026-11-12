/* 戰役動態地圖示範 v2.6（多場戰役；資料與程式分開）
 * v2.6：戰役和程式解耦——battles/index.json 列出所有戰役，每場一個資料夾（battle.json、theatre.json、assignments.json、geo/）。
 *       網址 ?battle=<id> 選戰役；標題旁的 ▲▼ 或鍵盤上下鍵切到上一場／下一場。
 * v2.5：整套美術換掉——淺色「編輯地圖」風格（紙白陸地、墨線前線、磚紅／海軍藍、橘色只給交戰），左側改成固定的敘事欄。
 * v2.4：UI 重做——自畫部隊牌（兵種圖示＋番號＋層級點）、交戰分三級重要度、左右面板改分頁、全局／陣營視角、地圖降噪。
 * v2.3：預設「追蹤模式」——自由鏡頭、連續時鐘、點選部隊看指揮官／航跡／交戰對手、戰鬥序列清單、鎖定鏡頭。
 *       v2.2 的導演式播放（自動鏡頭、事件字卡、焦點淡化、主攻箭頭）收進「導覽模式」（?mode=tour 或右上膠囊鈕）。
 * 底圖：MapLibre GL JS，離線向量來源（Natural Earth GeoJSON：陸地、海面、國界、河流、經緯網）。
 * 戰況：兩個 MapLibre custom layer（WebGL）。
 *   terr ：軸心控制區形變＋包圍圈（多重多邊形）＋前線；放在海面層下面，讓海面蓋掉超出海岸的部分。
 *   battle：B 兵力（箭頭、船隊、部隊符號）、C 交戰、D 地名；放在最上面。
 * 每幀在 CPU 投影到螢幕像素，用 js/gl.js 一次批次畫完（不每幀 setData，軟體 GL 下差很多）。
 */
(() => {
'use strict';
const Q = new URLSearchParams(location.search);
const RM = matchMedia('(prefers-reduced-motion: reduce)').matches || Q.get('rm') === '1';
const $ = s => document.querySelector(s);
let DAY0 = 0, BID = '', INDEX = [], TH = {};
const dayOf = iso => (Date.parse(iso + 'T00:00:00Z') - DAY0) / 864e5;
const clamp = (v, a, b) => v < a ? a : v > b ? b : v;
const lerp = (a, b, t) => a + (b - a) * t;
const ease = t => 0.5 - 0.5 * Math.cos(Math.PI * t);
const sstep = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
const R = Math.PI / 180;
const mx = lon => lon * R, my = lat => Math.log(Math.tan(Math.PI / 4 + lat * R / 2));
const ilon = x => x / R, ilat = y => (2 * Math.atan(Math.exp(y)) - Math.PI / 2) / R;
const N = 420, NPK = 72;
const SEC_PER_DAY = 1.2;
let BBOX = [-180, -85, 180, 85], CITIES = [], SEAS = [], KEY_RIVERS = [], SIDE_NAME = { axis: '軸心', allied: '盟軍' }, SIDES = ['axis', 'allied'], AREAS = null, BASE_RING = null;
const rgba = (r, g, b, a) => [r / 255, g / 255, b / 255, a];
const COL = { sea: '#d6e1e7', land: '#f4f1ea', uk: '#f4f1ea', allied: '#e3eaf2', axis: '#e6c7bd', third: '#d3d7c3', paper: '#faf8f3', coast: '#8fa2ad', river: 'rgba(104,152,190,0.75)', border: 'rgba(80,72,60,0.3)' };
let VIEW = ['axis', 'allied', 'third'].includes(Q.get('side')) ? Q.get('side') : 'all', ENGM = {}, layOpen = false, oobTab = 'units', oobSide = VIEW === 'all' ? 'axis' : VIEW, infoTab = 'ov', KCAM = [];
const isEnemy = u => VIEW !== 'all' && u.side !== VIEW;
const AXIS_FILL = rgba(186, 66, 48, 0.24), ALLIED_FILL = rgba(227, 234, 242, 1);
const INK = [38, 32, 28], ACC = [214, 96, 20];   // 墨色、橘色（橘色只用在交戰和選取）
let D, MAP, W = 0, H = 0, DPR = 1, MOBILE = false;
let KD = [], FR = [], PKS = [], unitIdx = {}, posBy = {}, SP = {}, CITYIDX = {};
let day = 0, playing = false, speed = 1, lastT = 0, lastEventKey = -1, selected = null, hover = null, hits = [];
let TOUR = Q.get('mode') === 'tour';
let follow = TOUR && Q.get('follow') !== '0', resume = null, dtGlobal = 0.016;
let lockId = null, ASG = {};
// ---------- 圖層（醋酸片疊圖）----------
const LAYERS = {
  forces: { key: 'B', name: '兵力調動', mode: 'on', a: 1, tint: '226,220,206' },
  eng:    { key: 'C', name: '交戰',     mode: 'auto', a: 1, tint: '226,220,206' },
  places: { key: 'D', name: '地名與註記', mode: 'on', a: 1, tint: '226,220,206' },
};
['forces', 'eng', 'places'].forEach(k => { const v = Q.get('L' + k); if (v) LAYERS[k].mode = v; });
function layerTarget(k, S) {
  const L = LAYERS[k]; if (L.mode === 'on') return 1; if (L.mode === 'off') return 0;
  if (k === 'eng' && !TOUR) return 1;
  if (k === 'eng') { const kf = D.keyframes[S.u > 0.5 ? S.j : S.i]; return D.engagements.some(e => e.k === S.i || e.k === S.j) && (kf.focus || []).includes('engagements') ? 1 : 0; }
  return 1;
}
function stepLayers(S, dt) { for (const k in LAYERS) { const L = LAYERS[k], t = layerTarget(k, S); L.a = RM ? t : L.a + (t - L.a) * Math.min(1, dt * 5); if (Math.abs(L.a - t) < 0.01) L.a = t; } }
const shocks = [];

// ---------- 載入 ----------
const J = (u, dflt) => fetch(u).then(r => { if (!r.ok) throw new Error(u + ' ' + r.status); return r.json(); }).catch(e => { if (dflt !== undefined) return dflt; throw e; });
J('battles/index.json').then(idx => {
  INDEX = idx.battles || []; BID = Q.get('battle') || idx.default || (INDEX[0] || {}).id;
  if (!INDEX.some(b => b.id === BID)) BID = idx.default || INDEX[0].id;
  const base = `battles/${BID}/`;
  return Promise.all([J(Q.get('data') || base + 'battle.json'), J(Q.get('asg') || base + 'assignments.json', { assignments: [] }), J(base + 'theatre.json', {})]);
}).then(([data, asg, th]) => {
  TH = th; D = data; ['units', 'positions', 'fronts', 'arrows', 'engagements'].forEach(k => D[k] = D[k] || []);
  DAY0 = Date.parse(D.meta.date_start + 'T00:00:00Z'); BBOX = TH.bbox || BBOX; CITIES = TH.places || []; SEAS = TH.sea_labels || []; KEY_RIVERS = TH.key_rivers || [];
  for (const k in TH.sides || {}) SIDE_NAME[k] = TH.sides[k].name_zh || SIDE_NAME[k];
  if (TH.sides) SIDES = Object.keys(TH.sides).filter(k => PLATE[k]); if (!SIDES.includes(VIEW)) VIEW = 'all'; oobSide = VIEW === 'all' ? SIDES[0] : VIEW; D.areas = D.areas || [];
  D = data; ENGM = asg.engagements || {}; (asg.assignments || []).forEach(a => { if (a.role === 'commander') ASG[a.unit_id] = a; }); prep(); measure(); buildSprites(); initMap(); bindUI();
  const qd = Q.get('date'); if (qd) day = clamp(dayOf(qd), 0, KD[KD.length - 1]); if (Q.get('day')) day = clamp(+Q.get('day'), 0, KD[KD.length - 1]);
  setDay(day, true);
  if (Q.get('speed')) setSpeed(+Q.get('speed'));
  const vw = Q.get('view'); if (vw) { const [lo, la, z] = vw.split(',').map(Number); setFollow(false); MAP.jumpTo({ center: [lo, la], zoom: z }); }
  else applyCamera(performance.now());
  if (Q.get('sel')) { selectUnit(Q.get('sel'), !vw); if (Q.get('lock') === '1') setLock(Q.get('sel')); } else if (Q.get('eng')) selectEng(Q.get('eng'));   // v2.3：可以用網址直接開在某個部隊／交戰
  MAP.once('load', () => { const chk = () => { if (MAP.areTilesLoaded() && MAP.getLayer('battle')) { window.__ready = true; if (Q.get('autoplay') === '1') play(true); } else setTimeout(chk, 80); }; chk(); });
  requestAnimationFrame(loop);
}).catch(e => { console.error(e); const d = document.createElement('div'); d.id = 'fatal'; d.textContent = '戰役資料載入失敗：' + (e.message || e); document.body.appendChild(d); });

// ---------- 資料前處理 ----------
function resampleRing(pts, n, closed) {
  const p = pts.map(v => [mx(v[0]), my(v[1])]); if (closed) p.push(p[0]);
  const cum = [0]; for (let i = 1; i < p.length; i++) cum.push(cum[i - 1] + Math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]));
  const L = cum[cum.length - 1], out = new Float64Array(n * 2); let j = 0;
  for (let k = 0; k < n; k++) { const s = L * k / (closed ? n : n - 1); while (j < p.length - 2 && cum[j + 1] < s) j++;
    const t = (s - cum[j]) / ((cum[j + 1] - cum[j]) || 1); out[2 * k] = lerp(p[j][0], p[j + 1][0], t); out[2 * k + 1] = lerp(p[j][1], p[j + 1][1], t); }
  return out;
}
function ringArea(pts) { let a = 0; for (let i = 0; i < pts.length; i++) { const p = pts[i], q = pts[(i + 1) % pts.length]; a += p[0] * q[1] - q[0] * p[1]; } return a; }
function smoothPath(pts, seg = 10) {
  const p = pts.map(v => [mx(v[0]), my(v[1])]), out = [];
  for (let i = 0; i < p.length - 1; i++) { const p0 = p[i - 1] || p[i], p1 = p[i], p2 = p[i + 1], p3 = p[i + 2] || p2;
    for (let s = 0; s < seg; s++) { const t = s / seg, t2 = t * t, t3 = t2 * t;
      out.push([0.5 * (2 * p1[0] + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3),
        0.5 * (2 * p1[1] + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)]); } }
  out.push(p[p.length - 1]); return out;
}
const TIER = { front: 0, army: 0, corps: 1, division: 2, brigade: 2 };
// 「取代型」上級：放大展開後自己隱藏（子單位就是它的全部）；其他上級（集團軍）保留，子單位另外出現
// 把一個環整理成固定點數、逆時針、起點對齊（從最北偏中的點開始），兩個關鍵日之間才能逐點內插
function ringPrep(ring, n) { let r = ring.map(p => [p[0], p[1]]); if (ringArea(r) < 0) r.reverse();
  const s = resampleRing(r, n, true); let cx = 0, cy = 0; for (let k = 0; k < n; k++) { cx += s[2 * k]; cy += s[2 * k + 1]; } cx /= n; cy /= n;
  let best = 0, bd = -1e9; for (let k = 0; k < n; k++) { const v = s[2 * k + 1] - cy - Math.abs(s[2 * k] - cx); if (v > bd) { bd = v; best = k; } }
  const a = new Float64Array(n * 2); for (let k = 0; k < n; k++) { const q = (best + k) % n; a[2 * k] = s[2 * q]; a[2 * k + 1] = s[2 * q + 1]; }
  return { ring: a, cx, cy }; }
const NA = 64;
// v2.8「勢力場」控制區：每個關鍵日把各方的範圍畫成點陣，算出「到自己邊界的有號距離」，存成一張浮點貼圖（R 軸心、G 盟軍、B 第三方、A 中立）。
// 兩個關鍵日之間把距離線性內插，每個點歸距離最大的那一方 → 任何時刻都是完整分割：不會重疊、不會留縫，口袋會自己平順縮小。
// 前線＝盟軍與敵方距離相等的那條線，由著色器直接畫（碰到中立國就不畫）。
let FLD = null;
function edt2(g, w, h) { const n = Math.max(w, h), INF = 1e20, f = new Float64Array(n), v = new Int32Array(n), z = new Float64Array(n + 1);
  const run = (off, st, len) => { for (let q = 0; q < len; q++) f[q] = g[off + q * st]; let k = 0; v[0] = 0; z[0] = -INF; z[1] = INF;
    for (let q = 1; q < len; q++) { let sx; do { const r = v[k]; sx = (f[q] - f[r] + q * q - r * r) / (q - r) / 2; } while (sx <= z[k] && --k > -1); k++; v[k] = q; z[k] = sx; z[k + 1] = INF; }
    k = 0; for (let q = 0; q < len; q++) { while (z[k + 1] < q) k++; const r = v[k]; g[off + q * st] = f[r] + (q - r) * (q - r); } };
  for (let x = 0; x < w; x++) run(x, w, h); for (let y = 0; y < h; y++) run(y * w, 1, w); }
function prepAreas() { const C = TH.control; if (!C || C.mode !== 'areas') return;
  const B = C.border; BASE_RING = new Float64Array(B.length * 2); B.forEach((p, i) => { BASE_RING[2 * i] = mx(p[0]); BASE_RING[2 * i + 1] = my(p[1]); });
  AREAS = D.keyframes.map(k => { const o = {}; D.areas.filter(a => a.date === k.date).forEach(a => { o[a.id] = Object.assign(ringPrep(a.ring, NA), { id: a.id, side: a.side, name: a.name_zh || '' }); }); return o; });
  J(`battles/${BID}/geo/landc.geojson`, { features: [] }).then(buildFields); }
function buildFields(landc) { const C = TH.control, t0 = performance.now();
  const x0 = mx(BBOX[0]), x1 = mx(BBOX[2]), y0 = my(BBOX[1]), y1 = my(BBOX[3]), GW = innerWidth <= 700 ? 448 : 640, GH = Math.round(GW * (y1 - y0) / (x1 - x0)), NP = GW * GH;
  const cv = document.createElement('canvas'); cv.width = GW; cv.height = GH; const g = cv.getContext('2d', { willReadFrequently: true });
  const CH = { axis: '#f00', allied: '#0f0', third: '#00f' }, gx = lo => (mx(lo) - x0) / (x1 - x0) * GW, gy = la => (y1 - my(la)) / (y1 - y0) * GH;
  const poly = (rings, col) => { g.fillStyle = col; g.beginPath(); for (const r of rings) { r.forEach((p, k) => k ? g.lineTo(gx(p[0]), gy(p[1])) : g.moveTo(gx(p[0]), gy(p[1]))); g.closePath(); } g.fill('evenodd'); };
  const under = C.under_ids || [], a = new Float64Array(NP), o = new Float64Array(NP), n = new Float64Array(NP), m = new Uint8Array(NP);
  D.keyframes.forEach((kf, ki) => { g.fillStyle = '#000'; g.fillRect(0, 0, GW, GH);
    for (const f of landc.features) { const col = CH[f.properties.k]; if (!col || !f.geometry) continue; (f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates).forEach(rs => poly(rs, col)); }
    poly([C.border], CH[C.base_side || 'axis']);
    const ar = D.areas.filter(q => q.date === kf.date);
    for (const [side, un] of [['allied', true], ['third', false], ['allied', false]]) ar.forEach(q => { if (q.side === side && under.includes(q.id) === un) poly([q.ring], CH[side]); });
    const px = g.getImageData(0, 0, GW, GH).data, out = new Float32Array(NP * 4);
    // 各方的有號距離：自己範圍內＝到「其他交戰方」的距離（中立國界不算邊界，否則夾在中立國之間的狹長地帶會整塊同時易手）；範圍外＝負的到自己的距離
    const outer = v => v === 1 ? 0 : v === 0 ? 1e20 : Math.pow(Math.max(0, 0.5 - v), 2);
    // 「夠厚」＝3×3 全是：描邊留下的半透明細邊、不到兩格寬的碎片不算距離的起點，否則會被當成近在咫尺的另一方
    const thick = (src, dst) => { let cnt = 0; for (let y = 0; y < GH; y++) for (let x = 0; x < GW; x++) { const i = y * GW + x; let ok = src[i] && x > 0 && y > 0 && x < GW - 1 && y < GH - 1; if (ok) for (let dy = -1; dy <= 1 && ok; dy++) for (let dx = -1; dx <= 1; dx++) if (!src[i + dy * GW + dx]) { ok = 0; break; } dst[i] = ok ? 0 : 1e20; if (ok) cnt++; } return cnt; };
    for (let c = 0; c < 3; c++) { const c1 = (c + 1) % 3, c2 = (c + 2) % 3; let any = false;
      for (let i = 0; i < NP; i++) { const v = px[4 * i + c] / 255; a[i] = v; m[i] = v >= 0.5 ? 1 : 0; if (m[i]) any = true; }
      if (!any) { for (let i = 0; i < NP; i++) out[4 * i + c] = -1000; continue; }
      const sub = thick(m, o) ? 1.5 : 0.5; if (sub === 0.5) for (let i = 0; i < NP; i++) o[i] = m[i] ? 0 : 1e20;   // 整個範圍都很小（例如只剩一個據點）：退回用全部像素
      for (let i = 0; i < NP; i++) m[i] = px[4 * i + c1] + px[4 * i + c2] >= 128 ? 1 : 0; thick(m, n);
      edt2(o, GW, GH); edt2(n, GW, GH);
      for (let i = 0; i < NP; i++) out[4 * i + c] = clamp(a[i] >= 0.5 ? Math.max(a[i] - 0.5, Math.sqrt(n[i]) - 1.5) : -Math.max(0.5 - a[i], Math.sqrt(o[i]) - sub), -1000, 1000); }
    for (let i = 0; i < NP; i++) { const v = clamp(1 - (px[4 * i] + px[4 * i + 1] + px[4 * i + 2]) / 255, 0, 1); o[i] = outer(v); n[i] = v === 1 ? 1e20 : v === 0 ? 0 : Math.pow(Math.max(0, v - 0.5), 2); }
    edt2(o, GW, GH); edt2(n, GW, GH); for (let i = 0; i < NP; i++) out[4 * i + 3] = clamp(Math.sqrt(n[i]) - Math.sqrt(o[i]), -1000, 1000);
    if (Q.get('dbg') === 'fld') (window.__fld = window.__fld || [])[ki] = out;
    BGL.fieldTex('k' + ki, GW, GH, out); });
  const flat = Array.from(BASE_RING), idx = earcut(flat), from = C.side_from && C.side_from.third ? dayOf(C.side_from.third) : null;
  FLD = { x0, x1, y0, y1, flat, idx, from, gw: GW, gh: GH }; window.__fieldMs = Math.round(performance.now() - t0); if (MAP) MAP.triggerRepaint(); }
const hexc = h => [parseInt(h.slice(1, 3), 16) / 255, parseInt(h.slice(3, 5), 16) / 255, parseInt(h.slice(5, 7), 16) / 255, 1];
function drawAreas() { F.pockets = []; if (!FLD) return; const S = F.S, L = FLD;
  const U = x => (x - L.x0) / (L.x1 - L.x0), V = y => (L.y1 - y) / (L.y1 - L.y0);
  const com = { a: 'k' + S.i, b: 'k' + S.j, e: S.e || 0, gate: L.from != null && day < L.from, dpr: DPR, ppc: (L.x1 - L.x0) * SC / L.gw, c0: hexc(COL.axis), c1: hexc(COL.allied), c2: hexc(COL.third), ink: rgba(...INK, 0.92), lc: rgba(...SIDE_COL.third, 0.75) };
  const fv = new Float32Array(L.idx.length * 4); L.idx.forEach((q, k) => { const x = L.flat[2 * q], y = L.flat[2 * q + 1]; fv[4 * k] = PX(x); fv[4 * k + 1] = PY(y); fv[4 * k + 2] = U(x); fv[4 * k + 3] = V(y); });
  BGL.field(Object.assign({ mode: 0, verts: fv }, com));
  const X0 = PX(L.x0), X1 = PX(L.x1), Y0 = PY(L.y1), Y1 = PY(L.y0);
  BGL.field(Object.assign({ mode: 1, verts: new Float32Array([X0, Y0, 0, 0, X1, Y0, 1, 0, X1, Y1, 1, 1, X0, Y0, 0, 0, X1, Y1, 1, 1, X0, Y1, 0, 1]) }, com));
  // 口袋名稱（放大才顯示）：位置在兩個關鍵日之間內插；只存在於其中一天的，淡入或淡出
  const ai = AREAS[S.i], aj = AREAS[S.j];
  for (const id of new Set([...Object.keys(ai), ...Object.keys(aj)])) { const p = ai[id], q = aj[id], meta = p || q; if (!meta.name) continue;
    const ra = p && q ? 1 : S.i === S.j ? 1 : p ? 1 - sstep(0.4, 0.9, S.e) : sstep(0.3, 0.9, S.e);
    F.pockets.push({ pp: [], meta, ra, cx: PX(p && q ? lerp(p.cx, q.cx, S.e) : meta.cx), cy: PY(p && q ? lerp(p.cy, q.cy, S.e) : meta.cy) }); } }
function prep() {
  KD = D.keyframes.map(k => dayOf(k.date)); prepAreas();
  const fr = D.keyframes.map(k => D.fronts.find(f => f.date === k.date));
  FR = fr.map(f => f && f.line ? resampleRing(f.line, N, false) : null);
  // 包圍圈：每個 id 在每個關鍵日的形狀（逆時針、起點對齊）
  PKS = fr.map(f => { const o = {}; ((f && f.pockets) || []).forEach(p => { let r = p.ring.slice(); if (ringArea(r) < 0) r.reverse();
    const s = resampleRing(r, NPK, true); let cx = 0, cy = 0; for (let k = 0; k < NPK; k++) { cx += s[2 * k]; cy += s[2 * k + 1]; } cx /= NPK; cy /= NPK;
    // 起點對齊：從正北方向最近的點開始
    let best = 0, bd = -1e9; for (let k = 0; k < NPK; k++) { const v = s[2 * k + 1] - cy - Math.abs(s[2 * k] - cx); if (v > bd) { bd = v; best = k; } }
    const a = new Float64Array(NPK * 2); for (let k = 0; k < NPK; k++) { const q = (best + k) % NPK; a[2 * k] = s[2 * q]; a[2 * k + 1] = s[2 * q + 1]; }
    o[p.id] = { id: p.id, side: p.side, name: p.name_zh, ring: a, cx, cy }; }); return o; });
  D.units.forEach(u => { unitIdx[u.id] = u; posBy[u.id] = {}; });
  D.positions.forEach(p => { posBy[p.unit_id][p.date] = p; });
  D.arrows.forEach(a => { a.k = D.keyframes.findIndex(k => k.date === a.date); a.sm = smoothPath(a.path); });
  D.engagements.forEach(e => { e.k = D.keyframes.findIndex(k => k.date === e.date); e.x = mx(e.lng); e.y = my(e.lat);
    const em = ENGM[e.id] || {}; e.imp = e.importance || em.importance || 1; e.sum = e.summary_zh || em.summary_zh || ''; e.label = e.name_zh.replace(/（示例）/, '');
    // v2.3：交戰是一段時間。資料有 from／to 就用；沒有就當作關鍵日前後各半天
    const END = KD[KD.length - 1]; e.t0 = clamp(e.from ? dayOf(e.from) : dayOf(e.date) - 0.5, 0, END); e.t1 = clamp(e.to ? dayOf(e.to) : dayOf(e.date) + 0.5, 0, END); });
  D.units.forEach(u => { u.kpos = D.keyframes.map(k => { const p = posBy[u.id][k.date]; return p ? { x: mx(p.lng), y: my(p.lat), st: p.state } : null; }); });
  D.units.forEach(u => { u.children = D.units.filter(c => c.parent_id === u.id).map(c => c.id); u.tier = u.tier ?? TIER[u.echelon] ?? 1; u.replace = (TH.replace_units || []).includes(u.id) || u.replace === true; u._st = 0; u._sa = 0; });
  D.keyframes.forEach(k => { const f = new Set(k.focus_units || []);
    for (let r = 0; r < 3; r++) D.units.forEach(u => { if (u.parent_id && f.has(u.parent_id)) f.add(u.id); });
    D.units.forEach(u => { if (u.parent_id && (k.focus_units || []).includes(u.id)) f.add(u.parent_id); }); k.fset = f; });
  const pr = { armor: 0, counter: 1, motorized: 2, infantry: 3, retreat: 4 };
  D.keyframes.forEach((k, i) => { const arr = D.arrows.filter(a => a.k === i && a.kind !== 'naval');
    arr.sort((a, b) => (k.fset.has(b.unit_id) - k.fset.has(a.unit_id)) || (pr[a.kind] - pr[b.kind])); arr.forEach((a, n) => a.show = n < 3);
    D.arrows.filter(a => a.k === i && a.kind === 'naval').forEach((a, n) => a.show = n < 1); });
  D.engagements.forEach(e => { const k = D.keyframes[e.k]; e.focus = e.units.some(x => k.fset.has(x.unit_id)); });
  CITIES.forEach(c => CITYIDX[c[0]] = c);
}

// ---------- 鏡頭 ----------
let CAM = {};
function measure() { MOBILE = innerWidth <= 700; const r = $('#map-wrap').getBoundingClientRect(); W = Math.round(r.width); H = Math.round(r.height); DPR = +(Q.get('pr') || Math.min(devicePixelRatio || 1, MOBILE ? 2 : 1.5));
  ['overview', 'mid', 'close'].forEach(n => CAM[n] = camFor(n)); KCAM = D.keyframes.map((k, i) => evCam(i)); }
function evCam(i) { const k = D.keyframes[i], pts = [];
  D.engagements.forEach(e => { if (e.k === i) pts.push([e.x, e.y]); });
  (k.focus_units || []).forEach(id => { const u = unitIdx[id], p = u && u.kpos && u.kpos[i]; if (p) pts.push([p.x, p.y]); });
  if (!pts.length) return CAM[k.camera];
  const x0 = Math.min(...pts.map(p => p[0])), x1 = Math.max(...pts.map(p => p[0])), y0 = Math.min(...pts.map(p => p[1])), y1 = Math.max(...pts.map(p => p[1]));
  const padX = MOBILE ? 44 : 170, padT = MOBILE ? 120 : 110, padB = MOBILE ? 60 : 90;
  const z = clamp(Math.log2(Math.min((W - 2 * padX) / Math.max(x1 - x0, 1e-5), (H - padT - padB) / Math.max(y1 - y0, 1e-5)) * 2 * Math.PI / 512), CAM.overview.z, 7.9 - (MOBILE ? 0.9 : 0));
  const sc = 512 * Math.pow(2, z) / (2 * Math.PI); return { x: (x0 + x1) / 2, y: (y0 + y1) / 2 + (padT - padB) / 2 / sc, z }; }
function gotoChapter(i) { pause(); lastEventKey = i; const c = MAP.getCenter(); setDay(KD[i], true);
  if (TOUR) { follow = true; $('#follow').hidden = true; resume = { t0: performance.now(), x: mx(c.lng), y: my(c.lat), z: MAP.getZoom() }; }
  else { const k = KCAM[i]; MAP.easeTo({ center: [ilon(k.x), ilat(k.y)], zoom: k.z, duration: RM ? 0 : 900 }); }
  if (MOBILE) window.__setOob(false); infoKey = ''; refreshInfo(true); }
function camFor(name) {
  const b = (MOBILE && D.meta.cameras_mobile ? D.meta.cameras_mobile : D.meta.cameras)[name]; const padT = MOBILE ? 56 : 34, padB = MOBILE ? 56 : 28, padX = MOBILE ? 6 : 40;
  const x0 = mx(b[0]), x1 = mx(b[2]), y0 = my(b[1]), y1 = my(b[3]);
  const s = Math.min((W - 2 * padX) / (x1 - x0), (H - padT - padB) / (y1 - y0));
  return { x: (x0 + x1) / 2, y: (y0 + y1) / 2 + (padT - padB) / 2 / s, z: Math.log2(s * 2 * Math.PI / 512) };
}
function segIndex(d) { let i = 0; while (i < KD.length - 2 && d >= KD[i + 1]) i++; return i; }
function camAt(d) {
  const i = segIndex(d), a = KCAM[i], b = KCAM[Math.min(i + 1, KD.length - 1)];
  if (a === b) return a; const u = (d - KD[i]) / (KD[i + 1] - KD[i]); const t = RM ? (u >= 1 ? 1 : 0) : ease(clamp((u - 0.35) / 0.6, 0, 1));
  return { x: lerp(a.x, b.x, t), y: lerp(a.y, b.y, t), z: lerp(a.z, b.z, t) };
}
function applyCamera(now) {
  if (!TOUR || !follow) { applyLock(); return; } let c = camAt(day);
  if (resume) { const t = ease(clamp((now - resume.t0) / 900, 0, 1)); c = { x: lerp(resume.x, c.x, t), y: lerp(resume.y, c.y, t), z: lerp(resume.z, c.z, t) }; if (t >= 1) resume = null; }
  const cur = MAP.getCenter(), z0 = MAP.getZoom(); const lo = ilon(c.x), la = ilat(c.y);
  if (Math.abs(cur.lng - lo) < 1e-7 && Math.abs(cur.lat - la) < 1e-7 && Math.abs(z0 - c.z) < 1e-6) return;
  MAP.jumpTo({ center: [lo, la], zoom: c.z });
}
function setFollow(v) { if (v && !follow) { const c = MAP.getCenter(); resume = { t0: performance.now(), x: mx(c.lng), y: my(c.lat), z: MAP.getZoom() }; }
  follow = v; $('#follow').hidden = v || !TOUR; }

// ---------- 地圖 ----------
function initMap() {
  const src = n => ({ type: 'geojson', data: `battles/${BID}/geo/${n}.geojson`, maxzoom: 7, tolerance: 0.3, buffer: 16 });
  const style = { version: 8, sources: { land: src('land'), landc: src('landc'), rivers: src('rivers'), borders: src('borders'), sea: src('sea'), grat: src('graticule') },
    layers: [
      { id: 'bg', type: 'background', paint: { 'background-color': COL.sea } },
      { id: 'land', type: 'fill', source: 'landc', paint: { 'fill-antialias': false, 'fill-color': ['match', ['get', 'k'], 'allied', COL.allied, 'uk', COL.uk, 'axis', COL.axis, 'third', COL.third, COL.land] } },
      { id: 'sea', type: 'fill', source: 'sea', paint: { 'fill-color': COL.sea, 'fill-antialias': false } },
      // v2.2：海上經緯網與海岸外光拿掉（軟體 GL 下這兩層加起來約 2–3 ms／幀），只留 1px 海岸線；放大到 7.5 級以上再加回經緯網
      { id: 'grat', type: 'line', source: 'grat', minzoom: 7.5, paint: { 'line-color': 'rgba(70,100,120,0.10)', 'line-width': 1 } },
      { id: 'coast', type: 'line', source: 'land', paint: { 'line-color': COL.coast, 'line-width': 1.1 } },
      // 戰役相關河流（默茲、斯海爾德、摩澤爾、萊茵）一直顯示；其他河流放大到 7 級以上才出現（也省軟體 GL 的填色成本）
      { id: 'rivers', type: 'line', source: 'rivers', filter: ['in', ['get', 'name'], ['literal', KEY_RIVERS]], paint: { 'line-color': COL.river, 'line-width': ['interpolate', ['linear'], ['zoom'], 6, 0.9, 9, 1.8] } },
      { id: 'rivers-other', type: 'line', source: 'rivers', minzoom: 8, filter: ['!', ['in', ['get', 'name'], ['literal', KEY_RIVERS]]], paint: { 'line-color': COL.river, 'line-width': 0.9 } },
      // 國界：實線細線（虛線 SDF 在軟體 GL 下每像素多一次貼圖查詢）
      { id: 'borders', type: 'line', source: 'borders', paint: { 'line-color': COL.border, 'line-width': 1, 'line-dasharray': [2, 2] } },
    ] };
  const c0 = CAM.overview;
  // 戰區外留一圈紙色邊（可以縮小到看見整個戰區，不會卡在邊界）；底圖資料只到 bbox，外面用紙色蓋掉
  const PADX = (BBOX[2] - BBOX[0]) * 0.2, PADY = (BBOX[3] - BBOX[1]) * 0.2, bb = [[BBOX[0], BBOX[1]], [BBOX[2], BBOX[1]], [BBOX[2], BBOX[3]], [BBOX[0], BBOX[3]], [BBOX[0], BBOX[1]]];
  MAP = new maplibregl.Map({ container: 'map', style, center: [ilon(c0.x), ilat(c0.y)], zoom: c0.z, minZoom: (TH.min_zoom || 4.6) - 0.8, maxZoom: 10.5, maxBounds: [[BBOX[0] - PADX, Math.max(BBOX[1] - PADY, -80)], [BBOX[2] + PADX, Math.min(BBOX[3] + PADY, 80)]],
    dragRotate: false, pitchWithRotate: false, touchPitch: false, keyboard: false, fadeDuration: 0, attributionControl: false, pixelRatio: DPR, antialias: false, renderWorldCopies: false, maxTileCacheSize: 200 });
  MAP.touchZoomRotate.disableRotation();
  MAP.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right');
  MAP.addControl(new maplibregl.AttributionControl({ compact: true, customAttribution: '底圖：Natural Earth（公有領域）｜MapLibre GL JS' }), 'bottom-right');
  MAP.on('load', () => { if (TH.control && TH.control.border) { const B = TH.control.border, runs = []; let run = [];
      for (let i = 0; i <= B.length; i++) { const p = B[i % B.length]; run.push([p[0], p[1]]); if (p[2] === 'sea' || i === B.length) { if (run.length > 1) runs.push(run); run = []; } }
      MAP.addSource('hist', { type: 'geojson', data: { type: 'Feature', properties: {}, geometry: { type: 'MultiLineString', coordinates: runs } } });
      MAP.addLayer({ id: 'hist', type: 'line', source: 'hist', paint: { 'line-color': 'rgba(60,52,44,0.62)', 'line-width': 1.3, 'line-dasharray': [5, 2, 1, 2] } });
      MAP.setPaintProperty('borders', 'line-color', 'rgba(80,72,60,0.13)'); }
    MAP.addSource('mat', { type: 'geojson', data: { type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [[[-179, -84], [179, -84], [179, 84], [-179, 84], [-179, -84]], bb.slice().reverse()] } } });
    MAP.addLayer({ id: 'mat', type: 'fill', source: 'mat', paint: { 'fill-color': COL.paper, 'fill-antialias': false } });
    MAP.addSource('frame', { type: 'geojson', data: { type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: bb } } });
    MAP.addLayer({ id: 'frame', type: 'line', source: 'frame', paint: { 'line-color': 'rgba(60,52,44,0.55)', 'line-width': 1 } });
    MAP.addLayer(terrLayer, 'sea'); MAP.addLayer(battleLayer); document.querySelectorAll('.maplibregl-compact-show').forEach(e => e.classList.remove('maplibregl-compact-show'));
    (Q.get('hide') || '').split(',').filter(Boolean).forEach(l => MAP.getLayer(l) && MAP.setLayoutProperty(l, 'visibility', 'none')); });   // 除錯／量測用
  MAP.on('movestart', e => { if (e.originalEvent && TOUR) setFollow(false); });
  MAP.on('dragstart', () => { if (lockId) setLock(null); });
  window.__map = MAP;
}
const terrLayer = { id: 'terr', type: 'custom', renderingMode: '2d', onAdd(m, gl) { BGL.init(gl); }, render(gl) { computeFrame(); BGL.begin(); drawTerritory(); BGL.flush(W, H); } };
const battleLayer = { id: 'battle', type: 'custom', renderingMode: '2d', onAdd(m, gl) { BGL.init(gl); }, render(gl) { BGL.begin(); drawTop(); BGL.flush(W, H); } };

// ---------- 符號圖集 ----------
function textCanvas(txt, font, fill, stroke, sw, dot) {
  const c = document.createElement('canvas'), g = c.getContext('2d'); g.font = font; const tw = g.measureText(txt).width; const fs = parseFloat(font.match(/(\d+(\.\d+)?)px/)[1]);
  const pad = sw + 2, dx = dot ? 8 : 0, w = Math.ceil(tw + pad * 2 + dx), h = Math.ceil(fs * 1.4 + pad * 2);
  c.width = Math.ceil(w * DPR); c.height = Math.ceil(h * DPR); g.scale(DPR, DPR); g.font = font; g.textBaseline = 'middle'; g.lineJoin = 'round';
  if (dot) { g.fillStyle = '#3a342d'; g.strokeStyle = 'rgba(255,255,255,0.95)'; g.lineWidth = 2; g.beginPath(); g.arc(pad + 2.5, h / 2 + fs * 0.35, 2.3, 0, 7); g.stroke(); g.fill(); }
  if (sw) { g.strokeStyle = stroke; g.lineWidth = sw; g.strokeText(txt, pad + dx, h / 2); } g.fillStyle = fill; g.fillText(txt, pad + dx, h / 2);
  return { c, w, h, ax: dot ? pad + 2.5 : w / 2, ay: dot ? h / 2 + fs * 0.35 : h / 2 };
}
// v2.4：自畫部隊牌。一塊陣營色的牌子＝兵種圖示＋番號；牌子底下的小點＝層級（1 旅、2 師、3 軍、4 集團軍）
const PLATE = { axis: '#b8402f', allied: '#2f5d9b', third: '#5c7a3a' };   // 三個顏色位置；顯示名稱由 theatre.json 的 sides 決定
function drawGlyph(g, br) { g.fillStyle = '#fff'; g.strokeStyle = '#fff'; g.lineCap = 'round'; g.lineJoin = 'round'; g.beginPath();
  if (br === 'armor') { g.roundRect(0, 7, 16, 5, 2.5); g.rect(2.5, 4, 11, 3.4); g.rect(5, 1, 6, 3.4); g.fill(); g.beginPath(); g.lineWidth = 1.6; g.moveTo(11, 2.6); g.lineTo(16, 2.6); g.stroke(); }
  else if (br === 'motorized') { g.rect(0, 2, 9.5, 7); g.rect(10.5, 4.5, 5, 4.5); g.fill(); g.beginPath(); g.arc(3.5, 10, 2, 0, 7); g.fill(); g.beginPath(); g.arc(12, 10, 2, 0, 7); g.fill(); }
  else if (br === 'air') { g.lineWidth = 2.2; g.moveTo(8, 0.8); g.lineTo(8, 11.2); g.moveTo(1, 5); g.lineTo(15, 5); g.stroke(); g.beginPath(); g.lineWidth = 1.6; g.moveTo(5, 11); g.lineTo(11, 11); g.stroke(); }
  else if (br === 'naval') { g.moveTo(0.5, 7); g.lineTo(15.5, 7); g.lineTo(12.5, 11.5); g.lineTo(3.5, 11.5); g.closePath(); g.rect(5, 3.6, 6, 3); g.fill(); g.beginPath(); g.lineWidth = 1.4; g.moveTo(8, 0.5); g.lineTo(8, 4); g.stroke(); }
  else { g.arc(8, 8.2, 6.2, Math.PI, 0); g.closePath(); g.rect(0.5, 8, 15, 2.6); g.fill(); } }
function counterCanvas(u, forceK) { const k = forceK || (MOBILE ? 0.84 : 1) * (u.tier === 0 ? 1.12 : u.tier === 1 ? 1 : 0.9); const lab = u.label || '';
  const c = document.createElement('canvas'), g = c.getContext('2d'); const font = `700 ${12 * k}px "Noto Sans CJK TC",system-ui,sans-serif`; g.font = font; const tw = lab ? g.measureText(lab).width : 0;
  const gw = 16 * k, pad = 5 * k, h = Math.round(21 * k), w = Math.ceil(pad + gw + (lab ? 4 * k + tw : 0) + pad), m = 2, pipH = 5;
  c.width = Math.ceil((w + 2 * m) * DPR); c.height = Math.ceil((h + 2 * m + pipH) * DPR); g.scale(DPR, DPR); g.translate(m, m);
  g.beginPath(); g.roundRect(0, 0, w, h, 4.5 * k); g.lineWidth = 3; g.strokeStyle = 'rgba(255,255,255,.96)'; g.stroke(); g.fillStyle = PLATE[u.side]; g.fill();
  g.save(); g.translate(pad, (h - 12 * k) / 2); g.scale(k, k); drawGlyph(g, u.branch); g.restore();
  if (lab) { g.font = font; g.fillStyle = '#fff'; g.textBaseline = 'middle'; g.fillText(lab, pad + gw + 4 * k, h / 2 + 0.5); }
  const n = { brigade: 1, division: 2, corps: 3, army: 4, front: 5 }[u.echelon] || 0; for (let i = 0; i < n; i++) { const x = w / 2 - (n * 5 - 2) / 2 + i * 5; g.fillStyle = '#fff'; g.fillRect(x - 0.8, h + 1.4, 4.6, 4.2); g.fillStyle = PLATE[u.side]; g.fillRect(x, h + 2.2, 3, 2.6); }
  return { cv: c, w: w + 2 * m, h: h + 2 * m + pipH }; }
function buildSprites() {
  const A = BGL.Atlas(DPR, 2048); const add = (cv, w, h, ax, ay) => A.add(cv, w, h, ax, ay);
  SP.unit = {};
  D.units.forEach(u => { const c = counterCanvas(u); const sp = add(c.cv, c.w, c.h); SP.unit[u.id] = [sp, sp]; });
  const disc = (txt, bg, d = 16, fsz = 10) => { const c = document.createElement('canvas'); c.width = c.height = Math.round(d * DPR); const g = c.getContext('2d'); g.scale(DPR, DPR);
    g.fillStyle = bg; g.beginPath(); g.arc(d / 2, d / 2, d / 2 - 0.5, 0, 7); g.fill(); g.strokeStyle = '#fff'; g.lineWidth = 1.5; g.stroke();
    g.fillStyle = '#fff'; g.font = `700 ${fsz}px "Noto Sans CJK TC",sans-serif`; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(txt, d / 2, d / 2 + 0.5); return add(c, d, d); };
  SP.badge = { attack: disc('攻', '#d8341f'), defend: disc('守', '#2f6fd0'), retreat: disc('退', '#7d6a3a'), encircled: disc('圍', '#8a1f6a'), surrendered: disc('降', '#555'), evacuating: disc('撤', '#1b8a9a') };
  SP.count = {}; for (let n = 1; n <= 12; n++) { const c = document.createElement('canvas'); const w = n >= 10 ? 26 : 22, h = 15; c.width = Math.round(w * DPR); c.height = Math.round(h * DPR); const g = c.getContext('2d'); g.scale(DPR, DPR);
    g.fillStyle = '#ffffff'; g.strokeStyle = 'rgba(38,32,28,0.55)'; g.lineWidth = 1; g.beginPath(); g.roundRect(0.5, 0.5, w - 1, h - 1, 7); g.fill(); g.stroke();
    g.fillStyle = '#26201c'; g.font = '700 10.5px "Noto Sans CJK TC",sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('+' + n, w / 2, h / 2 + 0.5); SP.count[n] = add(c, w, h); }
  { const c = document.createElement('canvas'), d = 22; c.width = c.height = Math.round(d * DPR); const g = c.getContext('2d'); g.scale(DPR, DPR); g.translate(11, 11);   // 交戰記號：橘色圓點＋白色交叉
    g.fillStyle = '#fff'; g.beginPath(); g.arc(0, 0, 10.5, 0, 7); g.fill(); g.fillStyle = '#d66014'; g.beginPath(); g.arc(0, 0, 8.6, 0, 7); g.fill();
    g.strokeStyle = '#fff'; g.lineWidth = 2.2; g.lineCap = 'round'; g.beginPath(); g.moveTo(-3.6, -3.6); g.lineTo(3.6, 3.6); g.moveTo(3.6, -3.6); g.lineTo(-3.6, 3.6); g.stroke(); SP.swords = add(c, d, d); }
  { const c = document.createElement('canvas'), d = 16; c.width = c.height = Math.round(d * DPR); const g = c.getContext('2d'); g.scale(DPR, DPR); const r = g.createRadialGradient(8, 8, 0, 8, 8, 8);
    r.addColorStop(0, 'rgba(47,93,155,1)'); r.addColorStop(0.4, 'rgba(47,93,155,0.6)'); r.addColorStop(1, 'rgba(47,93,155,0)'); g.fillStyle = r; g.fillRect(0, 0, d, d); SP.ship = add(c, 8, 8); }
  const fs = MOBILE ? 11 : 13; SP.city = {};
  CITIES.forEach(([n]) => { const t = textCanvas(n, `500 ${fs}px "Noto Sans CJK TC",sans-serif`, '#3a342d', 'rgba(255,255,255,0.92)', 3.5, true); SP.city[n] = add(t.c, t.w, t.h, t.ax, t.ay + fs * 0.0); SP.city[n].tw = t.w; SP.city[n].th = t.h; });
  SP.sheet = {}; for (const k of SHEET_ORDER) { const L = LAYERS[k]; const fs2 = MOBILE ? 9.5 : 11; const t = textCanvas(`${L.key}｜${L.name}`, `700 ${fs2}px "Noto Sans CJK TC",sans-serif`, 'rgba(226,220,206,0.75)', null, 0, false);
    const c2 = document.createElement('canvas'); c2.width = t.c.width; c2.height = t.c.height; const g2 = c2.getContext('2d'); g2.fillStyle = 'rgba(226,220,206,0.10)'; g2.fillRect(0, Math.round(3 * DPR), c2.width, c2.height - Math.round(6 * DPR)); g2.drawImage(t.c, 0, 0); SP.sheet[k] = add(c2, t.w, t.h, 0, 0); }
  SP.sea = SEAS.map(([n]) => { const t = textCanvas(n, `italic ${MOBILE ? 12 : 15}px "Noto Serif CJK TC",serif`, 'rgba(84,112,130,0.75)', null, 0, false); return add(t.c, t.w, t.h); });
  BGL.setAtlas(A.cv); window.__atlas = A.cv;
}

// ---------- 每幀狀態 ----------
function state(d) {
  const i = segIndex(d), j = Math.min(i + 1, KD.length - 1);
  const u = j === i ? 0 : clamp((d - KD[i]) / (KD[j] - KD[i]), 0, 1), e = RM ? (u < 1 ? 0 : 1) : (TOUR ? ease(u) : u);   // 追蹤模式：等速內插，部隊不會在每個關鍵日頓一下
  return { i, j, u, e, atKey: Math.min(Math.abs(d - KD[i]), Math.abs(d - KD[j])) < 0.04 };
}
let F = null; let CX = 0, CY = 0, SC = 1, ZOOM = 6;
const PX = x => (x - CX) * SC + W / 2, PY = y => -(y - CY) * SC + H / 2;
const front = new Float64Array(N * 2); let hasFront = false;
// 縮放分級：λ 0＝集團軍、1＝軍、2＝師。手機符號較小，等效縮放 +0.9
function lambdaFor(z) { const ez = z + (MOBILE ? 0.9 : 0); return sstep(5.6, 6.0, ez) + sstep(7.25, 7.6, ez); }
function computeFrame() {
  const c = MAP.getCenter(); ZOOM = MAP.getZoom(); CX = mx(c.lng); CY = my(c.lat); SC = 512 * Math.pow(2, ZOOM) / (2 * Math.PI);
  const S = state(day); const A = FR[S.i] || FR[S.j], B = FR[S.j] || A; hasFront = !!A; if (A) for (let k = 0; k < N * 2; k++) front[k] = lerp(A[k], B[k], S.e);
  hits = [];
  F = { S, lam: lambdaFor(ZOOM), now: performance.now() };
  F.units = unitScreens(S, F.lam);
}
// ---------- A：控制區＋包圍圈＋前線 ----------
function drawTerritory() {
  F.pockets = []; if (AREAS) return drawAreas(); if (!hasFront) return;   // 這場戰役（或這一天）沒有前線資料：只畫底圖和部隊
  const S = F.S; const fc = TH.front_close || []; const flat = new Float64Array(N * 2 + fc.length * 2); const pts = new Array(N);
  for (let n = 0; n < N; n++) { const X = PX(front[2 * n]), Y = PY(front[2 * n + 1]); flat[2 * n] = X; flat[2 * n + 1] = Y; pts[n] = [X, Y]; }
  const cl = fc.map(p => [p[0] == null ? front[0] : mx(p[0]), my(p[1])]);   // 把前線接成軸心控制區的多邊形；經度 null＝前線起點的經度
  cl.forEach((p, k) => { flat[2 * N + 2 * k] = PX(p[0]); flat[2 * N + 2 * k + 1] = PY(p[1]); });
  const DBG = Q.get('dbg') || ''; if (!DBG.includes('nofill')) BGL.fillIdx(flat, earcut(flat), AXIS_FILL);
  // 包圍圈：兩日都有＝形變；只有前一日＝陷落（縮回中心）；只有後一日＝整段都在（它本來就是盟軍地）
  const rings = [];
  const pi = PKS[S.i], pj = PKS[S.j]; const ids = new Set([...Object.keys(pi), ...Object.keys(pj)]);
  for (const id of ids) { const a = pi[id], b = pj[id]; let r = new Float64Array(NPK * 2), meta = a || b;
    if (a && b) for (let k = 0; k < NPK * 2; k++) r[k] = lerp(a.ring[k], b.ring[k], S.e);
    else if (a) { const t = S.i === S.j ? 0 : clamp(S.e * 1.15, 0, 1); for (let k = 0; k < NPK; k++) { r[2 * k] = lerp(a.ring[2 * k], a.cx, t); r[2 * k + 1] = lerp(a.ring[2 * k + 1], a.cy, t); } if (t >= 0.98) continue; }
    else r = b.ring;
    const ra = a ? 1 : (S.i === S.j ? 1 : sstep(0.3, 0.9, S.e));   // 剛形成的包圍圈：外框與名稱隨時間淡入
    const fl = new Float64Array(NPK * 2), pp = []; for (let k = 0; k < NPK; k++) { fl[2 * k] = PX(r[2 * k]); fl[2 * k + 1] = PY(r[2 * k + 1]); pp.push([fl[2 * k], fl[2 * k + 1]]); }
    BGL.fillIdx(fl, earcut(fl), meta.side === 'axis' ? AXIS_FILL : ALLIED_FILL); rings.push({ pp, meta, ra, cx: PX(meta.cx), cy: PY(meta.cy) }); }
  F.pockets = rings;
  const core = rgba(...INK, 0.92), dash = TOUR && !S.atKey ? [7, 5] : null;
  if (!DBG.includes('noline')) { BGL.line(pts, false, 6, [1, 1, 1, 0.85]); BGL.line(pts, false, 2.2, core, dash); }
  for (const r of rings) { BGL.line(r.pp, true, 5, [1, 1, 1, 0.85 * r.ra]); BGL.line(r.pp, true, 1.8, [core[0], core[1], core[2], core[3] * r.ra], dash); }
}
// ---------- 上層：D 地名 → B 兵力 → C 交戰 ----------
function drawTop() {
  const S = F.S;
  stepSheets();
  LATE = [];
  drawSheet('places', LAYERS.places.a); if (LAYERS.places.a > 0.03) drawPlaces(S, LAYERS.places.a);
  drawSheet('forces', LAYERS.forces.a); if (LAYERS.forces.a > 0.02) { if (TOUR) drawArrows(S, LAYERS.forces.a); if (!RM) drawShips(S, LAYERS.forces.a);
    if (hover && hover.type === 'unit' && !(selected && selected.id === hover.id)) drawTrail(hover.id, false);
    if (selected && selected.type === 'unit') drawTrail(selected.id, true);
    drawUnits(F.units, S, LAYERS.forces.a); }
  for (const l of LATE) BGL.sprite(l[0], l[1], l[2], 1, l[3]);
  drawSheet('eng', LAYERS.eng.a); if (LAYERS.eng.a > 0.02) drawEngagements(S, LAYERS.eng.a);
  drawPocketTags(S);
  if (!RM) drawShocks();
  updateTip();
}
// 醋酸片片框：畫在 WebGL 裡（只畫片緣、套準十字、片名；不做整片底色，省三次全畫面混色）
const SHEET_ORDER = ['places', 'forces', 'eng'];
function drawSheet(k, A) {
  return;   // v2.5：醋酸片片框拿掉
  if (A < 0.02 || !TOUR) return; const i = SHEET_ORDER.indexOf(k) + 1; const m = (MOBILE ? 4 : 8) + i * (MOBILE ? 3 : 5);
  const bot = MOBILE ? H : H - 84; const x = m + i * 2 + 0.5, y = m + i * 2 + 0.5, w = W - 2 * m - 1, h = bot - 2 * m - 1;
  BGL.line([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], true, 1, rgba(226, 220, 206, 0.2 * A));
  const c = rgba(226, 220, 206, 0.4 * A); [[x + 10, y + 10], [x + w - 10, y + 10], [x + 10, y + h - 10], [x + w - 10, y + h - 10]].forEach(([cx, cy]) => { BGL.line([[cx - 5, cy], [cx + 5, cy]], false, 1, c); BGL.line([[cx, cy - 5], [cx, cy + 5]], false, 1, c); });
  const t = SP.sheet[k]; BGL.sprite(t, x + w - 18 - (i - 1) * (MOBILE ? 86 : 108) - t.w, y + h - t.h - 6, 1, A);
}
function stepSheets() {}
// ---------- 箭頭 ----------
function arrowGeom(pts, prog, w0, w1, head) {
  const cum = [0]; for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
  const L = cum[cum.length - 1] * prog; if (L < head * 0.6) return null;
  const q = [pts[0]]; for (let i = 1; i < pts.length; i++) { if (cum[i] <= L) q.push(pts[i]); else { const t = (L - cum[i - 1]) / (cum[i] - cum[i - 1]); q.push([lerp(pts[i - 1][0], pts[i][0], t), lerp(pts[i - 1][1], pts[i][1], t)]); break; } }
  const body = []; let acc = 0; const bodyL = Math.max(L - head, 0.01);
  body.push(q[0]); for (let i = 1; i < q.length; i++) { const sl = Math.hypot(q[i][0] - q[i - 1][0], q[i][1] - q[i - 1][1]); if (acc + sl >= bodyL) { const t = (bodyL - acc) / sl; body.push([lerp(q[i - 1][0], q[i][0], t), lerp(q[i - 1][1], q[i][1], t)]); break; } acc += sl; body.push(q[i]); }
  const tip = q[q.length - 1], root = body[body.length - 1];
  const L2 = [], R2 = [], F2 = []; let a2 = 0;
  for (let i = 0; i < body.length; i++) { const p0 = body[Math.max(i - 1, 0)], p1 = body[Math.min(i + 1, body.length - 1)]; let dx = p1[0] - p0[0], dy = p1[1] - p0[1]; const dl = Math.hypot(dx, dy) || 1; dx /= dl; dy /= dl;
    if (i) a2 += Math.hypot(body[i][0] - body[i - 1][0], body[i][1] - body[i - 1][1]); const f = a2 / bodyL, w = lerp(w0, w1, f) / 2;
    L2.push([body[i][0] - dy * w, body[i][1] + dx * w]); R2.push([body[i][0] + dy * w, body[i][1] - dx * w]); F2.push(f); }
  let hx = tip[0] - root[0], hy = tip[1] - root[1]; const hl = Math.hypot(hx, hy) || 1; hx /= hl; hy /= hl; const hw = w1 * 1.05 + 6;
  const HL = [root[0] - hy * hw, root[1] + hx * hw], HR = [root[0] + hy * hw, root[1] - hx * hw];
  return { L2, R2, F2, HL, HR, tip, ring: [...L2, HL, tip, HR, ...R2.slice().reverse()] };
}
const AST = { armor: [4, 17, [184, 64, 47], 19], infantry: [3, 11, [201, 108, 92], 14], motorized: [4, 13, [47, 93, 155], 16], counter: [4, 15, [47, 93, 155], 17], retreat: [3, 9, [120, 138, 165], 12] };
function drawArrows(S, LA) {
  const sc = (MOBILE ? 0.7 : 1) * clamp(Math.pow(2, (ZOOM - 7.2) * 0.35), 0.8, 1.5);
  for (const a of D.arrows) {
    if (a.kind === 'naval' || !a.show) continue;
    let prog, alpha;
    if (a.k === S.j && S.j !== S.i) { prog = clamp(S.e * 1.1, 0, 1); alpha = 1; }
    else if (a.k === S.i) { prog = 1; alpha = S.atKey && S.u < 0.5 ? 1 : clamp(1 - S.u / 0.3, 0, 1); if (S.i === KD.length - 1) alpha = 1; }
    else continue;
    alpha *= LA; if (alpha <= 0.01) continue;
    const st = AST[a.kind] || AST.infantry; const pts = a.sm.map(v => [PX(v[0]), PY(v[1])]);
    const g = arrowGeom(pts, prog, st[0] * sc, st[1] * sc, st[3] * sc); if (!g) continue;
    BGL.line(g.ring, true, 3.5, [1, 1, 1, 0.9 * alpha]);
    const [r, gg, b] = st[2]; const col = f => rgba(r, gg, b, alpha * lerp(0.35, 0.92, f));
    const T = [];
    for (let i = 0; i < g.L2.length - 1; i++) { const c0 = col(g.F2[i]), c1 = col(g.F2[i + 1]);
      T.push([g.L2[i][0], g.L2[i][1], c0], [g.R2[i][0], g.R2[i][1], c0], [g.L2[i + 1][0], g.L2[i + 1][1], c1], [g.R2[i][0], g.R2[i][1], c0], [g.R2[i + 1][0], g.R2[i + 1][1], c1], [g.L2[i + 1][0], g.L2[i + 1][1], c1]); }
    const ch = col(1); T.push([g.HL[0], g.HL[1], ch], [g.tip[0], g.tip[1], ch], [g.HR[0], g.HR[1], ch]);
    BGL.tris(T);
    if (a.kind === 'retreat') BGL.line(g.ring, true, 1, rgba(...INK, 0.45 * alpha), [5, 4]);
  }
}
// ---------- 部隊：縮放分級＋堆疊 ----------
function aggW(u, lam) {
  // 自己出現的權重：每一層上級都要「展開」到這一層
  let w = 1, c = u;
  while (c.parent_id) { const p = unitIdx[c.parent_id]; w *= clamp(lam - (c.tier - 1), 0, 1); c = p; }
  if (!u.parent_id && u.display === 'detail') w *= clamp(lam - (u.tier - 1), 0, 1);
  if (u.replace && u._hasKids) { const mt = Math.min(...u.children.filter(id => unitIdx[id]._present).map(id => unitIdx[id].tier)); w *= 1 - clamp(lam - (mt - 1), 0, 1); }
  return w;
}
function unitScreens(S, lam) {
  const out = []; const dt = dtGlobal;
  for (const u of D.units) { const a = u.kpos[S.i], b = u.kpos[S.j]; u._present = !!(a || b); }
  for (const u of D.units) u._hasKids = u.children.some(id => unitIdx[id]._present);
  for (const u of D.units) {
    const a = u.kpos[S.i], b = u.kpos[S.j]; u._vis = 0; if (!a && !b) { u._sa = 0; continue; }
    let x, y, al = 1, st; u._spd = 0;
    if (a && b) { x = lerp(a.x, b.x, S.e); y = lerp(a.y, b.y, S.e); st = S.u < 0.5 ? a.st : b.st;
      if (S.i !== S.j) { const km = haversine(ilon(a.x), ilat(a.y), ilon(b.x), ilat(b.y)); u._spd = km / (KD[S.j] - KD[S.i]); u._brg = Math.atan2(b.x - a.x, b.y - a.y); } }
    else if (a) { x = a.x; y = a.y; al = 1 - S.e; st = a.st; if (S.i === S.j) al = 1; }
    else { x = b.x; y = b.y; al = S.e; st = b.st; }
    u._mx = x; u._my = y; u._stNow = st;
    al *= aggW(u, isEnemy(u) ? Math.max(0, lam - 1) : lam); u._vis = al;   // 陣營視角：對方只看得到高一級的單位
    if (al < 0.03) continue;
    const fw = TOUR ? lerp(D.keyframes[S.i].fset.has(u.id) ? 1 : 0, D.keyframes[S.j].fset.has(u.id) ? 1 : 0, S.e) : 1;
    const o = { u, X: PX(x), Y: PY(y), al, st, fw, members: [] }; if (a && b && S.i !== S.j) { o.tx = PX(b.x); o.ty = PY(b.y); }
    out.push(o);
  }
  // 堆疊：同陣營、距離小於 r 的符號併成一格（焦點／高梯隊當代表），右上角顯示 +n
  const r = MOBILE ? 25 : 34; out.sort((p, q) => (q.fw - p.fw) || (q.al - p.al) || (p.u.tier - q.u.tier));
  const heads = [];
  for (const o of out) { let h = null; if (o.al > 0.25) for (const k of heads) { if (k.u.side === o.u.side && Math.abs(k.X - o.X) < r && Math.abs(k.Y - o.Y) < r * 0.8) { h = k; break; } }
    if (h) { h.members.push(o); o.head = h; } else if (o.al > 0.25) heads.push(o); else o.head = null; }
  for (const o of out) { const tgt = o.head ? 1 : 0; o.u._st = RM ? tgt : o.u._st + (tgt - o.u._st) * Math.min(1, dt * 9); }
  return out;
}
function drawUnits(list, S, LA) {
  const order = list.slice().sort((a, b) => a.fw - b.fw); let selDrawn = false;
  // 選了一場交戰：沒參戰的部隊退到背景
  const selE = !TOUR && selected && selected.type === 'eng' ? D.engagements.find(x => x.id === selected.id) : null; let dimSet = null;
  if (selE) { dimSet = new Set(); selE.units.forEach(x => lineage(x.unit_id).forEach(i => dimSet.add(i))); }
  for (const o of order) {
    const sp = SP.unit[o.u.id][0];
    const isHover = hover && hover.type === 'unit' && hover.id === o.u.id, isSel = selected && selected.type === 'unit' && selected.id === o.u.id, f = isHover ? 1 : o.fw;
    const enemy = isEnemy(o.u) && !isHover && !isSel;
    const sc = lerp(0.72, 1, f) * (enemy ? 0.86 : 1); let al = o.al * LA * lerp(0.4, 1, f) * (1 - o.u._st) * (enemy ? 0.6 : 1);
    if (dimSet && !dimSet.has(o.u.id) && !isHover) al *= 0.3;
    if (al < 0.01) continue;
    const X = Math.round(o.X * DPR) / DPR, Y = Math.round(o.Y * DPR) / DPR, hw = sp.w / 2 * sc, hh = sp.h / 2 * sc;
    const nm = o.members.filter(m => m.al > 0.25).length;
    // 行進中的部隊：一支短箭頭指向下一個紀錄點
    if (!TOUR && !enemy && !dimSet && o.tx !== undefined && o.st !== 'defend' && o.st !== 'encircled' && o.st !== 'surrendered') { const dx = o.tx - o.X, dy = o.ty - o.Y, dl = Math.hypot(dx, dy), s0 = hw + 3;
      if (dl > s0 + 12) { const ux = dx / dl, uy = dy / dl, L = Math.min(dl, s0 + 20), c = rgba(...SIDE_COL[o.u.side], 0.75 * al), x1 = X + ux * L, y1 = Y + uy * L;
        BGL.line([[X + ux * s0, Y + uy * s0], [x1, y1]], false, 1.6, c); BGL.tris([[x1 + ux * 7, y1 + uy * 7, c], [x1 - uy * 4, y1 + ux * 4, c], [x1 + uy * 4, y1 - ux * 4, c]]); } }
    if (nm) { BGL.sprite(sp, X + 5 * sc, Y - 4 * sc, sc, al * 0.3); BGL.sprite(sp, X + 2.5 * sc, Y - 2 * sc, sc, al * 0.55); }
    BGL.sprite(sp, X, Y, sc, al);
    // 狀態徽章：追蹤模式只在滑過或選取時出現（平常看牌子和箭頭就夠）
    const bd = SP.badge[o.st], showB = TOUR ? f > 0.5 : (isHover || isSel); if (bd && o.st !== 'move' && showB) BGL.sprite(bd, X + hw - 1, Y - hh + 1, 0.95, al * (TOUR ? clamp((f - 0.5) * 2, 0, 1) : 1));
    if (nm) BGL.sprite(SP.count[Math.min(nm, 12)], X - hw - 3, Y - hh + 2, 1, Math.max(al, 0.75 * LA * o.al * (dimSet ? 0.3 : 1)));
    if (isSel) { selDrawn = true; const x0 = X - hw - 2, y0 = Y - hh - 2, x1 = X + hw + 2, y1 = Y + hh + 2; BGL.line([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], true, 1.5, rgba(...ACC, 1)); }
    hits.push({ type: 'unit', id: o.u.id, x: o.X, y: o.Y, r: 21, stack: o.members.filter(m => m.al > 0.25).map(m => m.u.id) });
  }
  if (selected && selected.type === 'unit' && !selDrawn) { const u = unitIdx[selected.id]; if (u && u._present && u._mx !== undefined) BGL.circle(PX(u._mx), PY(u._my), 13, 1.5, rgba(...ACC, 0.95), 28); }
}
// 交戰連線要接到「畫面上看得到的那個符號」：自己 → 所在堆疊的代表 → 上級 → 子單位平均
function reprPos(id) {
  const o = F.units.find(q => q.u.id === id && q.al > 0.25);
  if (o) { const h = o.head && o.u._st > 0.5 ? o.head : o; return [h.X, h.Y]; }
  const u = unitIdx[id]; if (!u) return null;
  if (u.parent_id) { const p = F.units.find(q => q.u.id === u.parent_id && q.al > 0.25); if (p) return reprPos(p.u.id); }
  const ks = F.units.filter(q => u.children.includes(q.u.id) && q.al > 0.25); if (ks.length) return [ks.reduce((s, q) => s + q.X, 0) / ks.length, ks.reduce((s, q) => s + q.Y, 0) / ks.length];
  if (u._mx !== undefined && u._present) return [PX(u._mx), PY(u._my)];
  return null;
}
// ---------- C 交戰 ----------
function glow(X, Y, r, c) { const T = [], e = [c[0], c[1], c[2], 0]; for (let i = 0; i < 30; i++) { const a0 = i / 30 * 6.2832, a1 = (i + 1) / 30 * 6.2832; T.push([X, Y, c], [X + Math.cos(a0) * r, Y + Math.sin(a0) * r, e], [X + Math.cos(a1) * r, Y + Math.sin(a1) * r, e]); } BGL.tris(T); }
function drawEngagements(S, LA) {
  F.engTags = [];
  for (const e of D.engagements) {
    let al = engAlpha(e, S); e._on = 0;
    if (al <= 0.01) continue;
    const X = PX(e.x), Y = PY(e.y); if (X < -40 || Y < -40 || X > W + 40 || Y > H + 40) continue;
    const isHover = (hover && hover.type === 'eng' && hover.id === e.id) || (selected && selected.type === 'eng' && selected.id === e.id), foc = !TOUR || e.focus;
    const br = RM ? 0.5 : 0.5 + 0.5 * Math.sin(F.now / 1100);
    if (!TOUR) {
      // v2.4：三級重要度。1 一般＝小劍；2 重要＝劍＋細環＋名稱；3 關鍵＝光暈＋擴散環＋大名稱＋連線
      const imp = isHover ? Math.max(e.imp, 2) : e.imp; al *= LA;
      if (imp >= 2) for (const p of e.units) { const q = reprPos(p.unit_id); if (!q) continue;
        BGL.line([[q[0], q[1]], [X, Y]], false, imp === 3 ? 2 : 1.3, rgba(...SIDE_COL[unitIdx[p.unit_id].side], (imp === 3 ? 0.9 : 0.6) * al), p.role === 'attacker' ? [5, 3] : [1.5, 3]); }
      let R = 9;
      if (e.imp === 3) { R = 21 + br * 2; glow(X, Y, R + 22, rgba(...ACC, 0.26 * al)); BGL.circle(X, Y, R, 2.2, rgba(...ACC, 0.95 * al), 48);
        if (!RM) { const ph = (F.now / 1700) % 1; BGL.circle(X, Y, R + ph * 26, 1.3, rgba(...ACC, (1 - ph) * 0.7 * al), 48); } }
      else if (imp === 2) { R = 13; BGL.circle(X, Y, R + br, 1.4, rgba(...ACC, 0.8 * al), 32); }
      BGL.sprite(SP.swords, X, Y, e.imp === 3 ? 1.35 : imp === 2 ? 0.95 : 0.62, al * (imp === 1 ? 0.85 : 1));
      hits.push({ type: 'eng', id: e.id, x: X, y: Y, r: e.imp === 3 ? 30 : 16 });
      if (imp >= 2) F.engTags.push({ e, X, Y, R: R + (e.imp === 3 ? 14 : 5), al, pin: isHover });
      e._X = X; e._Y = Y; e._on = al; continue;
    }
    al *= LA * (foc || isHover ? 1 : 0.38);
    if (foc || isHover) for (const p of e.units) { const q = reprPos(p.unit_id); if (!q) continue;
      BGL.line([[q[0], q[1]], [X, Y]], false, 1, rgba(...SIDE_COL[unitIdx[p.unit_id].side], 0.55 * al), p.role === 'attacker' ? [4, 3] : [1.5, 3]); }
    BGL.circle(X, Y, 11 + br * 2, 1, rgba(...ACC, (0.25 + 0.2 * br) * al), 32);
    BGL.sprite(SP.swords, X, Y, 1, al);
    hits.push({ type: 'eng', id: e.id, x: X, y: Y, r: 16 });
    e._X = X; e._Y = Y; e._on = al;
  }
  // 交戰名稱：HTML 小標，跟著記號走
  const box = $('#eng-tags'), tags = F.engTags, key = tags.map(t => t.e.id).join(',');
  if (box._key !== key) { box._key = key; box.innerHTML = tags.map(t => `<span data-id="${t.e.id}" class="i${t.e.imp}">${t.e.imp === 3 ? '<b>關鍵交戰</b>' : ''}<em>${esc(t.e.label)}</em></span>`).join(''); }
  // 名稱牌互相避開：重要的先放；依序試 上／下／右／左，都會蓋到別人就先收起來（滑過或選取的那個一定顯示）
  if (box._key2 !== key) { box._key2 = key; box._els = {}; for (const el of box.children) { box._els[el.dataset.id] = el; el._w = el.offsetWidth; el._h = el.offsetHeight; } }
  const placed = [], hit = r => placed.some(q => r[0] < q[2] + 4 && r[2] > q[0] - 4 && r[1] < q[3] + 4 && r[3] > q[1] - 4);
  const slot = (t, w, h, k) => k === 0 ? [t.X - w / 2, t.Y - t.R - h] : k === 1 ? [t.X - w / 2, t.Y + t.R] : k === 2 ? [t.X + t.R, t.Y - h / 2] : [t.X - t.R - w, t.Y - h / 2];
  for (const t of tags.slice().sort((p, q) => (q.pin - p.pin) || (q.e.imp - p.e.imp) || (p.e.id < q.e.id ? -1 : 1))) { const el = box._els[t.e.id]; if (!el) continue; const w = el._w, h = el._h;
    let use = -1, r; for (const k of [el._slot || 0, 0, 1, 2, 3]) { const p = slot(t, w, h, k); r = [p[0], p[1], p[0] + w, p[1] + h]; if (!hit(r)) { use = k; break; } }
    if (use < 0) { if (!t.pin) { el.style.opacity = 0; continue; } use = 0; const p = slot(t, w, h, 0); r = [p[0], p[1], p[0] + w, p[1] + h]; }
    el._slot = use; placed.push(r); el.classList.toggle('alt', use !== 0); el.style.transform = `translate(${Math.round(r[0])}px,${Math.round(r[1])}px)`; el.style.opacity = t.al.toFixed(2); }
}
// 包圍圈名稱（D 片開著時，放大才顯示）
function drawPocketTags(S) { /* 名稱放在 HTML 小標（#pk-tags），避免另做文字圖集 */
  const box = $('#pk-tags'); const show = LAYERS.places.a > 0.3 && ZOOM + (MOBILE ? 0.9 : 0) > 7.0; const want = show ? F.pockets.filter(p => p.ra > 0.5) : [];
  const key = want.map(p => p.meta.id).join(','); if (box._key !== key) { box._key = key; box.innerHTML = want.map(p => `<span data-id="${p.meta.id}">${p.meta.name}${D.meta.is_example ? '<small>示例</small>' : ''}</span>`).join(''); }
  if (!show) return; for (const p of want) { const el = box.querySelector(`[data-id="${p.meta.id}"]`); if (el) el.style.transform = `translate(${Math.round(p.cx)}px,${Math.round(p.cy - 30)}px) translate(-50%,-100%)`; }
}
// ---------- D 地名 ----------
let LATE = [];
function drawPlaces(S, A) {
  const all = LAYERS.places.mode === 'on'; const ez = ZOOM + (MOBILE ? 0.9 : 0);
  const li = new Set(D.keyframes[S.i].places || []), lj = new Set(D.keyframes[S.j].places || []);
  const cand = [];
  for (const [n, lo, la, rk] of CITIES) {
    const day1 = lerp(li.has(n) ? 1 : 0, lj.has(n) ? 1 : 0, S.e);
    // 自動：當日 6–8 個；放大到師級時，畫面內 rank≥2 的城市也淡淡出現
    let a = all ? (rk >= 3 || (rk >= 2 && ez > 6.2) || ez > 7.2 ? 1 : 0) : Math.max(day1, ez > 7.8 && rk >= 1 ? 0.55 * sstep(7.8, 8.3, ez) : 0);
    if (a < 0.03) continue; const X = PX(mx(lo)), Y = PY(my(la)); if (X < -60 || X > W + 20 || Y < -20 || Y > H + 20) continue;
    cand.push({ n, X, Y, a, p: day1 * 10 + rk });
  }
  cand.sort((p, q) => q.p - p.p); const placed = [];
  if (!TOUR && LAYERS.forces.a > 0.5) for (const o of F.units) if (o.al > 0.25 && !o.head) placed.push([o.X - 30, o.Y - 16, o.X + 30, o.Y + 18]);   // 地名不壓部隊牌
  for (const c of cand) { const sp = SP.city[c.n]; const x0 = c.X - sp.ax, y0 = c.Y - sp.ay, x1 = x0 + sp.w, y1 = y0 + sp.h;
    if (placed.some(r => x0 < r[2] - 4 && x1 > r[0] + 4 && y0 < r[3] - 4 && y1 > r[1] + 4)) continue; placed.push([x0, y0, x1, y1]);
    if (TOUR && c.p >= 10 && !all) { LATE.push([sp, Math.round(c.X * DPR) / DPR, Math.round(c.Y * DPR) / DPR, c.a * A]); continue; }   // 當日關鍵地名（例如 5/13 色當）改畫在部隊上面，不被符號蓋住
    BGL.sprite(sp, Math.round(c.X * DPR) / DPR, Math.round(c.Y * DPR) / DPR, 1, c.a * A); }
  SEAS.forEach(([n, lo, la], k) => BGL.sprite(SP.sea[k], PX(mx(lo)), PY(my(la)), 1, 0.55 * A));
}
// ---------- 撤退船隊 ----------
function drawShips(S, LA) {
  for (const a of D.arrows) { if (a.kind !== 'naval' || !a.show) continue;
    let al; if (a.k === S.j && S.j !== S.i) al = S.e; else if (a.k === S.i) al = S.i === KD.length - 1 ? 0.3 : 1 - S.e * 0.7; else continue;
    if (a.k <= S.i && D.keyframes[S.i].date >= D.meta.date_end) al *= 0.3;
    al *= LA; const pts = a.sm.map(v => [PX(v[0]), PY(v[1])]); const n = pts.length - 1;
    BGL.line(pts, false, 1.2, rgba(47, 93, 155, 0.5 * al), [4, 5]);
    for (let m = 0; m < 6; m++) { const f = ((F.now / 7000) + m / 6) % 1; const fi = f * n, i0 = fi | 0, t = fi - i0; const p0 = pts[i0], p1 = pts[Math.min(i0 + 1, n)];
      BGL.sprite(SP.ship, lerp(p0[0], p1[0], t), lerp(p0[1], p1[1], t), 1, al * 0.7 * Math.sin(f * 3.14)); } }
}
function drawShocks() {
  for (let i = shocks.length - 1; i >= 0; i--) { const s = shocks[i]; const t = (F.now - s.t0) / 2200; if (t > 1) { shocks.splice(i, 1); continue; }
    BGL.circle(PX(s.x), PY(s.y), 12 + ease(t) * Math.min(W, H) * 0.22, 1, rgba(240, 228, 206, (1 - t) * 0.28), 64); }
}
// 兵種配對標籤：HTML 小框，跟著交戰點
function updateTip() {
  const tip = $('#tip');
  if (hover && hover.type === 'unit') { const u = unitIdx[hover.id]; if (u && u._present && u._mx !== undefined) { const key = u.id + (u._stNow || ''); if (tip._id !== key) { tip._id = key; const c = ASG[u.id];
      tip.innerHTML = `<b>${esc(u.name_zh)}</b><span>${ST[u._stNow] || ''}${c ? '｜' + esc(c.name_zh) : ''}</span>`; }
    tip.hidden = false; tip.style.transform = `translate(${Math.round(PX(u._mx) + 20)}px,${Math.round(PY(u._my) + 12)}px)`; return; } } const tgt = (hover && hover.type === 'eng') ? hover : (selected && selected.type === 'eng' ? selected : null);
  const e = TOUR && tgt && D.engagements.find(x => x.id === tgt.id);
  if (!e || !e._on) { if (!tip.hidden) tip.hidden = true; return; }
  if (tip._id !== e.id) { tip._id = e.id; tip.innerHTML = `<b>${e.interaction_zh}</b><span>${e.name_zh}</span>`; }
  tip.hidden = false; tip.style.transform = `translate(${Math.round(e._X + 15)}px,${Math.round(e._Y + 8)}px)`;
}
// ---------- HUD ----------
let lastDayInt = -1, lastHr = -2, TLW = 0, lastAV = '', lastPlaying = null;
function updateHUD(force) {
  const di = Math.floor(day + 1e-6); const S = state(day);
  if (di !== lastDayInt || force) { lastDayInt = di; const dt = new Date(DAY0 + di * 864e5);
    $('#date-d').textContent = `${dt.getUTCFullYear()}年${dt.getUTCMonth() + 1}月${dt.getUTCDate()}日`; lastHr = -2;
    const kf = D.keyframes[S.atKey && S.u > 0.5 ? S.j : S.i]; $('#phase').textContent = kf.event_zh; }
  const hr = TOUR ? -1 : Math.min(23, Math.floor((day - di) * 24 + 1e-6)); if (hr !== lastHr) { lastHr = hr; $('#date-hr').textContent = hr < 0 ? '' : String(hr).padStart(2, '0') + ':00'; }
  if ($('#interp').hidden !== S.atKey) $('#interp').hidden = S.atKey;
  // 時間軸只改 transform（合成器處理，不重排、不重畫；軟體 GL 下每幀重畫時間軸很貴）
  const f = day / KD[KD.length - 1]; const ww = TLW || ($('#tl-track-wrap').clientWidth); TLW = ww;
  $('#tl-fill').style.transform = `scaleX(${f.toFixed(4)})`; $('#tl-head').style.transform = `translateX(${(f * ww).toFixed(1)}px)`;
  const chip = $('#tl-chip'); const rd = Math.round(day); if (chip._d !== rd) { chip._d = rd; const dt = new Date(DAY0 + rd * 864e5); chip.textContent = `${dt.getUTCMonth() + 1}/${dt.getUTCDate()}`; chip._w = chip.offsetWidth || 40; }
  chip.style.transform = `translateX(${clamp(f * ww, chip._w / 2, ww - chip._w / 2).toFixed(1)}px) translateX(-50%)`;
  const av = day.toFixed(1); if (av !== lastAV) { lastAV = av; $('#tl-track').setAttribute('aria-valuenow', av); }
  if (playing !== lastPlaying) { lastPlaying = playing; $('#btn-play').textContent = playing ? '❚❚' : '▶'; $('#btn-play').setAttribute('aria-label', playing ? '暫停' : '播放'); }
}
function fireEvent(j, withFx) {
  return;   // v2.5：不再跳事件字卡（會蓋住地圖）。導覽模式的說明改放在左側章節列
  const kf = D.keyframes[j]; const el = $('#event');
  el.querySelector('.ev-zh').textContent = kf.event_zh; el.querySelector('.ev-en').textContent = kf.event_line || '';
  el.classList.remove('show'); void el.offsetWidth; el.classList.add('show'); if (!el._ae) { el._ae = 1; el.addEventListener('animationend', ev => { if (ev.animationName === 'evshow') el.classList.remove('show'); }); }
  if (kf.major && withFx && !RM) { const e = D.engagements.find(x => x.k === j); if (e) shocks.push({ x: e.x, y: e.y, t0: performance.now() }); }
}
// ---------- 時間軸 ----------
function layoutTimeline() { TLW = 0; const ch = $('#tl-chip'); if (ch) ch._d = null;
  const ticks = $('#tl-ticks'), labs = $('#tl-labels'); ticks.innerHTML = ''; labs.innerHTML = '';
  const T = KD[KD.length - 1]; const wrapW = $('#tl-track-wrap').getBoundingClientRect().width;
  D.keyframes.forEach((k, i) => { const d = document.createElement('div'); d.className = 'tk' + (k.major ? ' major' : ''); d.style.left = (KD[i] / T * 100) + '%'; ticks.appendChild(d); });
  const order = D.keyframes.map((k, i) => ({ i, p: (k.major ? 2 : 0) + (i === 0 || i === KD.length - 1 ? 1 : 0) })).sort((a, b) => b.p - a.p || a.i - b.i);
  const placed = []; const mctx = document.createElement('canvas').getContext('2d'); mctx.font = `${MOBILE ? 11 : 12}px "Noto Sans CJK TC",sans-serif`;
  for (const { i } of order) { const k = D.keyframes[i]; const md = k.date.slice(5).replace(/^0/, '').replace('-0', '/').replace('-', '/'); const txt = MOBILE ? md : `${md}${k.major ? ' ' + k.event_zh.split('：')[0].split('・')[0] : ''}`;
    const w = mctx.measureText(txt).width + 8; let x = KD[i] / T * wrapW; x = clamp(x, w / 2, wrapW - w / 2);
    if (placed.some(p => Math.abs(p.x - x) < (p.w + w) / 2)) continue; placed.push({ x, w, i, txt }); }
  placed.forEach(p => { const d = document.createElement('div'); d.className = 'lb' + (D.keyframes[p.i].major ? ' major' : ''); d.textContent = p.txt; d.style.left = p.x + 'px'; d.onclick = () => { pause(); jumpTo(p.i); }; labs.appendChild(d); });
  window.__labels = placed.map(p => ({ x: p.x, w: p.w, txt: p.txt }));
}
function setDay(d, force) { const prev = day; day = clamp(d, 0, KD[KD.length - 1]);
  if (playing) for (let j = 0; j < KD.length; j++) if (prev < KD[j] && day >= KD[j] && j !== lastEventKey) { lastEventKey = j; fireEvent(j, true); }
  updateHUD(force); }
function jumpTo(i) { lastEventKey = i; setDay(KD[i], true); fireEvent(i, !RM); }
function play(fromStart) { if (day >= KD[KD.length - 1] - 1e-6) { day = 0; } if (fromStart && day === 0) { lastEventKey = 0; fireEvent(0, true); } playing = true; lastT = 0; updateHUD(); }
function pause() { playing = false; updateHUD(); }
function setSpeed(s) { speed = s; document.querySelectorAll('#speed button').forEach(b => b.classList.toggle('on', +b.dataset.s === s)); }
function renderChips() {
  const root = $('#layers'); root.innerHTML = '';
  const seg = document.createElement('div'); seg.className = 'seg'; seg.setAttribute('role', 'group'); seg.setAttribute('aria-label', '視角');
  [['all', '全局'], ...SIDES.map(k => [k, SIDE_NAME[k]])].forEach(([v, t]) => { const b = document.createElement('button'); b.textContent = t; b.className = VIEW === v ? 'on ' + v : v; b.setAttribute('aria-pressed', VIEW === v);
    b.title = v === 'all' ? '全局視角：兩軍同等顯示' : '陣營視角：這一方看到師級；對方只看到高一級的單位，而且變淡'; b.onclick = () => setView(v); seg.appendChild(b); });
  const lb = document.createElement('button'); lb.id = 'lay-btn'; lb.className = 'chip' + (layOpen ? ' on' : ''); lb.textContent = '圖層'; lb.setAttribute('aria-expanded', layOpen); lb.onclick = () => { layOpen = !layOpen; renderChips(); };
  const box = document.createElement('div'); box.id = 'lay-pop'; box.hidden = !layOpen; const lg = document.createElement('button'); lg.className = 'chip'; lg.textContent = '圖例'; lg.onclick = () => $('#legend-btn').click(); root.append(seg, lb, lg, box);
  { const ms = document.createElement('div'); ms.className = 'seg mode'; ms.setAttribute('role', 'group'); ms.setAttribute('aria-label', '模式');
    [[false, '追蹤', '追蹤模式：自由鏡頭，點部隊看細節'], [true, '導覽', '導覽模式：照章節自動移動鏡頭，只強調當日焦點（快捷鍵 T）']].forEach(([v, t, tt]) => { const b = document.createElement('button'); b.textContent = t; b.title = tt; b.className = TOUR === v ? 'on' : ''; b.setAttribute('aria-pressed', TOUR === v); b.onclick = () => setTour(v); ms.appendChild(b); }); root.prepend(ms); }
  const a = document.createElement('button'); a.className = 'chip locked'; a.disabled = true; a.innerHTML = '<i style="background:#ff4b3a"></i>A｜控制區<small>常駐</small>'; box.appendChild(a);
  for (const k of ['forces', 'eng', 'places']) { const L = LAYERS[k]; const b = document.createElement('button');
    b.className = 'chip ' + L.mode; b.setAttribute('aria-pressed', L.mode !== 'off');
    b.innerHTML = `<i style="background:rgb(${L.tint})"></i>${L.key}｜${L.name}<small>${{ on: '開', off: '關', auto: '自動' }[L.mode]}</small>`;
    b.title = '點一下切換：自動 → 開 → 關';
    b.onclick = () => { const cyc = k === 'forces' ? ['on', 'off'] : ['auto', 'on', 'off']; L.mode = cyc[(cyc.indexOf(L.mode) + 1) % cyc.length]; renderChips(); setRiverOpacity(); };
    box.appendChild(b); }
}
let riverA = -1; function setRiverOpacity() { const a = +LAYERS.places.a.toFixed(2); if (a === riverA || !MAP.getLayer('rivers')) return; riverA = a; ['rivers', 'rivers-other', 'borders'].forEach(l => MAP.setPaintProperty(l, 'line-opacity', a)); }
function buildSheets() { return;
  const wrap = $('#sheets'); wrap.innerHTML = '';
  ['places', 'forces', 'eng'].forEach((k, n) => { const L = LAYERS[k]; const d = document.createElement('div'); d.className = 'sheet'; d.style.setProperty('--i', n + 1);
    d.innerHTML = `<i class="rg tl"></i><i class="rg tr"></i><i class="rg bl"></i><i class="rg br"></i><span class="tag">${L.key}｜${L.name}</span>`; wrap.appendChild(d); sheetEls[k] = d; });
}
function nearest(x, y) { let best = null, bd = 1e9; hits.forEach(h => { const d = Math.hypot(h.x - x, h.y - y); if (d < h.r && d < bd) { bd = d; best = h; } }); return best; }
function bindUI() {
  renderChips(); buildSheets();
  if (Q.get('glass') === '0') document.body.classList.add('no-blur');
  $('#btn-play').onclick = () => playing ? pause() : play(true);
  $('#btn-prev').onclick = () => { pause(); const i = KD.findLastIndex(k => k < day - 1e-3); jumpTo(Math.max(i, 0)); };
  $('#btn-next').onclick = () => { pause(); const i = KD.findIndex(k => k > day + 1e-3); jumpTo(i < 0 ? KD.length - 1 : i); };
  $('#follow').onclick = () => setFollow(true);
  document.querySelectorAll('#speed button').forEach(b => b.onclick = () => setSpeed(+b.dataset.s));
  const tr = $('#tl-track'); let drag = false;
  const seek = ev => { const r = tr.getBoundingClientRect(); setDay(clamp((ev.clientX - r.left) / r.width, 0, 1) * KD[KD.length - 1], true); };
  tr.addEventListener('pointerdown', ev => { drag = true; pause(); tr.setPointerCapture(ev.pointerId); seek(ev); });
  tr.addEventListener('pointermove', ev => drag && seek(ev)); tr.addEventListener('pointerup', () => drag = false);
  addEventListener('keydown', ev => { if (ev.code === 'Space') { ev.preventDefault(); playing ? pause() : play(true); } if (ev.code === 'ArrowRight') $('#btn-next').click(); if (ev.code === 'ArrowLeft') $('#btn-prev').click(); if (ev.code === 'ArrowUp' || ev.code === 'ArrowDown') { ev.preventDefault(); switchBattle(ev.code === 'ArrowUp' ? -1 : 1); } if (ev.code === 'Escape') closeInfo(); if (ev.key === 'f' && TOUR) setFollow(true); if (ev.key === 't') setTour(!TOUR); if (ev.key === 'l' && selected && selected.type === 'unit') setLock(lockId === selected.id ? null : selected.id); });
  document.body.classList.toggle('tour', TOUR); if (TOUR) oobTab = 'ch';
  $('#info-body').addEventListener('click', onPanelClick); $('#oob-body').addEventListener('click', onPanelClick); $('#now').addEventListener('click', onPanelClick); document.body.dataset.view = VIEW;
  $('#lg-branch').innerHTML = [['infantry', '步兵'], ['armor', '裝甲'], ['motorized', '摩托化'], ['air', '空軍'], ['naval', '海軍']].map(([b, t]) => `<div class="lg-row"><img alt="" src="${counterCanvas({ side: 'allied', branch: b, label: '', tier: 1, echelon: '' }, 1).cv.toDataURL()}">${t}</div>`).join('');
  const ob = $('#oob'), obb = $('#oob-btn'); const setOob = v => { ob.hidden = !v; obb.setAttribute('aria-expanded', v); };
  setOob(MOBILE ? Q.get('oob') === '1' : true); initBattleNav(); obb.onclick = () => setOob(ob.hidden); $('#oob-close').onclick = () => setOob(false); window.__setOob = setOob;
  const lg = $('#legend'), lb = $('#legend-btn');
  const setLg = v => { lg.hidden = !v; lb.setAttribute('aria-expanded', v); };
  setLg(Q.get('legend') === '1');
  lb.onclick = () => setLg(lg.hidden); $('#legend-close').onclick = () => setLg(false);
  $('#info-close').onclick = closeInfo;
  const el = $('#map');
  el.addEventListener('mousemove', ev => { const r = el.getBoundingClientRect(); hover = nearest(ev.clientX - r.left, ev.clientY - r.top); MAP.getCanvas().style.cursor = hover ? 'pointer' : ''; });
  el.addEventListener('mouseleave', () => hover = null);
  MAP.on('click', e => { const h = nearest(e.point.x, e.point.y); if (h) openInfo(h); else closeInfo(); });
  let rt; addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(() => { const m0 = MOBILE, d0 = DPR; measure(); if (m0 !== MOBILE || d0 !== DPR) { buildSprites(); MAP.setPixelRatio(DPR); } layoutTimeline(); }, 150); });
  layoutTimeline();
  window.__select = selectUnit; window.__setView = setView; window.__setDay = d => setDay(d, true);
  window.__unfollow = () => setFollow(false); window.__follow = () => setFollow(true); window.__state = () => ({ day, follow, zoom: MAP.getZoom(), lam: F && F.lam });
}
// ---------- v2.6：多場戰役 ----------
// 換戰役用「換網址重新載入」：每場戰役有自己的底圖、圖集和時間軸，整頁重來最不會留下上一場的狀態。保留模式和視角。
function battleURL(id) { const q = new URLSearchParams(); q.set('battle', id); if (TOUR) q.set('mode', 'tour'); if (VIEW !== 'all') q.set('side', VIEW); ['rm', 'pr'].forEach(k => Q.get(k) && q.set(k, Q.get(k))); return location.pathname + '?' + q; }
function switchBattle(dir) { const i = INDEX.findIndex(b => b.id === BID), n = INDEX[i + dir]; if (n) location.assign(battleURL(n.id)); }
function initBattleNav() {
  const i = INDEX.findIndex(b => b.id === BID), m = D.meta; const t = m.title_zh || BID;
  $('#battle-title').textContent = t; document.title = `${t}｜戰役動態地圖${m.banner ? '（' + m.banner + '）' : ''}`;
  const bn = $('#banner'); bn.textContent = m.banner || ''; bn.hidden = !m.banner;
  $('#map').setAttribute('aria-label', `${t} 動態地圖（可拖曳與縮放）`); $('#tl-track').setAttribute('aria-valuemax', KD[KD.length - 1]);
  $('#lg-sides').textContent = `部隊牌（${SIDES.map(k => ({ axis: '紅', allied: '藍', third: '綠' }[k] + '＝' + SIDE_NAME[k])).join('，')}）`;
  if (SIDES.includes('third')) $('#lg-allied').parentElement.insertAdjacentHTML('afterend', `<div class="lg-row"><i class="sw sw-third"></i>${esc(SIDE_NAME.third)}控制區</div>`);
  if (TH.control && TH.control.border_name_zh) $('#lg-allied').parentElement.insertAdjacentHTML('afterend', `<div class="lg-row"><i class="sw sw-hist"></i>${esc(TH.control.border_name_zh)}</div>`); $('#lg-axis').textContent = `${SIDE_NAME.axis}控制區`; $('#lg-allied').textContent = `${SIDE_NAME.allied}控制區`;
  $('#lg-note').textContent = `${m.note || ''} 拉遠看集團軍，拉近展開成軍、師。部隊位置是關鍵日之間的內插，不是逐時紀錄。底圖：Natural Earth（公有領域，現代國界）。`;
  const nav = $('#battle-nav'); nav.hidden = INDEX.length < 2;
  [['#bt-prev', -1], ['#bt-next', 1]].forEach(([s, d]) => { const b = $(s), n = INDEX[i + d]; b.disabled = !n; b.title = n ? `${d < 0 ? '上一場' : '下一場'}：${n.title_zh}（鍵盤 ${d < 0 ? '↑' : '↓'}）` : (d < 0 ? '已是第一場' : '已是最後一場'); b.onclick = () => switchBattle(d); });
  $('#bt-count').textContent = `${i + 1} / ${INDEX.length}`; $('#bt-count').dataset.t = t;
  const menu = $('#bt-menu'); menu.innerHTML = INDEX.map(b => `<a href="${battleURL(b.id)}" class="${b.id === BID ? 'on' : ''}"${b.id === BID ? ' aria-current="page"' : ''}><b>${esc(b.title_zh)}</b><span>${esc(b.period_zh || '')}</span>${b.status === 'example' ? '<i>示例</i>' : b.status === 'draft' ? '<i>需查證</i>' : b.status === 'skeleton' ? '<i>骨架</i>' : ''}</a>`).join('');
  const tb = $('#bt-count'); tb.onclick = ev => { ev.stopPropagation(); menu.hidden = !menu.hidden; tb.setAttribute('aria-expanded', !menu.hidden); };
  addEventListener('click', ev => { if (!menu.hidden && !menu.contains(ev.target)) { menu.hidden = true; tb.setAttribute('aria-expanded', false); } });
}
const ECH = { front: '方面軍（XXXXX）', army: '集團軍／軍團（XXXX）', corps: '軍（XXX）', division: '師（XX）', brigade: '旅（X）' };
const BR = { infantry: '步兵', armor: '裝甲', motorized: '摩托化', air: '空軍', naval: '海軍' };
const ST = { attack: '進攻', defend: '防守', retreat: '撤退', move: '移動', encircled: '被包圍', surrendered: '投降', evacuating: '撤離中' };
// ---------- v2.3：追蹤模式（選取、航跡、鎖定鏡頭、戰鬥序列）----------
const SIDE_COL = { axis: [184, 64, 47], allied: [47, 93, 155], third: [92, 122, 58] };
const STC = { attack: '攻', defend: '守', retreat: '退', move: '移', encircled: '圍', surrendered: '降', evacuating: '撤' };
const EMARK = { front: 'XXXXX', army: 'XXXX', corps: 'XXX', division: 'XX', brigade: 'X' };
const DIRS = ['北', '東北', '東', '東南', '南', '西南', '西', '西北'];
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const fmtDay = d => { const t = new Date(DAY0 + Math.round(d * 24) * 36e5); return `${t.getUTCMonth() + 1}/${t.getUTCDate()}`; };
function haversine(lo1, la1, lo2, la2) { const a = Math.sin((la2 - la1) * R / 2) ** 2 + Math.cos(la1 * R) * Math.cos(la2 * R) * Math.sin((lo2 - lo1) * R / 2) ** 2; return 12742 * Math.asin(Math.sqrt(a)); }
function engAlpha(e, S) {
  if (TOUR) { if (e.k === S.j && S.j !== S.i) return clamp((S.u - 0.55) / 0.35, 0, 1); if (e.k === S.i) return S.i === KD.length - 1 ? 1 : clamp(1 - (S.u - 0.15) / 0.3, 0, 1); return 0; }
  if (day < e.t0 || day > e.t1) return 0; const END = KD[KD.length - 1];
  return Math.min(e.t0 <= 0 ? 1 : sstep(e.t0, e.t0 + 0.1, day), e.t1 >= END ? 1 : 1 - sstep(e.t1 - 0.1, e.t1, day));
}
// 自己＋所有上級＋所有下級：交戰資料可能記在軍或師任一層
function lineage(id) { const s = new Set([id]); let c = unitIdx[id]; while (c && c.parent_id) { s.add(c.parent_id); c = unitIdx[c.parent_id]; }
  const down = u => u.children.forEach(k => { s.add(k); down(unitIdx[k]); }); down(unitIdx[id]); return s; }
function activeEngs(id) { const fam = lineage(id), S = state(day); return D.engagements.filter(e => engAlpha(e, S) > 0.01 && e.units.some(x => fam.has(x.unit_id))); }
// 航跡：走過的是實線，之後的是虛線，每個紀錄點一個小圈
function drawTrail(id, strong) { const u = unitIdx[id]; if (!u || !u._present || u._mx === undefined) return; const [r, g, b] = SIDE_COL[u.side];
  const cur = [PX(u._mx), PY(u._my)], past = [], fut = [cur]; const far = (p, q) => Math.hypot(p[0] - q[0], p[1] - q[1]) > 0.5;
  u.kpos.forEach((p, k) => { if (!p) return; const q = [PX(p.x), PY(p.y)]; const L = KD[k] <= day ? past : fut; if (!L.length || far(L[L.length - 1], q)) L.push(q); });
  if (!past.length || far(past[past.length - 1], cur)) past.push(cur);
  const a = strong ? 1 : 0.55;
  if (past.length > 1) { BGL.line(past, false, 5.5, [1, 1, 1, 0.9 * a]); BGL.line(past, false, 2.5, rgba(r, g, b, 0.95 * a)); }
  if (fut.length > 1) BGL.line(fut, false, 1.3, rgba(r, g, b, 0.55 * a), [3, 4]);
  u.kpos.forEach((p, k) => { if (p) BGL.circle(PX(p.x), PY(p.y), 3, 1.5, rgba(...INK, (KD[k] <= day ? 0.9 : 0.4) * a), 12); });
}
// 鎖定鏡頭：跟著選取的部隊走（只改中心，不改縮放；拖曳地圖就解除）
function applyLock() { if (!lockId || !MAP || MAP.isMoving()) return; const u = unitIdx[lockId]; if (!u || !u._present || u._mx === undefined) return;
  const c = MAP.getCenter(), cx = mx(c.lng), cy = my(c.lat), k = RM ? 1 : Math.min(1, dtGlobal * 6), nx = lerp(cx, u._mx, k), ny = lerp(cy, u._my - lockOff() / SC, k);
  if (Math.hypot(nx - cx, ny - cy) * SC < 0.05) return; MAP.jumpTo({ center: [ilon(nx), ilat(ny)] }); }
const lockOff = () => MOBILE ? H * 0.24 : 0;   // 手機的資訊卡蓋住下半部，選取的部隊往上擺
function setLock(id) { lockId = id; infoKey = ''; refreshInfo(true); }
function setTour(v) { TOUR = v; document.body.classList.toggle('tour', v); oobTab = v ? 'ch' : (oobTab === 'ch' ? 'units' : oobTab);
  if (v) { lockId = null; follow = false; setFollow(true); } else { follow = false; resume = null; $('#follow').hidden = true; $('#event').classList.remove('show'); }
  renderChips(); lastDayInt = -1; updateHUD(true); infoKey = ''; refreshInfo(true); }
function selectUnit(id, fly) { const u = unitIdx[id]; if (!u) return; let S = state(day);
  if (!u.kpos[S.i] && !u.kpos[S.j]) { let best = -1; u.kpos.forEach((p, k) => { if (p && (best < 0 || Math.abs(KD[k] - day) < Math.abs(KD[best] - day))) best = k; }); if (best < 0) return; pause(); setDay(KD[best], true); S = state(day); }
  openInfo({ type: 'unit', id, stack: [] });
  if (fly) { const a = u.kpos[S.i], b = u.kpos[S.j]; const x = a && b ? lerp(a.x, b.x, S.e) : (a || b).x, y = a && b ? lerp(a.y, b.y, S.e) : (a || b).y;
    const need = (u.tier === 0 && u.display !== 'detail' ? 0 : u.tier <= 1 ? 6.2 : 7.8) - (MOBILE ? 0.9 : 0); if (TOUR) setFollow(false);
    MAP.easeTo({ center: [ilon(x), ilat(y)], zoom: Math.max(MAP.getZoom(), need), duration: RM ? 0 : 700, offset: [0, -lockOff()] }); if (MOBILE) window.__setOob(false); } }
function selectEng(id, fly) { const e = D.engagements.find(x => x.id === id); if (!e) return;
  if (fly) { if (day < e.t0 || day > e.t1) { pause(); setDay(dayOf(e.date), true); } if (TOUR) setFollow(false); MAP.easeTo({ center: [e.lng, e.lat], zoom: Math.max(MAP.getZoom(), 6.8 - (MOBILE ? 0.9 : 0)), duration: RM ? 0 : 700, offset: [0, -lockOff()] }); if (MOBILE) window.__setOob(false); }
  openInfo({ type: 'eng', id }); }
function onPanelClick(ev) { const b = ev.target.closest('[data-u],[data-e],[data-day],[data-act],[data-tab],[data-ch],[data-side]'); if (!b) return;
  if (b.dataset.ch) return gotoChapter(+b.dataset.ch);
  if (b.dataset.side) { oobSide = b.dataset.side; infoKey = ''; return refreshInfo(true); }
  if (b.dataset.tab) { if (b.dataset.scope === 'oob') oobTab = b.dataset.tab; else infoTab = b.dataset.tab; infoKey = ''; refreshInfo(true); }
  else if (b.dataset.u) selectUnit(b.dataset.u, true); else if (b.dataset.e) selectEng(b.dataset.e, true);
  else if (b.dataset.day) { pause(); setDay(+b.dataset.day, true); refreshInfo(true); }
  else if (b.dataset.act === 'lock') setLock(lockId === selected.id ? null : selected.id); }
const ulink = id => `<button class="ul ${unitIdx[id].side}" data-u="${id}">${esc(unitIdx[id].name_zh)}</button>`;
function cmdHTML(id, compact) { const c = ASG[id];
  if (compact) return c ? `<small class="cmd-in">${esc(c.name_zh)}</small>` : '';
  if (!c) return `<div class="cmd none"><small>指揮官</small>資料待補</div>`;
  return `<div class="cmd"><small>${esc(c.title_zh || '指揮官')}</small><b>${esc(c.name_zh)}</b><span>${esc(c.name_orig || '')}</span><em>任期：${c.from || c.to ? `${c.from || '？'} – ${c.to || '？'}` : '待查'}｜${esc(c.status_zh || '需查證')}</em></div>`; }
function setView(v) { VIEW = v; if (v !== 'all') oobSide = v; document.body.dataset.view = v; renderChips(); infoKey = ''; refreshInfo(true); }
// 資訊卡：標題＋分頁。static（有可點的東西，內容變了才重畫）＋ live（純文字，播放時持續更新）
const tabs = (scope, cur, list) => `<div class="tabs" role="tablist">${list.map(([k, t, n]) => `<button role="tab" data-tab="${k}" data-scope="${scope}" aria-selected="${cur === k}" class="${cur === k ? 'on' : ''}">${t}${n ? `<i>${n}</i>` : ''}</button>`).join('')}</div>`;
const IMPZ = { 3: '關鍵', 2: '重要', 1: '' };
function engRow(e, u) { const st = day < e.t0 ? 'pre' : day > e.t1 ? 'post' : 'now'; const opp = u ? e.units.filter(x => unitIdx[x.unit_id].side !== u.side).map(x => ulink(x.unit_id)).join('') : '';
  return `<div class="eg ${st} i${e.imp}"><button class="el" data-e="${e.id}"><i>${fmtDay(dayOf(e.date))}</i><span>${esc(e.label)}</span>${IMPZ[e.imp] ? `<em>${IMPZ[e.imp]}</em>` : ''}${st === 'now' ? '<b>進行中</b>' : ''}</button>${opp ? `<div>對手：${opp}</div>` : ''}</div>`; }
function unitStatic(h) { const u = unitIdx[h.id], S = state(day);
  const chain = []; let p = u; while (p.parent_id) { p = unitIdx[p.parent_id]; chain.unshift(p.id); }
  const fam = lineage(u.id), engs = D.engagements.filter(e => e.units.some(x => fam.has(x.unit_id))).sort((a, b) => a.t0 - b.t0), nNow = engs.filter(e => day >= e.t0 && day <= e.t1).length;
  let pane;
  if (infoTab === 'eng') pane = engs.length ? engs.map(e => engRow(e, u)).join('') : '<div class="none">這個部隊沒有交戰紀錄</div>';
  else if (infoTab === 'org') pane = `<h4>上級</h4><div class="links">${chain.length ? chain.map(ulink).join('<b>›</b>') : '<span class="none">（最上層）</span>'}</div>${u.children.length ? `<h4>下轄</h4><div class="links">${u.children.map(ulink).join('')}</div>` : ''}${(h.stack || []).length ? `<h4>地圖上疊在一起</h4><div class="links">${h.stack.map(ulink).join('')}</div>` : ''}`;
  else if (infoTab === 'trk') pane = `<div class="wps">${u.kpos.map((q, k) => q ? `<button class="wp${k === S.i ? ' on' : ''}" data-day="${KD[k]}"><i>${fmtDay(KD[k])}</i><span>${ST[q.st] || q.st}</span>${(posBy[u.id][D.keyframes[k].date] || {}).status === 'derived' ? '<small>推算</small>' : ''}</button>` : '').join('')}</div><p class="hint">點日期跳到那一天。「推算」＝位置由上級單位推出來。</p>`;
  else pane = `${cmdHTML(u.id)}<div id="info-live"></div>`;
  return `<div class="ih"><img class="ic" alt="" src="${iconURL(u)}"><div><h3>${esc(u.name_zh)}</h3><div class="orig">${esc(u.name_orig)}</div></div></div>
    <div class="meta"><span class="${u.side}">${SIDE_NAME[u.side]}</span><span>${(ECH[u.echelon] || u.echelon).replace(/（.*）/, '')}</span><span>${BR[u.branch] || u.branch}</span><button data-act="lock" class="${lockId === u.id ? 'on' : ''}" title="鏡頭跟著這個部隊（快捷鍵 L）">${lockId === u.id ? '◉ 鎖定中' : '◎ 鎖定鏡頭'}</button></div>
    ${tabs('info', infoTab, [['ov', '概況'], ['eng', '交戰', nNow || ''], ['org', '編制'], ['trk', '航跡']])}<div class="pane">${pane}</div>
    <div class="foot"><span class="ex">${esc(D.meta.banner || '')}</span></div>`; }
function unitLive(h) { const u = unitIdx[h.id], S = state(day); if (!u._present || u._mx === undefined) return '<dl><dt>狀態</dt><dd>這個時間不在戰場上</dd></dl>';
  const lat = ilat(u._my), lng = ilon(u._mx); const pr = (posBy[u.id][D.keyframes[S.i].date] || posBy[u.id][D.keyframes[S.j].date] || {}).precision_m;
  const mv = u._spd > 1 ? `約 ${Math.round(u._spd)} 公里／日，往${DIRS[((Math.round(u._brg / (Math.PI / 4)) % 8) + 8) % 8]}` : '停留';
  return `<dl><dt>狀態</dt><dd>${ST[u._stNow] || '—'}</dd><dt>移動</dt><dd>${mv}</dd><dt>位置</dt><dd>${lat.toFixed(2)}°N　${Math.abs(lng).toFixed(2)}°${lng < 0 ? 'W' : 'E'}${pr ? `（±${Math.round(pr / 1000)} 公里）` : ''}</dd><dt>依據</dt><dd>${S.atKey ? '關鍵日的紀錄點' : '兩個紀錄點之間內插（推估）'}</dd></dl>`; }
function engStatic(h) { const e = D.engagements.find(x => x.id === h.id);
  const side = r => e.units.filter(x => x.role === r).map(x => `<div class="pr">${ulink(x.unit_id)}${cmdHTML(x.unit_id, true)}</div>`).join('') || '<span class="none">—</span>';
  return `<div class="ih"><div class="ic eng i${e.imp}">⚔</div><div><h3>${esc(e.label)}</h3><div class="orig">${e.date}｜${esc(e.interaction_zh)}</div></div></div>
    <div class="meta">${IMPZ[e.imp] ? `<span class="imp i${e.imp}">${IMPZ[e.imp]}交戰</span>` : '<span>一般交戰</span>'}<button data-day="${dayOf(e.date)}">跳到這一天</button></div>
    ${e.sum ? `<p class="sum">${esc(e.sum)}</p>` : ''}<div id="info-live"></div>
    <div class="vs"><div><h4>攻方</h4>${side('attacker')}</div><div><h4>守方</h4>${side('defender')}</div></div>
    <div class="foot"><span class="ex">${esc(D.meta.banner || '')}</span><span class="none">${D.meta.is_example ? '結果：示例資料不填' : ''}</span></div>`; }
function engLive(h) { const e = D.engagements.find(x => x.id === h.id); return `<dl><dt>狀態</dt><dd>${day < e.t0 ? '尚未開始' : day > e.t1 ? '已結束' : '進行中'}</dd><dt>時段</dt><dd>${fmtDay(e.t0)} – ${fmtDay(e.t1)}（起訖需查證）</dd></dl>`; }
const ICONS = {}; function iconURL(u) { return ICONS[u.id] || (ICONS[u.id] = counterCanvas(u, 1.5).cv.toDataURL()); }
let infoKey = '', liveKey = '', lastInfoT = 0, oobKey = '', nowKey = '';
function refreshInfo(force) { if (!D) return; const now = performance.now(); if (!force && now - lastInfoT < 200) return; lastInfoT = now;
  if (selected) { const st = selected.type === 'unit' ? unitStatic(selected) : engStatic(selected); if (st !== infoKey) { infoKey = st; liveKey = ''; $('#info-body').innerHTML = st; }
    const lv = selected.type === 'unit' ? unitLive(selected) : engLive(selected); if (lv !== liveKey) { liveKey = lv; const el = $('#info-live'); if (el) el.innerHTML = lv; } }
  if (!$('#oob').hidden) { const html = oobHTML(); if (html !== oobKey) { oobKey = html; const box = $('#oob-body'), old = box.querySelector('.ob-list'), k0 = old && old.dataset.k, st = old ? old.scrollTop : 0; box.innerHTML = html;
      const nl = box.querySelector('.ob-list'); if (nl.dataset.k === k0) nl.scrollTop = st;   // 重畫時保留捲動位置
      const on = oobTab === 'ch' && nl.querySelector('.ch.on'); if (on && (on.offsetTop < nl.scrollTop || on.offsetTop + on.offsetHeight > nl.scrollTop + nl.clientHeight)) nl.scrollTop = Math.max(0, on.offsetTop - 60); } }
  // 上方「交戰中」列：依重要度排，最重要的在前面；陣營視角時標出我方是攻還是守
  const S = state(day), act = TOUR ? [] : D.engagements.filter(e => engAlpha(e, S) > 0.01).sort((a, b) => b.imp - a.imp);
  const role = e => { if (VIEW === 'all') return ''; const m = e.units.find(x => unitIdx[x.unit_id].side === VIEW); return m ? `<small>${m.role === 'attacker' ? '我方進攻' : '我方防守'}</small>` : ''; };
  const names = (e, r) => e.units.filter(x => x.role === r).map(x => `<i class="${unitIdx[x.unit_id].side}">${esc(unitIdx[x.unit_id].name_zh)}</i>`).join('、');
  const ci = (S.atKey && S.u > 0.5) ? S.j : S.i;
  const kf = D.keyframes[ci];
  const nh = TOUR ? `<div class="ch on"><span class="ct"><i>${fmtDay(KD[ci])}</i><strong>${esc(kf.event_zh)}</strong></span>${kf.event_line ? `<span class="np">${esc(kf.event_line)}</span>` : ''}</div>` : `<h2>此刻的交戰<small>${act.length || ''}</small></h2>` + (act.length ? act.map(e => `<button data-e="${e.id}" data-fly="1" class="nc i${e.imp}${selected && selected.id === e.id ? ' sel' : ''}"><span class="nt">${e.imp === 3 ? '<b>關鍵</b>' : e.imp === 2 ? '<b class="b2">重要</b>' : ''}<strong>${esc(e.label)}</strong>${role(e)}</span>${e.imp >= 2 && e.sum ? `<span class="np">${esc(e.sum)}</span>` : ''}<span class="nv">${names(e, 'attacker') || '—'}<u>攻 ▸ 守</u>${names(e, 'defender') || '—'}</span></button>`).join('') : '<p class="none">這個時間沒有交戰紀錄</p>');
  document.body.classList.toggle('no-eng', !TOUR && !act.length);
  if (nh !== nowKey) { nowKey = nh; const el = $('#now'); el.innerHTML = nh; el.hidden = !nh; const on = TOUR && !MOBILE && el.querySelector('.ch.on'); if (on) el.scrollTop = Math.max(0, on.offsetTop - el.clientHeight / 2 + on.offsetHeight / 2); } }
function oobHTML() { const sel = selected && selected.type === 'unit' ? selected.id : null, selE = selected && selected.type === 'eng' ? selected.id : null, S = state(day), ci = (S.atKey && S.u > 0.5) ? S.j : S.i;
  const row = (u, d) => `<button class="ob ${u.side}${u._present ? '' : ' off'}${sel === u.id ? ' sel' : ''}" data-u="${u.id}" style="padding-left:${6 + d * 14}px"><img alt="" src="${iconURL(u)}"><span>${esc(u.name_zh)}</span><small>${u._present ? (STC[u._stNow] || '') : '—'}</small></button>` + u.children.map(id => row(unitIdx[id], d + 1)).join('');
  let body;
  if (oobTab === 'ch') body = D.keyframes.map((k, i) => `<button class="ch${i === ci ? ' on' : i < ci ? ' past' : ''}${k.major ? ' major' : ''}" data-ch="${i}"><span class="ct"><i>${fmtDay(KD[i])}</i><strong>${esc(k.event_zh)}</strong></span>${i === ci && k.event_line ? `<span class="np">${esc(k.event_line)}</span>` : ''}</button>`).join('') + '<p class="hint">點一章：跳到那一天，鏡頭移到當天的交戰地點。</p>';
  else if (oobTab === 'eng') body = D.engagements.slice().sort((a, b) => a.t0 - b.t0).map(e => { const st = day < e.t0 ? 'pre' : day > e.t1 ? 'post' : 'now';
    return `<button class="er ${st} i${e.imp}${selE === e.id ? ' sel' : ''}" data-e="${e.id}" data-fly="1"><i>${fmtDay(dayOf(e.date))}</i><span>${esc(e.label)}</span>${IMPZ[e.imp] ? `<em>${IMPZ[e.imp]}</em>` : ''}</button>`; }).join('');
  else body = `<div class="sub" role="group" aria-label="陣營">${SIDES.map(k => [k, SIDE_NAME[k]]).map(([k, t]) => `<button data-side="${k}" class="${k}${oobSide === k ? ' on' : ''}" aria-pressed="${oobSide === k}">${t}</button>`).join('')}</div>` + D.units.filter(u => !u.parent_id && u.side === oobSide).map(u => row(u, 0)).join('');
  return tabs('oob', oobTab, [['ch', '章節'], ['units', '部隊'], ['eng', '交戰']]) + `<div class="ob-list" data-k="${oobTab}${oobTab === 'units' ? oobSide : ''}">${body}</div>`; }
function openInfo(h) { selected = h; if (lockId && !(h.type === 'unit' && h.id === lockId)) lockId = null; infoKey = ''; $('#info').hidden = false; refreshInfo(true); }
function closeInfo() { selected = null; lockId = null; $('#info').hidden = true; refreshInfo(true); }
// ---------- 主迴圈＋效能取樣 ----------
const bench = { on: false, dts: [], work: [] }; window.__bench = { start() { bench.dts = []; bench.slow = []; bench.on = true; }, stop() { bench.on = false; return { dts: bench.dts.slice(), slow: bench.slow || [] }; } };
let lastFrame = 0; const slowWin = []; let slowSum = 0, fbStage = Q.get('glass') === '0' ? 1 : 0;
function loop(now) {
  // 自動降級（兩段）：最近 180 幀有超過 18 幀大於 22ms → ①關掉 UI 毛玻璃；仍然慢 → ②地圖畫布解析度降到 0.85 倍（只在沒有 GPU 的環境會發生）
  if (lastFrame && fbStage < 2) { const d = now - lastFrame; slowWin.push(d > 22 ? 1 : 0); slowSum += d > 22 ? 1 : 0; if (slowWin.length > 180) slowSum -= slowWin.shift();
    if (slowWin.length >= 120 && slowSum > 18 && now > 4000) { if (Q.get('glass') !== 'keep' && fbStage === 0) { document.body.classList.add('no-blur'); window.__blurFallback = true; fbStage = 1; }
      else if (Q.get('pr') == null) { MAP.setPixelRatio(DPR * 0.85); window.__prFallback = +(DPR * 0.85).toFixed(2); fbStage = 2; } else fbStage = 2;
      slowWin.length = 0; slowSum = 0; } }
  if (bench.on && lastFrame) { bench.dts.push(now - lastFrame); if (now - lastFrame > 20) bench.slow.push([+day.toFixed(2), +(now - lastFrame).toFixed(1), +MAP.getZoom().toFixed(2)]); } lastFrame = now;
  const dt = lastT ? Math.min((now - lastT) / 1000, 0.1) : 0; lastT = now; dtGlobal = dt || 0.016;
  if (playing) { if (RM) stepRM(dt); else setDay(day + dt * speed / (TOUR ? SEC_PER_DAY : 1)); if (day >= KD[KD.length - 1]) pause(); }
  if (D) { stepLayers(state(day), dtGlobal); setRiverOpacity(); applyCamera(now); MAP.triggerRepaint(); refreshInfo(); }
  requestAnimationFrame(loop);
}
let rmAcc = 0; function stepRM(dt) { rmAcc += dt * speed; if (rmAcc > 2) { rmAcc = 0; const i = KD.findIndex(k => k > day + 1e-3); if (i < 0) pause(); else jumpTo(i); } }
})();
