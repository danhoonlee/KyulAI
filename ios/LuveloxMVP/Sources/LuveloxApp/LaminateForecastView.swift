import KyulAIDDLaminateCore
import KyulAIDDLaminateApp
import SwiftUI

struct LaminateForecastView: View {
    @StateObject private var viewModel = PredictionViewModel()
    @FocusState private var focusedField: Field?

    private enum Field: Hashable {
        case theta1
        case theta2
    }

    private let baseURL = URL(string: DDLaminateDefaults.fallbackBaseURL)!

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                header
                inputCard
                if let result = viewModel.result {
                    resultCard(result)
                }
            }
            .padding(20)
        }
        #if os(iOS)
        .scrollDismissesKeyboard(.interactively)
        #endif
        .simultaneousGesture(TapGesture().onEnded { focusedField = nil })
        .background(Color(red: 0.97, green: 0.98, blue: 0.99))
        .navigationTitle("Laminate")
        .task {
            await viewModel.checkConnection(baseURL: baseURL)
        }
        .alert("Prediction error", isPresented: errorBinding) {
            Button("OK", role: .cancel) { viewModel.errorMessage = nil }
        } message: {
            Text(viewModel.errorMessage ?? "")
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("LAMINATE MODULE")
                .font(.caption.weight(.heavy))
                .foregroundStyle(.teal)
            Text("C2ES Laminate Forecast")
                .font(.system(size: 32, weight: .black, design: .rounded))
                .lineLimit(1)
                .minimumScaleFactor(0.58)
                .allowsTightening(true)
                .multilineTextAlignment(.leading)
                .fixedSize(horizontal: false, vertical: true)
            Text("Run Type, Pt, and force-displacement response prediction directly inside C2ES.")
                .font(.callout)
                .foregroundStyle(.secondary)
        }
    }

    private var inputCard: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Text("Inputs")
                    .font(.headline)
                Spacer()
                readinessBadge
            }

            Picker("Case", selection: $viewModel.selectedCase) {
                ForEach(DDLaminateCase.allCases) { laminateCase in
                    Text(laminateCase.rawValue).tag(laminateCase)
                }
            }
            .pickerStyle(.segmented)

            HStack(spacing: 12) {
                numericField("Theta 1", text: $viewModel.theta1, field: .theta1)
                numericField("Theta 2", text: $viewModel.theta2, field: .theta2)
            }

            modelPicker

            Button {
                focusedField = nil
                Task { await viewModel.predict(baseURL: baseURL) }
            } label: {
                HStack {
                    Text(viewModel.isPredicting ? "Predicting" : "Predict response")
                    Spacer()
                    Image(systemName: "waveform.path.ecg")
                }
                .font(.headline)
                .foregroundStyle(.white)
                .padding(.horizontal, 14)
                .frame(height: 46)
                .background(Color(red: 0.09, green: 0.13, blue: 0.18), in: RoundedRectangle(cornerRadius: 8))
            }
            .disabled(!viewModel.canPredict || viewModel.isPredicting)
        }
        .padding(18)
        .background(.white, in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.black.opacity(0.08)))
    }

    private var readinessBadge: some View {
        let text: String
        let color: Color
        switch viewModel.connectionState {
        case .idle:
            text = "Ready soon"
            color = .secondary
        case .checking:
            text = "Checking"
            color = .teal
        case .ready(let available):
            text = available ? "API ready" : "Model missing"
            color = available ? .green : .orange
        case .failed:
            text = "Offline"
            color = .red
        }
        return Text(text)
            .font(.caption.weight(.heavy))
            .foregroundStyle(color)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(color.opacity(0.12), in: Capsule())
    }

    private func numericField(_ title: String, text: Binding<String>, field: Field) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(.caption.weight(.bold))
                .foregroundStyle(.secondary)
            TextField("0", text: text)
                .focused($focusedField, equals: field)
                #if os(iOS)
                .keyboardType(.numbersAndPunctuation)
                #endif
                .font(.title3.monospacedDigit().weight(.bold))
                .padding(.horizontal, 12)
                .frame(height: 46)
                .background(Color(red: 0.96, green: 0.98, blue: 0.99), in: RoundedRectangle(cornerRadius: 8))
        }
    }

    private var modelPicker: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Model")
                .font(.caption.weight(.bold))
                .foregroundStyle(.secondary)
            Picker("Model", selection: Binding(
                get: { viewModel.selectedResponseModelKey },
                set: { viewModel.selectResponseModel(key: $0) }
            )) {
                ForEach(viewModel.responseModels) { model in
                    Text(model.displayLabel).tag(model.key)
                }
            }
            .pickerStyle(.menu)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 12)
            .frame(height: 46)
            .background(Color(red: 0.96, green: 0.98, blue: 0.99), in: RoundedRectangle(cornerRadius: 8))
        }
    }

    private func resultCard(_ result: ResponsePredictionResult) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Type \(result.predictedType)")
                        .font(.system(size: 34, weight: .black, design: .rounded))
                    Text(result.displayModelLabel)
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Text(result.confidence.percentText)
                    .font(.headline.monospacedDigit())
                    .foregroundStyle(.green)
            }

            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                metric("Pt", result.predictedPt.metricText(digits: 2))
                metric("Pt displacement", result.predictedPtDisplacement?.metricText(digits: 5) ?? "-")
                metric("Max force", result.predictedMaxForce.metricText(digits: 2))
                metric("Points", "\(result.curve.count)")
            }

            VStack(alignment: .leading, spacing: 10) {
                Text("Predicted curve")
                    .font(.headline)
                CurveChartView(points: result.curve, predictedPt: result.predictedPt, curveFit: result.curveFit)
                    .frame(height: 310)
            }

            probabilityBars(result)

            if let xai = result.xai {
                xaiInsight(xai)
            }

            if viewModel.isLoadingResponseDesignSpace {
                Text("Loading design-space insight...")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)
            } else if let insight = viewModel.responseDesignSpace {
                designSpaceInsight(insight)
            }
        }
        .padding(18)
        .background(.white, in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.black.opacity(0.08)))
    }

    private func metric(_ title: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(title)
                .font(.caption.weight(.bold))
                .foregroundStyle(.secondary)
            Text(value)
                .font(.headline.monospacedDigit())
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(Color(red: 0.96, green: 0.98, blue: 0.99), in: RoundedRectangle(cornerRadius: 8))
    }

    private func probabilityBars(_ result: ResponsePredictionResult) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Class probability")
                .font(.headline)
            ForEach(result.sortedProbabilities, id: \.label) { item in
                VStack(alignment: .leading, spacing: 5) {
                    HStack {
                        Text(item.label)
                        Spacer()
                        Text(item.value.percentText)
                            .monospacedDigit()
                    }
                    .font(.caption.weight(.bold))
                    GeometryReader { proxy in
                        ZStack(alignment: .leading) {
                            Capsule().fill(Color.gray.opacity(0.16))
                            Capsule()
                                .fill(item.label == "type\(result.predictedType)" ? Color.teal : Color.orange.opacity(0.45))
                                .frame(width: proxy.size.width * max(0, min(item.value, 1)))
                        }
                    }
                    .frame(height: 8)
                }
            }
        }
    }

    private func xaiInsight(_ xai: XAIExplanation) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Prediction insight")
                .font(.headline)
            Text(xai.summary)
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
            Text("Method: \(xai.method) · Feature set: \(xai.featureSet)")
                .font(.caption2.weight(.bold))
                .foregroundStyle(.teal)

            VStack(spacing: 0) {
                ForEach(Array(xai.topFeatures.prefix(5).enumerated()), id: \.element.id) { index, feature in
                    xaiFeatureRow(feature)
                    if index < min(xai.topFeatures.count, 5) - 1 {
                        Divider()
                    }
                }
            }
            .background(Color(red: 0.96, green: 0.98, blue: 0.99), in: RoundedRectangle(cornerRadius: 8))
        }
    }

    private func xaiFeatureRow(_ feature: XAIFeature) -> some View {
        HStack(alignment: .center, spacing: 10) {
            VStack(alignment: .leading, spacing: 3) {
                Text(feature.label)
                    .font(.caption.weight(.bold))
                    .foregroundStyle(.primary)
                    .lineLimit(1)
                Text(feature.explanation)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 8)
            VStack(alignment: .trailing, spacing: 4) {
                Text(feature.importance.percentText)
                    .font(.caption2.monospacedDigit().weight(.black))
                    .foregroundStyle(.teal)
                ProgressView(value: min(max(feature.importance, 0), 1))
                    .tint(.teal)
                    .frame(width: 78)
            }
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
    }

    private func designSpaceInsight(_ insight: DesignSpaceResponse) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Research insight")
                .font(.headline)
            if let candidate = insight.recommendations.first {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Top candidate")
                        .font(.caption.weight(.bold))
                        .foregroundStyle(.secondary)
                    Text("\(candidate.`case`.rawValue) · θ₁ \(candidate.theta1.angleText) · θ₂ \(candidate.theta2.angleText)")
                        .font(.subheadline.weight(.bold))
                    Text("Expected Pt \(candidate.expectedPt.metricText(digits: 2)) · \(candidate.observedType.typeText)")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)
                    scoreBreakdown(candidate)
                    if !insight.mapPoints.isEmpty {
                        InteractiveDesignSpaceMapView(insight: insight, topCandidate: candidate)
                    }
                }
                .padding(12)
                .background(Color(red: 0.96, green: 0.98, blue: 0.99), in: RoundedRectangle(cornerRadius: 8))
            }

            if !insight.caseInsights.isEmpty {
                Text("Case behavior zones")
                    .font(.subheadline.weight(.bold))
                ForEach(insight.caseInsights.prefix(3)) { item in
                    caseInsightRow(item)
                }
            }
        }
    }

    private func scoreBreakdown(_ candidate: DesignSpaceRecommendation) -> some View {
        let items: [(String, Double)] = [
            ("Pt", candidate.scoreComponents.pt),
            ("Type", candidate.scoreComponents.type),
            ("Distance", candidate.scoreComponents.proximity),
            ("Total", candidate.score),
        ]
        return VStack(alignment: .leading, spacing: 6) {
            Text("Recommendation score")
                .font(.caption2.weight(.bold))
                .foregroundStyle(.secondary)
            HStack(spacing: 6) {
                ForEach(items, id: \.0) { item in
                    VStack(spacing: 2) {
                        Text(item.0)
                            .font(.caption2.weight(.bold))
                        Text(item.1.percentText)
                            .font(.caption2.monospacedDigit().weight(.bold))
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 7)
                    .background(Color.teal.opacity(0.10), in: RoundedRectangle(cornerRadius: 8))
                    .foregroundStyle(.teal)
                }
            }
        }
    }

    private func caseInsightRow(_ item: DesignSpaceCaseInsight) -> some View {
        VStack(alignment: .leading, spacing: 5) {
            HStack {
                Text(item.`case`.rawValue)
                    .font(.caption.weight(.bold))
                Spacer()
                Text(item.focusKind.displayFocusKind)
                    .font(.caption2.weight(.bold))
                    .foregroundStyle(.teal)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.teal.opacity(0.10), in: Capsule())
            }
            Text("θ₁ \(rangeText(item.theta1Min, item.theta1Max)) · θ₂ \(rangeText(item.theta2Min, item.theta2Max))")
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)
            Text("Best Pt \(item.bestPt?.metricText(digits: 2) ?? "-") · θ₁ \(item.bestTheta1?.metricText(digits: 0) ?? "-") · θ₂ \(item.bestTheta2?.metricText(digits: 0) ?? "-") · \(item.bestType.typeText)")
                .font(.caption2)
                .foregroundStyle(.secondary)
            Text("\(item.focusCount)/\(item.count) · \(item.focusRate.percentText)")
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .padding(10)
        .background(Color(red: 0.96, green: 0.98, blue: 0.99), in: RoundedRectangle(cornerRadius: 8))
    }

    private func rangeText(_ lower: Double?, _ upper: Double?) -> String {
        guard let lower, let upper else { return "-" }
        return "\(lower.metricText(digits: 0)) to \(upper.metricText(digits: 0))"
    }

    private var errorBinding: Binding<Bool> {
        Binding(
            get: { viewModel.errorMessage != nil },
            set: { if !$0 { viewModel.errorMessage = nil } }
        )
    }
}

