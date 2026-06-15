import Foundation

public enum DDLaminateCase: String, CaseIterable, Codable, Identifiable, Sendable {
    case case2 = "Case2"
    case case3 = "Case3"
    case case4 = "Case4"

    public var id: String { rawValue }
}

public struct HealthResponse: Codable, Equatable, Hashable, Sendable {
    public let status: String
}

public struct ModelInfo: Codable, Equatable, Hashable, Identifiable, Sendable {
    public let key: String
    public let label: String
    public let description: String
    public let inputMode: String
    public let path: String
    public let available: Bool

    public var id: String { key }
    public var displayLabel: String { DDLaminateModelDisplayLabel.clean(label) }

    enum CodingKeys: String, CodingKey {
        case key
        case label
        case description
        case inputMode = "input_mode"
        case path
        case available
    }
}

public struct DDLaminateModelsResponse: Codable, Equatable, Hashable, Sendable {
    public let thetaModels: [ModelInfo]
    public let curveModels: [ModelInfo]
    public let responseModels: [ModelInfo]
    public let u3PtModels: [ModelInfo]

    public var responseSurrogate: ModelInfo? {
        responseModels.first { $0.key == DDLaminateDefaults.responseModelKey }
    }

    public init(
        thetaModels: [ModelInfo],
        curveModels: [ModelInfo],
        responseModels: [ModelInfo],
        u3PtModels: [ModelInfo] = []
    ) {
        self.thetaModels = thetaModels
        self.curveModels = curveModels
        self.responseModels = responseModels
        self.u3PtModels = u3PtModels
    }

    enum CodingKeys: String, CodingKey {
        case thetaModels = "theta_models"
        case curveModels = "curve_models"
        case responseModels = "response_models"
        case u3PtModels = "u3_pt_models"
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        thetaModels = try container.decode([ModelInfo].self, forKey: .thetaModels)
        curveModels = try container.decode([ModelInfo].self, forKey: .curveModels)
        responseModels = try container.decode([ModelInfo].self, forKey: .responseModels)
        u3PtModels = try container.decodeIfPresent([ModelInfo].self, forKey: .u3PtModels) ?? []
    }
}

public struct ResponsePredictionRequest: Codable, Equatable, Hashable, Sendable {
    public let theta1: Double
    public let theta2: Double
    public let `case`: DDLaminateCase
    public let model: String

    public init(
        theta1: Double,
        theta2: Double,
        case laminateCase: DDLaminateCase,
        model: String = DDLaminateDefaults.responseModelKey
    ) {
        self.theta1 = theta1
        self.theta2 = theta2
        self.case = laminateCase
        self.model = model
    }
}

public struct U3ForecastPredictionRequest: Codable, Equatable, Hashable, Sendable {
    public let theta1: Double
    public let theta2: Double
    public let `case`: DDLaminateCase
    public let testId: String
    public let model: String

    public init(
        theta1: Double,
        theta2: Double,
        case laminateCase: DDLaminateCase,
        testId: String = "Forecast",
        model: String = DDLaminateDefaults.u3PtModelKey
    ) {
        self.theta1 = theta1
        self.theta2 = theta2
        self.case = laminateCase
        self.testId = testId
        self.model = model
    }

    enum CodingKeys: String, CodingKey {
        case theta1
        case theta2
        case `case`
        case testId = "test_id"
        case model
    }
}

public struct ResponseCurvePoint: Codable, Equatable, Hashable, Identifiable, Sendable {
    public let displacement: Double
    public let force: Double

    public var id: String { "\(displacement)-\(force)" }
}

public struct XAIFeature: Codable, Equatable, Hashable, Identifiable, Sendable {
    public let name: String
    public let label: String
    public let importance: Double
    public let category: String
    public let explanation: String

    public var id: String { name }
}

public struct XAIExplanation: Codable, Equatable, Hashable, Sendable {
    public let title: String
    public let summary: String
    public let method: String
    public let featureSet: String
    public let topFeatures: [XAIFeature]
    public let notes: [String]

    enum CodingKeys: String, CodingKey {
        case title
        case summary
        case method
        case featureSet = "feature_set"
        case topFeatures = "top_features"
        case notes
    }
}

public struct ResponsePredictionResult: Codable, Equatable, Hashable, Sendable {
    public let predictedType: Int
    public let confidence: Double?
    public let probabilities: [String: Double]?
    public let modelKey: String
    public let modelLabel: String
    public let inputMode: String
    public let inputs: [String: JSONValue]
    public let notes: [String]
    public let features: [String: Double]?
    public let predictedPt: Double
    public let predictedMaxDisplacement: Double
    public let predictedMaxForce: Double
    public let curve: [ResponseCurvePoint]
    public let metrics: [String: JSONValue]
    public let xai: XAIExplanation?

    public var sortedProbabilities: [(label: String, value: Double)] {
        (probabilities ?? [:]).sorted { $0.key < $1.key }.map { ($0.key, $0.value) }
    }

    public var displayModelLabel: String { DDLaminateModelDisplayLabel.clean(modelLabel) }

    enum CodingKeys: String, CodingKey {
        case predictedType = "predicted_type"
        case confidence
        case probabilities
        case modelKey = "model_key"
        case modelLabel = "model_label"
        case inputMode = "input_mode"
        case inputs
        case notes
        case features
        case predictedPt = "predicted_pt"
        case predictedMaxDisplacement = "predicted_max_displacement"
        case predictedMaxForce = "predicted_max_force"
        case curve
        case metrics
        case xai
    }
}

