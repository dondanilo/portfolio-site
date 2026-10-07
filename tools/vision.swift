import Foundation
import Vision
import CoreImage
import AppKit

let args = CommandLine.arguments
let inPath = args[1], outDir = args[2]
let url = URL(fileURLWithPath: inPath)
let name = url.deletingPathExtension().lastPathComponent
guard let ci = CIImage(contentsOf: url) else { print("cannot load"); exit(1) }
let handler = VNImageRequestHandler(ciImage: ci, options: [:])
let faceReq = VNDetectFaceLandmarksRequest()
let maskReq = VNGenerateForegroundInstanceMaskRequest()
try handler.perform([faceReq, maskReq])
let W = ci.extent.width, H = ci.extent.height
if let f = faceReq.results?.first {
    func deg(_ n: NSNumber?) -> String { n.map { String(format: "%.1f", $0.doubleValue * 180 / .pi) } ?? "nil" }
    let bb = f.boundingBox
    print("\(name): faceBox x=\(Int(bb.minX*W)) y=\(Int((1-bb.maxY)*H)) w=\(Int(bb.width*W)) h=\(Int(bb.height*H)) roll=\(deg(f.roll)) yaw=\(deg(f.yaw)) pitch=\(deg(f.pitch))")
    if let lm = f.landmarks, let le = lm.leftPupil?.pointsInImage(imageSize: CGSize(width: W, height: H)).first, let re = lm.rightPupil?.pointsInImage(imageSize: CGSize(width: W, height: H)).first {
        let ang = atan2(re.y - le.y, re.x - le.x) * 180 / .pi
        print("  pupils L=(\(Int(le.x)),\(Int(H-le.y))) R=(\(Int(re.x)),\(Int(H-re.y))) eyeLineAngle=\(String(format: "%.1f", ang))")
    }
}
if let obs = maskReq.results?.first {
    let mask = try obs.generateScaledMaskForImage(forInstances: obs.allInstances, from: handler)
    let maskCI = CIImage(cvPixelBuffer: mask)
    let clear = CIImage(color: .clear).cropped(to: ci.extent)
    let out = ci.applyingFilter("CIBlendWithMask", parameters: [kCIInputBackgroundImageKey: clear, kCIInputMaskImageKey: maskCI])
    let ctx = CIContext()
    let dest = URL(fileURLWithPath: "\(outDir)/\(name)_cutout.png")
    try ctx.writePNGRepresentation(of: out, to: dest, format: .RGBA8, colorSpace: CGColorSpace(name: CGColorSpace.sRGB)!)
    let mdest = URL(fileURLWithPath: "\(outDir)/\(name)_mask.png")
    try ctx.writePNGRepresentation(of: maskCI, to: mdest, format: .L8, colorSpace: CGColorSpace(name: CGColorSpace.linearGray)!)
    print("  cutout saved, instances=\(obs.allInstances.count)")
}
