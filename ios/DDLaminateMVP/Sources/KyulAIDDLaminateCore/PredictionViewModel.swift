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
    @Published public var selectedResponseModelKey = DDLaminateDefaults.responseModelKey
    @Published public var responseModel: ModelInfo?
    @Published public var result: ResponsePredictionResult?
    @Published public var errorMessage: String?
    @Published public var isPredicting = false
    @Published public private(set) var recentRuns: [DDLaminateRecentRun] = []

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

    public func resetReadiness() {
        connectionState = .idle
        responseModels = []
        responseModel = nil
        result = nil
        errorMessage = nil
    }

    public func checkConnection(baseURL: URL) async {
        connectionState = .checking
        errorMessage = nil
        do {
            _ = try await apiClient.health(baseURL: baseURL)
            let models = try await apiClient.models(baseURL: baseURL)
            responseModels = models.responseModels
            normalizeModelSelection()
            connectionState = .ready(responseSurrogateAvailable: responseModel?.available == true)
        } catch {
            connectionState = .failed(error.localizedDescription)
            responseModels = []
            responseModel = nil
        }
    }

    public func selectResponseModel(key: String) {
        selectedResponseModelKey = key
        responseModel = responseModels.first { $0.key == key }
        result = nil
        updateReadyStateIfNeeded()
    }

    public func predict(baseURL: URL) async {
        guard let theta1Value = Double(theta1), let theta2Value = Double(theta2) else {
            errorMessage = "Enter numeric theta values."
            return
        }
        guard (-90...90).contains(theta1Value), (-90...90).contains(theta2Value) else {
            errorMessage = "Theta values must be between -90 and 90 degrees."
            return
        }
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

    public func applyRecentRun(_ run: DDLaminateRecentRun) {
        theta1 = run.theta1
        theta2 = run.theta2
        selectedCase = run.selectedCase
        selectedResponseModelKey = run.responseModelKey
        responseModel = responseModels.first { $0.key == run.responseModelKey } ?? responseModel
        result = nil
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

    private func normalizeModelSelection() {
        if responseModels.first(where: { $0.key == selectedResponseModelKey && $0.available }) == nil,
           let fallback = responseModels.first(where: { $0.key == DDLaminateDefaults.responseModelKey && $0.available }) ?? responseModels.first(where: \.available) ?? responseModels.first {
            selectedResponseModelKey = fallback.key
        }
        responseModel = responseModels.first { $0.key == selectedResponseModelKey }
    }

    private func updateReadyStateIfNeeded() {
        guard case .ready = connectionState else { return }
        connectionState = .ready(responseSurrogateAvailable: responseModel?.available == true)
    }
}

public struct DDLaminateRecentRun: Identifiable, Codable, Equatable, Sendable {
    public var id: String { signature }
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
        "\(DDLaminateModelDisplayLabel.cleanKey(responseModelKey)) · Theta \(theta1) / \(theta2)"
    }

    public var displayModelLabel: String {
        modelLabel ?? DDLaminateModelDisplayLabel.cleanKey(responseModelKey)
    }

    fileprivate var signature: String {
        "\(selectedCase.rawValue)|\(responseModelKey)|\(theta1)|\(theta2)"
    }
}
