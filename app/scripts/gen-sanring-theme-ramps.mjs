/**
 * 產生 sanring-theme.css 品牌色階（--sanring-primary/coral/sun/neutral/info/success/warn/
 * error-10..90）用的計算過程（2026-08-29，任務 3.0 後續）。
 *
 * 背景：sanring-theme.css 的語意層（--sanring-background/-foreground/-control/-primary
 * 等）已經 alias 到 --wl-* token，但底下的 9 階品牌色階原本還是 Sanring 原廠預設值，
 * 跟 --wl-* 是兩組不同的顏色——這支腳本把它們全部收斂成同一組來源：
 *
 * - primary/neutral：直接從 design-tokens.scss 已定案的 --wl-primary-* 與 --wl-gray-*
 *   十階，用 OKLCH 的 L（明度）當內插軸重新取樣成 Sanring 的 9 階（10-90），不是另外
 *   重新設計一條曲線。
 * - coral：借用 --wl-secondary-*（橙）十階，同樣重新取樣——這個專案沒有獨立的「珊瑚色」
 *   語意，coral 在 Sanring 元件庫裡的角色（次要強調/warm accent）跟我們的次色重疊，
 *   直接共用同一個色相家族。
 * - success/warn/error：這三個是全新色相（--wl-status-* 目前只有單一色號，不是九階
 *   ramp）。**第一版直接套用 design-tokens.scss 產生次色橙時的手法**（借主色藍在對應
 *   明度的色度曲線形狀等比縮放），跑出來發現色相在暗階嚴重漂移（warn 從錨點 H=78.5
 *   一路漂到 H=33 附近，接近 45 度）——藍色的 sRGB 色域邊界形狀是藍色自己的，套到黃色/
 *   綠色/紅色這些跟藍色色域邊界形狀差很多的色相，縮放後的色度在深色階超出該色相自己
 *   實際能呈現的範圍，被 RGB 裁切之後色相就跑掉了，不是同一個色相只是變暗。
 *   **改用色域邊界比例縮放**：對每個目標色相 H，先算它在每個明度 L 下 sRGB 色域內
 *   實際能達到的最大色度 Cmax(L,H)（二分搜尋），錨點的 C 相對於錨點所在明度的
 *   Cmax(anchorL,H) 是多少比例，其餘每一階都套用同一個比例乘上「那一階自己明度的
 *   Cmax」，而不是借別的色相的絕對色度數字——這樣色相在整條 ramp 上才會保持一致。
 * - sun：不新增第四個狀態色相，直接沿用 warn 的九階（CSS 裡用 var() 互相參照，不是
 *   複製一份新色碼）。
 * - info：不新增第五個色相，直接沿用 primary 的九階（同上，CSS 用 var() 參照）。
 *
 * 換算方法沿用 gen-design-token-ramps.mjs 的 OKLab/OKLCH 公式（同一份官方矩陣），
 * 這裡不重複驗證正轉反轉準確度，直接複用。
 *
 * Run: node gen-sanring-theme-ramps.mjs
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

// design-tokens.scss 目前定案的十階（複製值，不是 import——這支腳本本來就只是計算記錄，
// 不是 build 期間會實際執行的程式）
const WL_10_STEPS = [50,100,200,300,400,500,600,700,800,900];
const wlGray = {50:'#fcfcfb',100:'#f9f9f7',200:'#e1e0d9',300:'#c3c2b7',400:'#898781',500:'#6d6b67',600:'#52514e',700:'#383836',800:'#21201f',900:'#0b0b0b'};
const wlPrimary = {50:'#e4f1ff',100:'#cde2fb',200:'#9ec5f4',300:'#6da7ec',400:'#3987e5',500:'#256abf',600:'#184f95',700:'#0d366b',800:'#071f41',900:'#020b1c'};
const wlSecondary = {50:'#ffe9df',100:'#ffd5c6',200:'#faab8f',300:'#f17f55',400:'#e64900',500:'#bf2f00',600:'#951d00',700:'#6a0f00',800:'#410800',900:'#1c0300'};
const wlStatusGood = '#0ca30c';
const wlStatusWarning = '#fab219';
const wlStatusCritical = '#d03b3b';

const SANRING_9_STEPS = [10,20,30,40,50,60,70,80,90];

/** 把一條十階 ramp（以 L 為軸）內插/外推取樣成 9 個目標 L 值，H 用最近兩端線性內插。 */
function resampleByLightness(wlRamp) {
  const points = WL_10_STEPS.map(s => ({ step: s, ...(([L,C,H]) => ({L,C,H}))(oklch(wlRamp[s])) }));
  // L 是單調遞減（50 最淺 -> 900 最深），9 個 Sanring 目標 L 值：50 階跟 900 階之間等分
  const lLight = points[0].L, lDark = points[points.length - 1].L;
  const out = {};
  for (let i = 0; i < SANRING_9_STEPS.length; i++) {
    const t = i / (SANRING_9_STEPS.length - 1);
    const targetL = lLight + (lDark - lLight) * t;
    // 找 targetL 落在哪兩個既有錨點之間
    let lo = points[0], hi = points[points.length - 1];
    for (let j = 0; j < points.length - 1; j++) {
      if (points[j].L >= targetL && points[j + 1].L <= targetL) { lo = points[j]; hi = points[j + 1]; break; }
    }
    const segT = lo.L === hi.L ? 0 : (lo.L - targetL) / (lo.L - hi.L);
    const C = lo.C + (hi.C - lo.C) * segT;
    const H = lo.H + (hi.H - lo.H) * segT;
    out[SANRING_9_STEPS[i]] = hexFromOklch(targetL, C, H);
  }
  return out;
}

