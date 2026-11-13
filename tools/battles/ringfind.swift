// 地圖城鎮圓點（空心圓）自動偵測：找出「圓周暗、圓心亮」的小圓，輸出圓心像素座標，供控制點精確定位。
// 用法：swift tools/battles/ringfind.swift <in.jpg> <out.json> [rMin rMax] [x0 y0 x1 y1]
// 只讀原圖。輸出 [{"px":[x,y],"r":r,"score":s,"minSector":m}]，依 score 由高到低。
import Foundation
import CoreGraphics
import ImageIO

let a = CommandLine.arguments
guard a.count >= 3 else { print("用法：ringfind in.jpg out.json [rMin rMax] [x0 y0 x1 y1]"); exit(2) }
let rMin = a.count >= 5 ? Double(a[3])! : 3.0
let rMax = a.count >= 5 ? Double(a[4])! : 7.0
let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: a[1]) as CFURL, nil)!
let img = CGImageSourceCreateImageAtIndex(src, 0, nil)!
let W = img.width, H = img.height
var box = (0, 0, W, H)
if a.count >= 9 { box = (Int(a[5])!, Int(a[6])!, Int(a[7])!, Int(a[8])!) }
var buf = [UInt8](repeating: 0, count: W * H)
let ctx = CGContext(data: &buf, width: W, height: H, bitsPerComponent: 8, bytesPerRow: W,
                    space: CGColorSpaceCreateDeviceGray(), bitmapInfo: CGImageAlphaInfo.none.rawValue)!
ctx.draw(img, in: CGRect(x: 0, y: 0, width: W, height: H))
// CGContext 原點在左下，但 buffer 第 0 列即影像頂列（bitmap 記憶體由上而下）
@inline(__always) func dark(_ x: Double, _ y: Double) -> Double {
  let xi = Int(x), yi = Int(y)
  if xi < 0 || yi < 0 || xi >= W - 1 || yi >= H - 1 { return 0 }
  let fx = x - Double(xi), fy = y - Double(yi)
  let p = { (u: Int, v: Int) -> Double in 1.0 - Double(buf[v * W + u]) / 255.0 }
  return p(xi, yi) * (1 - fx) * (1 - fy) + p(xi + 1, yi) * fx * (1 - fy) + p(xi, yi + 1) * (1 - fx) * fy + p(xi + 1, yi + 1) * fx * fy
}
let NA = 32
var cosT = [Double](), sinT = [Double]()
for k in 0..<NA { let t = Double(k) * 2 * Double.pi / Double(NA); cosT.append(cos(t)); sinT.append(sin(t)) }
struct Hit { var x: Int; var y: Int; var r: Double; var s: Double; var m: Double }
var hits = [Hit]()
var radii = [Double](); var rr = rMin; while rr <= rMax + 1e-9 { radii.append(rr); rr += 0.5 }
for y in max(box.1, 10)..<min(box.3, H - 10) {
  for x in max(box.0, 10)..<min(box.2, W - 10) {
    let c0 = dark(Double(x), Double(y))
    if c0 > 0.35 { continue }
    var best = Hit(x: x, y: y, r: 0, s: -1, m: 0)
    for r in radii {
      var ring = 0.0; var sec = [Double](repeating: 0, count: 8)
      for k in 0..<NA { let d = dark(Double(x) + r * cosT[k], Double(y) + r * sinT[k]); ring += d; sec[k * 8 / NA] += d }
      ring /= Double(NA)
      let minSec = sec.min()! / Double(NA / 8)
      if minSec < 0.3 { continue }
      var inner = c0; var n = 1.0
      if r - 2.5 >= 1 { for k in stride(from: 0, to: NA, by: 4) { inner += dark(Double(x) + (r - 2.5) * cosT[k], Double(y) + (r - 2.5) * sinT[k]); n += 1 } }
      inner /= n
      var outer = 0.0
      for k in 0..<NA { outer += dark(Double(x) + (r + 2.5) * cosT[k], Double(y) + (r + 2.5) * sinT[k]) }
      outer /= Double(NA)
      let s = ring - inner - 0.5 * outer
      if s > best.s { best = Hit(x: x, y: y, r: r, s: s, m: minSec) }
    }
    if best.s > 0.25 { hits.append(best) }
  }
}
// 非極大值抑制（8 px 內只留最高分），再以 3×3 分數加權求次像素圓心
hits.sort { $0.s > $1.s }
var kept = [Hit]()
for h in hits { if !kept.contains(where: { abs($0.x - h.x) <= 8 && abs($0.y - h.y) <= 8 }) { kept.append(h) } }
var out = [[String: Any]]()
for h in kept {
  var sx = 0.0, sy = 0.0, sw = 0.0
  for g in hits where abs(g.x - h.x) <= 1 && abs(g.y - h.y) <= 1 { let w = max(g.s - 0.2, 0); sx += Double(g.x) * w; sy += Double(g.y) * w; sw += w }
  out.append(["px": [((sx / sw) * 10).rounded() / 10, ((sy / sw) * 10).rounded() / 10], "r": h.r,
              "score": (h.s * 1000).rounded() / 1000, "minSector": (h.m * 1000).rounded() / 1000])
}
let data = try! JSONSerialization.data(withJSONObject: out, options: [])
try! data.write(to: URL(fileURLWithPath: a[2]))
print("rings \(out.count) (raw \(hits.count)) image \(W)x\(H)")
