import KyulAIDDLaminateCore
import SwiftUI

struct DDLaminateComparisonView: View {
    let runs: [DDLaminateRecentRun]
    @Binding var selectedIDs: [String]

    private var selectedRuns: [DDLaminateRecentRun] {
        selectedIDs.compactMap { id in runs.first { $0.id == id } }
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                selectorCard
                if selectedRuns.count == 2 {
                    comparisonSummary(left: selectedRuns[0], right: selectedRuns[1])
                } else {
                    AppCard {
                        Text(L10n.t("compare.select.two"))
                            .font(.callout)
                            .foregroundStyle(AppTheme.muted)
                    }
                }
            }
            .padding(20)
        }
        .background(AppTheme.background.ignoresSafeArea())
    }

    private var selectorCard: some View {
        AppCard {
            VStack(alignment: .leading, spacing: 12) {
                Label(L10n.t("compare.pick.results"), systemImage: "checklist")
                    .font(.headline)
                    .foregroundStyle(AppTheme.ink)
                ForEach(Array(runs.enumerated()), id: \.element.id) { index, run in
                    Button {
                        toggle(run)
                    } label: {
                        HStack(spacing: 12) {
                            Image(systemName: selectedIDs.contains(run.id) ? "checkmark.circle.fill" : "circle")
                                .foregroundStyle(selectedIDs.contains(run.id) ? AppTheme.success : AppTheme.muted)
                            VStack(alignment: .leading, spacing: 4) {
                                Text(index == 0 ? "\(index + 1). \(L10n.t("recent.latest"))" : "\(index + 1). \(run.displayTitle)")
                                    .font(.subheadline.weight(.bold))
                                    .foregroundStyle(AppTheme.ink)
                                Text("\(run.displayModelLabel) · Theta \(run.theta1) / \(run.theta2)")
                                    .font(.caption)
                                    .foregroundStyle(AppTheme.muted)
                            }
                            Spacer()
                            VStack(alignment: .trailing, spacing: 5) {
                                comparisonBadge(run.predictedType.map { L10n.f("type.format", $0) } ?? "-")
                                comparisonBadge("Pt \(run.predictedPt?.metricText(digits: 2) ?? "-")")
                            }
                        }
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    if index < runs.count - 1 {
                        Divider()
                    }
                }
            }
        }
    }

    private func comparisonBadge(_ text: String) -> some View {
        Text(text)
            .font(.caption2.monospacedDigit().weight(.bold))
            .foregroundStyle(AppTheme.primary)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(AppTheme.primary.opacity(0.10), in: Capsule())
    }

    private func comparisonSummary(left: DDLaminateRecentRun, right: DDLaminateRecentRun) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            AppCard {
                VStack(alignment: .leading, spacing: 12) {
                    Label(L10n.t("compare.summary"), systemImage: "arrow.left.arrow.right")
                        .font(.headline)
                        .foregroundStyle(AppTheme.ink)
                    compareMetric(
                        title: "Pt",
                        left: left.predictedPt,
                        right: right.predictedPt,
                        digits: 2
                    )
                    compareMetric(
                        title: L10n.t("max.force"),
                        left: left.predictedMaxForce,
                        right: right.predictedMaxForce,
                        digits: 2
                    )
                    compareMetric(
                        title: L10n.t("pt.displacement"),
                        left: left.predictedPtDisplacement,
                        right: right.predictedPtDisplacement,
                        digits: 5
                    )
                    compareMetric(
                        title: L10n.t("confidence"),
                        left: left.confidence,
                        right: right.confidence,
                        digits: 3,
                        isPercent: true
                    )
                }
            }

            if !left.curve.isEmpty && !right.curve.isEmpty {
                AppCard {
                    VStack(alignment: .leading, spacing: 12) {
                        Label(L10n.t("compare.curves"), systemImage: "chart.xyaxis.line")
                            .font(.headline)
                            .foregroundStyle(AppTheme.ink)
                        ComparisonCurveChartView(
                            left: left.curve,
                            right: right.curve,
                            leftPt: left.predictedPt,
                            rightPt: right.predictedPt
                        )
                            .frame(height: 260)
                        HStack(spacing: 10) {
                            legend(L10n.t("compare.first"), color: AppTheme.primary)
                            legend(L10n.t("compare.second"), color: AppTheme.warning)
                        }
                    }
                }
            } else {
                AppCard {
                    Text(L10n.t("compare.curve.missing"))
                        .font(.callout)
                        .foregroundStyle(AppTheme.muted)
                }
            }

            AppCard {
                VStack(alignment: .leading, spacing: 12) {
                    Label(L10n.t("interpretation"), systemImage: "text.magnifyingglass")
                        .font(.headline)
                        .foregroundStyle(AppTheme.ink)
                    ForEach(comparisonInterpretation(left: left, right: right), id: \.self) { line in
                        Text("• \(line)")
                            .font(.callout)
                            .foregroundStyle(AppTheme.ink)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
            }
        }
    }

    private func compareMetric(title: String, left: Double?, right: Double?, digits: Int, isPercent: Bool = false) -> some View {
        let delta = zip(left, right).map { $0.1 - $0.0 }
        return VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.caption.weight(.semibold))
                .foregroundStyle(AppTheme.muted)
            HStack(spacing: 10) {
                metricPill(L10n.t("compare.first"), format(left, digits: digits, isPercent: isPercent), color: AppTheme.primary)
                metricPill(L10n.t("compare.second"), format(right, digits: digits, isPercent: isPercent), color: AppTheme.warning)
                metricPill("Δ", delta.map { signed($0, digits: digits, isPercent: isPercent) } ?? "-", color: AppTheme.accent)
            }
        }
    }

    private func metricPill(_ title: String, _ value: String, color: Color) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(title)
                .font(.caption2.weight(.black))
                .foregroundStyle(color)
            Text(value)
                .font(.caption.monospacedDigit().weight(.bold))
                .foregroundStyle(AppTheme.ink)
                .lineLimit(1)
                .minimumScaleFactor(0.72)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(9)
        .background(color.opacity(0.10), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
    }

    private func legend(_ text: String, color: Color) -> some View {
        HStack(spacing: 6) {
            Capsule()
                .fill(color)
                .frame(width: 18, height: 5)
            Text(text)
                .font(.caption.weight(.bold))
                .foregroundStyle(AppTheme.muted)
        }
    }

    private func toggle(_ run: DDLaminateRecentRun) {
        if selectedIDs.contains(run.id) {
            selectedIDs.removeAll { $0 == run.id }
        } else {
            if selectedIDs.count >= 2 {
                selectedIDs.removeFirst()
            }
            selectedIDs.append(run.id)
        }
    }

    private func comparisonInterpretation(left: DDLaminateRecentRun, right: DDLaminateRecentRun) -> [String] {
        [
            deltaSentence(
                key: "compare.interpretation.pt",
                left: left.predictedPt,
                right: right.predictedPt,
                digits: 2
            ),
            deltaSentence(
                key: "compare.interpretation.force",
                left: left.predictedMaxForce,
                right: right.predictedMaxForce,
                digits: 2
            ),
            confidenceSentence(left: left.confidence, right: right.confidence),
        ].compactMap { $0 }
    }

    private func deltaSentence(key: String, left: Double?, right: Double?, digits: Int) -> String? {
        guard let left, let right else { return nil }
        let delta = right - left
        if abs(delta) < 0.000001 {
            return L10n.f("\(key).same", right.metricText(digits: digits))
        }
        if delta > 0 {
            return L10n.f("\(key).higher", delta.metricText(digits: digits))
        }
        return L10n.f("\(key).lower", abs(delta).metricText(digits: digits))
    }

    private func confidenceSentence(left: Double?, right: Double?) -> String? {
        guard let left, let right else { return nil }
        let delta = right - left
        if abs(delta) < 0.02 {
            return L10n.t("compare.interpretation.confidence.similar")
        }
        return delta > 0
            ? L10n.t("compare.interpretation.confidence.higher")
            : L10n.t("compare.interpretation.confidence.lower")
    }

    private func format(_ value: Double?, digits: Int, isPercent: Bool) -> String {
        guard let value else { return "-" }
        return isPercent ? Optional(value).percentText : value.metricText(digits: digits)
    }

    private func signed(_ value: Double, digits: Int, isPercent: Bool) -> String {
        let sign = value > 0 ? "+" : ""
        if isPercent {
            return "\(sign)\((value * 100).metricText(digits: 1))%"
        }
        return "\(sign)\(value.metricText(digits: digits))"
    }
}

