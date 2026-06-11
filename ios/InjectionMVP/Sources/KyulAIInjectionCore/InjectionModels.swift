import Foundation

public struct HealthResponse: Codable, Equatable, Hashable, Sendable {
    public let status: String
}

public struct ModelInfo: Codable, Equatable, Hashable, Identifiable, Sendable {
    public let key: String
    public let label: String
    public let description: String
    public let path: String
    public let available: Bool

    public var id: String { key }
    public var displayLabel: String { ModelDisplayLabel.clean(label) }
}

public struct InjectionModelsResponse: Codable, Equatable, Hashable, Sendable {
    public let spruePressureModels: [ModelInfo]
    public let fillingPressureModels: [ModelInfo]

    public var defaultSprueModel: ModelInfo? {
        spruePressureModels.first { $0.key == InjectionDefaults.sprueModelKey }
    }

    public var defaultFillingModel: ModelInfo? {
        fillingPressureModels.first { $0.key == InjectionDefaults.fillingModelKey }
    }

    enum CodingKeys: String, CodingKey {
        case spruePressureModels = "sprue_pressure_models"
        case fillingPressureModels = "filling_pressure_models"
    }
}

public struct DoeOption: Codable, Equatable, Hashable, Identifiable, Sendable {
    public let id: String
    public let values: [String: JSONValue]

    public func double(_ key: String) -> Double? {
        values[key]?.doubleValue
    }

    public func string(_ key: String) -> String? {
        values[key]?.stringValue
    }
}

public struct InjectionDoeResponse: Codable, Equatable, Hashable, Sendable {
    public let geometries: [DoeOption]
    public let processes: [DoeOption]
}

public struct SpruePressurePredictionRequest: Codable, Equatable, Hashable, Sendable {
    public let geometryID: String?
    public let processID: String?
    public let model: String
    public let fillingModel: String
    public let Lmm: Double
    public let Wmm: Double
    public let tmm: Double
    public let Dmm: Double
    public let Rmm: Double?
    public let gateType: String
    public let gateSizeWidthMm: Double
    public let gateSizeHeightMm: Double
    public let meltTempC: Double
    public let moldTempC: Double
    public let injectionTimeS: Double
    public let packingPressureMPa: Double
    public let packingTimeS: Double

    public init(
        geometryID: String?,
        processID: String?,
        model: String = InjectionDefaults.sprueModelKey,
        fillingModel: String = InjectionDefaults.fillingModelKey,
        Lmm: Double,
        Wmm: Double,
        tmm: Double,
        Dmm: Double,
        Rmm: Double?,
        gateType: String,
        gateSizeWidthMm: Double,
        gateSizeHeightMm: Double,
        meltTempC: Double,
        moldTempC: Double,
        injectionTimeS: Double,
        packingPressureMPa: Double,
        packingTimeS: Double
    ) {
        self.geometryID = geometryID
        self.processID = processID
        self.model = model
        self.fillingModel = fillingModel
        self.Lmm = Lmm
        self.Wmm = Wmm
        self.tmm = tmm
        self.Dmm = Dmm
        self.Rmm = Rmm
        self.gateType = gateType
        self.gateSizeWidthMm = gateSizeWidthMm
        self.gateSizeHeightMm = gateSizeHeightMm
        self.meltTempC = meltTempC
        self.moldTempC = moldTempC
        self.injectionTimeS = injectionTimeS
        self.packingPressureMPa = packingPressureMPa
        self.packingTimeS = packingTimeS
    }

    enum CodingKeys: String, CodingKey {
        case geometryID = "geometry_id"
        case processID = "process_id"
        case model
        case fillingModel = "filling_model"
        case Lmm = "L_mm"
        case Wmm = "W_mm"
        case tmm = "t_mm"
        case Dmm = "D_mm"
        case Rmm = "R_mm"
        case gateType = "gate_type"
        case gateSizeWidthMm = "gate_size_width_mm"
        case gateSizeHeightMm = "gate_size_height_mm"
        case meltTempC = "melt_temp_C"
        case moldTempC = "mold_temp_C"
        case injectionTimeS = "injection_time_s"
        case packingPressureMPa = "packing_pressure_MPa"
        case packingTimeS = "packing_time_s"
    }
}

public struct SpruePressurePoint: Codable, Equatable, Hashable, Identifiable, Sendable {
    public let timeS: Double
    public let spruePressureMPa: Double

    public var id: String { "\(timeS)-\(spruePressureMPa)" }

    enum CodingKeys: String, CodingKey {
        case timeS = "time_s"
        case spruePressureMPa = "sprue_pressure_MPa"
    }
}

public struct FillingPressureBin: Codable, Equatable, Hashable, Identifiable, Sendable {
    public let group: Int
    public let fromMPa: Double
    public let toMPa: Double
    public let centerMPa: Double
    public let count: Int
    public let volumeRatioPct: Double

