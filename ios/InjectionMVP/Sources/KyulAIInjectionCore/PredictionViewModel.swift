import Foundation

public enum ConnectionState: Equatable, Sendable {
    case idle
    case checking
    case ready(sprueModelAvailable: Bool)
    case failed(String)
}

@MainActor
public final class PredictionViewModel: ObservableObject {
    private let apiClient: InjectionAPIClientProtocol
    private let userDefaults: UserDefaults
    private let recentRunsKey = "injection.recentRuns.v1"

    @Published public var geometryID = "G01"
    @Published public var processID = "P01"
    @Published public var Lmm = "154.01"
    @Published public var Wmm = "97.42"
    @Published public var tmm = "2.207"
    @Published public var Dmm = "17.61"
    @Published public var Rmm = "8.805"
    @Published public var gateType = "edge_gate"
    @Published public var gateWidth = "10.0"
    @Published public var gateHeight = "1.5"
    @Published public var meltTempC = "226.1"
    @Published public var moldTempC = "61.7"
    @Published public var injectionTimeS = "2.47"
    @Published public var packingPressureMPa = "69.0"
    @Published public var packingTimeS = "4.731"
    @Published public var connectionState: ConnectionState = .idle
    @Published public var sprueModels: [ModelInfo] = []
    @Published public var fillingModels: [ModelInfo] = []
    @Published public var selectedSprueModelKey = InjectionDefaults.sprueModelKey
    @Published public var selectedFillingModelKey = InjectionDefaults.fillingModelKey
    @Published public var sprueModel: ModelInfo?
    @Published public var fillingModel: ModelInfo?
    @Published public var geometries: [DoeOption] = []
    @Published public var processes: [DoeOption] = []
    @Published public var result: SpruePressurePredictionResult?
    @Published public var errorMessage: String?
    @Published public var isPredicting = false
    @Published public var assistantQuestion = "Why is melt temperature influential in this prediction?"
    @Published public private(set) var assistantAnswer: RagAnswerResponse?
    @Published public private(set) var assistantErrorMessage: String?
    @Published public private(set) var isAskingAssistant = false
    @Published public private(set) var recentRuns: [InjectionRecentRun] = []

    public init(
        apiClient: InjectionAPIClientProtocol = InjectionAPIClient(),
        userDefaults: UserDefaults = .standard
    ) {
        self.apiClient = apiClient
        self.userDefaults = userDefaults
        self.recentRuns = Self.loadRecentRuns(from: userDefaults, key: recentRunsKey)
    }

    public var canPredict: Bool {
        !isPredicting && connectionState != .checking
    }

    public func resetReadiness() {
        connectionState = .idle
        sprueModels = []
        fillingModels = []
        sprueModel = nil
        fillingModel = nil
        result = nil
        errorMessage = nil
        assistantAnswer = nil
        assistantErrorMessage = nil
    }

    public func checkConnection(baseURL: URL) async {
        connectionState = .checking
        errorMessage = nil
        do {
            _ = try await apiClient.health(baseURL: baseURL)
            let models = try await apiClient.models(baseURL: baseURL)
            let doe = try await apiClient.doe(baseURL: baseURL)
            sprueModels = models.spruePressureModels
            fillingModels = models.fillingPressureModels
            normalizeModelSelection()
            geometries = doe.geometries
            processes = doe.processes
            if let geometry = geometries.first(where: { $0.id == geometryID }) ?? geometries.first {
                applyGeometry(geometry)
            }
            if let process = processes.first(where: { $0.id == processID }) ?? processes.first {
                applyProcess(process)
            }
            connectionState = .ready(sprueModelAvailable: sprueModel?.available == true && fillingModel?.available == true)
        } catch {
            connectionState = .failed(error.localizedDescription)
            sprueModels = []
            fillingModels = []
            sprueModel = nil
            fillingModel = nil
        }
    }