/** 二分搜尋：在固定 L、H 下，sRGB 色域內（三個線性 RGB 通道都落在 [0,1]，還沒經過
    lin2s() 的裁切）能達到的最大色度 C。 */
function maxChromaInGamut(L, Hdeg) {
  const Hrad = Hdeg * Math.PI / 180;
  const inGamut = (C) => linFromOklab([L, C * Math.cos(Hrad), C * Math.sin(Hrad)])
    .every((c) => c >= -1e-6 && c <= 1 + 1e-6);
  let lo = 0, hi = 0.5; // OKLCH 色度實務上不會超過 0.5
  if (!inGamut(hi)) {
    // hi 本身就超出色域也沒關係，二分搜尋只需要 hi 是「一定超出」的上界
  }
  for (let i = 0; i < 40; i++) {
    const mid = (lo + hi) / 2;
    if (inGamut(mid)) lo = mid; else hi = mid;
  }
  return lo;
}

/** 錨點色相 H 固定不變，每一階的色度＝該階自己明度下的色域邊界 Cmax(L,H) 乘上「錨點色度
    佔錨點明度色域邊界的比例」——不借用其他色相的色度曲線形狀，色相才不會在深/淺階漂移。
    9 個目標明度沿用 --wl-primary 的明度範圍（跟 primary/coral/neutral 三條 resample
    出來的 ramp 同一個明度跨距，讓所有色相家族的「淺到深」視覺跨度一致）。 */
function generateFromAnchor(anchorHex) {
  const [aL, aC, aH] = oklch(anchorHex);
  const primaryPoints = WL_10_STEPS.map(s => oklch(wlPrimary[s]));
  const lLight = primaryPoints[0][0], lDark = primaryPoints[primaryPoints.length - 1][0];
  const ratio = aC / maxChromaInGamut(aL, aH);
  const out = {};
  for (let i = 0; i < SANRING_9_STEPS.length; i++) {
    const t = i / (SANRING_9_STEPS.length - 1);
    const targetL = lLight + (lDark - lLight) * t;
    const C = maxChromaInGamut(targetL, aH) * ratio;
    out[SANRING_9_STEPS[i]] = hexFromOklch(targetL, C, aH);
  }
  return { ramp: out, ratio, anchorL: aL, anchorC: aC, anchorH: aH };
}

const sanringNeutral = resampleByLightness(wlGray);
const sanringPrimary = resampleByLightness(wlPrimary);
const sanringCoral = resampleByLightness(wlSecondary);
const { ramp: sanringSuccess, ratio: successRatio } = generateFromAnchor(wlStatusGood);
const { ramp: sanringWarn, ratio: warnRatio } = generateFromAnchor(wlStatusWarning);
const { ramp: sanringError, ratio: errorRatio } = generateFromAnchor(wlStatusCritical);

for (const [name, ramp] of [['neutral (from wl-gray)', sanringNeutral], ['primary (from wl-primary)', sanringPrimary], ['coral (from wl-secondary)', sanringCoral], [`success (ratio=${successRatio.toFixed(3)})`, sanringSuccess], [`warn (ratio=${warnRatio.toFixed(3)})`, sanringWarn], [`error (ratio=${errorRatio.toFixed(3)})`, sanringError]]) {
  console.log(`\n=== ${name} ===`);
  for (const s of SANRING_9_STEPS) console.log(`  ${s}: ${ramp[s]}`);
}

// 驗證：色相是否在整條 ramp 上保持一致（跟錨點 H 的最大偏差）
console.log('\n=== 驗證：色相一致性（跟錨點 H 的最大偏差，理想應該只有幾度） ===');
for (const [name, ramp, anchorHex] of [['success', sanringSuccess, wlStatusGood], ['warn', sanringWarn, wlStatusWarning], ['error', sanringError, wlStatusCritical]]) {
  const [, , anchorH] = oklch(anchorHex);
  let maxDrift = 0;
  for (const s of SANRING_9_STEPS) {
    const [, , h] = oklch(ramp[s]);
    maxDrift = Math.max(maxDrift, Math.abs(h - anchorH));
  }
  console.log(`  ${name}: 最大偏差 ${maxDrift.toFixed(1)}°`);
}