public struct U3PtPredictionResult: Codable, Equatable, Hashable, Sendable {
    public let predictedType: Int?
    public let confidence: Double?
    public let probabilities: [String: Double]?
    public let predictedPt: Double
    public let predictedMaxDisplacement: Double
    public let predictedMaxForce: Double
    public let curve: [ResponseCurvePoint]
    public let modelKey: String
    public let modelLabel: String
    public let inputMode: String
    public let inputs: [String: JSONValue]
    public let notes: [String]
    public let metrics: [String: JSONValue]
    public let xai: XAIExplanation?

    public var displayModelLabel: String { DDLaminateModelDisplayLabel.clean(modelLabel) }

    enum CodingKeys: String, CodingKey {
        case predictedType = "predicted_type"
        case confidence
        case probabilities
        case predictedPt = "predicted_pt"
        case predictedMaxDisplacement = "predicted_max_displacement"
        case predictedMaxForce = "predicted_max_force"
        case curve
        case modelKey = "model_key"
        case modelLabel = "model_label"
        case inputMode = "input_mode"
        case inputs
        case notes
        case metrics
        case xai
    }
}

public struct ResponsePredictionFixture: Codable, Equatable, Hashable, Sendable {
    public let description: String
    public let endpoint: String
    public let method: String
    public let request: ResponsePredictionRequest
    public let response: ResponsePredictionResult
}

public enum JSONValue: Codable, Equatable, Hashable, Sendable {
    case string(String)
    case double(Double)
    case bool(Bool)
    case null

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            self = .null
        } else if let value = try? container.decode(Bool.self) {
            self = .bool(value)
        } else if let value = try? container.decode(Double.self) {
            self = .double(value)
        } else {
            self = .string(try container.decode(String.self))
        }
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .string(let value):
            try container.encode(value)
        case .double(let value):
            try container.encode(value)
        case .bool(let value):
            try container.encode(value)
        case .null:
            try container.encodeNil()
        }
    }
}

public enum DDLaminateDefaults {
    public static let responseModelKey = "response_surrogate_physics"
    public static let u3PtModelKey = "u3_forecast_physics"
    public static let fallbackBaseURL = "https://laminate.luvelox.com"
}

enum DDLaminateModelDisplayLabel {
    static func clean(_ label: String) -> String {
        let cleaned = label.trimmingCharacters(in: .whitespacesAndNewlines)
        let key = cleaned.lowercased()
        return aliases[key] ?? cleaned
    }

    static func cleanKey(_ key: String) -> String {
        keyAliases[key] ?? clean(key)
    }

    private static let aliases: [String: String] = [
        "laminate forecast - cases 2/3/4": "ExtraTrees + PCA",
        "laminate forecast - gointmlp nn + clt (legacy case3/4)": "GointMLP NN",
        "estimated response - extratrees + pca + clt": "ExtraTrees + PCA",
        "estimated response - gointmlp nn + clt": "GointMLP NN",
        "theta + case - randomforest": "RandomForest",
        "theta + case - gointmlp-style nn": "GointMLP NN",
        "curve + metadata - extratrees": "ExtraTrees",
        "curve + metadata - goint sequence nn": "GRU + GointMLP NN",
        "extra trees + pca": "ExtraTrees + PCA",
        "extratrees + pca": "ExtraTrees + PCA",
        "gointmlp-style nn": "GointMLP NN",
        "u3 forecast - extratrees + pca": "u3 Forecast - ExtraTrees + PCA",
        "u3 forecast - physics xai": "u3 Forecast - Physics XAI",
        "u3 forecast - gointmlp nn": "u3 Forecast - GointMLP NN",
        "u3 forecast - tree (theta)": "u3 Forecast - Tree (Theta)",
        "u3 forecast - tree + physics xai": "u3 Forecast - Tree + Physics XAI",
        "u3 forecast - gointmlp (theta)": "u3 Forecast - GointMLP (Theta)",
        "u3 forecast - gointmlp + physics xai": "u3 Forecast - GointMLP + Physics XAI",
        "laminate forecast - tree (theta)": "Laminate Forecast - Tree (Theta)",
        "laminate forecast - gointmlp (theta)": "Laminate Forecast - GointMLP (Theta)",
        "laminate forecast - tree + physics xai": "Laminate Forecast - Tree + Physics XAI",
        "laminate forecast - gointmlp + physics xai": "Laminate Forecast - GointMLP + Physics XAI",
    ]

    private static let keyAliases: [String: String] = [
        "response_surrogate": "ExtraTrees + PCA",
        "response_goint": "GointMLP NN",
        "response_surrogate_physics": "Laminate Forecast - Tree + Physics XAI",
        "response_goint_physics": "Laminate Forecast - GointMLP + Physics XAI",
        "theta_classical": "RandomForest",
        "theta_goint": "GointMLP NN",
        "curve_classical": "ExtraTrees",
        "curve_goint": "GRU + GointMLP NN",
        "u3_forecast": "u3 Forecast - Tree (Theta)",
        "u3_forecast_physics": "u3 Forecast - Tree + Physics XAI",
        "u3_forecast_goint": "u3 Forecast - GointMLP (Theta)",
        "u3_forecast_goint_physics": "u3 Forecast - GointMLP + Physics XAI",
    ]
}
