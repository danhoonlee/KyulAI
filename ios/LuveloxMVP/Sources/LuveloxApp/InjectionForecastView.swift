import KyulAIInjectionCore
import SwiftUI

struct InjectionForecastView: View {
    @StateObject private var viewModel = PredictionViewModel()

    private let baseURL = URL(string: InjectionDefaults.fallbackBaseURL)!

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
        .background(Color(red: 0.97, green: 0.98, blue: 0.99))
        .navigationTitle("Injection")
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
            Text("INJECTION MODULE")
                .font(.caption.weight(.heavy))
                .foregroundStyle(.teal)
            Text("Sprue Pressure Forecast")
                .font(.system(size: 32, weight: .black, design: .rounded))
            Text("Run Moldex3D-style sprue pressure and filling pressure prediction directly inside Luvelox.")
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

            HStack(spacing: 12) {
                pickerBlock("Geometry", selection: Binding(
                    get: { viewModel.geometryID },
                    set: { viewModel.selectGeometry(id: $0) }
                ), values: viewModel.geometries.map(\.id).ifEmpty(["G01"]))

                pickerBlock("Process", selection: Binding(
                    get: { viewModel.processID },
                    set: { viewModel.selectProcess(id: $0) }
                ), values: viewModel.processes.map(\.id).ifEmpty(["P01"]))
            }

            modelPicker(
                title: "Sprue model",
                selection: Binding(get: { viewModel.selectedSprueModelKey }, set: { viewModel.selectSprueModel(key: $0) }),
                models: viewModel.sprueModels
            )

            modelPicker(
                title: "Filling model",
                selection: Binding(get: { viewModel.selectedFillingModelKey }, set: { viewModel.selectFillingModel(key: $0) }),
                models: viewModel.fillingModels
            )

            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                compactValue("L", viewModel.Lmm, "mm")
                compactValue("W", viewModel.Wmm, "mm")
                compactValue("t", viewModel.tmm, "mm")
                compactValue("D", viewModel.Dmm, "mm")
                compactValue("Melt", viewModel.meltTempC, "C")
                compactValue("Mold", viewModel.moldTempC, "C")
                compactValue("Injection", viewModel.injectionTimeS, "s")
                compactValue("Packing", viewModel.packingPressureMPa, "MPa")
            }

            Button {
                Task { await viewModel.predict(baseURL: baseURL) }
            } label: {
                HStack {
                    Text(viewModel.isPredicting ? "Predicting" : "Predict pressure")
                    Spacer()
                    Image(systemName: "gauge.with.dots.needle.bottom.50percent")
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

    private func pickerBlock(_ title: String, selection: Binding<String>, values: [String]) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(.caption.weight(.bold))
                .foregroundStyle(.secondary)
            Picker(title, selection: selection) {
                ForEach(values, id: \.self) { value in
                    Text(value).tag(value)
                }
            }
            .pickerStyle(.menu)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 12)
            .frame(height: 46)
            .background(Color(red: 0.96, green: 0.98, blue: 0.99), in: RoundedRectangle(cornerRadius: 8))
        }
    }

    private func modelPicker(title: String, selection: Binding<String>, models: [ModelInfo]) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(.caption.weight(.bold))
                .foregroundStyle(.secondary)
            Picker(title, selection: selection) {
                ForEach(models) { model in
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

    private func compactValue(_ title: String, _ value: String, _ unit: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.caption.weight(.bold))
                .foregroundStyle(.secondary)
            Text("\(value) \(unit)")
                .font(.subheadline.monospacedDigit().weight(.bold))
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(10)
        .background(Color(red: 0.96, green: 0.98, blue: 0.99), in: RoundedRectangle(cornerRadius: 8))
    }

    private func resultCard(_ result: SpruePressurePredictionResult) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(result.predictedMaxPressureMPa.metricText(digits: 2))
                        .font(.system(size: 34, weight: .black, design: .rounded))
                    Text("Max sprue pressure MPa")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Text("\(result.predictedMaxTimeS.metricText(digits: 3)) s")
                    .font(.headline.monospacedDigit())
                    .foregroundStyle(.green)
            }

            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                metric("Sprue model", result.displayModelLabel)
                metric("Filling model", result.displayFillingModelLabel)
                metric("Curve points", "\(result.curve.count)")
                metric("Fill bins", "\(result.bestFillingPressure?.bins.count ?? 0)")
            }

            if let filling = result.bestFillingPressure {
                fillingSummary(filling)
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
                .font(.headline)
                .lineLimit(2)
                .minimumScaleFactor(0.75)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(Color(red: 0.96, green: 0.98, blue: 0.99), in: RoundedRectangle(cornerRadius: 8))
    }

    private func fillingSummary(_ summary: FillingPressureSummary) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Filling pressure")
                .font(.headline)
            ForEach(summary.bins.prefix(5)) { bin in
                VStack(alignment: .leading, spacing: 5) {
                    HStack {
                        Text("Group \(bin.group)")
                        Spacer()
                        Text("\(bin.volumeRatioPct.metricText(digits: 1))%")
                            .monospacedDigit()
                    }
                    .font(.caption.weight(.bold))
                    GeometryReader { proxy in
                        ZStack(alignment: .leading) {
                            Capsule().fill(Color.gray.opacity(0.16))
                            Capsule()
                                .fill(Color.teal)
                                .frame(width: proxy.size.width * max(0, min(bin.volumeRatioPct / 100.0, 1)))
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

private extension Array where Element == String {
    func ifEmpty(_ fallback: [String]) -> [String] {
        isEmpty ? fallback : self
    }
}

private extension Double {
    func metricText(digits: Int) -> String {
        formatted(.number.precision(.fractionLength(0...digits)))
    }
}