    public func selectSprueModel(key: String) {
        selectedSprueModelKey = key
        sprueModel = sprueModels.first { $0.key == key }
        result = nil
        assistantAnswer = nil
        assistantErrorMessage = nil
        updateReadyStateIfNeeded()
    }

    public func selectFillingModel(key: String) {
        selectedFillingModelKey = key
        fillingModel = fillingModels.first { $0.key == key }
        result = nil
        assistantAnswer = nil
        assistantErrorMessage = nil
        updateReadyStateIfNeeded()
    }

    public func selectGeometry(id: String) {
        geometryID = id
        if let geometry = geometries.first(where: { $0.id == id }) {
            applyGeometry(geometry)
        }
    }

    public func selectProcess(id: String) {
        processID = id
        if let process = processes.first(where: { $0.id == id }) {
            applyProcess(process)
        }
    }

    public func applyRecentRun(_ run: InjectionRecentRun) {
        selectedSprueModelKey = run.sprueModelKey
        selectedFillingModelKey = run.fillingModelKey
        sprueModel = sprueModels.first { $0.key == run.sprueModelKey } ?? sprueModel
        fillingModel = fillingModels.first { $0.key == run.fillingModelKey } ?? fillingModel
        geometryID = run.geometryID
        processID = run.processID
        Lmm = run.Lmm
        Wmm = run.Wmm
        tmm = run.tmm
        Dmm = run.Dmm
        Rmm = run.Rmm
        gateType = run.gateType
        gateWidth = run.gateWidth
        gateHeight = run.gateHeight
        meltTempC = run.meltTempC
        moldTempC = run.moldTempC
        injectionTimeS = run.injectionTimeS
        packingPressureMPa = run.packingPressureMPa
        packingTimeS = run.packingTimeS
        result = nil
        updateReadyStateIfNeeded()
    }

    public func clearRecentRuns() {
        recentRuns = []
        userDefaults.removeObject(forKey: recentRunsKey)
    }

    public func predict(baseURL: URL) async {
        if sprueModels.isEmpty || fillingModels.isEmpty {
            await checkConnection(baseURL: baseURL)
        }
        guard sprueModel?.available == true else {
            errorMessage = "The selected sprue model (\(selectedSprueModelKey)) is unavailable."
            return
        }
        guard fillingModel?.available == true else {
            errorMessage = "The selected filling model (\(selectedFillingModelKey)) is unavailable."
            return
        }
        guard let request = makeRequest() else {
            errorMessage = "Enter valid positive geometry and process values."
            return
        }

        isPredicting = true
        errorMessage = nil
        defer { isPredicting = false }

        do {
            result = try await apiClient.predictSpruePressure(baseURL: baseURL, request: request)
            assistantAnswer = nil
            assistantErrorMessage = nil
            saveRecentRun(from: request)
        } catch {
            errorMessage = "Prediction failed: \(error.localizedDescription)"
        }
    }

    public func askAssistant(baseURL: URL, language: String, question explicitQuestion: String? = nil) async {
        guard let result else {
            assistantErrorMessage = "Run a prediction before asking the assistant."
            return
        }
        let query = (explicitQuestion ?? assistantQuestion).trimmingCharacters(in: .whitespacesAndNewlines)
        guard query.count >= 2 else {
            assistantErrorMessage = "Enter a question."
            return
        }
        assistantQuestion = query
        isAskingAssistant = true
        assistantErrorMessage = nil
        defer { isAskingAssistant = false }
        do {
            assistantAnswer = try await apiClient.answerRag(
                baseURL: baseURL,
                request: RagAnswerRequest(
                    query: query,
                    topK: 3,
                    useLLM: true,
                    language: language,
                    predictionContext: assistantPredictionContext(for: result)
                )
            )
        } catch {
            assistantErrorMessage = "Assistant failed: \(error.localizedDescription)"
        }
    }

