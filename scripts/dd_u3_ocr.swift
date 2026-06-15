import AppKit
import Foundation
import Vision

struct OCRRow: Codable {
    let path: String
    let ok: Bool
    let lines: [String]
    let error: String?
}

func imagePaths(from arguments: [String]) throws -> [String] {
    if arguments.count == 2 && arguments[0] == "--list" {
        let text = try String(contentsOfFile: arguments[1], encoding: .utf8)
        return text.split(whereSeparator: \.isNewline).map(String.init)
    }
    return arguments
}

func recognize(path: String) -> OCRRow {
    let url = URL(fileURLWithPath: path)
    guard let image = NSImage(contentsOf: url) else {
        return OCRRow(path: path, ok: false, lines: [], error: "Could not load image")
    }

    var rect = CGRect(origin: .zero, size: image.size)
    guard let cgImage = image.cgImage(forProposedRect: &rect, context: nil, hints: nil) else {
        return OCRRow(path: path, ok: false, lines: [], error: "Could not create CGImage")
    }

    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = false
    request.minimumTextHeight = 0.01

    let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
    do {
        try handler.perform([request])
        let lines = (request.results ?? []).compactMap { observation in
            observation.topCandidates(1).first?.string
        }
        return OCRRow(path: path, ok: true, lines: lines, error: nil)
    } catch {
        return OCRRow(path: path, ok: false, lines: [], error: String(describing: error))
    }
}

let arguments = Array(CommandLine.arguments.dropFirst())
let encoder = JSONEncoder()
encoder.outputFormatting = [.withoutEscapingSlashes]

do {
    for path in try imagePaths(from: arguments) {
        autoreleasepool {
            let row = recognize(path: path)
            if let data = try? encoder.encode(row), let text = String(data: data, encoding: .utf8) {
                print(text)
            }
        }
    }
} catch {
    let row = OCRRow(path: "", ok: false, lines: [], error: String(describing: error))
    if let data = try? encoder.encode(row), let text = String(data: data, encoding: .utf8) {
        print(text)
    }
    exit(1)
}