private struct ComparisonCurveChartView: View {
    let left: [ResponseCurvePoint]
    let right: [ResponseCurvePoint]
    let leftPt: Double?
    let rightPt: Double?

    var body: some View {
        GeometryReader { proxy in
            ZStack(alignment: .bottomLeading) {
                RoundedRectangle(cornerRadius: 14)
                    .fill(AppTheme.field)
                Canvas { context, size in
                    guard let layout = ComparisonChartLayout(left: left, right: right, size: size) else { return }
                    context.stroke(
                        layout.leftPath,
                        with: .color(AppTheme.primary),
                        style: StrokeStyle(lineWidth: 3, lineCap: .round, lineJoin: .round)
                    )
                    context.stroke(
                        layout.rightPath,
                        with: .color(AppTheme.warning),
                        style: StrokeStyle(lineWidth: 3.5, lineCap: .round, lineJoin: .round, dash: [9, 7])
                    )
                    drawPtMarker(
                        context: context,
                        layout: layout,
                        points: left,
                        force: leftPt,
                        color: AppTheme.primary,
                        label: L10n.t("compare.first")
                    )
                    drawPtMarker(
                        context: context,
                        layout: layout,
                        points: right,
                        force: rightPt,
                        color: AppTheme.warning,
                        label: L10n.t("compare.second")
                    )
                }
                VStack(spacing: 0) {
                    HStack {
                        Text(L10n.t("axis.force"))
                            .padding(.leading, 12)
                            .padding(.top, 8)
                        Spacer()
                    }
                    Spacer()
                    HStack {
                        Spacer()
                        Text(L10n.t("axis.displacement"))
                        Spacer()
                    }
                    .padding(.bottom, 8)
                }
                .font(.caption2.weight(.semibold))
                .foregroundStyle(AppTheme.muted)
            }
        }
    }

