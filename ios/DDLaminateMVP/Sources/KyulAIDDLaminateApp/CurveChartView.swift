import KyulAIDDLaminateCore
import SwiftUI

private enum ChartZoom {
    static let minScale: CGFloat = 1
    static let maxScale: CGFloat = 5
}

public struct CurveChartView: View {
    private let points: [ResponseCurvePoint]
    private let predictedPt: Double?
    private let fitMode: CurveFitMode
    private let curveFit: ResponseCurveFit?
    private let isInteractive: Bool
    @State private var selectedPoint: ResponseCurvePoint?
    @State private var gestureInitialPoint: ResponseCurvePoint?
    @State private var isTrackingGesture = false
    @State private var gestureDidMove = false
    @State private var isPanningChart = false
    @State private var isScrubbingCurve = false
    @State private var isZoomingChart = false
    @State private var zoomScale: CGFloat = 1
    @State private var panOffset: CGSize = .zero
    @State private var panGestureStartOffset: CGSize = .zero
    @State private var zoomGestureStartScale: CGFloat?
    @State private var zoomGestureStartPan: CGSize?
    @State private var lastChartSize: CGSize = CGSize(width: 360, height: 260)

    public init(
        points: [ResponseCurvePoint],
        predictedPt: Double? = nil,
        fitMode: CurveFitMode = .standard,
        curveFit: ResponseCurveFit? = nil,
        isInteractive: Bool = true
    ) {
        self.points = points
        self.predictedPt = predictedPt
        self.fitMode = fitMode
        self.curveFit = curveFit
        self.isInteractive = isInteractive
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            if isInteractive {
                chartZoomControls
            }
            chartBody
            chartLegend
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(L10n.f("curve.accessibility", points.count))
    }

    private var viewport: ChartViewport {
        ChartViewport(scale: isInteractive ? zoomScale : 1, panOffset: isInteractive ? panOffset : .zero)
    }

    private var chartZoomControls: some View {
        HStack(spacing: 8) {
            Spacer(minLength: 0)
            Button {
                adjustZoom(by: 0.75)
            } label: {
                Image(systemName: "minus.magnifyingglass")
                    .frame(width: 30, height: 30)
            }
            .disabled(zoomScale <= ChartZoom.minScale + 0.01)

            Text("\(Int((zoomScale * 100).rounded()))%")
                .font(.caption2.monospacedDigit().weight(.black))
                .foregroundStyle(AppTheme.muted)
                .frame(width: 48)

            Button {
                adjustZoom(by: 1.35)
            } label: {
                Image(systemName: "plus.magnifyingglass")
                    .frame(width: 30, height: 30)
            }
            .disabled(zoomScale >= ChartZoom.maxScale - 0.01)

            Button {
                resetZoom()
            } label: {
                Image(systemName: "arrow.counterclockwise")
                    .frame(width: 30, height: 30)
            }
            .disabled(zoomScale <= ChartZoom.minScale + 0.01 && panOffset == .zero)
        }
        .buttonStyle(ChartIconButtonStyle())
        .padding(.horizontal, 4)
    }

