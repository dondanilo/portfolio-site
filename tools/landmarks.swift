import Foundation
import Vision
import CoreImage
let url = URL(fileURLWithPath: CommandLine.arguments[1])
let ci = CIImage(contentsOf: url)!
let W = ci.extent.width, H = ci.extent.height
let h = VNImageRequestHandler(ciImage: ci, options: [:])
let r = VNDetectFaceLandmarksRequest()
try h.perform([r])
guard let f = r.results?.first, let lm = f.landmarks else { print("{}"); exit(0) }
func c(_ reg: VNFaceLandmarkRegion2D?) -> [Double] {
  guard let p = reg?.pointsInImage(imageSize: CGSize(width: W, height: H)), !p.isEmpty else { return [] }
  let x = p.map{Double($0.x)}.reduce(0,+)/Double(p.count), y = p.map{Double($0.y)}.reduce(0,+)/Double(p.count)
  return [x/Double(W), 1 - y/Double(H)]
}
let bb = f.boundingBox
let d: [String: [Double]] = ["lPupil": c(lm.leftPupil), "rPupil": c(lm.rightPupil), "nose": c(lm.nose), "mouth": c(lm.outerLips), "lBrow": c(lm.leftEyebrow), "rBrow": c(lm.rightEyebrow), "face": [Double(bb.minX), Double(1-bb.maxY), Double(bb.width), Double(bb.height)]]
let j = try JSONSerialization.data(withJSONObject: d, options: [.sortedKeys])
print(String(data: j, encoding: .utf8)!)
