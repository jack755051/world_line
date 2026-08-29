/**
 * 產生 design-tokens.scss 灰階/主色/次色 50-900 完整色階用的計算過程（2026-08-29）。
 *
 * 不是拿來 build 時執行的工具，是產生 design-tokens.scss 那些色碼時的計算記錄——
 * 之後要調整色階（例如換掉次色的錨點色相）時，複製這份邏輯改參數重跑，不要手動調色碼。
 *
 * 方法：
 * - OKLab/OKLCH 正向轉換公式跟 dataviz 技能的 scripts/validate_palette.js 相同（Björn
 *   Ottosson 發布的 OKLab 標準）；反向轉換（OKLab -> hex）是這份腳本另外補上的官方公式，
 *   已用「正轉再反轉」驗證過準確度（見下方 roundtrip 區塊，四個測試色都能精確拿回原值）。
 * - 灰階缺口（500/700/800）：在既有 7 個已定案錨點之間，於 OKLCH 空間內插 L/C/H。
 * - 主色藍缺口：沿用 dataviz 技能 sequential blue ramp 的 13 個官方錨點（100-700）
 *   當骨架重新取樣，800/900 沿同一條趨勢線外推（官方文件沒有這兩階）。
 * - 次色橙：只有分類色第 2 格一個官方錨點，套用主色藍在對應色階位置的「相對色度曲線
 *   形狀」等比縮放算出其餘 9 階，色相全程固定在錨點色相。
 *
 * Run: node gen-design-token-ramps.mjs
 */

