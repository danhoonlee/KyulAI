import KyulAIInjectionCore
import SwiftUI

struct PressureChartView: View {
    let points: [SpruePressurePoint]
    let maxPressure: Double?
    @State private var selectedPoint: SpruePressurePoint?

    var body: some View {
        GeometryReader { proxy in
            let layout = chartLayout(size: proxy.size)
            ZStack {
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .fill(AppTheme.field)
                if points.count < 2 {
                    Text(ChartL10n.t("curve.empty"))
                        .font(.caption)
                        .foregroundStyle(AppTheme.muted)
                } else {
                    axisGrid(layout: layout)

                    Path { path in
                        for (index, point) in points.enumerated() {
                            let coordinate = layout.coordinate(time: point.timeS, pressure: point.spruePressureMPa)
                            if index == 0 {
                                path.move(to: coordinate)
                            } else {
                                path.addLine(to: coordinate)
                            }
                        }
                    }
                    .stroke(AppTheme.primary, style: StrokeStyle(lineWidth: 3, lineCap: .round, lineJoin: .round))

                    if let marker = markerPoint(layout: layout) {
                        Path { path in
                            path.move(to: CGPoint(x: marker.x, y: layout.top))
                            path.addLine(to: CGPoint(x: marker.x, y: layout.bottom))
                        }
                        .stroke(AppTheme.danger, style: StrokeStyle(lineWidth: 1.5, dash: [5, 5]))
                        Circle()
                            .fill(AppTheme.danger)
                            .frame(width: 9, height: 9)
                            .position(marker)
                    }

                    if let selectedPoint {
                        selectionOverlay(point: selectedPoint, layout: layout)
                    }

                    axisLabels(layout: layout)
                }
            }
            .contentShape(Rectangle())
            .gesture(
                DragGesture(minimumDistance: 0)
                    .onChanged { value in
                        selectedPoint = nearestPoint(to: value.location, layout: layout)
                    }
            )
        }
    }

    private func axisGrid(layout: ChartLayout) -> some View {
        ZStack {
            Path { path in
                path.move(to: CGPoint(x: layout.left, y: layout.bottom))
                path.addLine(to: CGPoint(x: layout.right, y: layout.bottom))
                path.move(to: CGPoint(x: layout.left, y: layout.top))
                path.addLine(to: CGPoint(x: layout.left, y: layout.bottom))

                for tick in layout.yTicks {
                    let y = layout.coordinate(time: 0, pressure: tick).y
                    path.move(to: CGPoint(x: layout.left, y: y))
                    path.addLine(to: CGPoint(x: layout.right, y: y))
                }

                for tick in layout.xTicks {
                    let x = layout.coordinate(time: tick, pressure: 0).x
                    path.move(to: CGPoint(x: x, y: layout.top))
                    path.addLine(to: CGPoint(x: x, y: layout.bottom))
                }
            }
            .stroke(AppTheme.muted.opacity(0.24), style: StrokeStyle(lineWidth: 1, dash: [3, 5]))

            Path { path in
                path.move(to: CGPoint(x: layout.left, y: layout.bottom))
                path.addLine(to: CGPoint(x: layout.right, y: layout.bottom))
                path.move(to: CGPoint(x: layout.left, y: layout.top))
                path.addLine(to: CGPoint(x: layout.left, y: layout.bottom))
            }
            .stroke(AppTheme.muted.opacity(0.55), lineWidth: 1)
        }
    }

    private func axisLabels(layout: ChartLayout) -> some View {
        ZStack {
            ForEach(Array(layout.xTicks.enumerated()), id: \.offset) { _, tick in
                Text(tick.axisText(digits: tick == 0 ? 0 : 1))
                    .font(.system(size: 10, weight: .semibold, design: .rounded).monospacedDigit())
                    .foregroundStyle(AppTheme.muted)
                    .position(x: layout.coordinate(time: tick, pressure: 0).x, y: layout.bottom + 14)
            }

            ForEach(Array(layout.yTicks.enumerated()), id: \.offset) { _, tick in
                Text(tick.axisText(digits: tick >= 10 ? 0 : 1))
                    .font(.system(size: 10, weight: .semibold, design: .rounded).monospacedDigit())
                    .foregroundStyle(AppTheme.muted)
                    .frame(width: layout.left - 8, alignment: .trailing)
                    .position(x: (layout.left - 8) / 2, y: layout.coordinate(time: 0, pressure: tick).y)
            }

            Text(ChartL10n.t("axis.time"))
                .font(.system(size: 10, weight: .bold, design: .rounded))
                .foregroundStyle(AppTheme.muted)
                .position(x: (layout.left + layout.right) / 2, y: layout.size.height - 8)

            Text(ChartL10n.t("axis.pressure"))
                .font(.system(size: 10, weight: .bold, design: .rounded))
                .foregroundStyle(AppTheme.muted)
                .position(x: layout.left + 38, y: layout.top - 9)
        }
    }

