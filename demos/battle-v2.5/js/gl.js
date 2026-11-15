/* 小型 WebGL 批次繪圖器：給 MapLibre custom layer 用（v2.2）
 * - geo：填色三角形＋反鋸齒粗線（每頂點：x,y,r,g,b,a,d,hw,s,dashOn,dashOff）
 * - spr：貼圖四邊形（x,y,u,v,alpha），貼圖來自一張圖集（atlas）
 * 座標一律是 CSS 像素（左上原點），著色器轉成 clip space。輸出為預乘 alpha（MapLibre 的混合模式）。 */
window.BGL = (() => {
'use strict';
const GEO_VS = `attribute vec2 p;attribute vec4 c;attribute vec4 e;attribute float f;uniform vec2 res;
varying vec4 vc;varying vec4 ve;varying float vf;
void main(){vc=c;ve=e;vf=f;gl_Position=vec4(p.x/res.x*2.0-1.0,1.0-p.y/res.y*2.0,0.0,1.0);}`;
const GEO_FS = `precision mediump float;varying vec4 vc;varying vec4 ve;varying float vf;
void main(){float a=vc.a; if(ve.y>0.0){float dist=abs(ve.x)*(ve.y+1.0); a*=clamp(ve.y+0.5-dist,0.0,1.0);}
 if(vf>0.0){float m=mod(ve.z,ve.w+vf); if(m>ve.w) discard;}
 gl_FragColor=vec4(vc.rgb*a,a);}`;
const FIL_FS = `precision mediump float;varying vec4 vc;varying vec4 ve;varying float vf;void main(){gl_FragColor=vec4(vc.rgb*vc.a,vc.a);}`;   // 大面積填色用的簡單著色器
const SPR_VS = `attribute vec2 p;attribute vec2 t;attribute float a;uniform vec2 res;varying vec2 vt;varying float va;
void main(){vt=t;va=a;gl_Position=vec4(p.x/res.x*2.0-1.0,1.0-p.y/res.y*2.0,0.0,1.0);}`;
const SPR_FS = `precision mediump float;uniform sampler2D tex;varying vec2 vt;varying float va;void main(){gl_FragColor=texture2D(tex,vt)*va;}`;
let gl, P = {}, bufG, bufS, tex, texW = 1, texH = 1;
let G = new Float32Array(1 << 18), gn = 0, S = new Float32Array(1 << 16), sn = 0, cmds = [];
const GS = 11, SS = 5;
function sh(type, src) { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; }
function prog(vs, fs, attrs) { const p = gl.createProgram(); gl.attachShader(p, sh(gl.VERTEX_SHADER, vs)); gl.attachShader(p, sh(gl.FRAGMENT_SHADER, fs)); gl.linkProgram(p);
  const o = { p, a: {}, u: {} }; attrs.forEach(n => o.a[n] = gl.getAttribLocation(p, n)); ['res', 'tex'].forEach(n => o.u[n] = gl.getUniformLocation(p, n)); return o; }
function init(g) { if (gl === g) return; gl = g; fldOK = null; fldP = null; for (const k in fldTex) delete fldTex[k];   /* 換了繪圖環境：勢力場的著色器和貼圖要重建 */ P.geo = prog(GEO_VS, GEO_FS, ['p', 'c', 'e', 'f']); P.fil = prog(GEO_VS, FIL_FS, ['p', 'c', 'e', 'f']); P.spr = prog(SPR_VS, SPR_FS, ['p', 't', 'a']); bufG = gl.createBuffer(); bufS = gl.createBuffer(); tex = gl.createTexture(); }
function setAtlas(cv) { texW = cv.width; texH = cv.height; pendingAtlas = cv; }   // 一律等到 custom layer 的 render 裡才上傳（不打亂 MapLibre 的 GL 狀態快取）
let pendingAtlas = null;
function upload(cv) { gl.bindTexture(gl.TEXTURE_2D, tex); gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, true);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, cv); gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE); }
// ---- 勢力場（v2.8）：每個關鍵日一張浮點貼圖，RGBA＝各方的有號距離；兩張貼圖依時間內插後取最大者＝該點歸誰 ----
const FLD_VS = `attribute vec2 p;attribute vec2 t;uniform vec2 res;varying vec2 uv;void main(){uv=t;gl_Position=vec4(p.x/res.x*2.0-1.0,1.0-p.y/res.y*2.0,0.0,1.0);}`;
const FLD_FS = `#extension GL_OES_standard_derivatives : enable
precision highp float;uniform sampler2D ta;uniform sampler2D tb;uniform float e;uniform float gate;uniform float mode;uniform float dpr;uniform float ppc;uniform vec4 c0;uniform vec4 c1;uniform vec4 c2;uniform vec4 ink;uniform vec4 lc;varying vec2 uv;
void main(){vec4 s=mix(texture2D(ta,uv),texture2D(tb,uv),e);
if(gate>0.5){s.a=max(s.a,s.b);s.b=-1e4;}
if(mode>1.5){if(s.a>=max(s.r,max(s.g,s.b))){gl_FragColor=vec4(0.0);return;}gl_FragColor=(s.r>=s.g&&s.r>=s.b)?c0:(s.g>=s.b?c1:c2);return;}
if(mode<0.5){gl_FragColor=(s.r>=s.g&&s.r>=s.b)?c0:(s.g>=s.b?c1:c2);return;}
float en=max(s.r,s.b);float f=s.g-en;float d=abs(f)/max(length(vec2(dFdx(f),dFdy(f)))*dpr,1.0/ppc);float ok=step(s.a,min(s.g,en)+0.5);
float ca=(1.0-smoothstep(2.4,3.4,d))*0.85*ok;float co=(1.0-smoothstep(0.6,1.6,d))*ink.a*ok;
float g=s.r-s.b;float dg=abs(g)/max(length(vec2(dFdx(g),dFdy(g)))*dpr,1.0/ppc);float tl=(1.0-smoothstep(0.3,1.3,dg))*lc.a*step(max(s.g,s.a),min(s.r,s.b)+0.5);
vec4 o=vec4(ca);o=o*(1.0-co)+vec4(ink.rgb*co,co);o=o*(1.0-tl)+vec4(lc.rgb*tl,tl);gl_FragColor=o;}`;
let fldP = null, bufF = null, fldOK = null; const fldTex = {}, fldPending = {};
function fieldTex(id, w, h, data) { fldPending[id] = { w, h, data }; }
function drawField(d, W, H) {
  if (fldOK === null) { const gl2 = typeof WebGL2RenderingContext !== 'undefined' && gl instanceof WebGL2RenderingContext;
    fldOK = gl2 ? 2 : (gl.getExtension('OES_texture_float') && gl.getExtension('OES_texture_float_linear') && gl.getExtension('OES_standard_derivatives') ? 1 : 0);
    if (fldOK) { try { const vs = fldOK === 2 ? '#version 300 es\n' + FLD_VS.replace(/attribute/g, 'in').replace(/varying/g, 'out') : FLD_VS;
      const fs = fldOK === 2 ? '#version 300 es\n' + FLD_FS.replace(/^#extension.*\n/, '').replace(/varying/g, 'in').replace(/texture2D/g, 'texture').replace(/gl_FragColor/g, 'oc').replace('varying vec2 uv;', '').replace('in vec2 uv;', 'in vec2 uv;out vec4 oc;') : FLD_FS;
      fldP = prog(vs, fs, ['p', 't']); ['ta', 'tb', 'e', 'gate', 'mode', 'dpr', 'ppc', 'c0', 'c1', 'c2', 'ink', 'lc'].forEach(n => fldP.u[n] = gl.getUniformLocation(fldP.p, n)); bufF = gl.createBuffer(); } catch (err) { console.warn('field shader', err); fldOK = 0; } } }
  if (!fldOK) return;
  for (const id of [d.a, d.b]) { const pd = fldPending[id]; if (!pd) continue; delete fldPending[id]; const t = fldTex[id] = fldTex[id] || gl.createTexture(); gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texImage2D(gl.TEXTURE_2D, 0, fldOK === 2 ? gl.RGBA16F : gl.RGBA, pd.w, pd.h, 0, gl.RGBA, gl.FLOAT, pd.data);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE); }
  if (!fldTex[d.a] || !fldTex[d.b]) return;
  const p = fldP; gl.useProgram(p.p); gl.uniform2f(p.u.res, W, H); gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, fldTex[d.b]); gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, fldTex[d.a]);
  gl.uniform1i(p.u.ta, 0); gl.uniform1i(p.u.tb, 1); gl.uniform1f(p.u.e, d.e); gl.uniform1f(p.u.gate, d.gate ? 1 : 0); gl.uniform1f(p.u.mode, d.mode); gl.uniform1f(p.u.dpr, d.dpr); gl.uniform1f(p.u.ppc, d.ppc);
  gl.uniform4fv(p.u.c0, d.c0); gl.uniform4fv(p.u.c1, d.c1); gl.uniform4fv(p.u.c2, d.c2); gl.uniform4fv(p.u.ink, d.ink); gl.uniform4fv(p.u.lc, d.lc);
  gl.bindBuffer(gl.ARRAY_BUFFER, bufF); gl.bufferData(gl.ARRAY_BUFFER, d.verts, gl.STREAM_DRAW);
  gl.enableVertexAttribArray(p.a.p); gl.vertexAttribPointer(p.a.p, 2, gl.FLOAT, false, 16, 0); gl.enableVertexAttribArray(p.a.t); gl.vertexAttribPointer(p.a.t, 2, gl.FLOAT, false, 16, 8);
  gl.drawArrays(gl.TRIANGLES, 0, d.verts.length / 4); gl.disableVertexAttribArray(p.a.p); gl.disableVertexAttribArray(p.a.t);
}
function field(d) { cmds.push({ k: 'd', n: 1, d }); }
function begin() { gn = 0; sn = 0; cmds = []; }
function cmd(kind, start) { const l = cmds[cmds.length - 1]; if (l && l.k === kind && kind !== 'd') return; cmds.push({ k: kind, s: start, n: 0 }); }
function growG(n) { if (gn + n * GS > G.length) { const b = new Float32Array(Math.max(G.length * 2, gn + n * GS)); b.set(G); G = b; } }
function growS(n) { if (sn + n * SS > S.length) { const b = new Float32Array(Math.max(S.length * 2, sn + n * SS)); b.set(S); S = b; } }
// 一個 geo 頂點
function v(x, y, c, d, hw, s, on, off) { G[gn++] = x; G[gn++] = y; G[gn++] = c[0]; G[gn++] = c[1]; G[gn++] = c[2]; G[gn++] = c[3]; G[gn++] = d; G[gn++] = hw; G[gn++] = s; G[gn++] = on; G[gn++] = off; }
function geoStart(nv, k = 'g') { growG(nv); cmd(k, gn / GS); }
function geoEnd() { const l = cmds[cmds.length - 1]; l.n = gn / GS - l.s; }
// 填色：flat 座標 [x0,y0,x1,y1...] + earcut 索引
function fillIdx(flat, idx, c) { geoStart(idx.length, 'f'); for (let i = 0; i < idx.length; i++) { const k = idx[i] * 2; v(flat[k], flat[k + 1], c, 0, 0, 0, 0, 0); } geoEnd(); }
// 三角形（每頂點各自顏色）
function tris(list) { geoStart(list.length, 'f'); for (const t of list) v(t[0], t[1], t[2], 0, 0, 0, 0, 0); geoEnd(); }
// 反鋸齒粗線（miter 接頭）；pts=[[x,y],...]
// dash=[on, off, phase?]：phase 是虛線起點的位移（像素），每幀改它就會沿線流動
function line(pts, closed, width, c, dash) {
  const n = pts.length; if (n < 2) return; const hw = width / 2, ex = hw + 1, on = dash ? dash[0] : 0, off = dash ? dash[1] : 0;
  const Lx = new Float32Array(n), Ly = new Float32Array(n), Rx = new Float32Array(n), Ry = new Float32Array(n), Sd = new Float32Array(n); let s = dash && dash[2] ? -dash[2] : 0;
  for (let i = 0; i < n; i++) {
    const p = pts[i], a = closed ? pts[(i - 1 + n) % n] : pts[Math.max(i - 1, 0)], b = closed ? pts[(i + 1) % n] : pts[Math.min(i + 1, n - 1)];
    let d1x = p[0] - a[0], d1y = p[1] - a[1], d2x = b[0] - p[0], d2y = b[1] - p[1]; let l1 = Math.hypot(d1x, d1y), l2 = Math.hypot(d2x, d2y);
    if (l1 < 1e-6) { d1x = d2x; d1y = d2y; l1 = l2; } if (l2 < 1e-6) { d2x = d1x; d2y = d1y; l2 = l1; } if (l1 < 1e-6) { d1x = 1; d1y = 0; l1 = l2 = 1; d2x = 1; d2y = 0; }
    d1x /= l1; d1y /= l1; d2x /= l2; d2y /= l2; let tx = d1x + d2x, ty = d1y + d2y; let tl = Math.hypot(tx, ty); if (tl < 1e-6) { tx = d1x; ty = d1y; tl = 1; } tx /= tl; ty /= tl;
    const nx = -ty, ny = tx; const m = 1 / Math.max(nx * -d1y + ny * d1x, 0.5);
    if (i) s += Math.hypot(p[0] - pts[i - 1][0], p[1] - pts[i - 1][1]);
    Lx[i] = p[0] + nx * ex * m; Ly[i] = p[1] + ny * ex * m; Rx[i] = p[0] - nx * ex * m; Ry[i] = p[1] - ny * ex * m; Sd[i] = s; }
  const segs = closed ? n : n - 1; geoStart(segs * 6);
  const send = closed ? s + Math.hypot(pts[0][0] - pts[n - 1][0], pts[0][1] - pts[n - 1][1]) : s;
  for (let i = 0; i < segs; i++) { const j = (i + 1) % n; const sj = j === 0 ? send : Sd[j];
    v(Lx[i], Ly[i], c, 1, hw, Sd[i], on, off); v(Rx[i], Ry[i], c, -1, hw, Sd[i], on, off); v(Lx[j], Ly[j], c, 1, hw, sj, on, off);
    v(Rx[i], Ry[i], c, -1, hw, Sd[i], on, off); v(Rx[j], Ry[j], c, -1, hw, sj, on, off); v(Lx[j], Ly[j], c, 1, hw, sj, on, off); }
  geoEnd(); }