    private func applyGeometry(_ geometry: DoeOption) {
        geometryID = geometry.id
        Lmm = geometry.double("L_mm")?.text(digits: 3) ?? Lmm
        Wmm = geometry.double("W_mm")?.text(digits: 3) ?? Wmm
        tmm = geometry.double("t_mm")?.text(digits: 3) ?? tmm
        Dmm = geometry.double("D_mm")?.text(digits: 3) ?? Dmm
        Rmm = geometry.double("R_mm")?.text(digits: 3) ?? Rmm
        gateType = geometry.string("gate_type") ?? gateType
        gateWidth = geometry.double("gate_size_width_mm")?.text(digits: 3) ?? gateWidth
        gateHeight = geometry.double("gate_size_height_mm")?.text(digits: 3) ?? gateHeight
    }

    private func applyProcess(_ process: DoeOption) {
        processID = process.id
        meltTempC = process.double("melt_temp_C")?.text(digits: 2) ?? meltTempC
        moldTempC = process.double("mold_temp_C")?.text(digits: 2) ?? moldTempC
        injectionTimeS = process.double("injection_time_s")?.text(digits: 3) ?? injectionTimeS
        packingPressureMPa = process.double("packing_pressure_MPa")?.text(digits: 2) ?? packingPressureMPa
        packingTimeS = process.double("packing_time_s")?.text(digits: 3) ?? packingTimeS
    }

    private func normalizeModelSelection() {
        if sprueModels.first(where: { $0.key == selectedSprueModelKey && $0.available }) == nil,
           let fallback = sprueModels.first(where: { $0.key == InjectionDefaults.sprueModelKey && $0.available }) ?? sprueModels.first(where: \.available) ?? sprueModels.first {
            selectedSprueModelKey = fallback.key
        }
        if fillingModels.first(where: { $0.key == selectedFillingModelKey && $0.available }) == nil,
           let fallback = fillingModels.first(where: { $0.key == InjectionDefaults.fillingModelKey && $0.available }) ?? fillingModels.first(where: \.available) ?? fillingModels.first {
            selectedFillingModelKey = fallback.key
        }
        sprueModel = sprueModels.first { $0.key == selectedSprueModelKey }
        fillingModel = fillingModels.first { $0.key == selectedFillingModelKey }
    }

    private func updateReadyStateIfNeeded() {
        guard case .ready = connectionState else { return }
        connectionState = .ready(sprueModelAvailable: sprueModel?.available == true && fillingModel?.available == true)
    }

    private func makeRequest() -> SpruePressurePredictionRequest? {
        guard
            let L = Double(Lmm), L > 0,
            let W = Double(Wmm), W > 0,
            let t = Double(tmm), t > 0,
            let D = Double(Dmm), D > 0,
            let gateWidthValue = Double(gateWidth), gateWidthValue > 0,
            let gateHeightValue = Double(gateHeight), gateHeightValue > 0,
            let melt = Double(meltTempC),
            let mold = Double(moldTempC),
            let injectionTime = Double(injectionTimeS), injectionTime > 0,
            let packingPressure = Double(packingPressureMPa), packingPressure > 0,
            let packingTime = Double(packingTimeS), packingTime > 0
        else {
            return nil
        }
        return SpruePressurePredictionRequest(
            geometryID: geometryID,
            processID: processID,
            model: selectedSprueModelKey,
            fillingModel: selectedFillingModelKey,
            Lmm: L,
            Wmm: W,
            tmm: t,
            Dmm: D,
            Rmm: Double(Rmm),
            gateType: gateType,
            gateSizeWidthMm: gateWidthValue,
            gateSizeHeightMm: gateHeightValue,
            meltTempC: melt,
            moldTempC: mold,
            injectionTimeS: injectionTime,
            packingPressureMPa: packingPressure,
            packingTimeS: packingTime
        )
    }

