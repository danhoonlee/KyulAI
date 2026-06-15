import KyulAIDDLaminateCore
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
            Text("Double-Double Forecast")
                .font(.system(size: 32, weight: .black, design: .rounded))
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

            probabilityBars(result)
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

    private var errorBinding: Binding<Bool> {
        Binding(
            get: { viewModel.errorMessage != nil },
            set: { if !$0 { viewModel.errorMessage = nil } }
        )
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
}