    private func drawPtMarker(
        context: GraphicsContext,
        layout: ComparisonChartLayout,
        points: [ResponseCurvePoint],
        force: Double?,
        color: Color,
        label: String
    ) {
        guard let marker = layout.ptMarker(points: points, force: force) else { return }

        var guide = Path()
        guide.move(to: CGPoint(x: marker.x, y: layout.plotFrame.minY))
        guide.addLine(to: CGPoint(x: marker.x, y: layout.plotFrame.maxY))
        context.stroke(
            guide,
            with: .color(color.opacity(0.62)),
            style: StrokeStyle(lineWidth: 1.4, dash: [5, 4])
        )

        let dot = CGRect(x: marker.x - 5, y: marker.y - 5, width: 10, height: 10)
        context.fill(Path(ellipseIn: dot), with: .color(.white))
        context.stroke(Path(ellipseIn: dot), with: .color(color), lineWidth: 2.5)

        let labelPoint = CGPoint(
            x: min(max(marker.x + 42, layout.plotFrame.minX + 48), layout.plotFrame.maxX - 48),
            y: max(marker.y - 18, layout.plotFrame.minY + 14)
        )
        context.draw(
            Text("\(label) Pt \(force?.metricText(digits: 2) ?? "-")")
                .font(.caption2.bold())
                .foregroundStyle(color),
            at: labelPoint
        )
    }
}

private struct ComparisonChartLayout {
    let leftPath: Path
    let rightPath: Path
    let plotFrame: CGRect
    private let left: [ResponseCurvePoint]
    private let right: [ResponseCurvePoint]
    private let minX: Double
    private let maxX: Double
    private let minY: Double
    private let maxY: Double

    init?(left: [ResponseCurvePoint], right: [ResponseCurvePoint], size: CGSize) {
        let allPoints = left + right
        let inset: CGFloat = 28
        let plotFrame = CGRect(x: inset, y: inset, width: max(1, size.width - inset * 2), height: max(1, size.height - inset * 2))
        guard left.count > 1,
              right.count > 1,
              let minX = allPoints.map(\.displacement).min(),
              let maxX = allPoints.map(\.displacement).max(),
              let minY = allPoints.map(\.force).min(),
              let maxY = allPoints.map(\.force).max(),
              maxX > minX,
              maxY > minY else {
            return nil
        }

        func makePath(_ points: [ResponseCurvePoint]) -> Path {
            var path = Path()
            for (index, point) in points.enumerated() {
                let x = plotFrame.minX + (point.displacement - minX) / (maxX - minX) * plotFrame.width
                let y = plotFrame.maxY - (point.force - minY) / (maxY - minY) * plotFrame.height
                if index == 0 {
                    path.move(to: CGPoint(x: x, y: y))
                } else {
                    path.addLine(to: CGPoint(x: x, y: y))
                }
            }
            return path
        }

        self.leftPath = makePath(left)
        self.rightPath = makePath(right)
        self.plotFrame = plotFrame
        self.left = left
        self.right = right
        self.minX = minX
        self.maxX = maxX
        self.minY = minY
        self.maxY = maxY
    }

    func ptMarker(points: [ResponseCurvePoint], force predictedPt: Double?) -> CGPoint? {
        guard let predictedPt, predictedPt.isFinite else { return nil }
        let candidate = points.min { lhs, rhs in
            abs(lhs.force - predictedPt) < abs(rhs.force - predictedPt)
        }
        guard let candidate else { return nil }
        let x = plotFrame.minX + (candidate.displacement - minX) / (maxX - minX) * plotFrame.width
        let y = plotFrame.maxY - (candidate.force - minY) / (maxY - minY) * plotFrame.height
        return CGPoint(x: x, y: y)
    }
}

private func zip(_ lhs: Double?, _ rhs: Double?) -> (Double, Double)? {
    guard let lhs, let rhs else { return nil }
    return (lhs, rhs)
}