    private func saveRecentRun(from request: SpruePressurePredictionRequest) {
        let run = InjectionRecentRun(
            geometryID: request.geometryID ?? geometryID,
            processID: request.processID ?? processID,
            sprueModelKey: request.model,
            fillingModelKey: request.fillingModel,
            Lmm: Lmm,
            Wmm: Wmm,
            tmm: tmm,
            Dmm: Dmm,
            Rmm: Rmm,
            gateType: gateType,
            gateWidth: gateWidth,
            gateHeight: gateHeight,
            meltTempC: meltTempC,
            moldTempC: moldTempC,
            injectionTimeS: injectionTimeS,
            packingPressureMPa: packingPressureMPa,
            packingTimeS: packingTimeS,
            createdAt: Date()
        )
        recentRuns = ([run] + recentRuns.filter { $0.signature != run.signature }).prefix(5).map { $0 }
        if let data = try? JSONEncoder().encode(recentRuns) {
            userDefaults.set(data, forKey: recentRunsKey)
        }
    }

    private func assistantPredictionContext(for result: SpruePressurePredictionResult) -> JSONValue {
        var payload: [String: JSONValue] = [
            "mode": .string("Injection Forecast"),
            "inputs": .object(result.inputs),
            "model_key": .string(result.modelKey),
            "model_label": .string(result.displayModelLabel),
            "filling_model_key": .string(result.fillingModelKey),
            "filling_model_label": .string(result.displayFillingModelLabel),
            "predicted_max_pressure_MPa": .double(result.predictedMaxPressureMPa),
            "predicted_max_time_s": .double(result.predictedMaxTimeS),
            "curve_points": .double(Double(result.curve.count)),
        ]
        if let fillingMax = result.bestFillingPressure?.stats["max_MPa"] {
            payload["predicted_filling_max_MPa"] = .double(fillingMax)
        }
        if let xai = result.xai {
            payload["xai"] = .object([
                "title": .string(xai.title),
                "summary": .string(xai.summary),
                "method": .string(xai.method),
                "feature_set": .string(xai.featureSet),
                "top_features": .array(xai.topFeatures.map { feature in
                    .object([
                        "name": .string(feature.name),
                        "label": .string(feature.label),
                        "category": .string(feature.category),
                        "importance": .double(feature.importance),
                        "local_sensitivity": .double(feature.localSensitivity),
                        "local_value": feature.localValue.map(JSONValue.double) ?? .null,
                        "perturbation": .string(feature.perturbation),
                        "explanation": .string(feature.explanation),
                    ])
                }),
            ])
        }
        return .object(payload)
    }

    private static func loadRecentRuns(from userDefaults: UserDefaults, key: String) -> [InjectionRecentRun] {
        guard let data = userDefaults.data(forKey: key),
              let runs = try? JSONDecoder().decode([InjectionRecentRun].self, from: data)
        else {
            return []
        }
        return Array(runs.prefix(5))
    }
}

public struct InjectionRecentRun: Identifiable, Codable, Equatable, Sendable {
    public var id: String { signature }
    public let geometryID: String
    public let processID: String
    public let sprueModelKey: String
    public let fillingModelKey: String
    public let Lmm: String
    public let Wmm: String
    public let tmm: String
    public let Dmm: String
    public let Rmm: String
    public let gateType: String
    public let gateWidth: String
    public let gateHeight: String
    public let meltTempC: String
    public let moldTempC: String
    public let injectionTimeS: String
    public let packingPressureMPa: String
    public let packingTimeS: String
    public let createdAt: Date

    public var displayTitle: String {
        "\(geometryID) / \(processID)"
    }

    public var displaySubtitle: String {
        "\(meltTempC)C, \(injectionTimeS)s, \(packingPressureMPa)MPa"
    }

    fileprivate var signature: String {
        [
            geometryID, processID, sprueModelKey, fillingModelKey,
            Lmm, Wmm, tmm, Dmm, Rmm, gateType, gateWidth, gateHeight,
            meltTempC, moldTempC, injectionTimeS, packingPressureMPa, packingTimeS
        ].joined(separator: "|")
    }
}

private extension Double {
    func text(digits: Int) -> String {
        formatted(.number.precision(.fractionLength(0...digits)))
    }
}