    private var chartBody: some View {
        GeometryReader { proxy in
            ZStack(alignment: .bottomLeading) {
                RoundedRectangle(cornerRadius: 14)
                    .fill(AppTheme.field)
                Canvas { context, size in
                    guard let layout = ChartLayout(points: points, size: size, predictedPt: predictedPt, fitMode: fitMode, curveFit: curveFit, viewport: viewport) else { return }
                    drawAxes(context: context, layout: layout)
                    var clippedContext = context
                    clippedContext.clip(to: Path(layout.plotFrame))
                    clippedContext.stroke(
                        layout.path,
                        with: .linearGradient(
                            Gradient(colors: [AppTheme.primary, AppTheme.accent.opacity(0.86)]),
                            startPoint: CGPoint(x: layout.plotFrame.minX, y: layout.plotFrame.midY),
                            endPoint: CGPoint(x: layout.plotFrame.maxX, y: layout.plotFrame.midY)
                        ),
                        style: StrokeStyle(lineWidth: 3, lineCap: .round, lineJoin: .round)
                    )

                    if let bilinearFit = layout.bilinearFit {
                        drawBilinearFit(context: clippedContext, layout: layout, fit: bilinearFit)
                        drawPtKink(context: clippedContext, layout: layout, fit: bilinearFit)
                    }
                }
                if let layout = ChartLayout(points: points, size: proxy.size, predictedPt: predictedPt, fitMode: fitMode, curveFit: curveFit, viewport: viewport), let selectedPoint {
                    selectionOverlay(point: selectedPoint, layout: layout)
                }
                if let predictedPt {
                    VStack {
                        HStack {
                            Spacer()
                            Text("Pt \(predictedPt.metricText(digits: 2))")
                                .font(.caption2.bold())
                                .foregroundStyle(AppTheme.danger)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(.background.opacity(0.86), in: Capsule())
                        }
                        Spacer()
                    }
                    .padding(10)
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
            .contentShape(Rectangle())
            .gesture(chartDragGesture(size: proxy.size))
            .simultaneousGesture(chartMagnificationGesture(size: proxy.size))
            .onAppear {
                lastChartSize = proxy.size
            }
            .onChange(of: proxy.size) { _, newSize in
                lastChartSize = newSize
                panOffset = clampedPanOffset(panOffset, scale: zoomScale, size: newSize)
            }
        }
    }

    private func chartDragGesture(size: CGSize) -> some Gesture {
        DragGesture(minimumDistance: 0)
            .onChanged { value in
                guard !isZoomingChart else { return }
                if !isTrackingGesture {
                    gestureInitialPoint = selectedPoint
                    panGestureStartOffset = panOffset
                    isTrackingGesture = true
                    gestureDidMove = false
                    isPanningChart = false
                    isScrubbingCurve = startCurveScrub(at: value.location, size: size)
                }
                if abs(value.translation.width) > 6 || abs(value.translation.height) > 6 {
                    gestureDidMove = true
                }

                if isScrubbingCurve {
                    updateCurveScrub(at: value.location, size: size)
                    return
                }

                if isInteractive && zoomScale > ChartZoom.minScale + 0.01 && gestureDidMove {
                    isPanningChart = true
                    selectedPoint = nil
                    panOffset = clampedPanOffset(
                        CGSize(
                            width: panGestureStartOffset.width + value.translation.width,
                            height: panGestureStartOffset.height + value.translation.height
                        ),
                        scale: zoomScale,
                        size: size
                    )
                    return
                }

                if let layout = ChartLayout(
                    points: points,
                    size: size,
                    predictedPt: predictedPt,
                    fitMode: fitMode,
                    curveFit: curveFit,
                    viewport: viewport
                ) {
                    selectedPoint = layout.nearestPoint(to: value.location)
                }
            }
            .onEnded { value in
                defer {
                    gestureInitialPoint = nil
                    isTrackingGesture = false
                    gestureDidMove = false
                    isPanningChart = false
                    isScrubbingCurve = false
                }
                guard !isPanningChart else {
                    panOffset = clampedPanOffset(panOffset, scale: zoomScale, size: size)
                    return
                }
                if isScrubbingCurve {
                    updateCurveScrub(at: value.location, size: size)
                    return
                }
                if let layout = ChartLayout(
                    points: points,
                    size: size,
                    predictedPt: predictedPt,
                    fitMode: fitMode,
                    curveFit: curveFit,
                    viewport: viewport
                ) {
                    let nearestPoint = layout.nearestPoint(to: value.location)
                    if !gestureDidMove && gestureInitialPoint != nil {
                        selectedPoint = nil
                    } else {
                        selectedPoint = nearestPoint
                    }
                }
            }
    }

    private func startCurveScrub(at location: CGPoint, size: CGSize) -> Bool {
        guard let layout = ChartLayout(
            points: points,
            size: size,
            predictedPt: predictedPt,
            fitMode: fitMode,
            curveFit: curveFit,
            viewport: viewport
        ), layout.plotFrame.contains(location),
           let nearest = layout.nearestPoint(to: location) else {
            return false
        }
        if isInteractive,
           zoomScale > ChartZoom.minScale + 0.01,
           screenDistance(from: nearest, to: location, layout: layout) > 44 {
            return false
        }
        selectedPoint = nearest
        return true
    }

    private func updateCurveScrub(at location: CGPoint, size: CGSize) {
        guard let layout = ChartLayout(
            points: points,
            size: size,
            predictedPt: predictedPt,
            fitMode: fitMode,
            curveFit: curveFit,
            viewport: viewport
        ) else {
            return
        }
        let clampedLocation = CGPoint(
            x: min(max(location.x, layout.plotFrame.minX + 1), layout.plotFrame.maxX - 1),
            y: min(max(location.y, layout.plotFrame.minY + 1), layout.plotFrame.maxY - 1)
        )
        selectedPoint = layout.nearestPoint(to: clampedLocation)
    }

    private func screenDistance(from point: ResponseCurvePoint, to location: CGPoint, layout: ChartLayout) -> CGFloat {
        let coordinate = layout.coordinate(displacement: point.displacement, force: point.force)
        return hypot(coordinate.x - location.x, coordinate.y - location.y)
    }

    private func chartMagnificationGesture(size: CGSize) -> some Gesture {
        MagnificationGesture()
            .onChanged { value in
                guard isInteractive else { return }
                let startScale = zoomGestureStartScale ?? zoomScale
                let startPan = zoomGestureStartPan ?? panOffset
                if zoomGestureStartScale == nil {
                    zoomGestureStartScale = zoomScale
                    zoomGestureStartPan = panOffset
                }
                isZoomingChart = true
                selectedPoint = nil
                let nextScale = clampedZoomScale(startScale * value)
                zoomScale = nextScale
                panOffset = centeredPanForZoom(
                    startScale: startScale,
                    nextScale: nextScale,
                    startPan: startPan,
                    size: size
                )
            }
            .onEnded { _ in
                zoomScale = clampedZoomScale(zoomScale)
                panOffset = clampedPanOffset(panOffset, scale: zoomScale, size: size)
                zoomGestureStartScale = nil
                zoomGestureStartPan = nil
                isZoomingChart = false
            }
    }

    private func adjustZoom(by factor: CGFloat) {
        let startScale = zoomScale
        let startPan = panOffset
        let nextScale = clampedZoomScale(zoomScale * factor)
        withAnimation(.easeOut(duration: 0.18)) {
            zoomScale = nextScale
            panOffset = centeredPanForZoom(
                startScale: startScale,
                nextScale: nextScale,
                startPan: startPan,
                size: lastChartSize
            )
            selectedPoint = nil
        }
    }

    private func resetZoom() {
        withAnimation(.easeOut(duration: 0.18)) {
            zoomScale = ChartZoom.minScale
            panOffset = .zero
            selectedPoint = nil
        }
    }

    private func clampedZoomScale(_ value: CGFloat) -> CGFloat {
        min(max(value, ChartZoom.minScale), ChartZoom.maxScale)
    }

    private func clampedPanOffset(_ pan: CGSize, scale: CGFloat, size: CGSize) -> CGSize {
        let plot = ChartLayout.plotFrame(for: size)
        guard scale > ChartZoom.minScale + 0.01 else { return .zero }
        let minX = plot.width * (1 - scale)
        let maxY = plot.height * (scale - 1)
        return CGSize(
            width: min(max(pan.width, minX), 0),
            height: min(max(pan.height, 0), maxY)
        )
    }

    private func centeredPanForZoom(
        startScale: CGFloat,
        nextScale: CGFloat,
        startPan: CGSize,
        size: CGSize
    ) -> CGSize {
        let plot = ChartLayout.plotFrame(for: size)
        guard nextScale > ChartZoom.minScale + 0.01 else { return .zero }
        let anchorX = plot.width / 2
        let anchorFromBottom = plot.height / 2
        let safeStartScale = max(startScale, ChartZoom.minScale)
        let normalizedX = (anchorX - startPan.width) / max(plot.width * safeStartScale, 1)
        let normalizedY = (anchorFromBottom + startPan.height) / max(plot.height * safeStartScale, 1)
        let nextPan = CGSize(
            width: anchorX - normalizedX * plot.width * nextScale,
            height: normalizedY * plot.height * nextScale - anchorFromBottom
        )
        return clampedPanOffset(nextPan, scale: nextScale, size: size)
    }

    private var chartLegend: some View {
        let items: [(CurveLegendStyle, String)] = [
            (.curve, L10n.t("curve.legend.predicted.curve")),
            (.linearFit, L10n.t("curve.legend.linear.fit")),
            (.kinkGuide, L10n.t("curve.legend.kink.guide")),
            (.point, L10n.t("predicted.pt")),
        ]

        return ViewThatFits(in: .horizontal) {
            HStack(spacing: 14) {
                ForEach(items.indices, id: \.self) { index in
                    legendItem(style: items[index].0, title: items[index].1)
                }
            }

            LazyVGrid(
                columns: [
                    GridItem(.flexible(minimum: 110), alignment: .leading),
                    GridItem(.flexible(minimum: 110), alignment: .leading),
                ],
                alignment: .leading,
                spacing: 7
            ) {
                ForEach(items.indices, id: \.self) { index in
                    legendItem(style: items[index].0, title: items[index].1)
                }
            }
        }
        .padding(.horizontal, 4)
    }

    private func legendItem(style: CurveLegendStyle, title: String) -> some View {
        HStack(spacing: 7) {
            CurveLegendSwatch(style: style)
            Text(title)
                .font(.caption2.weight(.bold))
                .foregroundStyle(AppTheme.muted)
                .lineLimit(1)
                .minimumScaleFactor(0.82)
        }
    }

    private func drawAxes(context: GraphicsContext, layout: ChartLayout) {
        var gridPath = Path()
        layout.yTicks.dropFirst().dropLast().forEach { value in
            let y = layout.yPosition(for: value)
            gridPath.move(to: CGPoint(x: layout.plotFrame.minX, y: y))
            gridPath.addLine(to: CGPoint(x: layout.plotFrame.maxX, y: y))
        }
        layout.xTicks.dropFirst().dropLast().forEach { value in
            let x = layout.xPosition(for: value)
            gridPath.move(to: CGPoint(x: x, y: layout.plotFrame.minY))
            gridPath.addLine(to: CGPoint(x: x, y: layout.plotFrame.maxY))
        }
        context.stroke(gridPath, with: .color(Color(.sRGB, red: 0.90, green: 0.93, blue: 0.95, opacity: 1)), lineWidth: 1)

        var axisPath = Path()
        axisPath.move(to: CGPoint(x: layout.plotFrame.minX, y: layout.plotFrame.minY))
        axisPath.addLine(to: CGPoint(x: layout.plotFrame.minX, y: layout.plotFrame.maxY))
        axisPath.addLine(to: CGPoint(x: layout.plotFrame.maxX, y: layout.plotFrame.maxY))
        context.stroke(axisPath, with: .color(AppTheme.muted.opacity(0.48)), lineWidth: 1)

        let tickStyle = Font.caption2.monospacedDigit().weight(.semibold)
        layout.yTicks.forEach { value in
            context.draw(
                Text(value.axisTickText(smallValueDigits: 2)).font(tickStyle).foregroundStyle(AppTheme.muted),
                at: CGPoint(x: layout.plotFrame.minX - 6, y: layout.yPosition(for: value)),
                anchor: .trailing
            )
        }
        layout.xTicks.forEach { value in
            context.draw(
                Text(value.axisTickText(smallValueDigits: 4)).font(tickStyle).foregroundStyle(AppTheme.muted),
                at: CGPoint(x: layout.xPosition(for: value), y: layout.plotFrame.maxY + 16),
                anchor: .top
            )
        }
    }

    private func drawBilinearFit(context: GraphicsContext, layout: ChartLayout, fit: BilinearFit) {
        var slopePath = Path()
        slopePath.move(to: layout.coordinate(displacement: fit.firstStartX, force: fit.firstLine.y(at: fit.firstStartX)))
        slopePath.addLine(to: layout.coordinate(displacement: fit.firstEndX, force: fit.firstLine.y(at: fit.firstEndX)))
        slopePath.move(to: layout.coordinate(displacement: fit.secondStartX, force: fit.secondLine.y(at: fit.secondStartX)))
        slopePath.addLine(to: layout.coordinate(displacement: fit.secondEndX, force: fit.secondLine.y(at: fit.secondEndX)))
        context.stroke(
            slopePath,
            with: .color(AppTheme.danger.opacity(0.94)),
            style: StrokeStyle(lineWidth: 1.9, lineCap: .round, lineJoin: .round, dash: [7, 5])
        )

        let guideMarker: CurveCoordinate
        switch layout.fitMode {
        case .standard:
            guideMarker = fit.detectedKink ?? fit.kink
        case .u3:
            guideMarker = layout.fitIntersection ?? fit.kink
        }
        let kink = layout.coordinate(displacement: guideMarker.displacement, force: guideMarker.force)
        var guide = Path()
        guide.move(to: CGPoint(x: kink.x, y: layout.plotFrame.minY))
        guide.addLine(to: CGPoint(x: kink.x, y: layout.plotFrame.maxY))
        context.stroke(
            guide,
            with: .color(Color.purple.opacity(0.62)),
            style: StrokeStyle(lineWidth: 1.2, dash: [7, 4])
        )
    }

    private func drawPtKink(context: GraphicsContext, layout: ChartLayout, fit: BilinearFit) {
        let marker: CurveCoordinate
        switch layout.fitMode {
        case .standard:
            marker = fit.kink
        case .u3:
            marker = layout.fitIntersection ?? fit.kink
        }
        let coordinate = layout.coordinate(displacement: marker.displacement, force: marker.force)
        var diamond = Path()
        diamond.move(to: CGPoint(x: coordinate.x, y: coordinate.y - 7))
        diamond.addLine(to: CGPoint(x: coordinate.x + 7, y: coordinate.y))
        diamond.addLine(to: CGPoint(x: coordinate.x, y: coordinate.y + 7))
        diamond.addLine(to: CGPoint(x: coordinate.x - 7, y: coordinate.y))
        diamond.closeSubpath()
        context.fill(diamond, with: .color(.white))
        context.stroke(diamond, with: .color(Color.purple), lineWidth: 2)
    }

    private func selectionOverlay(point: ResponseCurvePoint, layout: ChartLayout) -> some View {
        let coordinate = layout.coordinate(displacement: point.displacement, force: point.force)
        let labelX = min(max(coordinate.x + 76, layout.plotFrame.minX + 82), layout.plotFrame.maxX - 82)
        let labelY = max(coordinate.y - 34, layout.plotFrame.minY + 24)
        return ZStack {
            Path { path in
                path.move(to: CGPoint(x: coordinate.x, y: layout.plotFrame.minY))
                path.addLine(to: CGPoint(x: coordinate.x, y: layout.plotFrame.maxY))
                path.move(to: CGPoint(x: layout.plotFrame.minX, y: coordinate.y))
                path.addLine(to: CGPoint(x: layout.plotFrame.maxX, y: coordinate.y))
            }
            .stroke(AppTheme.ink.opacity(0.24), style: StrokeStyle(lineWidth: 1, dash: [4, 4]))

            Circle()
                .fill(.white)
                .frame(width: 14, height: 14)
                .overlay(Circle().stroke(AppTheme.primary, lineWidth: 3))
                .position(coordinate)

            VStack(alignment: .leading, spacing: 2) {
                Text("x \(point.displacement.metricText(digits: 4))")
                Text("y \(point.force.metricText(digits: 2))")
            }
            .font(.caption2.bold().monospacedDigit())
            .foregroundStyle(AppTheme.ink)
            .padding(.horizontal, 8)
            .padding(.vertical, 6)
            .background(.background.opacity(0.92), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(AppTheme.primary.opacity(0.28), lineWidth: 1)
            )
            .position(x: labelX, y: labelY)
        }
    }
}

public enum CurveFitMode {
    case standard
    case u3
}

private enum CurveLegendStyle {
    case curve
    case linearFit
    case kinkGuide
    case point
}

private struct ChartIconButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.caption.weight(.black))
            .foregroundStyle(AppTheme.primary.opacity(configuration.isPressed ? 0.62 : 1))
            .background(
                AppTheme.primary.opacity(configuration.isPressed ? 0.16 : 0.09),
                in: RoundedRectangle(cornerRadius: 8, style: .continuous)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(AppTheme.primary.opacity(0.14), lineWidth: 1)
            )
    }
}