    public var id: Int { group }

    enum CodingKeys: String, CodingKey {
        case group
        case fromMPa = "from_MPa"
        case toMPa = "to_MPa"
        case centerMPa = "center_MPa"
        case count
        case volumeRatioPct = "volume_ratio_pct"
    }
}

public struct FillingPressureSummary: Codable, Equatable, Hashable, Sendable {
    public let sampleID: String
    public let sourceFile: String
    public let stats: [String: Double]
    public let bins: [FillingPressureBin]
    public let note: String

    enum CodingKeys: String, CodingKey {
        case sampleID = "sample_id"
        case sourceFile = "source_file"
        case stats
        case bins
        case note
    }
}

public struct SpruePressurePredictionResult: Codable, Equatable, Hashable, Sendable {
    public let modelKey: String
    public let modelLabel: String
    public let fillingModelKey: String
    public let fillingModelLabel: String
    public let predictedMaxTimeS: Double
    public let predictedMaxPressureMPa: Double
    public let curve: [SpruePressurePoint]
    public let inputs: [String: JSONValue]
    public let metrics: [String: JSONValue]
    public let notes: [String]
    public let validationWarnings: [ValidationWarning]
    public let fillingPressure: FillingPressureSummary?
    public let predictedFillingPressure: FillingPressureSummary?

    public var bestFillingPressure: FillingPressureSummary? {
        predictedFillingPressure ?? fillingPressure
    }

    public var displayModelLabel: String {
        ModelDisplayLabel.clean(modelLabel)
    }

    public var displayFillingModelLabel: String {
        ModelDisplayLabel.clean(fillingModelLabel)
    }

    enum CodingKeys: String, CodingKey {
        case modelKey = "model_key"
        case modelLabel = "model_label"
        case fillingModelKey = "filling_model_key"
        case fillingModelLabel = "filling_model_label"
        case predictedMaxTimeS = "predicted_max_time_s"
        case predictedMaxPressureMPa = "predicted_max_pressure_MPa"
        case curve
        case inputs
        case metrics
        case notes
        case validationWarnings = "validation_warnings"
        case fillingPressure = "filling_pressure"
        case predictedFillingPressure = "predicted_filling_pressure"
    }
}

private enum ModelDisplayLabel {
    static func clean(_ label: String) -> String {
        var cleaned = label.trimmingCharacters(in: .whitespacesAndNewlines)
        for prefix in rolePrefixes {
            if cleaned.range(of: prefix, options: [.caseInsensitive, .anchored]) != nil {
                cleaned.removeFirst(prefix.count)
                break
            }
        }
        let normalized = cleaned
            .trimmingCharacters(in: CharacterSet(charactersIn: " -:"))
            .trimmingCharacters(in: .whitespacesAndNewlines)
        return replacements[normalized.lowercased()] ?? normalized
    }

    private static let rolePrefixes = [
        "Sprue Pressure",
        "Filling Pressure",
    ]

    private static let replacements = [
        "classical ml + pca": "ExtraTrees + PCA",
        "classical ml histogram": "ExtraTrees histogram",
        "gointmlp-style nn": "GointMLP NN",
        "deeponet operator nn": "DeepONet NN",
        "deeponet histogram nn": "DeepONet NN",
    ]
}

public struct ValidationWarning: Codable, Equatable, Hashable, Sendable {
    public let level: String
    public let message: String
}

public enum JSONValue: Codable, Equatable, Hashable, Sendable {
    case string(String)
    case double(Double)
    case bool(Bool)
    case array([JSONValue])
    case object([String: JSONValue])
    case null

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            self = .null
        } else if let value = try? container.decode(Bool.self) {
            self = .bool(value)
        } else if let value = try? container.decode(Double.self) {
            self = .double(value)
        } else if let value = try? container.decode([JSONValue].self) {
            self = .array(value)
        } else if let value = try? container.decode([String: JSONValue].self) {
            self = .object(value)
        } else {
            self = .string(try container.decode(String.self))
        }
    }

    public var doubleValue: Double? {
        switch self {
        case .double(let value):
            value
        case .string(let value):
            Double(value)
        default:
            nil
        }
    }

    public var stringValue: String? {
        switch self {
        case .string(let value):
            value
        case .double(let value):
            value.formatted()
        case .bool(let value):
            String(value)
        case .array, .object:
            nil
        case .null:
            nil
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
        case .array(let value):
            try container.encode(value)
        case .object(let value):
            try container.encode(value)
        case .null:
            try container.encodeNil()
        }
    }
}

public enum InjectionDefaults {
    public static let sprueModelKey = "sprue_classical"
    public static let fillingModelKey = "filling_classical"
    public static let fallbackBaseURL = "https://injection.luvelox.com"
}
