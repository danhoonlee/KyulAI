import Foundation

public enum ConnectionState: Equatable, Sendable {
    case idle
    case checking
    case ready(responseSurrogateAvailable: Bool)
    case failed(String)
}

@MainActor
public final class PredictionViewModel: ObservableObject {
    private let apiClient: DDLaminateAPIClientProtocol
    private let fixtureLoader: FixtureLoading
    private let userDefaults: UserDefaults
    private let recentRunsKey = "ddLaminate.recentRuns.v1"

    @Published public var theta1 = "30"
    @Published public var theta2 = "-30"
    @Published public var selectedCase: DDLaminateCase = .case2
    @Published public var connectionState: ConnectionState = .idle
    @Published public var responseModels: [ModelInfo] = []
    @Published public var u3PtModels: [ModelInfo] = []
    @Published public var selectedResponseModelKey = DDLaminateDefaults.responseModelKey
    @Published public var selectedU3PtModelKey = DDLaminateDefaults.u3PtModelKey
    @Published public var responseModel: ModelInfo?
    @Published public var u3PtModel: ModelInfo?
    @Published public var result: ResponsePredictionResult?
    @Published public var u3PtResult: U3PtPredictionResult?
    @Published public var errorMessage: String?
    @Published public var isPredicting = false
    @Published public var isPredictingU3Pt = false
    @Published public private(set) var recentRuns: [DDLaminateRecentRun] = []

    public var responseForecastRecentRuns: [DDLaminateRecentRun] {
        recentRuns.filter { $0.kind == .responseForecast }
    }

    public var u3ForecastRecentRuns: [DDLaminateRecentRun] {
        recentRuns.filter { $0.kind == .u3Forecast }
    }

    public init(
        apiClient: DDLaminateAPIClientProtocol = DDLaminateAPIClient(),
        fixtureLoader: FixtureLoading = BundleFixtureLoader(),
        userDefaults: UserDefaults = .standard
    ) {
        self.apiClient = apiClient
        self.fixtureLoader = fixtureLoader
        self.userDefaults = userDefaults
        self.recentRuns = Self.loadRecentRuns(from: userDefaults, key: recentRunsKey)
    }

    public var canPredict: Bool {
        !isPredicting && connectionState != .checking
    }

    public var canPredictU3Pt: Bool {
        !isPredictingU3Pt && connectionState != .checking
    }

    public func resetReadiness() {
        connectionState = .idle
        responseModels = []
        u3PtModels = []
        responseModel = nil
        u3PtModel = nil
        result = nil
        u3PtResult = nil
        errorMessage = nil
    }

    public func checkConnection(baseURL: URL) async {
        connectionState = .checking
        errorMessage = nil
        do {
            _ = try await apiClient.health(baseURL: baseURL)
            let models = try await apiClient.models(baseURL: baseURL)
            responseModels = Self.optimalResponseModels(from: models.responseModels)
            u3PtModels = Self.optimalU3PtModels(from: models.u3PtModels)
            normalizeModelSelection()
            normalizeU3PtModelSelection()
            connectionState = .ready(responseSurrogateAvailable: responseModel?.available == true)
        } catch {
            connectionState = .failed(error.localizedDescription)
            responseModels = []
            u3PtModels = []
            responseModel = nil
            u3PtModel = nil
        }
    }

    public func selectResponseModel(key: String) {
        selectedResponseModelKey = key
        responseModel = responseModels.first { $0.key == key }
        result = nil
        updateReadyStateIfNeeded()
    }

    public func selectU3PtModel(key: String) {
        selectedU3PtModelKey = key
        u3PtModel = u3PtModels.first { $0.key == key }
        u3PtResult = nil
    }

    public func predict(baseURL: URL) async {
        guard let theta1Value = normalizedThetaValue(theta1), let theta2Value = normalizedThetaValue(theta2) else {
            errorMessage = "Enter numeric theta values."
            return
        }
        theta1 = Self.thetaInputString(theta1Value)
        theta2 = Self.thetaInputString(theta2Value)
        if responseModels.isEmpty {
            await checkConnection(baseURL: baseURL)
        }
        guard responseModel?.available == true else {
            errorMessage = "The selected model (\(DDLaminateModelDisplayLabel.cleanKey(selectedResponseModelKey))) is unavailable. Check the API base URL or server."
            return
        }
        let request = ResponsePredictionRequest(
            theta1: theta1Value,
            theta2: theta2Value,
            case: selectedCase,
            model: selectedResponseModelKey
        )
        isPredicting = true
        errorMessage = nil
        defer { isPredicting = false }

        do {
            result = try await apiClient.predictResponse(baseURL: baseURL, request: request)
            if let result {
                saveRecentRun(from: request, result: result)
            }
        } catch {
            errorMessage = "Prediction failed: \(error.localizedDescription)"
        }
    }