private struct CurveLegendSwatch: View {
    let style: CurveLegendStyle

    var body: some View {
        Canvas { context, size in
            let midY = size.height / 2
            switch style {
            case .curve:
                var path = Path()
                path.move(to: CGPoint(x: 1, y: midY))
                path.addLine(to: CGPoint(x: size.width - 1, y: midY))
                context.stroke(
                    path,
                    with: .linearGradient(
                        Gradient(colors: [AppTheme.primary, AppTheme.accent.opacity(0.86)]),
                        startPoint: CGPoint(x: 0, y: midY),
                        endPoint: CGPoint(x: size.width, y: midY)
                    ),
                    style: StrokeStyle(lineWidth: 3, lineCap: .round)
                )
            case .linearFit:
                var path = Path()
                path.move(to: CGPoint(x: 1, y: midY))
                path.addLine(to: CGPoint(x: size.width - 1, y: midY))
                context.stroke(
                    path,
                    with: .color(AppTheme.danger.opacity(0.94)),
                    style: StrokeStyle(lineWidth: 1.9, lineCap: .round, dash: [7, 5])
                )
            case .kinkGuide:
                var path = Path()
                path.move(to: CGPoint(x: size.width / 2, y: 1))
                path.addLine(to: CGPoint(x: size.width / 2, y: size.height - 1))
                context.stroke(
                    path,
                    with: .color(Color.purple.opacity(0.62)),
                    style: StrokeStyle(lineWidth: 1.4, lineCap: .round, dash: [5, 4])
                )
            case .point:
                let center = CGPoint(x: size.width / 2, y: midY)
                var diamond = Path()
                diamond.move(to: CGPoint(x: center.x, y: center.y - 5))
                diamond.addLine(to: CGPoint(x: center.x + 5, y: center.y))
                diamond.addLine(to: CGPoint(x: center.x, y: center.y + 5))
                diamond.addLine(to: CGPoint(x: center.x - 5, y: center.y))
                diamond.closeSubpath()
                context.fill(diamond, with: .color(.white))
                context.stroke(diamond, with: .color(Color.purple), lineWidth: 2)
            }
        }
        .frame(width: 28, height: 16)
    }
}

