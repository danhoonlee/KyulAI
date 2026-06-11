import Foundation

public enum DDLaminateAPIError: Error, LocalizedError, Equatable, Sendable {
    case invalidBaseURL(String)
    case invalidResponse
    case httpStatus(Int, String)
    case decoding(String)

    public var errorDescription: String? {
        switch self {
        case .invalidBaseURL(let value):
            "Invalid API base URL: \(value)"
        case .invalidResponse:
            "The server returned an invalid response."
        case .httpStatus(let code, let detail):
            detail.isEmpty ? "HTTP \(code)" : "HTTP \(code): \(detail)"
        case .decoding(let detail):
            "Could not decode API response: \(detail)"
        }
    }
}

public protocol DDLaminateAPIClientProtocol: Sendable {
    func health(baseURL: URL) async throws -> HealthResponse
    func models(baseURL: URL) async throws -> DDLaminateModelsResponse
    func predictResponse(baseURL: URL, request: ResponsePredictionRequest) async throws -> ResponsePredictionResult
}

public struct DDLaminateAPIClient: DDLaminateAPIClientProtocol {
    private let urlSession: URLSession
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    public init(urlSession: URLSession = .shared) {
        self.urlSession = urlSession
        self.decoder = JSONDecoder()
        self.encoder = JSONEncoder()
    }

    public func health(baseURL: URL) async throws -> HealthResponse {
        try await get(baseURL: baseURL, path: "/health")
    }

    public func models(baseURL: URL) async throws -> DDLaminateModelsResponse {
        try await get(baseURL: baseURL, path: "/api/v1/dd-laminate/models")
    }

    public func predictResponse(
        baseURL: URL,
        request: ResponsePredictionRequest
    ) async throws -> ResponsePredictionResult {
        var urlRequest = URLRequest(url: Self.endpoint(baseURL: baseURL, path: "/api/v1/dd-laminate/predict/response"))
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        urlRequest.httpBody = try encoder.encode(request)
        return try await send(urlRequest)
    }

    private func get<T: Decodable>(baseURL: URL, path: String) async throws -> T {
        let request = URLRequest(url: Self.endpoint(baseURL: baseURL, path: path))
        return try await send(request)
    }

    private func send<T: Decodable>(_ request: URLRequest) async throws -> T {
        let (data, response) = try await urlSession.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw DDLaminateAPIError.invalidResponse
        }
        guard (200..<300).contains(http.statusCode) else {
            let detail = Self.extractErrorDetail(from: data)
            throw DDLaminateAPIError.httpStatus(http.statusCode, detail)
        }
        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw DDLaminateAPIError.decoding(error.localizedDescription)
        }
    }

    static func endpoint(baseURL: URL, path: String) -> URL {
        guard var components = URLComponents(url: baseURL, resolvingAgainstBaseURL: false) else {
            return baseURL
        }
        let basePath = components.percentEncodedPath.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        let endpointPath = path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        let joinedPath = [basePath, endpointPath].filter { !$0.isEmpty }.joined(separator: "/")
        components.percentEncodedPath = "/" + joinedPath
        return components.url ?? baseURL
    }

    private static func extractErrorDetail(from data: Data) -> String {
        guard !data.isEmpty else { return "" }
        if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let detail = json["detail"] {
            return String(describing: detail)
        }
        return String(data: data, encoding: .utf8) ?? ""
    }
}

public enum BaseURLValidator {
    public static func parse(_ rawValue: String) throws -> URL {
        let trimmed = rawValue.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let url = URL(string: trimmed),
              let scheme = url.scheme?.lowercased(),
              ["http", "https"].contains(scheme),
              url.host != nil else {
            throw DDLaminateAPIError.invalidBaseURL(rawValue)
        }
        return url
    }
}
