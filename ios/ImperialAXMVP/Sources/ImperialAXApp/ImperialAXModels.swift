import Foundation

public struct ImperialAXModuleRoute: Codable, Equatable, Sendable {
    public let baseURL: URL
    public let webURL: URL
    public let apiPrefix: String
    public let healthPath: String
    public let modelsPath: String
    public let primaryPredictPath: String

    enum CodingKeys: String, CodingKey {
        case baseURL = "base_url"
        case webURL = "web_url"
        case apiPrefix = "api_prefix"
        case healthPath = "health_path"
        case modelsPath = "models_path"
        case primaryPredictPath = "primary_predict_path"
    }
}

public struct ImperialAXModule: Codable, Equatable, Identifiable, Sendable {
    public let id: String
    public let name: String
    public let shortName: String
    public let category: String
    public let summary: String
    public let icon: String
    public let status: String
    public let entitlementKey: String
    public let defaultEnabled: Bool
    public let tags: [String]
    public let capabilities: [String]
    public let route: ImperialAXModuleRoute
    public let access: String?
    public let accessReason: String?

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case shortName = "short_name"
        case category
        case summary
        case icon
        case status
        case entitlementKey = "entitlement_key"
        case defaultEnabled = "default_enabled"
        case tags
        case capabilities
        case route
        case access
        case accessReason = "access_reason"
    }

    public var isGranted: Bool {
        access == nil || access == "granted"
    }
}

public struct ImperialAXUserModulesResponse: Codable, Equatable, Sendable {
    public let brand: String
    public let licenseMode: String
    public let user: ImperialAXAccountUser?
    public let modules: [ImperialAXModule]

    enum CodingKeys: String, CodingKey {
        case brand
        case licenseMode = "license_mode"
        case user
        case modules
    }
}

public struct ImperialAXAccountUser: Codable, Equatable, Sendable {
    public let id: String
    public let email: String
    public let name: String
    public let company: String?
}

public struct ImperialAXAuthSession: Codable, Equatable, Sendable {
    public let accessToken: String
    public let tokenType: String
    public let user: ImperialAXAccountUser
    public let entitlements: [String]

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case tokenType = "token_type"
        case user
        case entitlements
    }

    public static let demo = ImperialAXAuthSession(
        accessToken: "demo-token",
        tokenType: "bearer",
        user: ImperialAXAccountUser(
            id: "demo-user",
            email: "demo@imperialax.com",
            name: "Demo Account",
            company: "ImperialAX MVP"
        ),
        entitlements: ["module.laminate", "module.injection"]
    )

    public static let danlee = ImperialAXAuthSession(
        accessToken: "danlee-token",
        tokenType: "bearer",
        user: ImperialAXAccountUser(
            id: "danlee",
            email: "danlee@imperialax.com",
            name: "Dan Lee",
            company: "ImperialAX"
        ),
        entitlements: ["module.laminate", "module.injection", "module.optimization", "module.admin"]
    )
}

public struct ImperialAXSignupPayload: Encodable, Equatable, Sendable {
    public let email: String
    public let password: String
    public let name: String
    public let company: String?
}

public struct ImperialAXAccessRequestPayload: Encodable, Equatable, Sendable {
    public let moduleId: String
    public let message: String

    enum CodingKeys: String, CodingKey {
        case moduleId = "module_id"
        case message
    }
}

public struct ImperialAXAccessRequestResponse: Codable, Equatable, Sendable {
    public let status: String
    public let moduleId: String
    public let message: String
    public let user: ImperialAXAccountUser?

    enum CodingKeys: String, CodingKey {
        case status
        case moduleId = "module_id"
        case message
        case user
    }
}

public enum ImperialAXFallbackCatalog {
    public static let modules: [ImperialAXModule] = [
        ImperialAXModule(
            id: "laminate",
            name: "Laminate",
            shortName: "Laminate",
            category: "Composite",
            summary: "Predict Type, Pt, and response curve.",
            icon: "layers",
            status: "active",
            entitlementKey: "module.laminate",
            defaultEnabled: true,
            tags: ["Double-Double", "Pt", "Force-displacement"],
            capabilities: ["response_prediction", "curve_chart", "history", "comparison"],
            route: ImperialAXModuleRoute(
                baseURL: URL(string: "https://laminate.imperialax.com")!,
                webURL: URL(string: "https://laminate.imperialax.com")!,
                apiPrefix: "/api/v1/dd-laminate",
                healthPath: "/health",
                modelsPath: "/api/v1/dd-laminate/models",
                primaryPredictPath: "/api/v1/dd-laminate/predict/response"
            ),
            access: "granted",
            accessReason: "Available in the ImperialAX MVP workspace."
        ),
        ImperialAXModule(
            id: "injection",
            name: "Injection",
            shortName: "Injection",
            category: "Molding",
            summary: "Predict sprue and filling pressure.",
            icon: "gauge",
            status: "active",
            entitlementKey: "module.injection",
            defaultEnabled: true,
            tags: ["Moldex3D", "Sprue pressure", "Filling pressure"],
            capabilities: ["sprue_pressure", "filling_histogram", "filling_animation", "history"],
            route: ImperialAXModuleRoute(
                baseURL: URL(string: "https://injection.imperialax.com")!,
                webURL: URL(string: "https://injection.imperialax.com")!,
                apiPrefix: "/api/v1/simple-injection",
                healthPath: "/health",
                modelsPath: "/api/v1/simple-injection/models",
                primaryPredictPath: "/api/v1/simple-injection/predict/sprue-pressure"
            ),
            access: "granted",
            accessReason: "Available in the ImperialAX MVP workspace."
        ),
        ImperialAXModule(
            id: "optimization",
            name: "Optimization",
            shortName: "Optimize",
            category: "Design",
            summary: "Rank promising design candidates.",
            icon: "sparkles",
            status: "active",
            entitlementKey: "module.optimization",
            defaultEnabled: false,
            tags: ["DOE", "Ranking", "Design space"],
            capabilities: ["candidate_ranking", "batch_prediction"],
            route: ImperialAXModuleRoute(
                baseURL: URL(string: "https://ai.imperialax.com")!,
                webURL: URL(string: "https://ai.imperialax.com/optimization.html")!,
                apiPrefix: "/api/v1/optimization",
                healthPath: "/health",
                modelsPath: "/api/v1/optimization/models",
                primaryPredictPath: "/api/v1/optimization/search"
            ),
            access: "locked",
            accessReason: "Requires Optimization module access."
        ),
    ]
}