private struct ChartViewport {
    let scale: CGFloat
    let panOffset: CGSize

    func clamped(for plotFrame: CGRect) -> ChartViewport {
        let safeScale = min(max(scale, ChartZoom.minScale), ChartZoom.maxScale)
        guard safeScale > ChartZoom.minScale + 0.01 else {
            return ChartViewport(scale: ChartZoom.minScale, panOffset: .zero)
        }
        let minX = plotFrame.width * (1 - safeScale)
        let maxY = plotFrame.height * (safeScale - 1)
        return ChartViewport(
            scale: safeScale,
            panOffset: CGSize(
                width: min(max(panOffset.width, minX), 0),
                height: min(max(panOffset.height, 0), maxY)
            )
        )
    }
}

private struct ChartLayout {
    let path: Path
    let plotFrame: CGRect
    let bilinearFit: BilinearFit?
    let fitIntersection: CurveCoordinate?
    let fitMode: CurveFitMode
    private let points: [ResponseCurvePoint]
    private let minX: Double
    private let maxX: Double
    private let minY: Double
    private let maxY: Double

    init?(
        points: [ResponseCurvePoint],
        size: CGSize,
        predictedPt: Double?,
        fitMode: CurveFitMode = .standard,
        curveFit: ResponseCurveFit? = nil,
        viewport: ChartViewport = ChartViewport(scale: ChartZoom.minScale, panOffset: .zero)
    ) {
        let plotFrame = Self.plotFrame(for: size)
        let viewport = viewport.clamped(for: plotFrame)
        guard points.count > 1,
              let fullMinX = points.map(\.displacement).min(),
              let fullMaxX = points.map(\.displacement).max(),
              let minY = points.map(\.force).min(),
              let maxY = points.map(\.force).max(),
              fullMaxX > fullMinX,
              maxY > minY else {
            return nil
        }

        let bilinearFit = fitMode == .u3
            ? Self.buildU3BilinearFit(points: points, predictedPt: predictedPt)
            : (Self.buildBackendBilinearFit(points: points, predictedPt: predictedPt, curveFit: curveFit)
               ?? Self.buildBilinearFit(points: points, predictedPt: predictedPt))
        let fitIntersection = bilinearFit.flatMap { Self.lineIntersection($0.firstLine, $0.secondLine) }
        var yValues = points.map(\.force)
        if let predictedPt, predictedPt.isFinite {
            yValues.append(predictedPt)
        }
        if let bilinearFit {
            yValues.append(contentsOf: [
                bilinearFit.firstLine.y(at: bilinearFit.firstStartX),
                bilinearFit.firstLine.y(at: bilinearFit.firstEndX),
                bilinearFit.secondLine.y(at: bilinearFit.secondStartX),
                bilinearFit.secondLine.y(at: bilinearFit.secondEndX),
                bilinearFit.kink.force,
            ])
            if let fitIntersection {
                yValues.append(fitIntersection.force)
            }
            if let detectedKink = bilinearFit.detectedKink {
                yValues.append(detectedKink.force)
            }
        }
        let adjustedMinY = min(0, yValues.min() ?? minY)
        let adjustedMaxY = (yValues.max() ?? maxY) * 1.06
        let visibleDomain = Self.visibleDomain(
            fullMinX: fullMinX,
            fullMaxX: fullMaxX,
            fullMinY: adjustedMinY,
            fullMaxY: adjustedMaxY,
            plotFrame: plotFrame,
            viewport: viewport
        )

        var path = Path()
        for (index, point) in points.enumerated() {
            let x = plotFrame.minX + (point.displacement - visibleDomain.minX) / (visibleDomain.maxX - visibleDomain.minX) * plotFrame.width
            let y = plotFrame.maxY - (point.force - visibleDomain.minY) / (visibleDomain.maxY - visibleDomain.minY) * plotFrame.height
            let cgPoint = CGPoint(x: x, y: y)
            if index == 0 {
                path.move(to: cgPoint)
            } else {
                path.addLine(to: cgPoint)
            }
        }

        self.path = path
        self.plotFrame = plotFrame
        self.bilinearFit = bilinearFit
        self.fitIntersection = fitIntersection
        self.fitMode = fitMode
        self.points = points
        self.minX = visibleDomain.minX
        self.maxX = visibleDomain.maxX
        self.minY = visibleDomain.minY
        self.maxY = visibleDomain.maxY
    }

