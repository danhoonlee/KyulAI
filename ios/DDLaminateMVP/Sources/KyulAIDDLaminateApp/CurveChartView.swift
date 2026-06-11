import KyulAIDDLaminateCore
import SwiftUI

struct CurveChartView: View {
    let points: [ResponseCurvePoint]
    let predictedPt: Double?
    @State private var selectedPoint: ResponseCurvePoint?
    @State private var gestureInitialPoint: ResponseCurvePoint?
    @State private var isTrackingGesture = false
    @State private var gestureDidMove = false

    init(points: [ResponseCurvePoint], predictedPt: Double? = nil) {
        self.points = points
        self.predictedPt = predictedPt
    }

    var body: some View {
        GeometryReader { proxy in
            ZStack(alignment: .bottomLeading) {
                RoundedRectangle(cornerRadius: 14)
                    .fill(AppTheme.field)
                Canvas { context, size in
                    guard let layout = ChartLayout(points: points, size: size, predictedPt: predictedPt) else { return }
                    if let bilinearFit = layout.bilinearFit {
                        drawBilinearFit(context: context, layout: layout, fit: bilinearFit)
                    }
                    context.stroke(
                        layout.path,
                        with: .linearGradient(
                            Gradient(colors: [AppTheme.primary, AppTheme.accent.opacity(0.86)]),
                            startPoint: CGPoint(x: layout.plotFrame.minX, y: layout.plotFrame.midY),
                            endPoint: CGPoint(x: layout.plotFrame.maxX, y: layout.plotFrame.midY)
                        ),
                        style: StrokeStyle(lineWidth: 3, lineCap: .round, lineJoin: .round)
                    )

                    if let bilinearFit = layout.bilinearFit {
                        drawPtKink(context: context, layout: layout, fit: bilinearFit)
                    }
                }
                if let layout = ChartLayout(points: points, size: proxy.size, predictedPt: predictedPt), let selectedPoint {
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
            .gesture(
                DragGesture(minimumDistance: 0)
                    .onChanged { value in
                        if let layout = ChartLayout(points: points, size: proxy.size, predictedPt: predictedPt) {
                            if !isTrackingGesture {
                                gestureInitialPoint = selectedPoint
                                isTrackingGesture = true
                                gestureDidMove = false
                            }
                            if abs(value.translation.width) > 6 || abs(value.translation.height) > 6 {
                                gestureDidMove = true
                            }
                            selectedPoint = layout.nearestPoint(to: value.location)
                        }
                    }
                    .onEnded { value in
                        if let layout = ChartLayout(points: points, size: proxy.size, predictedPt: predictedPt) {
                            let nearestPoint = layout.nearestPoint(to: value.location)
                            if !gestureDidMove && gestureInitialPoint != nil {
                                selectedPoint = nil
                            } else {
                                selectedPoint = nearestPoint
                            }
                        }
                        gestureInitialPoint = nil
                        isTrackingGesture = false
                        gestureDidMove = false
                    }
            )
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(L10n.f("curve.accessibility", points.count))
    }

    private func drawBilinearFit(context: GraphicsContext, layout: ChartLayout, fit: BilinearFit) {
        var slopePath = Path()
        slopePath.move(to: layout.coordinate(displacement: fit.firstStartX, force: fit.firstLine.y(at: fit.firstStartX)))
        slopePath.addLine(to: layout.coordinate(displacement: fit.firstEndX, force: fit.firstLine.y(at: fit.firstEndX)))
        slopePath.move(to: layout.coordinate(displacement: fit.secondStartX, force: fit.secondLine.y(at: fit.secondStartX)))
        slopePath.addLine(to: layout.coordinate(displacement: fit.secondEndX, force: fit.secondLine.y(at: fit.secondEndX)))
        context.stroke(
            slopePath,
            with: .color(AppTheme.danger.opacity(0.82)),
            style: StrokeStyle(lineWidth: 1.4, lineCap: .round, lineJoin: .round, dash: [6, 4])
        )

        let kink = layout.coordinate(displacement: fit.kink.displacement, force: fit.kink.force)
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
        let kink = layout.coordinate(displacement: fit.kink.displacement, force: fit.kink.force)
        let dot = CGRect(x: kink.x - 6, y: kink.y - 6, width: 12, height: 12)
        context.fill(Path(ellipseIn: dot), with: .color(AppTheme.danger))
        context.stroke(Path(ellipseIn: dot), with: .color(.white), lineWidth: 2)
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

private struct ChartLayout {
    let path: Path
    let plotFrame: CGRect
    let bilinearFit: BilinearFit?
    private let points: [ResponseCurvePoint]
    private let minX: Double
    private let maxX: Double
    private let minY: Double
    private let maxY: Double

    init?(points: [ResponseCurvePoint], size: CGSize, predictedPt: Double?) {
        let inset: CGFloat = 28
        let plotFrame = CGRect(
            x: inset,
            y: inset,
            width: max(1, size.width - inset * 2),
            height: max(1, size.height - inset * 2)
        )
        guard points.count > 1,
              let minX = points.map(\.displacement).min(),
              let maxX = points.map(\.displacement).max(),
              let minY = points.map(\.force).min(),
              let maxY = points.map(\.force).max(),
              maxX > minX,
              maxY > minY else {
            return nil
        }

        let bilinearFit = Self.buildBilinearFit(points: points, predictedPt: predictedPt)
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
        }
        let adjustedMinY = yValues.min() ?? minY
        let adjustedMaxY = (yValues.max() ?? maxY) * 1.06

        var path = Path()
        for (index, point) in points.enumerated() {
            let x = plotFrame.minX + (point.displacement - minX) / (maxX - minX) * plotFrame.width
            let y = plotFrame.maxY - (point.force - adjustedMinY) / (adjustedMaxY - adjustedMinY) * plotFrame.height
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
        self.points = points
        self.minX = minX
        self.maxX = maxX
        self.minY = adjustedMinY
        self.maxY = adjustedMaxY
    }

    func ptMarker(force predictedPt: Double?) -> CGPoint? {
        guard let predictedPt,
              predictedPt.isFinite,
              let curvePoint = interpolatedPoint(atForce: predictedPt) else {
            return nil
        }
        let x = plotFrame.minX + (curvePoint.displacement - minX) / (maxX - minX) * plotFrame.width
        let y = plotFrame.maxY - (curvePoint.force - minY) / (maxY - minY) * plotFrame.height
        return CGPoint(x: x, y: y)
    }

    func coordinate(displacement: Double, force: Double) -> CGPoint {
        let x = plotFrame.minX + (displacement - minX) / (maxX - minX) * plotFrame.width
        let y = plotFrame.maxY - (force - minY) / (maxY - minY) * plotFrame.height
        return CGPoint(x: x, y: y)
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

    private static func buildBilinearFit(points: [ResponseCurvePoint], predictedPt: Double?) -> BilinearFit? {
        guard let predictedPt,
              predictedPt.isFinite,
              let ptOnCurve = pointAtForce(points: points, force: predictedPt),
              let minX = points.map(\.displacement).min(),
              let maxX = points.map(\.displacement).max() else {
            return nil
        }
        let spanX = max(maxX - minX, 1e-9)
        let firstFitSamples = points.filter { point in
            point.displacement > minX + spanX * 0.01 &&
                point.displacement <= max(ptOnCurve.displacement * 0.92, minX + spanX * 0.18) &&
                point.force <= predictedPt * 0.82
        }
        let firstFallbackEnd = max(8, Int(Double(points.count) * 0.28))
        let firstSamples = firstFitSamples.count >= 4
            ? firstFitSamples
            : Array(points.dropFirst().prefix(max(0, min(firstFallbackEnd - 1, points.count - 1))))
        guard let firstFit = linearFit(firstSamples) else { return nil }

        let tailStart = max(ptOnCurve.displacement + spanX * 0.08, minX + spanX * 0.58)
        let secondFitSamples = points.filter { $0.displacement >= tailStart }
        let secondFallbackStart = max(0, Int(Double(points.count) * 0.72))
        let secondSamples = secondFitSamples.count >= 4
            ? secondFitSamples
            : Array(points.dropFirst(secondFallbackStart))
        guard let secondFit = linearFit(secondSamples),
              firstFit.slope > 0,
              secondFit.slope > 0 else {
            return nil
        }

        var kinkX = (predictedPt - firstFit.intercept) / firstFit.slope
        let minKinkX = minX + spanX * 0.08
        let maxKinkX = minX + spanX * 0.78
        if !kinkX.isFinite || kinkX < minKinkX || kinkX > maxKinkX {
            kinkX = ptOnCurve.displacement
        }

        let leftEnvelopeSamples = points.filter {
            $0.displacement < kinkX - spanX * 0.006 && $0.force <= predictedPt
        }
        let rightEnvelopeSamples = points.filter {
            $0.displacement > kinkX + spanX * 0.006 && $0.force >= predictedPt * 0.96
        }
        let firstSlope = leftUpperEnvelopeSlope(
            points: leftEnvelopeSamples,
            kinkX: kinkX,
            kinkForce: predictedPt,
            proposedSlope: firstFit.slope
        )
        let secondSlope = rightUpperEnvelopeSlope(
            points: rightEnvelopeSamples,
            kinkX: kinkX,
            kinkForce: predictedPt,
            proposedSlope: secondFit.slope
        )

        return BilinearFit(
            kink: CurveCoordinate(displacement: kinkX, force: predictedPt),
            firstLine: FittedLine(slope: firstSlope, intercept: predictedPt - firstSlope * kinkX),
            secondLine: FittedLine(slope: secondSlope, intercept: predictedPt - secondSlope * kinkX),
            firstStartX: minX,
            firstEndX: min(maxX, kinkX + spanX * 0.045),
            secondStartX: max(minX, kinkX - spanX * 0.025),
            secondEndX: maxX
        )
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
    let firstLine: FittedLine
    let secondLine: FittedLine
    let firstStartX: Double
    let firstEndX: Double
    let secondStartX: Double
    let secondEndX: Double
}