private struct InteractiveDesignSpaceMapView: View {
    let insight: DesignSpaceResponse
    let topCandidate: DesignSpaceRecommendation?

    @State private var selectedPoint: DesignSpacePoint?

    private let mapSize = CGSize(width: 540, height: 230)

    private var maxPt: Double {
        max(insight.mapPoints.map(\.pt).max() ?? 1, 1)
    }

    private var currentTheta1: Double? {
        inputDouble("theta1")
    }

    private var currentTheta2: Double? {
        inputDouble("theta2")
    }

    private var currentCase: DDLaminateCase? {
        inputString("case").flatMap(DDLaminateCase.init(rawValue:))
    }

    private var nearbyPoints: [DesignSpacePoint] {
        Array(insight.mapPoints.sorted { $0.distance < $1.distance }.prefix(6))
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("Design-space map")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(.secondary)
                Spacer()
                Text("Tap dots or rows · scroll map")
                    .font(.caption2.weight(.bold))
                    .foregroundStyle(.teal)
            }

            ScrollView(.horizontal, showsIndicators: true) {
                Canvas { context, size in
                    drawMap(context: &context, size: size)
                }
                .frame(width: mapSize.width, height: mapSize.height)
                .contentShape(Rectangle())
                .highPriorityGesture(
                    SpatialTapGesture()
                        .onEnded { value in
                            selectedPoint = nearestPoint(to: value.location, size: mapSize)
                        }
                )
                .padding(8)
                .background(Color.white.opacity(0.72), in: RoundedRectangle(cornerRadius: 8))
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.black.opacity(0.08)))
            }
            .frame(maxWidth: .infinity)

            selectedPointPanel
            nearbyPointButtons

            LazyVGrid(columns: [GridItem(.adaptive(minimum: 82), spacing: 8)], alignment: .leading, spacing: 6) {
                legendItem(label: "Type 1", color: .green)
                legendItem(label: "Type 2", color: .teal)
                legendItem(label: "Type 3", color: .red)
                legendItem(label: "Current", color: .purple)
                legendItem(label: "Candidate", color: .orange)
            }
        }
        .onAppear {
            if selectedPoint == nil {
                selectedPoint = nearbyPoints.first
            }
        }
    }

    @ViewBuilder
    private var selectedPointPanel: some View {
        if let selectedPoint {
            VStack(alignment: .leading, spacing: 4) {
                Text("\(selectedPoint.case.rawValue) · \(selectedPoint.testId)")
                    .font(.caption.weight(.black))
                    .foregroundStyle(.primary)
                Text("θ₁ \(selectedPoint.theta1.angleText) · θ₂ \(selectedPoint.theta2.angleText) · Pt \(selectedPoint.pt.metricText(digits: 2)) · \(selectedPoint.type.typeText)")
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(.secondary)
                Text("Distance \(selectedPoint.distance.metricText(digits: 2))")
                    .font(.caption2.monospacedDigit())
                    .foregroundStyle(.secondary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(10)
            .background(Color.teal.opacity(0.08), in: RoundedRectangle(cornerRadius: 8))
        } else {
            Text("Tap a dot to inspect Case, θ values, Pt, Type, and Test ID.")
                .font(.caption2.weight(.semibold))
                .foregroundStyle(.secondary)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(10)
                .background(Color.black.opacity(0.035), in: RoundedRectangle(cornerRadius: 8))
        }
    }

    @ViewBuilder
    private var nearbyPointButtons: some View {
        if !nearbyPoints.isEmpty {
            VStack(alignment: .leading, spacing: 6) {
                Text("Nearest experiment points")
                    .font(.caption2.weight(.bold))
                    .foregroundStyle(.secondary)
                ForEach(Array(nearbyPoints.enumerated()), id: \.offset) { _, point in
                    Button {
                        selectedPoint = point
                    } label: {
                        HStack(spacing: 8) {
                            Circle()
                                .fill(typeColor(point.type))
                                .frame(width: 8, height: 8)
                            VStack(alignment: .leading, spacing: 2) {
                                Text("\(point.case.rawValue) · \(point.testId)")
                                    .font(.caption2.weight(.black))
                                    .foregroundStyle(.primary)
                                Text("θ₁ \(point.theta1.angleText) · θ₂ \(point.theta2.angleText) · Pt \(point.pt.metricText(digits: 2))")
                                    .font(.caption2.monospacedDigit().weight(.semibold))
                                    .foregroundStyle(.secondary)
                            }
                            Spacer(minLength: 8)
                            Text(point.type.typeText)
                                .font(.caption2.weight(.bold))
                                .foregroundStyle(typeColor(point.type))
                        }
                        .padding(.horizontal, 10)
                        .padding(.vertical, 8)
                        .background(
                            pointKey(point) == selectedPoint.map { pointKey($0) }
                                ? Color.teal.opacity(0.12)
                                : Color.black.opacity(0.035),
                            in: RoundedRectangle(cornerRadius: 8)
                        )
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private func drawMap(context: inout GraphicsContext, size: CGSize) {
        let padding = EdgeInsets(top: 18, leading: 40, bottom: 34, trailing: 18)
        let plot = CGRect(
            x: padding.leading,
            y: padding.top,
            width: max(1, size.width - padding.leading - padding.trailing),
            height: max(1, size.height - padding.top - padding.bottom)
        )

        var plotBackground = Path()
        plotBackground.addRect(plot)
        context.fill(plotBackground, with: .color(.white.opacity(0.82)))

        for tick in stride(from: -90, through: 90, by: 45) {
            let tickValue = Double(tick)
            var grid = Path()
            grid.move(to: CGPoint(x: x(tickValue, in: plot), y: plot.minY))
            grid.addLine(to: CGPoint(x: x(tickValue, in: plot), y: plot.maxY))
            grid.move(to: CGPoint(x: plot.minX, y: y(tickValue, in: plot)))
            grid.addLine(to: CGPoint(x: plot.maxX, y: y(tickValue, in: plot)))
            context.stroke(grid, with: .color(.secondary.opacity(0.16)), lineWidth: 1)

            context.draw(
                Text("\(tick)").font(.caption2).foregroundStyle(.secondary),
                at: CGPoint(x: x(tickValue, in: plot), y: plot.maxY + 15),
                anchor: .center
            )
            context.draw(
                Text("\(tick)").font(.caption2).foregroundStyle(.secondary),
                at: CGPoint(x: plot.minX - 9, y: y(tickValue, in: plot)),
                anchor: .trailing
            )
        }

        var border = Path()
        border.addRect(plot)
        context.stroke(border, with: .color(.secondary.opacity(0.34)), lineWidth: 1)

        for point in insight.mapPoints {
            let center = pointCenter(point, plot: plot)
            let sameCase = currentCase.map { $0 == point.case } ?? true
            let radius = 3.0 + 4.2 * clamp(point.pt / maxPt)
            var dot = Path()
            dot.addEllipse(in: CGRect(
                x: center.x - radius,
                y: center.y - radius,
                width: radius * 2,
                height: radius * 2
            ))
            context.fill(dot, with: .color(typeColor(point.type).opacity(sameCase ? 0.74 : 0.24)))
        }

        if let selectedPoint {
            let center = pointCenter(selectedPoint, plot: plot)
            var selection = Path()
            selection.addEllipse(in: CGRect(x: center.x - 12, y: center.y - 12, width: 24, height: 24))
            context.stroke(selection, with: .color(.black.opacity(0.58)), lineWidth: 2.2)
        }

        if let topCandidate {
            drawCandidate(
                context: &context,
                center: CGPoint(x: x(topCandidate.theta1, in: plot), y: y(topCandidate.theta2, in: plot))
            )
        }

        if let currentTheta1, let currentTheta2 {
            drawCurrentInput(context: &context, center: CGPoint(x: x(currentTheta1, in: plot), y: y(currentTheta2, in: plot)))
        }

        context.draw(
            Text("θ₁").font(.caption2.weight(.bold)).foregroundStyle(.secondary),
            at: CGPoint(x: plot.midX, y: size.height - 7),
            anchor: .center
        )
        context.draw(
            Text("θ₂").font(.caption2.weight(.bold)).foregroundStyle(.secondary),
            at: CGPoint(x: 12, y: plot.midY),
            anchor: .center
        )
    }

    private func drawCurrentInput(context: inout GraphicsContext, center: CGPoint) {
        var halo = Path()
        halo.addEllipse(in: CGRect(x: center.x - 10, y: center.y - 10, width: 20, height: 20))
        context.fill(halo, with: .color(.white.opacity(0.92)))
        context.stroke(halo, with: .color(.purple.opacity(0.35)), lineWidth: 5)

        var marker = Path()
        marker.addEllipse(in: CGRect(x: center.x - 5, y: center.y - 5, width: 10, height: 10))
        context.fill(marker, with: .color(.purple))
    }

    private func drawCandidate(context: inout GraphicsContext, center: CGPoint) {
        let radius: CGFloat = 8
        var diamond = Path()
        diamond.move(to: CGPoint(x: center.x, y: center.y - radius))
        diamond.addLine(to: CGPoint(x: center.x + radius, y: center.y))
        diamond.addLine(to: CGPoint(x: center.x, y: center.y + radius))
        diamond.addLine(to: CGPoint(x: center.x - radius, y: center.y))
        diamond.closeSubpath()
        context.fill(diamond, with: .color(.white.opacity(0.92)))
        context.stroke(diamond, with: .color(.orange), lineWidth: 2.4)
    }

    private func nearestPoint(to location: CGPoint, size: CGSize) -> DesignSpacePoint? {
        let padding = EdgeInsets(top: 18, leading: 40, bottom: 34, trailing: 18)
        let plot = CGRect(
            x: padding.leading,
            y: padding.top,
            width: max(1, size.width - padding.leading - padding.trailing),
            height: max(1, size.height - padding.top - padding.bottom)
        )
        let nearest = insight.mapPoints
            .map { point in
                let center = pointCenter(point, plot: plot)
                return (point, hypot(center.x - location.x, center.y - location.y))
            }
            .min { $0.1 < $1.1 }
        guard let nearest, nearest.1 <= 48 else { return nil }
        return nearest.0
    }

    private func pointKey(_ point: DesignSpacePoint) -> String {
        "\(point.case.rawValue)-\(point.testId)-\(point.theta1)-\(point.theta2)"
    }

    private func pointCenter(_ point: DesignSpacePoint, plot: CGRect) -> CGPoint {
        CGPoint(x: x(point.theta1, in: plot), y: y(point.theta2, in: plot))
    }

    private func x(_ value: Double, in plot: CGRect) -> CGFloat {
        plot.minX + CGFloat(clamp((value + 90) / 180)) * plot.width
    }

    private func y(_ value: Double, in plot: CGRect) -> CGFloat {
        plot.maxY - CGFloat(clamp((value + 90) / 180)) * plot.height
    }

    private func legendItem(label: String, color: Color) -> some View {
        HStack(spacing: 6) {
            Circle()
                .fill(color)
                .frame(width: 8, height: 8)
            Text(label)
                .font(.caption2.weight(.semibold))
                .foregroundStyle(.secondary)
                .lineLimit(1)
        }
    }

    private func typeColor(_ type: Int?) -> Color {
        switch type {
        case 1:
            return .green
        case 2:
            return .teal
        case 3:
            return .red
        default:
            return .secondary
        }
    }

    private func clamp(_ value: Double) -> Double {
        min(max(value, 0), 1)
    }

    private func inputDouble(_ key: String) -> Double? {
        guard let value = insight.inputs[key] else { return nil }
        switch value {
        case .double(let double):
            return double
        case .string(let string):
            return Double(string)
        case .bool, .null:
            return nil
        }
    }

    private func inputString(_ key: String) -> String? {
        guard let value = insight.inputs[key] else { return nil }
        switch value {
        case .string(let string):
            return string
        case .double(let double):
            return double.metricText(digits: 0)
        case .bool(let bool):
            return String(bool)
        case .null:
            return nil
        }
    }
}

private extension ResponsePredictionResult {
    var predictedPtDisplacement: Double? {
        curve.displacement(atForce: predictedPt)
    }
}

private extension Array where Element == ResponseCurvePoint {
    func displacement(atForce targetForce: Double?) -> Double? {
        guard let force = targetForce, force.isFinite, let first else { return nil }
        if force <= first.force { return first.displacement }
        for index in 1..<count {
            let previous = self[index - 1]
            let current = self[index]
            let low = Swift.min(previous.force, current.force)
            let high = Swift.max(previous.force, current.force)
            guard force >= low, force <= high else { continue }
            let delta = current.force - previous.force
            if delta == 0 { return current.displacement }
            let ratio = (force - previous.force) / delta
            return previous.displacement + ratio * (current.displacement - previous.displacement)
        }
        return last?.displacement
    }
}

private extension Optional where Wrapped == Double {
    var percentText: String {
        guard let value = self else { return "-" }
        return value.formatted(.percent.precision(.fractionLength(1)))
    }
}

private extension Double {
    var percentText: String {
        formatted(.percent.precision(.fractionLength(1)))
    }

    func metricText(digits: Int) -> String {
        formatted(.number.precision(.fractionLength(0...digits)))
    }

    var angleText: String {
        formatted(.number.sign(strategy: .always()).precision(.fractionLength(0))) + " deg"
    }
}

private extension Optional where Wrapped == Int {
    var typeText: String {
        guard let value = self else { return "Type -" }
        return "Type \(value)"
    }
}

private extension String {
    var displayFocusKind: String {
        switch self {
        case "type1":
            return "Type 1 zone"
        case "high_pt":
            return "High Pt zone"
        default:
            return self
        }
    }
}