    static func plotFrame(for size: CGSize) -> CGRect {
        let leftInset: CGFloat = 54
        let rightInset: CGFloat = 18
        let topInset: CGFloat = 32
        let bottomInset: CGFloat = 58
        let availableFrame = CGRect(
            x: leftInset,
            y: topInset,
            width: max(1, size.width - leftInset - rightInset),
            height: max(1, size.height - topInset - bottomInset)
        )
        let targetRatio: CGFloat = 5.0 / 3.0
        var plotWidth = availableFrame.width
        var plotHeight = plotWidth / targetRatio
        if plotHeight > availableFrame.height {
            plotHeight = availableFrame.height
            plotWidth = plotHeight * targetRatio
        }
        return CGRect(
            x: availableFrame.midX - plotWidth / 2,
            y: availableFrame.midY - plotHeight / 2,
            width: max(1, plotWidth),
            height: max(1, plotHeight)
        )
    }

    private static func visibleDomain(
        fullMinX: Double,
        fullMaxX: Double,
        fullMinY: Double,
        fullMaxY: Double,
        plotFrame: CGRect,
        viewport: ChartViewport
    ) -> (minX: Double, maxX: Double, minY: Double, maxY: Double) {
        let scale = max(Double(viewport.scale), 1)
        let xSpan = max(fullMaxX - fullMinX, 1e-12)
        let ySpan = max(fullMaxY - fullMinY, 1e-12)
        let startXFraction = max(0, min(1 - 1 / scale, Double(-viewport.panOffset.width / max(plotFrame.width * viewport.scale, 1))))
        let startYFraction = max(0, min(1 - 1 / scale, Double(viewport.panOffset.height / max(plotFrame.height * viewport.scale, 1))))
        let minX = fullMinX + xSpan * startXFraction
        let minY = fullMinY + ySpan * startYFraction
        return (
            minX: minX,
            maxX: min(fullMaxX, minX + xSpan / scale),
            minY: minY,
            maxY: min(fullMaxY, minY + ySpan / scale)
        )
    }

    var xTicks: [Double] {
        Self.tickValues(min: minX, max: maxX, count: 6)
    }

    var yTicks: [Double] {
        Self.tickValues(min: minY, max: maxY, count: 6)
    }

    func xPosition(for value: Double) -> CGFloat {
        plotFrame.minX + (value - minX) / (maxX - minX) * plotFrame.width
    }

    func yPosition(for value: Double) -> CGFloat {
        plotFrame.maxY - (value - minY) / (maxY - minY) * plotFrame.height
    }

    func ptMarker(force predictedPt: Double?) -> CGPoint? {
        guard let predictedPt,
              predictedPt.isFinite,
              let curvePoint = interpolatedPoint(atForce: predictedPt) else {
            return nil
        }
        return CGPoint(x: xPosition(for: curvePoint.displacement), y: yPosition(for: curvePoint.force))
    }

    func coordinate(displacement: Double, force: Double) -> CGPoint {
        CGPoint(x: xPosition(for: displacement), y: yPosition(for: force))
    }

    func nearestPoint(to location: CGPoint) -> ResponseCurvePoint? {
        points.min { lhs, rhs in
            abs(coordinate(displacement: lhs.displacement, force: lhs.force).x - location.x) <
                abs(coordinate(displacement: rhs.displacement, force: rhs.force).x - location.x)
        }
    }

