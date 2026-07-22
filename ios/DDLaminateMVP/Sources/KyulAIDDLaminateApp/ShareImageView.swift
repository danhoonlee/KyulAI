import KyulAIDDLaminateCore
import SwiftUI

#if os(iOS)
import UIKit

struct ShareImageButton<Report: View, Label: View>: View {
    let fileName: String
    let report: Report
    let label: () -> Label

    @State private var shareURL: URL?

    var body: some View {
        Button {
            shareURL = renderReport()
        } label: {
            label()
        }
        .sheet(isPresented: Binding(
            get: { shareURL != nil },
            set: { if !$0 { shareURL = nil } }
        )) {
            if let shareURL {
                ActivityShareView(activityItems: [shareURL])
            }
        }
    }

    @MainActor
    private func renderReport() -> URL? {
        let renderer = ImageRenderer(
            content: report
                .frame(width: 900)
                .fixedSize(horizontal: false, vertical: true)
                .environment(\.colorScheme, .light)
        )
        renderer.scale = 2
        guard let image = renderer.uiImage, let data = image.pngData() else {
            return nil
        }
        let safeName = fileName.replacingOccurrences(of: " ", with: "-")
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("\(safeName)-\(UUID().uuidString).png")
        do {
            try data.write(to: url, options: .atomic)
            return url
        } catch {
            return nil
        }
    }
}

private struct ActivityShareView: UIViewControllerRepresentable {
    let activityItems: [Any]

    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: activityItems, applicationActivities: nil)
    }

    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}
#endif

struct LaminateShareImageReportView: View {
    let result: ResponsePredictionResult

    var body: some View {
        VStack(alignment: .leading, spacing: 24) {
            reportHeader

            HStack(spacing: 14) {
                reportMetric("TYPE", "Type \(result.predictedType)", AppTheme.primary)
                reportMetric("CONFIDENCE", result.confidence.percentText, AppTheme.success)
                reportMetric("PT", result.predictedPt.metricText(digits: 2), AppTheme.warning)
            }

            HStack(alignment: .top, spacing: 16) {
                reportSection("MODEL", ["Model: \(result.displayModelLabel)"])
                reportSection("INPUTS", result.shareInputSummaryPlainLines)
            }

            HStack(alignment: .top, spacing: 16) {
                reportSection("RESULTS", [
                    "Max force: \(result.predictedMaxForce.metricText(digits: 2))",
                    "Pt displacement: \(result.predictedPtDisplacement?.metricText(digits: 5) ?? "-")",
                    "Curve points: \(result.curve.count)",
                ])
                reportSection("GRAPH", [
                    "x Axis: displacement",
                    "y Axis: force",
                    "Pt marker: \(result.predictedPt.metricText(digits: 2))",
                ])
            }

            reportSection("INTERPRETATION", result.interpretationLines)

            VStack(alignment: .leading, spacing: 12) {
                Text("FORCE-DISPLACEMENT CURVE")
                    .font(.system(size: 18, weight: .black))
                    .foregroundStyle(AppTheme.muted)
                CurveChartView(points: result.curve, predictedPt: result.predictedPt, curveFit: result.curveFit, isInteractive: false)
                    .frame(height: 360)
            }
            .padding(20)
            .background(AppTheme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        }
        .padding(36)
        .background(
            LinearGradient(
                colors: [Color.white, Color(red: 0.952, green: 0.980, blue: 0.976)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        )
    }

    private var reportHeader: some View {
        HStack(alignment: .center, spacing: 18) {
            Text("ImperialAX")
                .font(.system(size: 24, weight: .black, design: .rounded))
                .foregroundStyle(.white)
                .frame(width: 86, height: 86)
                .background(AppTheme.accent, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            VStack(alignment: .leading, spacing: 5) {
                Text("ImperialAX Laminate Forecast")
                    .font(.system(size: 34, weight: .black, design: .rounded))
                    .foregroundStyle(AppTheme.ink)
                Text("Generated result summary")
                    .font(.system(size: 17, weight: .semibold))
                    .foregroundStyle(AppTheme.muted)
            }
            Spacer()
        }
    }

    private func reportMetric(_ title: String, _ value: String, _ color: Color) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.system(size: 14, weight: .black))
                .foregroundStyle(AppTheme.muted)
            Text(value)
                .font(.system(size: 28, weight: .black, design: .rounded).monospacedDigit())
                .foregroundStyle(color)
                .lineLimit(1)
                .minimumScaleFactor(0.72)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(18)
        .background(Color.white.opacity(0.82), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(color.opacity(0.20), lineWidth: 1)
        )
    }

    private func reportSection(_ title: String, _ lines: [String]) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(title)
                .font(.system(size: 15, weight: .black))
                .foregroundStyle(AppTheme.primary)
            ForEach(lines, id: \.self) { line in
                Text("• \(line)")
                    .font(.system(size: 17, weight: .semibold))
                    .foregroundStyle(AppTheme.ink)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .frame(maxWidth: .infinity, alignment: .topLeading)
        .padding(18)
        .background(Color.white.opacity(0.82), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
    }
}
