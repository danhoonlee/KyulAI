import KyulAIDDLaminateCore
import SwiftUI

struct ResultDetailView: View {
    let result: ResponsePredictionResult

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                heroCard
                metricsGrid
                interpretationCard
                curveCard
                probabilityCard
                if !result.notes.isEmpty {
                    notesCard
                }
            }
            .padding(20)
        }
        .background(AppTheme.background.ignoresSafeArea())
        .navigationTitle(L10n.t("result"))
        .appInlineNavigationTitle()
        .toolbar {
            ShareLink(item: result.shareSummaryText) {
                Image(systemName: "square.and.arrow.up")
            }
            #if os(iOS)
            ShareImageButton(
                fileName: "luvelox-laminate-forecast",
                report: LaminateShareImageReportView(result: result)
            ) {
                Image(systemName: "photo")
            }
            #endif
        }
    }

    private var heroCard: some View {
        AppCard {
            VStack(alignment: .leading, spacing: 14) {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 6) {
                        Text(L10n.t("predicted.type"))
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(AppTheme.muted)
                        Text(L10n.f("type.format", result.predictedType))
                            .font(.system(size: 48, weight: .black, design: .rounded))
                            .foregroundStyle(AppTheme.ink)
                    }
                    Spacer()
                    VStack(alignment: .trailing, spacing: 4) {
                        Text(result.confidence.percentText)
                            .font(.title2.monospacedDigit().weight(.bold))
                            .foregroundStyle(AppTheme.primary)
                        Text(L10n.t("confidence"))
                            .font(.caption2.weight(.semibold))
                            .foregroundStyle(AppTheme.muted)
                    }
                }
                Divider()
                VStack(alignment: .leading, spacing: 4) {
                    Text(result.displayModelLabel)
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(AppTheme.ink)
                    Text(result.inputMode.uppercased())
                        .font(.caption2.monospaced().weight(.bold))
                        .foregroundStyle(AppTheme.primary)
                }
            }
        }
    }

    private var metricsGrid: some View {
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
            metricCard(L10n.t("predicted.pt"), result.predictedPt.metricText(digits: 2), "force")
            metricCard(L10n.t("max.force"), result.predictedMaxForce.metricText(digits: 2), "force")
            metricCard(L10n.t("pt.displacement"), result.predictedPtDisplacement?.metricText(digits: 5) ?? "-", "disp.")
            metricCard(L10n.t("curve.points"), "\(result.curve.count)", "samples")
        }
    }

    private func metricCard(_ title: String, _ value: String, _ unit: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.caption.weight(.semibold))
                .foregroundStyle(AppTheme.muted)
            Text(value)
                .font(.title3.monospacedDigit().weight(.bold))
                .foregroundStyle(AppTheme.ink)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
            Text(unit)
                .font(.caption2.weight(.semibold))
                .foregroundStyle(AppTheme.muted)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(AppTheme.card, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(AppTheme.primary.opacity(0.10), lineWidth: 1)
        )
    }

    private var curveCard: some View {
        AppCard {
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    Label(L10n.t("response.curve"), systemImage: "chart.xyaxis.line")
                        .font(.headline)
                        .foregroundStyle(AppTheme.ink)
                    Spacer()
                    Text(L10n.t("pt.marker"))
                        .font(.caption2.bold())
                        .foregroundStyle(AppTheme.danger)
                }
                CurveChartView(points: result.curve, predictedPt: result.predictedPt)
                    .frame(height: 280)
            }
        }
    }

    private var interpretationCard: some View {
        AppCard {
            InterpretationSummaryView(result: result)
        }
    }

    private var probabilityCard: some View {
        AppCard {
            VStack(alignment: .leading, spacing: 14) {
                Label(L10n.t("class.probabilities"), systemImage: "chart.bar.fill")
                    .font(.headline)
                    .foregroundStyle(AppTheme.ink)
                if result.sortedProbabilities.isEmpty {
                    Text(L10n.t("no.probabilities"))
                        .font(.callout)
                        .foregroundStyle(AppTheme.muted)
                } else {
                    ForEach(result.sortedProbabilities, id: \.label) { probability in
                        probabilityRow(label: probability.label, value: probability.value)
                    }
                }
            }
        }
    }

    private func probabilityRow(label: String, value: Double) -> some View {
        VStack(alignment: .leading, spacing: 7) {
            HStack {
                Text(label.capitalized)
                    .font(.subheadline.weight(.bold))
                    .foregroundStyle(AppTheme.ink)
                Spacer()
                Text(Optional(value).percentText)
                    .font(.subheadline.monospacedDigit().weight(.bold))
                    .foregroundStyle(AppTheme.muted)
            }
            GeometryReader { proxy in
                ZStack(alignment: .leading) {
                    Capsule()
                        .fill(AppTheme.field)
                    Capsule()
                        .fill(label == "type\(result.predictedType)" ? AppTheme.primary : AppTheme.accent.opacity(0.28))
                        .frame(width: max(6, proxy.size.width * min(max(value, 0), 1)))
                }
            }
            .frame(height: 8)
        }
    }

    private var notesCard: some View {
        AppCard {
            VStack(alignment: .leading, spacing: 12) {
                Label(L10n.t("notes"), systemImage: "exclamationmark.triangle.fill")
                    .font(.headline)
                    .foregroundStyle(AppTheme.warning)
                ForEach(result.notes, id: \.self) { note in
                    Text(note)
                        .font(.callout)
                        .foregroundStyle(AppTheme.ink)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
    }
}

struct InterpretationSummaryView: View {
    let result: ResponsePredictionResult
    var maxLines: Int?

    init(result: ResponsePredictionResult, maxLines: Int? = nil) {
        self.result = result
        self.maxLines = maxLines
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label(L10n.t("interpretation"), systemImage: "text.magnifyingglass")
                .font(.headline)
                .foregroundStyle(AppTheme.ink)
            ForEach(Array(result.interpretationLines.prefix(maxLines ?? Int.max)), id: \.self) { line in
                HStack(alignment: .firstTextBaseline, spacing: 8) {
                    Circle()
                        .fill(AppTheme.primary)
                        .frame(width: 5, height: 5)
                    Text(line)
                        .font(.callout)
                        .foregroundStyle(AppTheme.ink)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            Text(L10n.t("interpretation.disclaimer"))
                .font(.caption2)
                .foregroundStyle(AppTheme.muted)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}

extension ResponsePredictionResult {
    var interpretationLines: [String] {
        [
            confidenceInterpretation,
            ptInterpretation,
            curveInterpretation,
        ].compactMap { $0 }
    }

    var shareSummaryText: String {
        let modelLines = [
            "Luvelox Laminate Forecast",
            "",
            "MODEL",
            "• Model: \(displayModelLabel)",
            "",
            "INPUTS",
        ]
        let inputLines = shareInputSummaryLines.map { "• \($0)" }
        let resultLines = [
            "",
            "RESULTS",
            "• Predicted type: Type \(predictedType)",
            "• Confidence: \(confidence.percentText)",
            "• Pt: \(predictedPt.metricText(digits: 2))",
            "• Max force: \(predictedMaxForce.metricText(digits: 2))",
            "• Pt displacement: \(predictedPtDisplacement?.metricText(digits: 5) ?? "-")",
            "",
            "INTERPRETATION",
        ]
        let interpretationSummaryLines = self.interpretationLines.map { "• \($0)" }
        let chartLines = [
            "",
            "CHART",
            "• Response curve: \(curve.count) points",
            "",
            "GRAPH",
            "• Pt marker: \(predictedPt.metricText(digits: 2))",
            "• x Axis: displacement",
            "• y Axis: force",
        ]
        let lines = modelLines + inputLines + resultLines + interpretationSummaryLines + chartLines
        return lines.joined(separator: "\n").trimmingCharacters(in: .newlines)
    }

    var shareInputSummaryPlainLines: [String] {
        [
            inputValue("case").map { "Case: \($0)" },
            theta1Line,
            theta2Line,
        ].compactMap { $0 }
    }

    private var shareInputSummaryLines: [String] {
        shareInputSummaryPlainLines
    }

    private var confidenceInterpretation: String {
        guard let confidence else {
            return L10n.f("interpretation.confidence.none", predictedType)
        }
        if confidence >= 0.75 {
            return L10n.f("interpretation.confidence.high", predictedType)
        }
        if confidence >= 0.60 {
            return L10n.f("interpretation.confidence.medium", predictedType)
        }
        return L10n.f("interpretation.confidence.low", predictedType)
    }

    private var ptInterpretation: String {
        guard predictedMaxForce > 0 else {
            return L10n.t("interpretation.pt.generic")
        }
        let ratio = max(0, min(predictedPt / predictedMaxForce, 1))
        let percent = Int((ratio * 100).rounded())
        if ratio < 0.45 {
            return L10n.f("interpretation.pt.early", percent)
        }
        if ratio > 0.75 {
            return L10n.f("interpretation.pt.late", percent)
        }
        return L10n.f("interpretation.pt.mid", percent)
    }

    private var curveInterpretation: String? {
        guard curve.count >= 3, let maxPoint = curve.max(by: { $0.force < $1.force }) else {
            return nil
        }
        let finalForce = curve.last?.force ?? maxPoint.force
        guard maxPoint.force > 0 else {
            return nil
        }
        let retained = finalForce / maxPoint.force
        if retained < 0.25 {
            return L10n.t("interpretation.curve.strong.softening")
        }
        if retained < 0.75 {
            return L10n.t("interpretation.curve.softening")
        }
        return L10n.t("interpretation.curve.stable")
    }

    private var theta1Line: String? {
        guard let theta1 = inputValue("theta1") else { return nil }
        return "Theta 1: \(theta1) deg"
    }

    private var theta2Line: String? {
        guard let theta2 = inputValue("theta2") else { return nil }
        return "Theta 2: \(theta2) deg"
    }

    private func inputValue(_ key: String, digits: Int = 4) -> String? {
        inputs[key]?.shareTextValue(digits: digits)
    }
}

private extension JSONValue {
    func shareTextValue(digits: Int) -> String? {
        switch self {
        case .string(let value):
            value
        case .double(let value):
            value.formatted(.number.precision(.fractionLength(0...digits)))
        case .bool(let value):
            String(value)
        case .null:
            nil
        }
    }
}