    public func predictU3Pt(baseURL: URL, csvURL: URL, u3Bucket: String) async {
        guard !DDLaminateDefaults.u3PtModelKeys.contains(selectedU3PtModelKey) else {
            await predictU3Forecast(baseURL: baseURL)
            return
        }
        guard let theta1Value = normalizedThetaValue(theta1), let theta2Value = normalizedThetaValue(theta2) else {
            errorMessage = "Enter numeric theta values."
            return
        }
        theta1 = Self.thetaInputString(theta1Value)
        theta2 = Self.thetaInputString(theta2Value)
        if u3PtModels.isEmpty {
            await checkConnection(baseURL: baseURL)
        }
        guard u3PtModel?.available == true else {
            errorMessage = "The selected u3 Pt model (\(DDLaminateModelDisplayLabel.cleanKey(selectedU3PtModelKey))) is unavailable. Check the API base URL or server."
            return
        }
        isPredictingU3Pt = true
        errorMessage = nil
        defer { isPredictingU3Pt = false }

        do {
            u3PtResult = try await apiClient.predictU3Pt(
                baseURL: baseURL,
                case: selectedCase,
                theta1: theta1Value,
                theta2: theta2Value,
                u3Bucket: u3Bucket,
                model: selectedU3PtModelKey,
                csvURL: csvURL
            )
        } catch {
            errorMessage = "u3 Pt prediction failed: \(error.localizedDescription)"
        }
    }

    public func predictU3Forecast(baseURL: URL) async {
        guard let theta1Value = normalizedThetaValue(theta1), let theta2Value = normalizedThetaValue(theta2) else {
            errorMessage = "Enter numeric theta values."
            return
        }
        theta1 = Self.thetaInputString(theta1Value)
        theta2 = Self.thetaInputString(theta2Value)
        if u3PtModels.isEmpty {
            await checkConnection(baseURL: baseURL)
        }
        guard u3PtModel?.available == true else {
            errorMessage = "The selected u3 Pt model (\(DDLaminateModelDisplayLabel.cleanKey(selectedU3PtModelKey))) is unavailable. Check the API base URL or server."
            return
        }
        isPredictingU3Pt = true
        errorMessage = nil
        defer { isPredictingU3Pt = false }

        let request = U3ForecastPredictionRequest(
            theta1: theta1Value,
            theta2: theta2Value,
            case: selectedCase,
            model: selectedU3PtModelKey
        )
        do {
            u3PtResult = try await apiClient.predictU3Forecast(baseURL: baseURL, request: request)
            if let u3PtResult {
                saveRecentRun(from: request, result: u3PtResult)
            }
        } catch {
            errorMessage = "u3 Forecast failed: \(error.localizedDescription)"
        }
    }

    public func applyRecentRun(_ run: DDLaminateRecentRun) {
        theta1 = run.theta1Display
        theta2 = run.theta2Display
        selectedCase = run.selectedCase
        switch run.kind {
        case .responseForecast:
            selectedResponseModelKey = run.responseModelKey
            responseModel = responseModels.first { $0.key == run.responseModelKey } ?? responseModel
        case .u3Forecast:
            selectedU3PtModelKey = run.responseModelKey
            u3PtModel = u3PtModels.first { $0.key == run.responseModelKey } ?? u3PtModel
        }
        result = nil
        u3PtResult = nil
        updateReadyStateIfNeeded()
    }

    public func clearRecentRuns() {
        recentRuns = []
        userDefaults.removeObject(forKey: recentRunsKey)
    }

    public func deleteRecentRuns(ids: Set<String>) {
        guard !ids.isEmpty else { return }
        recentRuns.removeAll { ids.contains($0.id) }
        if recentRuns.isEmpty {
            userDefaults.removeObject(forKey: recentRunsKey)
        } else if let data = try? JSONEncoder().encode(recentRuns) {
            userDefaults.set(data, forKey: recentRunsKey)
        }
    }

