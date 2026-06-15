import KyulAIInjectionCore
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

struct InjectionShareImageReportView: View {
    let result: SpruePressurePredictionResult

    var body: some View {
        VStack(alignment: .leading, spacing: 22) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("C2ES Injection Forecast")
                        .font(.system(size: 34, weight: .black, design: .rounded))
                        .foregroundStyle(AppTheme.ink)
                    Text("Generated result summary")
                        .font(.system(size: 17, weight: .semibold))
                        .foregroundStyle(AppTheme.muted)
                }
                Spacer()
                Text(result.predictedMaxPressureMPa.metricText(digits: 2) + " MPa")
                    .font(.system(size: 30, weight: .black, design: .rounded))
                    .foregroundStyle(AppTheme.primary)
            }

            Text(result.shareSummaryText)
                .font(.system(size: 22, weight: .semibold, design: .monospaced))
                .foregroundStyle(AppTheme.ink)
                .lineSpacing(5)
                .fixedSize(horizontal: false, vertical: true)

            VStack(alignment: .leading, spacing: 12) {
                Text("GRAPH")
                    .font(.system(size: 20, weight: .black))
                    .foregroundStyle(AppTheme.muted)
                PressureChartView(points: result.curve, maxPressure: result.predictedMaxPressureMPa)
                    .frame(height: 330)
            }
            .padding(18)
            .background(AppTheme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        }
        .padding(34)
        .background(Color.white)
    }
}