function circle(x, y, r, width, c, segs = 40) { const p = []; for (let i = 0; i < segs; i++) { const a = i / segs * 6.2832; p.push([x + Math.cos(a) * r, y + Math.sin(a) * r]); } line(p, true, width, c); }
// 貼圖：sp={u0,v0,u1,v1,w,h(css),ax,ay(css 錨點)}
function sprite(sp, x, y, sc, alpha) { if (alpha < 0.01) return; growS(6); cmd('s', sn / SS);
  const x0 = x - sp.ax * sc, y0 = y - sp.ay * sc, x1 = x0 + sp.w * sc, y1 = y0 + sp.h * sc;
  const q = [[x0, y0, sp.u0, sp.v0], [x1, y0, sp.u1, sp.v0], [x0, y1, sp.u0, sp.v1], [x1, y0, sp.u1, sp.v0], [x1, y1, sp.u1, sp.v1], [x0, y1, sp.u0, sp.v1]];
  for (const t of q) { S[sn++] = t[0]; S[sn++] = t[1]; S[sn++] = t[2]; S[sn++] = t[3]; S[sn++] = alpha; }
  const l = cmds[cmds.length - 1]; l.n = sn / SS - l.s; }
function flush(W, H) {
  if (!cmds.length) return;
  if (pendingAtlas) { upload(pendingAtlas); pendingAtlas = null; }
  gl.disable(gl.STENCIL_TEST); /* 深度測試沿用 MapLibre 為本層設定的唯讀深度（讓上面的不透明海面層蓋得住） */ gl.depthMask(false); gl.disable(gl.CULL_FACE); gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
  gl.bindBuffer(gl.ARRAY_BUFFER, bufG); gl.bufferData(gl.ARRAY_BUFFER, G.subarray(0, gn), gl.STREAM_DRAW);
  gl.bindBuffer(gl.ARRAY_BUFFER, bufS); gl.bufferData(gl.ARRAY_BUFFER, S.subarray(0, sn), gl.STREAM_DRAW);
  let cur = null;
  for (const c of cmds) { if (!c.n) continue;
    if (c.k === 'd') { if (cur) dis(cur); cur = null; drawField(c.d, W, H); continue; }
    if (c.k !== cur) { if (cur) dis(cur); cur = c.k;
      if (c.k === 'g' || c.k === 'f') { const p = c.k === 'g' ? P.geo : P.fil; gl.useProgram(p.p); gl.uniform2f(p.u.res, W, H); gl.bindBuffer(gl.ARRAY_BUFFER, bufG); const st = GS * 4;
        gl.enableVertexAttribArray(p.a.p); gl.vertexAttribPointer(p.a.p, 2, gl.FLOAT, false, st, 0);
        gl.enableVertexAttribArray(p.a.c); gl.vertexAttribPointer(p.a.c, 4, gl.FLOAT, false, st, 8);
        gl.enableVertexAttribArray(p.a.e); gl.vertexAttribPointer(p.a.e, 4, gl.FLOAT, false, st, 24);
        gl.enableVertexAttribArray(p.a.f); gl.vertexAttribPointer(p.a.f, 1, gl.FLOAT, false, st, 40); }
      else { const p = P.spr; gl.useProgram(p.p); gl.uniform2f(p.u.res, W, H); gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, tex); gl.uniform1i(p.u.tex, 0);
        gl.bindBuffer(gl.ARRAY_BUFFER, bufS); const st = SS * 4;
        gl.enableVertexAttribArray(p.a.p); gl.vertexAttribPointer(p.a.p, 2, gl.FLOAT, false, st, 0);
        gl.enableVertexAttribArray(p.a.t); gl.vertexAttribPointer(p.a.t, 2, gl.FLOAT, false, st, 8);
        gl.enableVertexAttribArray(p.a.a); gl.vertexAttribPointer(p.a.a, 1, gl.FLOAT, false, st, 16); } }
    gl.drawArrays(gl.TRIANGLES, c.s, c.n); }
  if (cur) dis(cur);
}
function dis(k) { const p = k === 'g' ? P.geo : k === 'f' ? P.fil : P.spr; for (const n in p.a) if (p.a[n] >= 0) gl.disableVertexAttribArray(p.a[n]); }
// ---- 圖集（shelf packing）----
function Atlas(dpr, size = 2048) { const cv = document.createElement('canvas'); cv.width = cv.height = size; const g = cv.getContext('2d'); let x = 1, y = 1, rowH = 0;
  return { cv, dpr, add(src, cssW, cssH, ax, ay) { const w = src.width, h = src.height; if (x + w + 1 > size) { x = 1; y += rowH + 1; rowH = 0; } if (y + h > size) { console.warn('atlas full'); return null; }
      g.drawImage(src, x, y); const sp = { u0: x / size, v0: y / size, u1: (x + w) / size, v1: (y + h) / size, w: cssW ?? w / dpr, h: cssH ?? h / dpr, ax: ax ?? (cssW ?? w / dpr) / 2, ay: ay ?? (cssH ?? h / dpr) / 2 };
      x += w + 1; rowH = Math.max(rowH, h); return sp; } }; }
return { init, setAtlas, begin, field, fieldTex, fillIdx, tris, line, circle, sprite, flush, Atlas };
})();