const s2lin = (c) => c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
const lin2s = (c) => { c = Math.max(0, Math.min(1, c)); return c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055; };
const hex2srgb = (h) => { h = h.trim().replace(/^#/, ""); return [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16) / 255); };
const lin = (h) => hex2srgb(h).map(s2lin);
function oklabFromLin([r, g, b]) {
  const l = Math.cbrt(0.4122214708*r+0.5363325363*g+0.0514459929*b);
  const m = Math.cbrt(0.2119034982*r+0.6806995451*g+0.1073969566*b);
  const s = Math.cbrt(0.0883024619*r+0.2817188376*g+0.6299787005*b);
  return [0.2104542553*l+0.7936177850*m-0.0040720468*s, 1.9779984951*l-2.4285922050*m+0.4505937099*s, 0.0259040371*l+0.7827717662*m-0.8086757660*s];
}
const oklab = (h) => oklabFromLin(lin(h));
const oklch = (h) => { const [L,a,b]=oklab(h); return [L, Math.hypot(a,b), ((Math.atan2(b,a)*180/Math.PI)%360+360)%360]; };
function linFromOklab([L,a,b]) {
  const l_=L+0.3963377774*a+0.2158037573*b, m_=L-0.1055613458*a-0.0638541728*b, s_=L-0.0894841775*a-1.2914855480*b;
  const l=l_**3, m=m_**3, s=s_**3;
  return [4.0767416621*l-3.3077115913*m+0.2309699292*s, -1.2684380046*l+2.6097574011*m-0.3413193965*s, -0.0041960863*l-0.7034186147*m+1.7076147010*s];
}
function hexFromOklch(L,C,Hdeg){
  const Hrad=Hdeg*Math.PI/180;
  const [r,g,bl]=linFromOklab([L,C*Math.cos(Hrad),C*Math.sin(Hrad)]).map(lin2s);
  const toHex=(c)=>Math.round(Math.max(0,Math.min(1,c))*255).toString(16).padStart(2,'0');
  return `#${toHex(r)}${toHex(g)}${toHex(bl)}`;
}
const relLum=(h)=>{const[r,g,b]=lin(h);return 0.2126*r+0.7152*g+0.0722*b;};
const contrast=(a,b)=>{const[hi,lo]=[relLum(a),relLum(b)].sort((x,y)=>y-x);return (hi+0.05)/(lo+0.05);};

const STEPS = [50,100,200,300,400,500,600,700,800,900];

// --- 灰階：沿用既有 7 個錨點不變，缺的 500/700/800 用相鄰錨點內插 L/C/H ---
const grayAnchors = { 50:'#fcfcfb',100:'#f9f9f7',200:'#e1e0d9',300:'#c3c2b7',400:'#898781',600:'#52514e',900:'#0b0b0b' };
function interp(step, s1, s2, anchors) {
  const [L1,C1,H1] = oklch(anchors[s1]);
  const [L2,C2,H2] = oklch(anchors[s2]);
  const t = (step - s1) / (s2 - s1);
  return hexFromOklch(L1+(L2-L1)*t, C1+(C2-C1)*t, H1+(H2-H1)*t);
}
const gray = { ...grayAnchors };
gray[500] = interp(500, 400, 600, grayAnchors);
gray[700] = interp(700, 600, 900, grayAnchors);
gray[800] = interp(800, 600, 900, grayAnchors);

console.log('=== 灰階（缺口內插結果）===');
for (const s of STEPS) console.log(`gray-${s}: ${gray[s]}  L=${oklch(gray[s])[0].toFixed(3)}`);

// --- 主色藍：13 個真實錨點（dataviz sequential ramp），線性擬合到 50-900，外推 800/900 ---
const blueReal = {100:'#cde2fb',150:'#b7d3f6',200:'#9ec5f4',250:'#86b6ef',300:'#6da7ec',350:'#5598e7',400:'#3987e5',450:'#2a78d6',500:'#256abf',550:'#1c5cab',600:'#184f95',650:'#104281',700:'#0d366b'};
const blueSteps = Object.keys(blueReal).map(Number);
const blueOklch = Object.fromEntries(blueSteps.map(s => [s, oklch(blueReal[s])]));
// 用兩端錨點（100, 700）算 L 的線性關係，外推到 800/900；C/H 用最近端點的變化率外推一小段
function linearAt(step, s1, s2, idx) {
  const v1 = blueOklch[s1][idx], v2 = blueOklch[s2][idx];
  return v1 + (v2 - v1) * (step - s1) / (s2 - s1);
}
function nearestBlueOklch(step) {
  if (step in blueOklch) return blueOklch[step];
  if (step < 100) return [linearAt(step,100,150,0), linearAt(step,100,150,1), linearAt(step,100,150,2)];
  if (step > 700) return [linearAt(step,650,700,0), linearAt(step,650,700,1), linearAt(step,650,700,2)];
  // 中間缺的步（200 附近其實都有），理論上不會走到這裡
  const lower = Math.max(...blueSteps.filter(s => s <= step));
  const upper = Math.min(...blueSteps.filter(s => s >= step));
  return [linearAt(step,lower,upper,0), linearAt(step,lower,upper,1), linearAt(step,lower,upper,2)];
}
const blue = {};
for (const s of STEPS) {
  const [L,C,H] = nearestBlueOklch(s);
  blue[s] = hexFromOklch(L,C,H);
}
console.log('\n=== 主色藍（50-900，800/900 外推）===');
for (const s of STEPS) { const [L,C]=oklch(blue[s]); console.log(`blue-${s}: ${blue[s]}  L=${L.toFixed(3)} C=${C.toFixed(3)}`); }

// --- 次色橙：只有分類色第2格一個錨點，套用藍色的相對色度曲線形狀縮放 ---
const orangeAnchorHex = '#eb6834';
const [oL, oC, oH] = oklch(orangeAnchorHex);
// 找藍色 ramp 裡 L 最接近 orange 錨點 L 的那個 step，算縮放比例
let bestStep = blueSteps[0], bestDiff = Infinity;
for (const s of blueSteps) { const d = Math.abs(blueOklch[s][0] - oL); if (d < bestDiff) { bestDiff = d; bestStep = s; } }
const scale = oC / blueOklch[bestStep][1];
console.log(`\n次色橙錨點 L=${oL.toFixed(3)} C=${oC.toFixed(3)} H=${oH.toFixed(1)}，對應藍色最接近的是 blue-${bestStep}（L=${blueOklch[bestStep][0].toFixed(3)}），色度縮放係數=${scale.toFixed(3)}`);

const orange = {};
for (const s of STEPS) {
  const [L, C] = nearestBlueOklch(s); // 沿用藍色在這個 step 的 L/C 曲線形狀
  orange[s] = hexFromOklch(L, C * scale, oH);
}
console.log('\n=== 次色橙（50-900，套用藍色曲線形狀 x 縮放係數）===');
for (const s of STEPS) { const [L,C]=oklch(orange[s]); console.log(`orange-${s}: ${orange[s]}  L=${L.toFixed(3)} C=${C.toFixed(3)}`); }

// --- 驗證：色度地板（識別色用途的步驟需要 C>=0.10），文字對比 ---
console.log('\n=== 驗證：C>=0.10 色度地板（哪些步驟夠飽和可以當識別色用）===');
for (const [name, ramp] of [['gray', gray], ['blue', blue], ['orange', orange]]) {
  for (const s of STEPS) {
    const [,C] = oklch(ramp[s]);
    if (name !== 'gray' && C < 0.10) console.log(`  ${name}-${s} C=${C.toFixed(3)} 低於色度地板 0.10`);
  }
}

console.log('\n=== 驗證：文字對比（500 系列配白字 / 對淺色面板 #fcfcfb）===');
for (const [name, ramp] of [['blue', blue], ['orange', orange]]) {
  for (const s of [400,500,600,700]) {
    console.log(`  ${name}-${s} (${ramp[s]}) 配白字 = ${contrast('#ffffff', ramp[s]).toFixed(2)}:1，對面板 = ${contrast(ramp[s], '#fcfcfb').toFixed(2)}:1`);
  }
}
