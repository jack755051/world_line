/* 敦克爾克 1940 兩軍對壘示範 v2.2（示例，非史料）
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
const DAY0 = Date.UTC(1940, 4, 10);
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
const BBOX = [-6.5, 46.0, 13.0, 56.5];
const rgba = (r, g, b, a) => [r / 255, g / 255, b / 255, a];
const COL = { sea: '#0a1720', land: '#26292a', uk: '#24303a', allied: '#264b85', coast: '#7f97a3', river: 'rgba(90,150,190,0.55)', border: 'rgba(200,210,215,0.28)' };
const KEY_RIVERS = ['Maas', 'Schelde', 'Mosel', 'Rhein', 'Rhin', 'Rhine', 'Waal', 'Lek', 'Nederrijn', 'IJssel', 'Thames'];
const AXIS_FILL = rgba(92, 18, 22, 0.86), ALLIED_FILL = rgba(38, 75, 133, 1);
let D, MAP, W = 0, H = 0, DPR = 1, MOBILE = false;
let KD = [], FR = [], PKS = [], unitIdx = {}, posBy = {}, SP = {}, CITYIDX = {};
let day = 0, playing = false, speed = 1, lastT = 0, lastEventKey = -1, selected = null, hover = null, hits = [];
let follow = Q.get('follow') !== '0', resume = null, dtGlobal = 0.016;
// ---------- 圖層（醋酸片疊圖）----------
const LAYERS = {
  forces: { key: 'B', name: '兵力調動', mode: 'on', a: 1, tint: '226,220,206' },
  eng:    { key: 'C', name: '交戰',     mode: 'auto', a: 1, tint: '226,220,206' },
  places: { key: 'D', name: '地名與註記', mode: 'auto', a: 1, tint: '226,220,206' },
};
['forces', 'eng', 'places'].forEach(k => { const v = Q.get('L' + k); if (v) LAYERS[k].mode = v; });
function layerTarget(k, S) {
  const L = LAYERS[k]; if (L.mode === 'on') return 1; if (L.mode === 'off') return 0;
  if (k === 'eng') { const kf = D.keyframes[S.u > 0.5 ? S.j : S.i]; return D.engagements.some(e => e.k === S.i || e.k === S.j) && (kf.focus || []).includes('engagements') ? 1 : 0; }
  return 1;
}
function stepLayers(S, dt) { for (const k in LAYERS) { const L = LAYERS[k], t = layerTarget(k, S); L.a = RM ? t : L.a + (t - L.a) * Math.min(1, dt * 5); if (Math.abs(L.a - t) < 0.01) L.a = t; } }
const shocks = [];

// ---------- 載入 ----------
fetch(Q.get('data') || 'data/dunkirk-1940.example.json').then(r => r.json()).then(data => {
  D = data; prep(); measure(); buildSprites(); initMap(); bindUI();
  const qd = Q.get('date'); if (qd) day = clamp(dayOf(qd), 0, KD[KD.length - 1]); if (Q.get('day')) day = clamp(+Q.get('day'), 0, KD[KD.length - 1]);
  setDay(day, true);
  if (Q.get('speed')) setSpeed(+Q.get('speed'));
  const vw = Q.get('view'); if (vw) { const [lo, la, z] = vw.split(',').map(Number); setFollow(false); MAP.jumpTo({ center: [lo, la], zoom: z }); }
  else applyCamera(performance.now());
  MAP.once('load', () => { const chk = () => { if (MAP.areTilesLoaded() && MAP.getLayer('battle')) { window.__ready = true; if (Q.get('autoplay') === '1') play(true); } else setTimeout(chk, 80); }; chk(); });
  requestAnimationFrame(loop);
});

// ---------- 資料前處理 ----------
const CITIES = [['敦克爾克', 2.377, 51.034, 3], ['加萊', 1.858, 50.951, 2], ['布洛涅', 1.614, 50.726, 2], ['阿布維爾', 1.835, 50.105, 2], ['亞眠', 2.295, 49.894, 2],
  ['阿拉斯', 2.777, 50.291, 2], ['里爾', 3.057, 50.629, 2], ['色當', 4.944, 49.702, 3], ['迪南', 4.912, 50.261, 2], ['布魯塞爾', 4.352, 50.847, 3], ['安特衛普', 4.402, 51.219, 2],
  ['鹿特丹', 4.479, 51.924, 2], ['阿姆斯特丹', 4.9, 52.37, 2], ['奧斯坦德', 2.918, 51.226, 1], ['尼烏波特', 2.75, 51.13, 1], ['伊珀爾', 2.885, 50.851, 1], ['巴黎', 2.352, 48.857, 3],
  ['多佛', 1.313, 51.128, 2], ['倫敦', -0.12, 51.507, 3], ['列日', 5.57, 50.633, 2], ['盧森堡', 6.13, 49.61, 1], ['聖康坦', 3.287, 49.848, 1], ['蘭斯', 4.03, 49.26, 1],
  ['根特', 3.72, 51.05, 1], ['格拉沃利訥', 2.128, 50.986, 1], ['聖奧梅爾', 2.252, 50.75, 1], ['科隆', 6.96, 50.94, 2], ['蒙科爾內', 4.016, 49.693, 1], ['讓布盧', 4.69, 50.56, 1], ['漢努特', 5.08, 50.67, 1], ['蒙泰梅', 4.737, 49.882, 1], ['拉昂', 3.62, 49.564, 1], ['拉帕訥', 2.59, 51.10, 1]];
const SEAS = [['北　海', 3.0, 52.75], ['英吉利海峽', 0.2, 50.3]];
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
const TIER = { army: 0, corps: 1, division: 2, brigade: 2 };
// 「取代型」上級：放大展開後自己隱藏（子單位就是它的全部）；其他上級（集團軍）保留，子單位另外出現
const REPLACE = new Set(['de-pgk', 'bef', 'de-xix', 'de-xli', 'de-xv', 'de-xvi', 'fr-cc']);
function prep() {
  KD = D.keyframes.map(k => dayOf(k.date));
  const fr = D.keyframes.map(k => D.fronts.find(f => f.date === k.date));
  FR = fr.map(f => resampleRing(f.line, N, false));
  // 包圍圈：每個 id 在每個關鍵日的形狀（逆時針、起點對齊）
  PKS = fr.map(f => { const o = {}; (f.pockets || []).forEach(p => { let r = p.ring.slice(); if (ringArea(r) < 0) r.reverse();
    const s = resampleRing(r, NPK, true); let cx = 0, cy = 0; for (let k = 0; k < NPK; k++) { cx += s[2 * k]; cy += s[2 * k + 1]; } cx /= NPK; cy /= NPK;
    // 起點對齊：從正北方向最近的點開始
    let best = 0, bd = -1e9; for (let k = 0; k < NPK; k++) { const v = s[2 * k + 1] - cy - Math.abs(s[2 * k] - cx); if (v > bd) { bd = v; best = k; } }
    const a = new Float64Array(NPK * 2); for (let k = 0; k < NPK; k++) { const q = (best + k) % NPK; a[2 * k] = s[2 * q]; a[2 * k + 1] = s[2 * q + 1]; }
    o[p.id] = { id: p.id, side: p.side, name: p.name_zh, ring: a, cx, cy }; }); return o; });
  D.units.forEach(u => { unitIdx[u.id] = u; posBy[u.id] = {}; });
  D.positions.forEach(p => { posBy[p.unit_id][p.date] = p; });
  D.arrows.forEach(a => { a.k = D.keyframes.findIndex(k => k.date === a.date); a.sm = smoothPath(a.path); });
  D.engagements.forEach(e => { e.k = D.keyframes.findIndex(k => k.date === e.date); e.x = mx(e.lng); e.y = my(e.lat); });
  D.units.forEach(u => { u.kpos = D.keyframes.map(k => { const p = posBy[u.id][k.date]; return p ? { x: mx(p.lng), y: my(p.lat), st: p.state } : null; }); });
  D.units.forEach(u => { u.children = D.units.filter(c => c.parent_id === u.id).map(c => c.id); u.tier = TIER[u.echelon] ?? 1; u.replace = REPLACE.has(u.id) || u.replace === true; u._st = 0; u._sa = 0; });
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
  ['overview', 'mid', 'close'].forEach(n => CAM[n] = camFor(n)); }
function camFor(name) {
  const b = (MOBILE && D.meta.cameras_mobile ? D.meta.cameras_mobile : D.meta.cameras)[name]; const padT = MOBILE ? 8 : 90, padB = MOBILE ? 8 : 104, padX = MOBILE ? 6 : 30;
  const x0 = mx(b[0]), x1 = mx(b[2]), y0 = my(b[1]), y1 = my(b[3]);
  const s = Math.min((W - 2 * padX) / (x1 - x0), (H - padT - padB) / (y1 - y0));
  return { x: (x0 + x1) / 2, y: (y0 + y1) / 2 + (padT - padB) / 2 / s, z: Math.log2(s * 2 * Math.PI / 512) };
}
function segIndex(d) { let i = 0; while (i < KD.length - 2 && d >= KD[i + 1]) i++; return i; }
function camAt(d) {
  const i = segIndex(d), a = CAM[D.keyframes[i].camera], b = CAM[D.keyframes[Math.min(i + 1, KD.length - 1)].camera];
  if (a === b) return a; const u = (d - KD[i]) / (KD[i + 1] - KD[i]); const t = RM ? (u >= 1 ? 1 : 0) : ease(clamp((u - 0.35) / 0.6, 0, 1));
  return { x: lerp(a.x, b.x, t), y: lerp(a.y, b.y, t), z: lerp(a.z, b.z, t) };
}
function applyCamera(now) {
  if (!follow) return; let c = camAt(day);
  if (resume) { const t = ease(clamp((now - resume.t0) / 900, 0, 1)); c = { x: lerp(resume.x, c.x, t), y: lerp(resume.y, c.y, t), z: lerp(resume.z, c.z, t) }; if (t >= 1) resume = null; }
  const cur = MAP.getCenter(), z0 = MAP.getZoom(); const lo = ilon(c.x), la = ilat(c.y);
  if (Math.abs(cur.lng - lo) < 1e-7 && Math.abs(cur.lat - la) < 1e-7 && Math.abs(z0 - c.z) < 1e-6) return;
  MAP.jumpTo({ center: [lo, la], zoom: c.z });
}
function setFollow(v) { if (v && !follow) { const c = MAP.getCenter(); resume = { t0: performance.now(), x: mx(c.lng), y: my(c.lat), z: MAP.getZoom() }; }
  follow = v; $('#follow').hidden = v; }

// ---------- 地圖 ----------
function initMap() {
  const src = n => ({ type: 'geojson', data: `geo/${n}.geojson`, maxzoom: 7, tolerance: 0.3, buffer: 16 });
  const style = { version: 8, sources: { land: src('land'), landc: src('landc'), rivers: src('rivers'), borders: src('borders'), sea: src('sea'), grat: src('graticule') },
    layers: [
      { id: 'bg', type: 'background', paint: { 'background-color': COL.sea } },
      { id: 'land', type: 'fill', source: 'landc', paint: { 'fill-antialias': false, 'fill-color': ['match', ['get', 'k'], 'allied', COL.allied, 'uk', COL.uk, COL.land] } },
      { id: 'sea', type: 'fill', source: 'sea', paint: { 'fill-color': COL.sea, 'fill-antialias': false } },
      // v2.2：海上經緯網與海岸外光拿掉（軟體 GL 下這兩層加起來約 2–3 ms／幀），只留 1px 海岸線；放大到 7.5 級以上再加回經緯網
      { id: 'grat', type: 'line', source: 'grat', minzoom: 7.5, paint: { 'line-color': 'rgba(120,170,200,0.08)', 'line-width': 1 } },
      { id: 'coast', type: 'line', source: 'land', paint: { 'line-color': COL.coast, 'line-width': 1.1 } },
      // 戰役相關河流（默茲、斯海爾德、摩澤爾、萊茵）一直顯示；其他河流放大到 7 級以上才出現（也省軟體 GL 的填色成本）
      { id: 'rivers', type: 'line', source: 'rivers', filter: ['in', ['get', 'name'], ['literal', KEY_RIVERS]], paint: { 'line-color': COL.river, 'line-width': ['interpolate', ['linear'], ['zoom'], 6, 0.9, 9, 1.8] } },
      { id: 'rivers-other', type: 'line', source: 'rivers', minzoom: 7, filter: ['!', ['in', ['get', 'name'], ['literal', KEY_RIVERS]]], paint: { 'line-color': COL.river, 'line-width': 0.9 } },
      // 國界：實線細線（虛線 SDF 在軟體 GL 下每像素多一次貼圖查詢）
      { id: 'borders', type: 'line', source: 'borders', paint: { 'line-color': 'rgba(200,210,215,0.22)', 'line-width': 1 } },
    ] };
  const c0 = CAM.overview;
  MAP = new maplibregl.Map({ container: 'map', style, center: [ilon(c0.x), ilat(c0.y)], zoom: c0.z, minZoom: 4.6, maxZoom: 10.5, maxBounds: [[BBOX[0], BBOX[1]], [BBOX[2], BBOX[3]]],
    dragRotate: false, pitchWithRotate: false, touchPitch: false, keyboard: false, fadeDuration: 0, attributionControl: false, pixelRatio: DPR, antialias: false, renderWorldCopies: false, maxTileCacheSize: 200 });
  MAP.touchZoomRotate.disableRotation();
  MAP.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right');
  MAP.addControl(new maplibregl.AttributionControl({ compact: true, customAttribution: '底圖：Natural Earth（公有領域）｜MapLibre GL JS' }), 'bottom-right');
  MAP.on('load', () => { MAP.addLayer(terrLayer, 'sea'); MAP.addLayer(battleLayer); document.querySelectorAll('.maplibregl-compact-show').forEach(e => e.classList.remove('maplibregl-compact-show'));
    (Q.get('hide') || '').split(',').filter(Boolean).forEach(l => MAP.getLayer(l) && MAP.setLayoutProperty(l, 'visibility', 'none')); });   // 除錯／量測用
  MAP.on('movestart', e => { if (e.originalEvent) setFollow(false); });
  window.__map = MAP;
}
const terrLayer = { id: 'terr', type: 'custom', renderingMode: '2d', onAdd(m, gl) { BGL.init(gl); }, render(gl) { computeFrame(); BGL.begin(); drawTerritory(); BGL.flush(W, H); } };
const battleLayer = { id: 'battle', type: 'custom', renderingMode: '2d', onAdd(m, gl) { BGL.init(gl); }, render(gl) { BGL.begin(); drawTop(); BGL.flush(W, H); } };

// ---------- 符號圖集 ----------
function textCanvas(txt, font, fill, stroke, sw, dot) {
  const c = document.createElement('canvas'), g = c.getContext('2d'); g.font = font; const tw = g.measureText(txt).width; const fs = parseFloat(font.match(/(\d+(\.\d+)?)px/)[1]);
  const pad = sw + 2, dx = dot ? 8 : 0, w = Math.ceil(tw + pad * 2 + dx), h = Math.ceil(fs * 1.4 + pad * 2);
  c.width = Math.ceil(w * DPR); c.height = Math.ceil(h * DPR); g.scale(DPR, DPR); g.font = font; g.textBaseline = 'middle'; g.lineJoin = 'round';
  if (dot) { g.fillStyle = '#e2dccd'; g.strokeStyle = 'rgba(5,8,12,0.85)'; g.lineWidth = 2; g.beginPath(); g.arc(pad + 2.5, h / 2 + fs * 0.35, 2.3, 0, 7); g.stroke(); g.fill(); }
  if (sw) { g.strokeStyle = stroke; g.lineWidth = sw; g.strokeText(txt, pad + dx, h / 2); } g.fillStyle = fill; g.fillText(txt, pad + dx, h / 2);
  return { c, w, h, ax: dot ? pad + 2.5 : w / 2, ay: dot ? h / 2 + fs * 0.35 : h / 2 };
}
function buildSprites() {
  const A = BGL.Atlas(DPR, 2048); const add = (cv, w, h, ax, ay) => A.add(cv, w, h, ax, ay);
  const size = MOBILE ? 15 : 22;
  SP.unit = {};
  D.units.forEach(u => {
    SP.unit[u.id] = ['P', 'A'].map(st => {
      const code = u.sidc.slice(0, 3) + st + u.sidc.slice(4);
      const sym = new ms.Symbol(code, { size: u.echelon === 'army' ? size + 2 : size, uniqueDesignation: u.label, outlineWidth: 3, outlineColor: 'rgba(4,6,10,0.95)',
        infoColor: '#f1ece0', infoSize: 46, colorMode: u.side === 'axis' ? { Hostile: '#ff6a5c' } : { Friend: '#79c8ff' } });
      const cv = sym.asCanvas(DPR); const a = sym.getAnchor(), sz = sym.getSize();
      return add(cv, sz.width, sz.height, a.x, a.y);
    });
  });
  const disc = (txt, bg, d = 16, fsz = 10) => { const c = document.createElement('canvas'); c.width = c.height = Math.round(d * DPR); const g = c.getContext('2d'); g.scale(DPR, DPR);
    g.fillStyle = bg; g.beginPath(); g.arc(d / 2, d / 2, d / 2 - 0.5, 0, 7); g.fill(); g.strokeStyle = '#000'; g.lineWidth = 1; g.stroke();
    g.fillStyle = '#fff'; g.font = `700 ${fsz}px "Noto Sans CJK TC",sans-serif`; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(txt, d / 2, d / 2 + 0.5); return add(c, d, d); };
  SP.badge = { attack: disc('攻', '#d8341f'), defend: disc('守', '#2f6fd0'), retreat: disc('退', '#7d6a3a'), encircled: disc('圍', '#8a1f6a'), surrendered: disc('降', '#555'), evacuating: disc('撤', '#1b8a9a') };
  SP.count = {}; for (let n = 1; n <= 12; n++) { const c = document.createElement('canvas'); const w = n >= 10 ? 26 : 22, h = 15; c.width = Math.round(w * DPR); c.height = Math.round(h * DPR); const g = c.getContext('2d'); g.scale(DPR, DPR);
    g.fillStyle = 'rgba(12,16,20,0.92)'; g.strokeStyle = 'rgba(217,196,143,0.9)'; g.lineWidth = 1; g.beginPath(); g.roundRect(0.5, 0.5, w - 1, h - 1, 7); g.fill(); g.stroke();
    g.fillStyle = '#e9dfc2'; g.font = '700 10.5px "Noto Sans CJK TC",sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('+' + n, w / 2, h / 2 + 0.5); SP.count[n] = add(c, w, h); }
  { const c = document.createElement('canvas'), d = 18; c.width = c.height = Math.round(d * DPR); const g = c.getContext('2d'); g.scale(DPR, DPR); g.translate(9, 9);
    g.strokeStyle = 'rgba(217,196,143,0.95)'; g.lineWidth = 1.6; g.lineCap = 'round'; g.beginPath();
    g.moveTo(-5, 5); g.lineTo(5, -5); g.moveTo(5, 5); g.lineTo(-5, -5); g.moveTo(-6.5, 2); g.lineTo(-2, 6.5); g.moveTo(6.5, 2); g.lineTo(2, 6.5); g.stroke(); SP.swords = add(c, d, d); }
  { const c = document.createElement('canvas'), d = 16; c.width = c.height = Math.round(d * DPR); const g = c.getContext('2d'); g.scale(DPR, DPR); const r = g.createRadialGradient(8, 8, 0, 8, 8, 8);
    r.addColorStop(0, 'rgba(230,252,255,1)'); r.addColorStop(0.4, 'rgba(127,227,255,0.6)'); r.addColorStop(1, 'rgba(127,227,255,0)'); g.fillStyle = r; g.fillRect(0, 0, d, d); SP.ship = add(c, 8, 8); }
  const fs = MOBILE ? 11 : 13; SP.city = {};
  CITIES.forEach(([n]) => { const t = textCanvas(n, `500 ${fs}px "Noto Sans CJK TC",sans-serif`, '#e2dccd', 'rgba(5,8,12,0.85)', 3, true); SP.city[n] = add(t.c, t.w, t.h, t.ax, t.ay + fs * 0.0); SP.city[n].tw = t.w; SP.city[n].th = t.h; });
  SP.sheet = {}; for (const k of SHEET_ORDER) { const L = LAYERS[k]; const fs2 = MOBILE ? 9.5 : 11; const t = textCanvas(`${L.key}｜${L.name}`, `700 ${fs2}px "Noto Sans CJK TC",sans-serif`, 'rgba(226,220,206,0.75)', null, 0, false);
    const c2 = document.createElement('canvas'); c2.width = t.c.width; c2.height = t.c.height; const g2 = c2.getContext('2d'); g2.fillStyle = 'rgba(226,220,206,0.10)'; g2.fillRect(0, Math.round(3 * DPR), c2.width, c2.height - Math.round(6 * DPR)); g2.drawImage(t.c, 0, 0); SP.sheet[k] = add(c2, t.w, t.h, 0, 0); }
  SP.sea = SEAS.map(([n]) => { const t = textCanvas(n, `italic ${MOBILE ? 12 : 15}px "Noto Serif CJK TC",serif`, 'rgba(127,200,230,0.8)', null, 0, false); return add(t.c, t.w, t.h); });
  BGL.setAtlas(A.cv); window.__atlas = A.cv;
}

// ---------- 每幀狀態 ----------
function state(d) {
  const i = segIndex(d), j = Math.min(i + 1, KD.length - 1);
  const u = j === i ? 0 : clamp((d - KD[i]) / (KD[j] - KD[i]), 0, 1), e = RM ? (u < 1 ? 0 : 1) : ease(u);
  return { i, j, u, e, atKey: Math.min(Math.abs(d - KD[i]), Math.abs(d - KD[j])) < 0.04 };
}
let F = null; let CX = 0, CY = 0, SC = 1, ZOOM = 6;
const PX = x => (x - CX) * SC + W / 2, PY = y => -(y - CY) * SC + H / 2;
const front = new Float64Array(N * 2);
// 縮放分級：λ 0＝集團軍、1＝軍、2＝師。手機符號較小，等效縮放 +0.9
function lambdaFor(z) { const ez = z + (MOBILE ? 0.9 : 0); return sstep(5.6, 6.0, ez) + sstep(7.25, 7.6, ez); }
function computeFrame() {
  const c = MAP.getCenter(); ZOOM = MAP.getZoom(); CX = mx(c.lng); CY = my(c.lat); SC = 512 * Math.pow(2, ZOOM) / (2 * Math.PI);
  const S = state(day); const A = FR[S.i], B = FR[S.j]; for (let k = 0; k < N * 2; k++) front[k] = lerp(A[k], B[k], S.e);
  hits = [];
  F = { S, lam: lambdaFor(ZOOM), now: performance.now() };
  F.units = unitScreens(S, F.lam);
}
// ---------- A：控制區＋包圍圈＋前線 ----------
function drawTerritory() {
  const S = F.S; const flat = new Float64Array(N * 2 + 6); const pts = new Array(N);
  for (let n = 0; n < N; n++) { const X = PX(front[2 * n]), Y = PY(front[2 * n + 1]); flat[2 * n] = X; flat[2 * n + 1] = Y; pts[n] = [X, Y]; }
  const cl = [[mx(13.2), my(46.5)], [mx(13.2), my(56.8)], [front[0], my(56.8)]]; cl.forEach((p, k) => { flat[2 * N + 2 * k] = PX(p[0]); flat[2 * N + 2 * k + 1] = PY(p[1]); });
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
  const core = S.atKey ? rgba(240, 228, 206, 0.9) : rgba(240, 228, 206, 0.7), dash = S.atKey ? null : [7, 5];
  // 只畫畫面附近的前線點（省頂點）
  if (!DBG.includes('noline')) { BGL.line(pts, false, 7, rgba(220, 70, 55, 0.22)); BGL.line(pts, false, 1.5, core, dash); }
  for (const r of rings) { BGL.line(r.pp, true, 7, rgba(220, 70, 55, 0.22 * r.ra)); BGL.line(r.pp, true, 1.5, [core[0], core[1], core[2], core[3] * r.ra], dash); }
}
// ---------- 上層：D 地名 → B 兵力 → C 交戰 ----------
function drawTop() {
  const S = F.S;
  stepSheets();
  LATE = [];
  drawSheet('places', LAYERS.places.a); if (LAYERS.places.a > 0.03) drawPlaces(S, LAYERS.places.a);
  drawSheet('forces', LAYERS.forces.a); if (LAYERS.forces.a > 0.02) { drawArrows(S, LAYERS.forces.a); if (!RM) drawShips(S, LAYERS.forces.a); drawUnits(F.units, S, LAYERS.forces.a); }
  for (const l of LATE) BGL.sprite(l[0], l[1], l[2], 1, l[3]);
  drawSheet('eng', LAYERS.eng.a); if (LAYERS.eng.a > 0.02) drawEngagements(S, LAYERS.eng.a);
  drawPocketTags(S);
  if (!RM) drawShocks();
  updateTip();
}
// 醋酸片片框：畫在 WebGL 裡（只畫片緣、套準十字、片名；不做整片底色，省三次全畫面混色）
const SHEET_ORDER = ['places', 'forces', 'eng'];
function drawSheet(k, A) {
  if (A < 0.02) return; const i = SHEET_ORDER.indexOf(k) + 1; const m = (MOBILE ? 4 : 8) + i * (MOBILE ? 3 : 5);
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
const AST = { armor: [5, 22, [232, 98, 82], 22], infantry: [3, 12, [214, 128, 114], 15], motorized: [4, 15, [104, 160, 236], 17], counter: [5, 18, [104, 160, 236], 20], retreat: [3, 10, [140, 162, 190], 13] };
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
    BGL.line(g.ring, true, 3, [0, 0, 0, 0.55 * alpha]);
    const [r, gg, b] = st[2]; const col = f => rgba(r, gg, b, alpha * (f < 0.5 ? lerp(0.1, 0.6, f * 2) : lerp(0.6, 0.95, (f - 0.5) * 2)));
    const T = [];
    for (let i = 0; i < g.L2.length - 1; i++) { const c0 = col(g.F2[i]), c1 = col(g.F2[i + 1]);
      T.push([g.L2[i][0], g.L2[i][1], c0], [g.R2[i][0], g.R2[i][1], c0], [g.L2[i + 1][0], g.L2[i + 1][1], c1], [g.R2[i][0], g.R2[i][1], c0], [g.R2[i + 1][0], g.R2[i + 1][1], c1], [g.L2[i + 1][0], g.L2[i + 1][1], c1]); }
    const ch = col(1); T.push([g.HL[0], g.HL[1], ch], [g.tip[0], g.tip[1], ch], [g.HR[0], g.HR[1], ch]);
    BGL.tris(T);
    BGL.line(g.ring, true, 1, rgba(240, 228, 206, (a.kind === 'retreat' ? 0.35 : 0.55) * alpha), a.kind === 'retreat' ? [5, 4] : null);
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
    let x, y, al = 1, st;
    if (a && b) { x = lerp(a.x, b.x, S.e); y = lerp(a.y, b.y, S.e); st = S.u < 0.5 ? a.st : b.st; }
    else if (a) { x = a.x; y = a.y; al = 1 - S.e; st = a.st; if (S.i === S.j) al = 1; }
    else { x = b.x; y = b.y; al = S.e; st = b.st; }
    u._mx = x; u._my = y;
    al *= aggW(u, lam); u._vis = al;
    if (al < 0.03) continue;
    const fw = lerp(D.keyframes[S.i].fset.has(u.id) ? 1 : 0, D.keyframes[S.j].fset.has(u.id) ? 1 : 0, S.e);
    out.push({ u, X: PX(x), Y: PY(y), al, st, fw, members: [] });
  }
  // 堆疊：同陣營、距離小於 r 的符號併成一格（焦點／高梯隊當代表），右上角顯示 +n
  const r = MOBILE ? 19 : 27; out.sort((p, q) => (q.fw - p.fw) || (q.al - p.al) || (p.u.tier - q.u.tier));
  const heads = [];
  for (const o of out) { let h = null; if (o.al > 0.25) for (const k of heads) { if (k.u.side === o.u.side && Math.abs(k.X - o.X) < r && Math.abs(k.Y - o.Y) < r * 0.8) { h = k; break; } }
    if (h) { h.members.push(o); o.head = h; } else if (o.al > 0.25) heads.push(o); else o.head = null; }
  for (const o of out) { const tgt = o.head ? 1 : 0; o.u._st = RM ? tgt : o.u._st + (tgt - o.u._st) * Math.min(1, dt * 9); }
  return out;
}
function drawUnits(list, S, LA) {
  const interp = !S.atKey;
  // 先畫非焦點，再畫焦點（焦點壓在上面）
  const order = list.slice().sort((a, b) => a.fw - b.fw);
  for (const o of order) {
    const sp = SP.unit[o.u.id][interp ? 1 : 0];
    const isHover = hover && hover.type === 'unit' && hover.id === o.u.id, f = isHover ? 1 : o.fw;
    const sc = lerp(0.72, 1, f); const al = o.al * LA * lerp(0.4, 1, f) * (1 - o.u._st);
    if (al < 0.01) continue;
    const X = Math.round(o.X * DPR) / DPR, Y = Math.round(o.Y * DPR) / DPR;
    const nm = o.members.filter(m => m.al > 0.25).length;
    if (nm) { BGL.sprite(sp, X + 6 * sc, Y - 5 * sc, sc, al * 0.3); BGL.sprite(sp, X + 3 * sc, Y - 2.5 * sc, sc, al * 0.55); }
    BGL.sprite(sp, X, Y, sc, al);
    const bd = SP.badge[o.st]; if (bd && o.st !== 'move' && f > 0.5) BGL.sprite(bd, X + 14 * sc, Y - 14 * sc, 0.95, al * clamp((f - 0.5) * 2, 0, 1));
    if (nm) BGL.sprite(SP.count[Math.min(nm, 12)], X - sp.ax * sc - 4, Y - sp.ay * sc + 2, 1, Math.max(al, 0.75 * LA * o.al));
    if (selected && selected.type === 'unit' && selected.id === o.u.id) { const x0 = X - sp.ax * sc - 3, y0 = Y - sp.ay * sc - 3, x1 = x0 + sp.w * sc + 6, y1 = y0 + sp.h * sc + 6; BGL.line([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], true, 1.5, rgba(217, 196, 143, 1)); }
    hits.push({ type: 'unit', id: o.u.id, x: o.X, y: o.Y, r: 22, stack: o.members.map(m => m.u.id) });
  }
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
function drawEngagements(S, LA) {
  for (const e of D.engagements) {
    let al;
    if (e.k === S.j && S.j !== S.i) al = clamp((S.u - 0.55) / 0.35, 0, 1);
    else if (e.k === S.i) al = S.i === KD.length - 1 ? 1 : clamp(1 - (S.u - 0.15) / 0.3, 0, 1);
    else continue;
    if (al <= 0.01) continue;
    const X = PX(e.x), Y = PY(e.y); if (X < -40 || Y < -40 || X > W + 40 || Y > H + 40) continue;
    const isHover = hover && hover.type === 'eng' && hover.id === e.id;
    al *= LA * (e.focus || isHover ? 1 : 0.38);
    if (e.focus || isHover) for (const p of e.units) { const q = reprPos(p.unit_id); if (!q) continue;
      const c = unitIdx[p.unit_id].side === 'axis' ? rgba(232, 98, 82, 0.55 * al) : rgba(104, 160, 236, 0.55 * al);
      BGL.line([[q[0], q[1]], [X, Y]], false, 1, c, p.role === 'attacker' ? [4, 3] : [1.5, 3]); }
    const br = RM ? 0.5 : 0.5 + 0.5 * Math.sin(F.now / 1100);
    BGL.circle(X, Y, 11 + br * 2, 1, rgba(217, 196, 143, (0.25 + 0.2 * br) * al), 32);
    BGL.sprite(SP.swords, X, Y, 1, al);
    hits.push({ type: 'eng', id: e.id, x: X, y: Y, r: 16 });
    e._X = X; e._Y = Y; e._on = al;
  }
}
// 包圍圈名稱（D 片開著時，放大才顯示）
function drawPocketTags(S) { /* 名稱放在 HTML 小標（#pk-tags），避免另做文字圖集 */
  const box = $('#pk-tags'); const show = LAYERS.places.a > 0.3 && ZOOM + (MOBILE ? 0.9 : 0) > 7.0; const want = show ? F.pockets.filter(p => p.ra > 0.5) : [];
  const key = want.map(p => p.meta.id).join(','); if (box._key !== key) { box._key = key; box.innerHTML = want.map(p => `<span data-id="${p.meta.id}">${p.meta.name}<small>示例</small></span>`).join(''); }
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
  for (const c of cand) { const sp = SP.city[c.n]; const x0 = c.X - sp.ax, y0 = c.Y - sp.ay, x1 = x0 + sp.w, y1 = y0 + sp.h;
    if (placed.some(r => x0 < r[2] - 4 && x1 > r[0] + 4 && y0 < r[3] - 4 && y1 > r[1] + 4)) continue; placed.push([x0, y0, x1, y1]);
    if (c.p >= 10 && !all) { LATE.push([sp, Math.round(c.X * DPR) / DPR, Math.round(c.Y * DPR) / DPR, c.a * A]); continue; }   // 當日關鍵地名（例如 5/13 色當）改畫在部隊上面，不被符號蓋住
    BGL.sprite(sp, Math.round(c.X * DPR) / DPR, Math.round(c.Y * DPR) / DPR, 1, c.a * A); }
  SEAS.forEach(([n, lo, la], k) => BGL.sprite(SP.sea[k], PX(mx(lo)), PY(my(la)), 1, 0.55 * A));
}
// ---------- 撤退船隊 ----------
function drawShips(S, LA) {
  for (const a of D.arrows) { if (a.kind !== 'naval' || !a.show) continue;
    let al; if (a.k === S.j && S.j !== S.i) al = S.e; else if (a.k === S.i) al = S.i === KD.length - 1 ? 0.3 : 1 - S.e * 0.7; else continue;
    if (a.k <= S.i && D.keyframes[S.i].date >= '1940-06-04') al *= 0.3;
    al *= LA; const pts = a.sm.map(v => [PX(v[0]), PY(v[1])]); const n = pts.length - 1;
    BGL.line(pts, false, 1.2, rgba(191, 243, 255, 0.25 * al), [4, 5]);
    for (let m = 0; m < 6; m++) { const f = ((F.now / 7000) + m / 6) % 1; const fi = f * n, i0 = fi | 0, t = fi - i0; const p0 = pts[i0], p1 = pts[Math.min(i0 + 1, n)];
      BGL.sprite(SP.ship, lerp(p0[0], p1[0], t), lerp(p0[1], p1[1], t), 1, al * 0.7 * Math.sin(f * 3.14)); } }
}
function drawShocks() {
  for (let i = shocks.length - 1; i >= 0; i--) { const s = shocks[i]; const t = (F.now - s.t0) / 2200; if (t > 1) { shocks.splice(i, 1); continue; }
    BGL.circle(PX(s.x), PY(s.y), 12 + ease(t) * Math.min(W, H) * 0.22, 1, rgba(240, 228, 206, (1 - t) * 0.28), 64); }
}
// 兵種配對標籤：HTML 小框，跟著交戰點
function updateTip() {
  const tip = $('#tip'); const tgt = (hover && hover.type === 'eng') ? hover : (selected && selected.type === 'eng' ? selected : null);
  const e = tgt && D.engagements.find(x => x.id === tgt.id);
  if (!e || !e._on) { if (!tip.hidden) tip.hidden = true; return; }
  if (tip._id !== e.id) { tip._id = e.id; tip.innerHTML = `<b>${e.interaction_zh}</b><span>${e.name_zh}</span>`; }
  tip.hidden = false; tip.style.transform = `translate(${Math.round(e._X + 15)}px,${Math.round(e._Y + 8)}px)`;
}
// ---------- HUD ----------
let lastDayInt = -1, TLW = 0, lastAV = '', lastPlaying = null;
function updateHUD(force) {
  const di = Math.floor(day + 1e-6); const S = state(day);
  if (di !== lastDayInt || force) { lastDayInt = di; const dt = new Date(DAY0 + di * 864e5);
    $('#date-main').textContent = `1940年${dt.getUTCMonth() + 1}月${dt.getUTCDate()}日`;
    const kf = D.keyframes[S.atKey && S.u > 0.5 ? S.j : S.i]; $('#phase').textContent = kf.event_zh; }
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
  const box = $('#layers'); box.innerHTML = '';
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
  addEventListener('keydown', ev => { if (ev.code === 'Space') { ev.preventDefault(); playing ? pause() : play(true); } if (ev.code === 'ArrowRight') $('#btn-next').click(); if (ev.code === 'ArrowLeft') $('#btn-prev').click(); if (ev.code === 'Escape') closeInfo(); if (ev.key === 'f') setFollow(true); });
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
  window.__unfollow = () => setFollow(false); window.__follow = () => setFollow(true); window.__state = () => ({ day, follow, zoom: MAP.getZoom(), lam: F && F.lam });
}
const ECH = { army: '集團軍／軍團（XXXX）', corps: '軍（XXX）', division: '師（XX）', brigade: '旅（X）' };
const BR = { infantry: '步兵', armor: '裝甲', motorized: '摩托化', air: '空軍', naval: '海軍' };
const ST = { attack: '進攻', defend: '防守', retreat: '撤退', move: '移動', encircled: '被包圍', surrendered: '投降', evacuating: '撤離中' };
function openInfo(h) { selected = h; const S = state(day); const box = $('#info-body');
  if (h.type === 'unit') { const u = unitIdx[h.id]; const p = u.kpos[S.u > 0.5 ? S.j : S.i] || u.kpos[S.i] || u.kpos[S.j]; const par = u.parent_id ? unitIdx[u.parent_id].name_zh : '—';
    const stk = (h.stack || []).length ? `<dt>同一格</dt><dd>${h.stack.map(id => unitIdx[id].name_zh).join('、')}</dd>` : '';
    box.innerHTML = `<h3>${u.name_zh}</h3><div class="orig">${u.name_orig}</div><dl><dt>陣營</dt><dd>${u.side === 'axis' ? '軸心（德國）' : '盟軍'}</dd><dt>梯隊</dt><dd>${ECH[u.echelon] || u.echelon}</dd><dt>上級</dt><dd>${par}</dd><dt>兵種</dt><dd>${BR[u.branch] || u.branch}</dd><dt>狀態</dt><dd>${p ? ST[p.st] || p.st : '—'}${S.atKey ? '' : '（位置內插，推估）'}</dd>${stk}<dt>符號碼</dt><dd><code>${u.sidc}</code></dd></dl><div class="ex">示例，非史料</div>`; }
  else { const e = D.engagements.find(x => x.id === h.id); const nm = r => e.units.filter(x => x.role === r).map(x => unitIdx[x.unit_id].name_zh).join('、') || '—';
    box.innerHTML = `<h3>${e.name_zh}</h3><div class="orig">${e.date}</div><dl><dt>兵種配對</dt><dd>${e.interaction_zh}</dd><dt>攻方</dt><dd>${nm('attacker')}</dd><dt>守方</dt><dd>${nm('defender')}</dd><dt>結果</dt><dd>（示例資料不填）</dd></dl><div class="ex">示例，非史料</div>`; }
  $('#info').hidden = false; }
function closeInfo() { selected = null; $('#info').hidden = true; }
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
  if (playing) { if (RM) stepRM(dt); else setDay(day + dt * speed / SEC_PER_DAY); if (day >= KD[KD.length - 1]) pause(); }
  if (D) { stepLayers(state(day), dtGlobal); setRiverOpacity(); applyCamera(now); MAP.triggerRepaint(); }
  requestAnimationFrame(loop);
}
let rmAcc = 0; function stepRM(dt) { rmAcc += dt * speed; if (rmAcc > 2) { rmAcc = 0; const i = KD.findIndex(k => k > day + 1e-3); if (i < 0) pause(); else jumpTo(i); } }
})();