    private func markerPoint(layout: ChartLayout) -> CGPoint? {
        guard let maxPressure else { return nil }
        let closest = points.min { abs($0.spruePressureMPa - maxPressure) < abs($1.spruePressureMPa - maxPressure) }
        guard let closest else { return nil }
        return layout.coordinate(time: closest.timeS, pressure: closest.spruePressureMPa)
    }

    private func selectionOverlay(point: SpruePressurePoint, layout: ChartLayout) -> some View {
        let coordinate = layout.coordinate(time: point.timeS, pressure: point.spruePressureMPa)
        let labelX = min(max(coordinate.x + 66, layout.left + 72), layout.right - 72)
        let labelY = max(coordinate.y - 34, layout.top + 24)
        return ZStack {
            Path { path in
                path.move(to: CGPoint(x: coordinate.x, y: layout.top))
                path.addLine(to: CGPoint(x: coordinate.x, y: layout.bottom))
                path.move(to: CGPoint(x: layout.left, y: coordinate.y))
                path.addLine(to: CGPoint(x: layout.right, y: coordinate.y))
            }
            .stroke(AppTheme.ink.opacity(0.26), style: StrokeStyle(lineWidth: 1, dash: [4, 4]))

            Circle()
                .fill(.white)
                .frame(width: 14, height: 14)
                .overlay(Circle().stroke(AppTheme.primary, lineWidth: 3))
                .position(coordinate)

            VStack(alignment: .leading, spacing: 2) {
                Text("\(point.timeS.axisText(digits: 3)) s")
                Text("\(point.spruePressureMPa.axisText(digits: 2)) MPa")
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

    private func nearestPoint(to location: CGPoint, layout: ChartLayout) -> SpruePressurePoint? {
        points.min { lhs, rhs in
            abs(layout.coordinate(time: lhs.timeS, pressure: lhs.spruePressureMPa).x - location.x) <
                abs(layout.coordinate(time: rhs.timeS, pressure: rhs.spruePressureMPa).x - location.x)
        }
    }

    private func chartLayout(size: CGSize) -> ChartLayout {
        let maxTime = max(points.map(\.timeS).max() ?? 1, 0.000001)
        let maxPressureValue = max(points.map(\.spruePressureMPa).max() ?? 1, maxPressure ?? 1, 0.000001)
        return ChartLayout(size: size, maxTime: maxTime, maxPressure: maxPressureValue)
    }
}

private struct ChartLayout {
    let size: CGSize
    let maxTime: Double
    let maxPressure: Double

    var left: CGFloat { 46 }
    var right: CGFloat { max(left + 1, size.width - 14) }
    var top: CGFloat { 28 }
    var bottom: CGFloat { max(top + 1, size.height - 34) }
    var xTicks: [Double] { [0, maxTime / 2, maxTime] }
    var yTicks: [Double] { [0, maxPressure / 2, maxPressure] }

    func coordinate(time: Double, pressure: Double) -> CGPoint {
        let x = left + CGFloat(time / maxTime) * (right - left)
        let y = bottom - CGFloat(pressure / maxPressure) * (bottom - top)
        return CGPoint(x: x, y: y)
    }
}

private extension Double {
    func axisText(digits: Int) -> String {
        formatted(.number.precision(.fractionLength(0...digits)))
    }
}

private enum ChartL10n {
    static func t(_ key: String) -> String {
        NSLocalizedString(key, bundle: bundle, comment: "")
    }

    private static var bundle: Bundle {
        #if SWIFT_PACKAGE
        .module
        #else
        .main
        #endif
    }
}
