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
    public let panelAIn: Double
    public let panelBIn: Double

    public init(
        theta1: Double,
        theta2: Double,
        case laminateCase: DDLaminateCase,
        model: String = DDLaminateDefaults.responseModelKey,
        panelAIn: Double = 6,
        panelBIn: Double = 4
    ) {
        self.theta1 = theta1
        self.theta2 = theta2
        self.case = laminateCase
        self.model = model
        self.panelAIn = panelAIn
        self.panelBIn = panelBIn
    }

    enum CodingKeys: String, CodingKey {
        case theta1
        case theta2
        case `case`
        case model
        case panelAIn = "panel_a_in"
        case panelBIn = "panel_b_in"
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        theta1 = try container.decode(Double.self, forKey: .theta1)
        theta2 = try container.decode(Double.self, forKey: .theta2)
        self.case = try container.decode(DDLaminateCase.self, forKey: .case)
        model = try container.decodeIfPresent(String.self, forKey: .model) ?? DDLaminateDefaults.responseModelKey
        panelAIn = try container.decodeIfPresent(Double.self, forKey: .panelAIn) ?? 6
        panelBIn = try container.decodeIfPresent(Double.self, forKey: .panelBIn) ?? 4
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

public enum DesignSpaceScope: String, Codable, Equatable, Hashable, Sendable {
    case response
    case u3
}

public struct DesignSpaceRequest: Codable, Equatable, Hashable, Sendable {
    public let theta1: Double
    public let theta2: Double
    public let `case`: DDLaminateCase
    public let scope: DesignSpaceScope

    public init(
        theta1: Double,
        theta2: Double,
        case laminateCase: DDLaminateCase,
        scope: DesignSpaceScope = .response
    ) {
        self.theta1 = theta1
        self.theta2 = theta2
        self.case = laminateCase
        self.scope = scope
    }
}

public struct LocalXAIRequest: Codable, Equatable, Hashable, Sendable {
    public let theta1: Double
    public let theta2: Double
    public let `case`: DDLaminateCase
    public let model: String
    public let panelAIn: Double?
    public let panelBIn: Double?

    public init(
        theta1: Double,
        theta2: Double,
        case laminateCase: DDLaminateCase,
        model: String,
        panelAIn: Double? = nil,
        panelBIn: Double? = nil
    ) {
        self.theta1 = theta1
        self.theta2 = theta2
        self.case = laminateCase
        self.model = model
        self.panelAIn = panelAIn
        self.panelBIn = panelBIn
    }

    enum CodingKeys: String, CodingKey {
        case theta1
        case theta2
        case `case`
        case model
        case panelAIn = "panel_a_in"
        case panelBIn = "panel_b_in"
    }
}

public struct ResponseCurvePoint: Codable, Equatable, Hashable, Identifiable, Sendable {
    public let displacement: Double
    public let force: Double

    public var id: String { "\(displacement)-\(force)" }
}

public struct ResponseCurveFitLine: Codable, Equatable, Hashable, Sendable {
    public let slope: Double
    public let intercept: Double
}

public struct ResponseCurveFitPoint: Codable, Equatable, Hashable, Sendable {
    public let displacement: Double
    public let force: Double
}

public struct ResponseCurveFitWindow: Codable, Equatable, Hashable, Sendable {
    public let start: Int
    public let end: Int
}

public struct ResponseCurveFit: Codable, Equatable, Hashable, Sendable {
    public let kink: ResponseCurveFitPoint?
    public let detectedKink: ResponseCurveFitPoint?
    public let firstLine: ResponseCurveFitLine?
    public let secondLine: ResponseCurveFitLine?
    public let firstStartX: Double?
    public let firstEndX: Double?
    public let secondStartX: Double?
    public let secondEndX: Double?
    public let firstWindow: ResponseCurveFitWindow?
    public let secondWindow: ResponseCurveFitWindow?

    enum CodingKeys: String, CodingKey {
        case kink
        case detectedKink = "detected_kink"
        case firstLine = "first_line"
        case secondLine = "second_line"
        case firstStartX = "first_start_x"
        case firstEndX = "first_end_x"
        case secondStartX = "second_start_x"
        case secondEndX = "second_end_x"
        case firstWindow = "first_window"
        case secondWindow = "second_window"
    }
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

public struct PredictionUncertainty: Codable, Equatable, Hashable, Sendable {
    public let reliabilityScore: Double
    public let confidenceLabel: String
    public let interpolationScore: Double
    public let interpolationLabel: String
    public let nearestDistance: Double?
    public let nearestCount: Int
    public let localPtStd: Double?
    public let ptIntervalLow: Double?
    public let ptIntervalHigh: Double?
    public let typeConsistency: Double?
    public let notes: [String]

    enum CodingKeys: String, CodingKey {
        case reliabilityScore = "reliability_score"
        case confidenceLabel = "confidence_label"
        case interpolationScore = "interpolation_score"
        case interpolationLabel = "interpolation_label"
        case nearestDistance = "nearest_distance"
        case nearestCount = "nearest_count"
        case localPtStd = "local_pt_std"
        case ptIntervalLow = "pt_interval_low"
        case ptIntervalHigh = "pt_interval_high"
        case typeConsistency = "type_consistency"
        case notes
    }
}

public struct DesignSpaceScoreBreakdown: Codable, Equatable, Hashable, Sendable {
    public let pt: Double
    public let type: Double
    public let proximity: Double

    enum CodingKeys: String, CodingKey {
        case pt
        case type
        case proximity
    }
}

public struct DesignSpacePoint: Codable, Equatable, Hashable, Identifiable, Sendable {
    public let theta1: Double
    public let theta2: Double
    public let `case`: DDLaminateCase
    public let testId: String
    public let pt: Double
    public let type: Int?
    public let distance: Double
    public let source: String

    public var id: String {
        "\(`case`.rawValue)-\(testId)-\(theta1)-\(theta2)-\(pt)"
    }

    public init(
        theta1: Double,
        theta2: Double,
        case laminateCase: DDLaminateCase,
        testId: String,
        pt: Double,
        type: Int?,
        distance: Double,
        source: String
    ) {
        self.theta1 = theta1
        self.theta2 = theta2
        self.case = laminateCase
        self.testId = testId
        self.pt = pt
        self.type = type
        self.distance = distance
        self.source = source
    }

    enum CodingKeys: String, CodingKey {
        case theta1
        case theta2
        case `case`
        case testId = "test_id"
        case pt
        case type
        case distance
        case source
    }
}

public struct DesignSpaceRecommendation: Codable, Equatable, Hashable, Identifiable, Sendable {
    public let theta1: Double
    public let theta2: Double
    public let `case`: DDLaminateCase
    public let expectedPt: Double
    public let observedType: Int?
    public let score: Double
    public let scoreComponents: DesignSpaceScoreBreakdown
    public let rationale: String

    public var id: String {
        "\(`case`.rawValue)-\(theta1)-\(theta2)-\(expectedPt)"
    }

    enum CodingKeys: String, CodingKey {
        case theta1
        case theta2
        case `case`
        case expectedPt = "expected_pt"
        case observedType = "observed_type"
        case score
        case scoreComponents = "score_components"
        case rationale
    }
}

public struct DesignSpaceCaseInsight: Codable, Equatable, Hashable, Identifiable, Sendable {
    public let `case`: DDLaminateCase
    public let count: Int
    public let focusKind: String
    public let focusCount: Int
    public let focusRate: Double
    public let theta1Min: Double?
    public let theta1Max: Double?
    public let theta2Min: Double?
    public let theta2Max: Double?
    public let bestTheta1: Double?
    public let bestTheta2: Double?
    public let bestPt: Double?
    public let bestType: Int?

    public var id: String { `case`.rawValue }

    enum CodingKeys: String, CodingKey {
        case `case`
        case count
        case focusKind = "focus_kind"
        case focusCount = "focus_count"
        case focusRate = "focus_rate"
        case theta1Min = "theta1_min"
        case theta1Max = "theta1_max"
        case theta2Min = "theta2_min"
        case theta2Max = "theta2_max"
        case bestTheta1 = "best_theta1"
        case bestTheta2 = "best_theta2"
        case bestPt = "best_pt"
        case bestType = "best_type"
    }
}

public struct DesignSpaceResponse: Codable, Equatable, Hashable, Sendable {
    public let scope: DesignSpaceScope
    public let inputs: [String: JSONValue]
    public let mapPoints: [DesignSpacePoint]
    public let caseInsights: [DesignSpaceCaseInsight]
    public let recommendations: [DesignSpaceRecommendation]
    public let notes: [String]

    public init(
        scope: DesignSpaceScope,
        inputs: [String: JSONValue],
        mapPoints: [DesignSpacePoint] = [],
        caseInsights: [DesignSpaceCaseInsight],
        recommendations: [DesignSpaceRecommendation],
        notes: [String]
    ) {
        self.scope = scope
        self.inputs = inputs
        self.mapPoints = mapPoints
        self.caseInsights = caseInsights
        self.recommendations = recommendations
        self.notes = notes
    }

    enum CodingKeys: String, CodingKey {
        case scope
        case inputs
        case mapPoints = "map_points"
        case caseInsights = "case_insights"
        case recommendations
        case notes
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        scope = try container.decode(DesignSpaceScope.self, forKey: .scope)
        inputs = try container.decode([String: JSONValue].self, forKey: .inputs)
        mapPoints = try container.decodeIfPresent([DesignSpacePoint].self, forKey: .mapPoints) ?? []
        caseInsights = try container.decode([DesignSpaceCaseInsight].self, forKey: .caseInsights)
        recommendations = try container.decode([DesignSpaceRecommendation].self, forKey: .recommendations)
        notes = try container.decode([String].self, forKey: .notes)
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(scope, forKey: .scope)
        try container.encode(inputs, forKey: .inputs)
        try container.encode(mapPoints, forKey: .mapPoints)
        try container.encode(caseInsights, forKey: .caseInsights)
        try container.encode(recommendations, forKey: .recommendations)
        try container.encode(notes, forKey: .notes)
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
    public let curveFit: ResponseCurveFit?
    public let metrics: [String: JSONValue]
    public var xai: XAIExplanation?
    public let uncertainty: PredictionUncertainty?

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
        case curveFit = "curve_fit"
        case metrics
        case xai
        case uncertainty
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
    public let curveFit: ResponseCurveFit?
    public let modelKey: String
    public let modelLabel: String
    public let inputMode: String
    public let inputs: [String: JSONValue]
    public let notes: [String]
    public let metrics: [String: JSONValue]
    public var xai: XAIExplanation?
    public let uncertainty: PredictionUncertainty?

    public var displayModelLabel: String { DDLaminateModelDisplayLabel.clean(modelLabel) }

    enum CodingKeys: String, CodingKey {
        case predictedType = "predicted_type"
        case confidence
        case probabilities
        case predictedPt = "predicted_pt"
        case predictedMaxDisplacement = "predicted_max_displacement"
        case predictedMaxForce = "predicted_max_force"
        case curve
        case curveFit = "curve_fit"
        case modelKey = "model_key"
        case modelLabel = "model_label"
        case inputMode = "input_mode"
        case inputs
        case notes
        case metrics
        case xai
        case uncertainty
    }
}

public struct RagAnswerRequest: Codable, Equatable, Sendable {
    public let query: String
    public let topK: Int
    public let useLLM: Bool
    public let language: String
    public let predictionContext: [String: String]?

    public init(
        query: String,
        topK: Int = 3,
        useLLM: Bool = true,
        language: String = "auto",
        predictionContext: [String: String]? = nil
    ) {
        self.query = query
        self.topK = topK
        self.useLLM = useLLM
        self.language = language
        self.predictionContext = predictionContext
    }

    enum CodingKeys: String, CodingKey {
        case query
        case topK = "top_k"
        case useLLM = "use_llm"
        case language
        case predictionContext = "prediction_context"
    }
}

public struct RagAnswerResponse: Codable, Equatable, Sendable {
    public let query: String
    public let answer: String
    public let provider: String
    public let model: String
    public let retrievalCount: Int
    public let usedLLM: Bool
    public let error: String

    enum CodingKeys: String, CodingKey {
        case query
        case answer
        case provider
        case model
        case retrievalCount = "retrieval_count"
        case usedLLM = "used_llm"
        case error
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
    public static let responseModelKey = "response_surrogate_physics_v2"
    public static let responseModelKeys = [
        "response_surrogate_physics_v2",
        "response_goint_physics_nn_v2",
        "response_distilled_grid_conf_v1",
    ]
    public static let u3PtModelKey = "u3_forecast_physics_v2"
    public static let u3PtModelKeys = [
        "u3_forecast_physics_v2",
        "u3_forecast_goint_physics_v2",
    ]
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
        "u3 forecast - physics xai": "u3 Forecast - Machine Learning",
        "u3 forecast - gointmlp nn": "u3 Forecast - GointMLP NN",
        "u3 forecast - tree (theta)": "u3 Forecast - Tree (Theta)",
        "u3 forecast - tree + physics xai": "u3 Forecast - Machine Learning",
        "u3 forecast - tree + compact physics xai": "u3 Forecast - Machine Learning",
        "u3 forecast - machine learning": "u3 Forecast - Machine Learning",
        "u3 forecast - gointmlp (theta)": "u3 Forecast - GointMLP (Theta)",
        "u3 forecast - gointmlp + physics xai": "u3 Forecast - Deep Learning",
        "u3 forecast - gointmlp + compact physics xai": "u3 Forecast - Deep Learning",
        "u3 forecast - deep learning": "u3 Forecast - Deep Learning",
        "laminate forecast - tree (theta)": "Laminate Forecast - Tree (Theta)",
        "laminate forecast - gointmlp (theta)": "Laminate Forecast - GointMLP (Theta)",
        "laminate forecast - tree + physics xai": "Laminate Forecast - Machine Learning",
        "laminate forecast - tree + compact physics xai": "Laminate Forecast - Machine Learning",
        "laminate forecast - machine learning": "Laminate Forecast - Machine Learning",
        "laminate forecast - gointmlp + physics xai": "Laminate Forecast - Deep Learning",
        "laminate forecast - gointmlp + nn-friendly physics xai": "Laminate Forecast - Deep Learning",
        "laminate forecast - gointmlp + compact physics xai": "Laminate Forecast - Deep Learning",
        "laminate forecast - deep learning": "Laminate Forecast - Deep Learning",
        "laminate forecast - distilled nn v3": "Laminate Forecast - Distilled NN v3",
        "laminate forecast - distilled nn v2": "Laminate Forecast - Distilled NN v2",
        "laminate forecast - distilled nn": "Laminate Forecast - Distilled NN",
    ]

    private static let keyAliases: [String: String] = [
        "response_surrogate": "ExtraTrees + PCA",
        "response_goint": "GointMLP NN",
        "response_surrogate_physics": "Laminate Forecast - Machine Learning",
        "response_surrogate_physics_v2": "Laminate Forecast - Machine Learning",
        "response_goint_physics": "Laminate Forecast - Deep Learning",
        "response_goint_physics_nn_v2": "Laminate Forecast - Deep Learning",
        "response_distilled_grid_conf_v1": "Laminate Forecast - Distilled NN v3",
        "response_distilled_grid_v1": "Laminate Forecast - Distilled NN v2",
        "response_distilled_v1": "Laminate Forecast - Distilled NN",
        "theta_classical": "RandomForest",
        "theta_goint": "GointMLP NN",
        "curve_classical": "ExtraTrees",
        "curve_goint": "GRU + GointMLP NN",
        "u3_forecast": "u3 Forecast - Tree (Theta)",
        "u3_forecast_physics": "u3 Forecast - Machine Learning",
        "u3_forecast_physics_v2": "u3 Forecast - Machine Learning",
        "u3_forecast_goint": "u3 Forecast - GointMLP (Theta)",
        "u3_forecast_goint_physics": "u3 Forecast - Deep Learning",
        "u3_forecast_goint_physics_v2": "u3 Forecast - Deep Learning",
    ]
}