    private func interpolatedPoint(atForce targetForce: Double) -> CurveCoordinate? {
        if targetForce <= points[0].force {
            return CurveCoordinate(displacement: points[0].displacement, force: points[0].force)
        }
        for index in 1..<points.count {
            let previous = points[index - 1]
            let current = points[index]
            let low = min(previous.force, current.force)
            let high = max(previous.force, current.force)
            guard targetForce >= low, targetForce <= high else {
                continue
            }
            let forceDelta = current.force - previous.force
            guard forceDelta != 0 else {
                return CurveCoordinate(displacement: current.displacement, force: current.force)
            }
            let ratio = (targetForce - previous.force) / forceDelta
            return CurveCoordinate(
                displacement: previous.displacement + ratio * (current.displacement - previous.displacement),
                force: targetForce
            )
        }
        guard let last = points.last else { return nil }
        return CurveCoordinate(displacement: last.displacement, force: last.force)
    }

    private static func tickValues(min: Double, max: Double, count: Int) -> [Double] {
        guard count > 1 else { return [min] }
        let span = max - min
        return (0..<count).map { index in
            min + span * Double(index) / Double(count - 1)
        }
    }

    private static func buildBackendBilinearFit(
        points: [ResponseCurvePoint],
        predictedPt: Double?,
        curveFit: ResponseCurveFit?
    ) -> BilinearFit? {
        guard let curveFit,
              points.count >= 2,
              let firstLine = curveFit.firstLine,
              let secondLine = curveFit.secondLine,
              let kink = curveFit.kink,
              let minX = points.map(\.displacement).min(),
              let maxX = points.map(\.displacement).max() else {
            return nil
        }
        let first = FittedLine(slope: firstLine.slope, intercept: firstLine.intercept)
        let second = FittedLine(slope: secondLine.slope, intercept: secondLine.intercept)
        guard first.slope.isFinite,
              first.intercept.isFinite,
              second.slope.isFinite,
              second.intercept.isFinite,
              kink.displacement.isFinite,
              kink.force.isFinite else {
            return nil
        }
        let detectedKink = curveFit.detectedKink.flatMap { point -> CurveCoordinate? in
            guard point.displacement.isFinite, point.force.isFinite else { return nil }
            return CurveCoordinate(displacement: point.displacement, force: point.force)
        }
        let predictedPoint = predictedPt.flatMap {
            $0.isFinite ? pointAtForce(points: points, force: $0) : nil
        }
        return BilinearFit(
            kink: CurveCoordinate(displacement: kink.displacement, force: kink.force),
            detectedKink: detectedKink,
            predictedPoint: predictedPoint,
            firstLine: first,
            secondLine: second,
            firstStartX: curveFit.firstStartX?.takeIfFinite() ?? minX,
            firstEndX: curveFit.firstEndX?.takeIfFinite() ?? min(maxX, kink.displacement),
            secondStartX: curveFit.secondStartX?.takeIfFinite() ?? max(minX, kink.displacement),
            secondEndX: curveFit.secondEndX?.takeIfFinite() ?? maxX
        )
    }

    private static func buildBilinearFit(points: [ResponseCurvePoint], predictedPt: Double?) -> BilinearFit? {
        buildKinkBilinearFit(points: points, predictedPt: predictedPt)
    }

    private static func buildU3BilinearFit(points: [ResponseCurvePoint], predictedPt: Double?) -> BilinearFit? {
        guard let fit = buildKinkBilinearFit(points: points, predictedPt: predictedPt),
              let minX = points.map(\.displacement).min(),
              let maxX = points.map(\.displacement).max() else {
            return nil
        }
        let spanX = max(maxX - minX, 1e-9)
        let kinkX = min(max(fit.kink.displacement, minX), maxX)
        return BilinearFit(
            kink: fit.kink,
            detectedKink: fit.detectedKink,
            predictedPoint: fit.predictedPoint,
            firstLine: fit.firstLine,
            secondLine: fit.secondLine,
            firstStartX: minX,
            firstEndX: min(maxX, kinkX + spanX * 0.035),
            secondStartX: kinkX,
            secondEndX: maxX
        )
    }

    private static func buildKinkBilinearFit(points: [ResponseCurvePoint], predictedPt: Double?) -> BilinearFit? {
        let sorted = points
            .filter { $0.displacement.isFinite && $0.force.isFinite }
            .sorted { $0.displacement < $1.displacement }
        guard sorted.count >= 10,
              let minX = sorted.first?.displacement,
              let maxX = sorted.last?.displacement else {
            return nil
        }
        let initialKink = bestInitialWindowForKink(sorted)
        let kinkIndex = initialKink.flatMap {
            detectKinkStart(sorted, initialSlope: $0.line.slope, startIndexMin: $0.end + 1)
        }
        let endForInitial = kinkIndex.map { max(0, $0 - 1) } ?? (sorted.count - 1)
        guard let first = bestInitialLinearWindow(sorted, endIndex: endForInitial) else {
            return nil
        }

        let second: FitWindow?
        var detectedKink: CurveCoordinate?
        if let kinkIndex {
            detectedKink = CurveCoordinate(
                displacement: sorted[kinkIndex].displacement,
                force: sorted[kinkIndex].force
            )
            let secondStart = max(first.end + 1, kinkIndex + KinkFit.postSkipAfterKink)
            second = bestSecondWindowPostKink(
                sorted,
                startAfterIndex: secondStart,
                kinkIndex: kinkIndex,
                firstLine: first.line,
                kinkX: sorted[kinkIndex].displacement
            )
        } else {
            second = bestFallbackSecondWindow(sorted, startAfterIndex: first.end + 1)
        }
        guard let second,
              var pt = lineIntersection(first.line, second.line),
              pt.force > 0 else {
            return nil
        }

        if let detectedKink, pt.displacement > detectedKink.displacement + KinkFit.preKinkEps {
            let clampedX = detectedKink.displacement - KinkFit.preKinkEps
            pt = CurveCoordinate(displacement: clampedX, force: first.line.y(at: clampedX))
        }
        let ptX = min(max(pt.displacement, minX), maxX)
        pt = CurveCoordinate(displacement: ptX, force: first.line.y(at: ptX))
        guard pt.displacement.isFinite, pt.force.isFinite else {
            return nil
        }

        let spanX = max(maxX - minX, 1e-9)
        let predictedPoint = predictedPt.flatMap {
            $0.isFinite ? pointAtForce(points: sorted, force: $0) : nil
        }
        return BilinearFit(
            kink: pt,
            detectedKink: detectedKink,
            predictedPoint: predictedPoint,
            firstLine: first.line,
            secondLine: second.line,
            firstStartX: minX,
            firstEndX: min(maxX, pt.displacement + spanX * 0.045),
            secondStartX: max(minX, pt.displacement - spanX * 0.025),
            secondEndX: maxX
        )
    }

