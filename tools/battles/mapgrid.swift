// 地圖判讀輔助：裁切原圖一塊、縮放，並疊上以「原圖像素」標示的格線，供人工讀控制點與要素座標。
// 用法：swift tools/battles/mapgrid.swift <in.jpg> <x> <y> <w> <h> <outWidth> <gridStep> <out.jpg>
// 只讀原圖，輸出新檔；不改原圖。
import Foundation
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers
import CoreText

let a = CommandLine.arguments
guard a.count == 9, let x = Int(a[2]), let y = Int(a[3]), let w = Int(a[4]), let h = Int(a[5]),
      let ow = Int(a[6]), let step = Int(a[7]) else {
  print("用法：mapgrid.swift in x y w h outWidth gridStep out"); exit(2) }
let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: a[1]) as CFURL, nil)!
let img = CGImageSourceCreateImageAtIndex(src, 0, nil)!
let crop = img.cropping(to: CGRect(x: x, y: y, width: w, height: h))!
let s = Double(ow) / Double(crop.width)
let oh = Int(Double(crop.height) * s)
let ctx = CGContext(data: nil, width: ow, height: oh, bitsPerComponent: 8, bytesPerRow: 0,
                    space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
ctx.interpolationQuality = .high
ctx.draw(crop, in: CGRect(x: 0, y: 0, width: ow, height: oh))
ctx.setStrokeColor(CGColor(red: 0, green: 0.7, blue: 1, alpha: 0.55)); ctx.setLineWidth(1)
let font = CTFontCreateWithName("Helvetica" as CFString, 11, nil)
func label(_ t: String, _ px: Double, _ py: Double) {
  let attr = NSAttributedString(string: t, attributes: [kCTFontAttributeName as NSAttributedString.Key: font,
    kCTForegroundColorAttributeName as NSAttributedString.Key: CGColor(red: 0, green: 0.35, blue: 0.9, alpha: 1)])
  let line = CTLineCreateWithAttributedString(attr); ctx.textPosition = CGPoint(x: px, y: py); CTLineDraw(line, ctx) }
var gx = ((x + step - 1) / step) * step
while gx < x + crop.width { let px = Double(gx - x) * s
  ctx.move(to: CGPoint(x: px, y: 0)); ctx.addLine(to: CGPoint(x: px, y: Double(oh))); ctx.strokePath()
  label("\(gx)", px + 2, Double(oh) - 12); gx += step }
var gy = ((y + step - 1) / step) * step
while gy < y + crop.height { let py = Double(oh) - Double(gy - y) * s
  ctx.move(to: CGPoint(x: 0, y: py)); ctx.addLine(to: CGPoint(x: Double(ow), y: py)); ctx.strokePath()
  label("\(gy)", 2, py + 2); gy += step }
let out = ctx.makeImage()!
let dst = CGImageDestinationCreateWithURL(URL(fileURLWithPath: a[8]) as CFURL, UTType.jpeg.identifier as CFString, 1, nil)!
CGImageDestinationAddImage(dst, out, [kCGImageDestinationLossyCompressionQuality: 0.85] as CFDictionary)
CGImageDestinationFinalize(dst)
print("ok \(ow)x\(oh) scale \(s)")