    public func loadFixturePreview() {
        do {
            let fixture = try fixtureLoader.loadResponsePredictionFixture()
            theta1 = String(format: "%.0f", fixture.request.theta1)
            theta2 = String(format: "%.0f", fixture.request.theta2)
            selectedCase = fixture.request.case
            selectedResponseModelKey = fixture.request.model
            result = fixture.response
            errorMessage = nil
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func saveRecentRun(from request: ResponsePredictionRequest, result: ResponsePredictionResult) {
        let run = DDLaminateRecentRun(
            kind: .responseForecast,
            selectedCase: request.case,
            responseModelKey: request.model,
            theta1: theta1,
            theta2: theta2,
            createdAt: Date(),
            predictedType: result.predictedType,
            confidence: result.confidence,
            predictedPt: result.predictedPt,
            predictedMaxForce: result.predictedMaxForce,
            predictedMaxDisplacement: result.predictedMaxDisplacement,
            modelLabel: result.displayModelLabel,
            curve: result.curve
        )
        recentRuns = ([run] + recentRuns.filter { $0.signature != run.signature }).prefix(5).map { $0 }
        if let data = try? JSONEncoder().encode(recentRuns) {
            userDefaults.set(data, forKey: recentRunsKey)
        }
    }

    private func saveRecentRun(from request: U3ForecastPredictionRequest, result: U3PtPredictionResult) {
        let run = DDLaminateRecentRun(
            kind: .u3Forecast,
            selectedCase: request.case,
            responseModelKey: request.model,
            theta1: theta1,
            theta2: theta2,
            createdAt: Date(),
            predictedType: result.predictedType,
            confidence: result.confidence,
            predictedPt: result.predictedPt,
            predictedMaxForce: result.predictedMaxForce,
            predictedMaxDisplacement: result.predictedMaxDisplacement,
            modelLabel: result.displayModelLabel,
            curve: result.curve
        )
        recentRuns = ([run] + recentRuns.filter { $0.signature != run.signature }).prefix(5).map { $0 }
        if let data = try? JSONEncoder().encode(recentRuns) {
            userDefaults.set(data, forKey: recentRunsKey)
        }
    }

    private static func loadRecentRuns(from userDefaults: UserDefaults, key: String) -> [DDLaminateRecentRun] {
        guard let data = userDefaults.data(forKey: key),
              let runs = try? JSONDecoder().decode([DDLaminateRecentRun].self, from: data)
        else {
            return []
        }
        return Array(runs.prefix(5))
    }

    private func normalizedThetaValue(_ text: String) -> Double? {
        guard let value = Double(text.trimmingCharacters(in: .whitespacesAndNewlines)) else {
            return nil
        }
        return min(90, max(-90, value)).rounded()
    }

    private static func thetaInputString(_ value: Double) -> String {
        String(Int(min(90, max(-90, value)).rounded()))
    }

    private static func optimalResponseModels(from models: [ModelInfo]) -> [ModelInfo] {
        let byKey = Dictionary(uniqueKeysWithValues: models.map { ($0.key, $0) })
        let optimalModels = DDLaminateDefaults.responseModelKeys.compactMap { byKey[$0] }
        return optimalModels.isEmpty ? models : optimalModels
    }

    private static func optimalU3PtModels(from models: [ModelInfo]) -> [ModelInfo] {
        let byKey = Dictionary(uniqueKeysWithValues: models.map { ($0.key, $0) })
        let optimalModels = DDLaminateDefaults.u3PtModelKeys.compactMap { byKey[$0] }
        return optimalModels.isEmpty ? models : optimalModels
    }

    private func normalizeModelSelection() {
        if responseModels.first(where: { $0.key == selectedResponseModelKey && $0.available }) == nil,
           let fallback = responseModels.first(where: { $0.key == DDLaminateDefaults.responseModelKey && $0.available }) ?? responseModels.first(where: \.available) ?? responseModels.first {
            selectedResponseModelKey = fallback.key
        }
        responseModel = responseModels.first { $0.key == selectedResponseModelKey }
    }

    private func normalizeU3PtModelSelection() {
        if u3PtModels.first(where: { $0.key == selectedU3PtModelKey && $0.available }) == nil,
           let fallback = u3PtModels.first(where: { $0.key == DDLaminateDefaults.u3PtModelKey && $0.available }) ?? u3PtModels.first(where: \.available) ?? u3PtModels.first {
            selectedU3PtModelKey = fallback.key
        }
        u3PtModel = u3PtModels.first { $0.key == selectedU3PtModelKey }
    }

    private func updateReadyStateIfNeeded() {
        guard case .ready = connectionState else { return }
        connectionState = .ready(responseSurrogateAvailable: responseModel?.available == true)
    }
}

public enum DDLaminateRecentRunKind: String, Codable, Equatable, Sendable {
    case responseForecast
    case u3Forecast
}

public struct DDLaminateRecentRun: Identifiable, Codable, Equatable, Sendable {
    public var id: String { signature }
    public let kind: DDLaminateRecentRunKind
    public let selectedCase: DDLaminateCase
    public let responseModelKey: String
    public let theta1: String
    public let theta2: String
    public let createdAt: Date
    public let predictedType: Int?
    public let confidence: Double?
    public let predictedPt: Double?
    public let predictedMaxForce: Double?
    public let predictedMaxDisplacement: Double?
    public let modelLabel: String?
    public let curve: [ResponseCurvePoint]

    public init(
        kind: DDLaminateRecentRunKind = .responseForecast,
        selectedCase: DDLaminateCase,
        responseModelKey: String,
        theta1: String,
        theta2: String,
        createdAt: Date,
        predictedType: Int? = nil,
        confidence: Double? = nil,
        predictedPt: Double? = nil,
        predictedMaxForce: Double? = nil,
        predictedMaxDisplacement: Double? = nil,
        modelLabel: String? = nil,
        curve: [ResponseCurvePoint] = []
    ) {
        self.kind = kind
        self.selectedCase = selectedCase
        self.responseModelKey = responseModelKey
        self.theta1 = theta1
        self.theta2 = theta2
        self.createdAt = createdAt
        self.predictedType = predictedType
        self.confidence = confidence
        self.predictedPt = predictedPt
        self.predictedMaxForce = predictedMaxForce
        self.predictedMaxDisplacement = predictedMaxDisplacement
        self.modelLabel = modelLabel
        self.curve = curve
    }

    enum CodingKeys: String, CodingKey {
        case kind
        case selectedCase
        case responseModelKey
        case theta1
        case theta2
        case createdAt
        case predictedType
        case confidence
        case predictedPt
        case predictedMaxForce
        case predictedMaxDisplacement
        case modelLabel
        case curve
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        kind = try container.decodeIfPresent(DDLaminateRecentRunKind.self, forKey: .kind) ?? .responseForecast
        selectedCase = try container.decode(DDLaminateCase.self, forKey: .selectedCase)
        responseModelKey = try container.decodeIfPresent(String.self, forKey: .responseModelKey) ?? DDLaminateDefaults.responseModelKey
        theta1 = try container.decode(String.self, forKey: .theta1)
        theta2 = try container.decode(String.self, forKey: .theta2)
        createdAt = try container.decode(Date.self, forKey: .createdAt)
        predictedType = try container.decodeIfPresent(Int.self, forKey: .predictedType)
        confidence = try container.decodeIfPresent(Double.self, forKey: .confidence)
        predictedPt = try container.decodeIfPresent(Double.self, forKey: .predictedPt)
        predictedMaxForce = try container.decodeIfPresent(Double.self, forKey: .predictedMaxForce)
        predictedMaxDisplacement = try container.decodeIfPresent(Double.self, forKey: .predictedMaxDisplacement)
        modelLabel = try container.decodeIfPresent(String.self, forKey: .modelLabel)
        curve = try container.decodeIfPresent([ResponseCurvePoint].self, forKey: .curve) ?? []
    }

    public var displayTitle: String {
        selectedCase.rawValue
    }

    public var displaySubtitle: String {
        "\(DDLaminateModelDisplayLabel.cleanKey(responseModelKey)) · Theta \(theta1Display) / \(theta2Display)"
    }

    public var displayModelLabel: String {
        modelLabel.map(DDLaminateModelDisplayLabel.clean) ?? DDLaminateModelDisplayLabel.cleanKey(responseModelKey)
    }

    public var theta1Display: String {
        Self.integerAngleText(theta1)
    }

    public var theta2Display: String {
        Self.integerAngleText(theta2)
    }

    fileprivate var signature: String {
        "\(kind.rawValue)|\(selectedCase.rawValue)|\(responseModelKey)|\(theta1)|\(theta2)"
    }

    private static func integerAngleText(_ text: String) -> String {
        guard let value = Double(text.trimmingCharacters(in: .whitespacesAndNewlines)) else {
            return text
        }
        return String(Int(min(90, max(-90, value)).rounded()))
    }
}