    private static func fitWindow(_ points: [ResponseCurvePoint], start: Int, end: Int) -> FitWindow? {
        guard start >= 0, end < points.count, start <= end else {
            return nil
        }
        let window = Array(points[start...end])
        guard let line = linearFit(window) else {
            return nil
        }
        return FitWindow(
            start: start,
            end: end,
            line: line,
            r2: lineR2(window, line),
            mse: lineSse(window, line) / max(Double(window.count), 1)
        )
    }

    private static func bestInitialWindowForKink(_ points: [ResponseCurvePoint]) -> FitWindow? {
        let minLen = 3
        let maxLen = 5
        let halfIndex = Int(Double(points.count) * 0.5)
        let endMax = min(halfIndex - 1, maxLen - 1)
        var best: (window: FitWindow, sse: Double)?
        guard endMax >= minLen - 1 else {
            return nil
        }
        for end in (minLen - 1)...endMax {
            guard let candidate = fitWindow(points, start: 0, end: end) else {
                continue
            }
            let sse = lineSse(Array(points[0...end]), candidate.line)
            if best == nil || sse < best!.sse {
                best = (candidate, sse)
            }
        }
        return best?.window
    }

    private static func slidingSlopes(_ points: [ResponseCurvePoint], window: Int = KinkFit.kinkWin) -> [Double] {
        let adjustedWindow = window.isMultiple(of: 2) ? window + 1 : window
        let half = adjustedWindow / 2
        return points.indices.map { index in
            if index < half || index >= points.count - half {
                return Double.nan
            }
            return linearFit(Array(points[(index - half)...(index + half)]))?.slope ?? Double.nan
        }
    }

    private static func detectKinkStart(
        _ points: [ResponseCurvePoint],
        initialSlope: Double,
        startIndexMin: Int
    ) -> Int? {
        let slopes = slidingSlopes(points)
        let threshold = initialSlope * KinkFit.slopeDropFrac
        let limit = points.count - KinkFit.kinkHold
        guard limit >= max(startIndexMin, 0) else {
            return nil
        }
        for index in max(startIndexMin, 0)...limit {
            let segment = slopes[index..<(index + KinkFit.kinkHold)]
            if segment.allSatisfy({ $0.isFinite && $0 <= threshold }) {
                return index
            }
        }
        return nil
    }

    private static func bestInitialLinearWindow(_ points: [ResponseCurvePoint], endIndex: Int) -> FitWindow? {
        var best: FitWindow?
        let cappedEnd = min(max(Int(endIndex), 0), points.count - 1)
        for length in 3...KinkFit.initialMaxLen {
            let startMax = cappedEnd - (length - 1)
            guard startMax >= 0 else {
                continue
            }
            for start in 0...startMax {
                guard let candidate = fitWindow(points, start: start, end: start + length - 1) else {
                    continue
                }
                let bestLength = best.map { $0.end - $0.start + 1 } ?? 0
                if best == nil ||
                    candidate.r2 > best!.r2 ||
                    (abs(candidate.r2 - best!.r2) < 1e-12 && length > bestLength) {
                    best = candidate
                }
            }
        }
        return best
    }

    private static func bestSecondWindowPostKink(
        _ points: [ResponseCurvePoint],
        startAfterIndex: Int,
        kinkIndex: Int,
        firstLine: FittedLine,
        kinkX: Double
    ) -> FitWindow? {
        func sweep(strict: Bool, useMaxU: Bool) -> (window: FitWindow, score: Double)? {
            let startMin = max(Int(startAfterIndex), kinkIndex + 1)
            var startMax = points.count - KinkFit.secondLen
            if useMaxU {
                let lastWithinMax = points.enumerated().reduce(-1) { last, item in
                    item.element.displacement <= KinkFit.secondFitMaxU ? item.offset : last
                }
                if lastWithinMax >= 0 && lastWithinMax - (KinkFit.secondLen - 1) >= startMin {
                    startMax = min(startMax, lastWithinMax - (KinkFit.secondLen - 1))
                }
            }
            guard startMax >= startMin else {
                return nil
            }
            var best: (window: FitWindow, score: Double)?
            for start in startMin...startMax {
                guard let candidate = fitWindow(points, start: start, end: start + KinkFit.secondLen - 1),
                      let pt = lineIntersection(firstLine, candidate.line) else {
                    continue
                }
                if strict && pt.displacement > kinkX + KinkFit.preKinkEps {
                    continue
                }
                let distance = max(0, kinkX - pt.displacement)
                let score = candidate.mse + KinkFit.nearWeight * pow(abs(firstLine.slope), 2) * pow(distance, 2)
                if best == nil || score < best!.score {
                    best = (candidate, score)
                }
            }
            return best
        }
        return sweep(strict: true, useMaxU: true)?.window
            ?? sweep(strict: false, useMaxU: true)?.window
            ?? sweep(strict: true, useMaxU: false)?.window
            ?? sweep(strict: false, useMaxU: false)?.window
    }

    private static func bestFallbackSecondWindow(_ points: [ResponseCurvePoint], startAfterIndex: Int) -> FitWindow? {
        let startMin = max(0, startAfterIndex)
        let startMax = points.count - KinkFit.secondLen
        guard startMax >= startMin else {
            return nil
        }
        var best: FitWindow?
        for start in startMin...startMax {
            guard let candidate = fitWindow(points, start: start, end: start + KinkFit.secondLen - 1) else {
                continue
            }
            if best == nil || candidate.mse < best!.mse {
                best = candidate
            }
        }
        return best
    }

    private static func pointAtForce(points: [ResponseCurvePoint], force: Double) -> CurveCoordinate? {
        guard let first = points.first else { return nil }
        if force <= first.force {
            return CurveCoordinate(displacement: first.displacement, force: first.force)
        }
        for index in 1..<points.count {
            let previous = points[index - 1]
            let current = points[index]
            let low = min(previous.force, current.force)
            let high = max(previous.force, current.force)
            guard force >= low, force <= high else { continue }
            let delta = current.force - previous.force
            guard delta != 0 else {
                return CurveCoordinate(displacement: current.displacement, force: current.force)
            }
            let ratio = (force - previous.force) / delta
            return CurveCoordinate(
                displacement: previous.displacement + ratio * (current.displacement - previous.displacement),
                force: force
            )
        }
        guard let last = points.last else { return nil }
        return CurveCoordinate(displacement: last.displacement, force: last.force)
    }

    private static func linearFit(_ samples: [ResponseCurvePoint]) -> FittedLine? {
        let valid = samples.filter { $0.displacement.isFinite && $0.force.isFinite }
        guard valid.count >= 2 else { return nil }
        let meanX = valid.map(\.displacement).reduce(0, +) / Double(valid.count)
        let meanY = valid.map(\.force).reduce(0, +) / Double(valid.count)
        let numerator = valid.reduce(0.0) { sum, point in
            sum + (point.displacement - meanX) * (point.force - meanY)
        }
        let denominator = valid.reduce(0.0) { sum, point in
            sum + pow(point.displacement - meanX, 2)
        }
        guard abs(denominator) >= 1e-12 else { return nil }
        let slope = numerator / denominator
        return FittedLine(slope: slope, intercept: meanY - slope * meanX)
    }

    private static func lineSse(_ samples: [ResponseCurvePoint], _ line: FittedLine) -> Double {
        samples.reduce(0.0) { sum, point in
            let residual = point.force - line.y(at: point.displacement)
            return sum + residual * residual
        }
    }

    private static func lineR2(_ samples: [ResponseCurvePoint], _ line: FittedLine) -> Double {
        guard samples.count >= 2 else {
            return -.infinity
        }
        let meanY = samples.map(\.force).reduce(0, +) / Double(samples.count)
        let ssTotal = samples.reduce(0.0) { sum, point in
            sum + pow(point.force - meanY, 2)
        }
        if ssTotal <= 1e-18 {
            return lineSse(samples, line) <= 1e-18 ? 1 : 0
        }
        return 1 - lineSse(samples, line) / ssTotal
    }

    private static func rightUpperEnvelopeSlope(
        points: [ResponseCurvePoint],
        kinkX: Double,
        kinkForce: Double,
        proposedSlope: Double
    ) -> Double {
        var requiredSlope = proposedSlope
        for point in points {
            let deltaX = point.displacement - kinkX
            if deltaX > 1e-9 {
                requiredSlope = max(requiredSlope, (point.force - kinkForce) / deltaX)
            }
        }
        return max(requiredSlope * 1.015, proposedSlope)
    }

    private static func leftUpperEnvelopeSlope(
        points: [ResponseCurvePoint],
        kinkX: Double,
        kinkForce: Double,
        proposedSlope: Double
    ) -> Double {
        var cappedSlope = proposedSlope
        for point in points {
            let deltaX = kinkX - point.displacement
            if deltaX > 1e-9 {
                let upperSlope = (kinkForce - point.force) / deltaX
                if upperSlope.isFinite && upperSlope > 0 {
                    cappedSlope = min(cappedSlope, upperSlope * 0.985)
                }
            }
        }
        return max(cappedSlope, proposedSlope * 0.72)
    }

    private static func lineIntersection(_ firstLine: FittedLine, _ secondLine: FittedLine) -> CurveCoordinate? {
        let denominator = firstLine.slope - secondLine.slope
        guard denominator.isFinite, abs(denominator) >= 1e-9 else {
            return nil
        }
        let displacement = (secondLine.intercept - firstLine.intercept) / denominator
        let force = firstLine.y(at: displacement)
        guard displacement.isFinite, force.isFinite else {
            return nil
        }
        return CurveCoordinate(displacement: displacement, force: force)
    }
}

private enum KinkFit {
    static let kinkWin = 7
    static let slopeDropFrac = 0.65
    static let kinkHold = 3
    static let postSkipAfterKink = 2
    static let initialMaxLen = 7
    static let secondLen = 5
    static let preKinkEps = 1e-5
    static let nearWeight = 1.0
    static let secondFitMaxU = 0.3
}

private struct FitWindow {
    let start: Int
    let end: Int
    let line: FittedLine
    let r2: Double
    let mse: Double
}

private struct CurveCoordinate {
    let displacement: Double
    let force: Double
}

private struct FittedLine {
    let slope: Double
    let intercept: Double

    func y(at x: Double) -> Double {
        slope * x + intercept
    }
}

private struct BilinearFit {
    let kink: CurveCoordinate
    let detectedKink: CurveCoordinate?
    let predictedPoint: CurveCoordinate?
    let firstLine: FittedLine
    let secondLine: FittedLine
    let firstStartX: Double
    let firstEndX: Double
    let secondStartX: Double
    let secondEndX: Double
}

private extension Double {
    func takeIfFinite() -> Double? {
        isFinite ? self : nil
    }

    func axisTickText(smallValueDigits: Int) -> String {
        guard isFinite else { return "0" }
        let absolute = abs(self)
        let digits: Int
        if absolute >= 100 {
            digits = 0
        } else if absolute >= 10 {
            digits = 1
        } else if absolute >= 1 {
            digits = 2
        } else {
            digits = smallValueDigits
        }
        var text = String(format: "%.\(digits)f", self)
        while text.contains(".") && text.last == "0" {
            text.removeLast()
        }
        if text.last == "." {
            text.removeLast()
        }
        return text == "-0" ? "0" : text
    }
}
