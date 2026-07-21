import Foundation

public enum DDLaminateAPIError: Error, LocalizedError, Equatable, Sendable {
    case invalidBaseURL(String)
    case invalidResponse
    case httpStatus(Int, String)
    case decoding(String)
    case fileRead(String)

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
        case .fileRead(let detail):
            "Could not read CSV file: \(detail)"
        }
    }
}

public protocol DDLaminateAPIClientProtocol: Sendable {
    func health(baseURL: URL) async throws -> HealthResponse
    func models(baseURL: URL) async throws -> DDLaminateModelsResponse
    func predictResponse(baseURL: URL, request: ResponsePredictionRequest) async throws -> ResponsePredictionResult
    func predictU3Forecast(baseURL: URL, request: U3ForecastPredictionRequest) async throws -> U3PtPredictionResult
    func designSpace(baseURL: URL, request: DesignSpaceRequest) async throws -> DesignSpaceResponse
    func localXAI(baseURL: URL, request: LocalXAIRequest) async throws -> XAIExplanation
    func answerRag(baseURL: URL, request: RagAnswerRequest) async throws -> RagAnswerResponse
    func predictU3Pt(
        baseURL: URL,
        case laminateCase: DDLaminateCase,
        theta1: Double,
        theta2: Double,
        u3Bucket: String,
        model: String,
        csvURL: URL
    ) async throws -> U3PtPredictionResult
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
        let path = request.model == "response_geometry_tree_v1"
            ? "/api/v1/dd-laminate/predict/response-ensemble"
            : "/api/v1/dd-laminate/predict/response"
        var urlRequest = URLRequest(url: Self.endpoint(baseURL: baseURL, path: path))
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if request.model == "response_geometry_tree_v1" {
            urlRequest.httpBody = try encoder.encode(ResponseEnsemblePredictionRequest(from: request))
        } else {
            urlRequest.httpBody = try encoder.encode(request)
        }
        return try await send(urlRequest)
    }

    public func predictU3Forecast(
        baseURL: URL,
        request: U3ForecastPredictionRequest
    ) async throws -> U3PtPredictionResult {
        var urlRequest = URLRequest(url: Self.endpoint(baseURL: baseURL, path: "/api/v1/dd-laminate/predict/u3-forecast"))
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        urlRequest.httpBody = try encoder.encode(request)
        return try await send(urlRequest)
    }

    public func designSpace(
        baseURL: URL,
        request: DesignSpaceRequest
    ) async throws -> DesignSpaceResponse {
        var urlRequest = URLRequest(url: Self.endpoint(baseURL: baseURL, path: "/api/v1/dd-laminate/design-space"))
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        urlRequest.httpBody = try encoder.encode(request)
        return try await send(urlRequest)
    }

    public func localXAI(
        baseURL: URL,
        request: LocalXAIRequest
    ) async throws -> XAIExplanation {
        var urlRequest = URLRequest(url: Self.endpoint(baseURL: baseURL, path: "/api/v1/dd-laminate/xai/local"))
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        urlRequest.httpBody = try encoder.encode(request)
        return try await send(urlRequest)
    }

    public func answerRag(baseURL: URL, request: RagAnswerRequest) async throws -> RagAnswerResponse {
        var urlRequest = URLRequest(url: Self.endpoint(baseURL: baseURL, path: "/api/v1/rag/answer"))
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        urlRequest.httpBody = try encoder.encode(request)
        return try await send(urlRequest)
    }

    public func predictU3Pt(
        baseURL: URL,
        case laminateCase: DDLaminateCase,
        theta1: Double,
        theta2: Double,
        u3Bucket: String,
        model: String,
        csvURL: URL
    ) async throws -> U3PtPredictionResult {
        let didAccess = csvURL.startAccessingSecurityScopedResource()
        defer {
            if didAccess {
                csvURL.stopAccessingSecurityScopedResource()
            }
        }
        let csvData: Data
        do {
            csvData = try Data(contentsOf: csvURL)
        } catch {
            throw DDLaminateAPIError.fileRead(error.localizedDescription)
        }

        let boundary = "Boundary-\(UUID().uuidString)"
        var body = Data()
        func appendField(_ name: String, _ value: String) {
            body.appendString("--\(boundary)\r\n")
            body.appendString("Content-Disposition: form-data; name=\"\(name)\"\r\n\r\n")
            body.appendString("\(value)\r\n")
        }
        appendField("theta1", String(theta1))
        appendField("theta2", String(theta2))
        appendField("case", laminateCase.rawValue)
        appendField("u3_bucket", u3Bucket)
        appendField("test_id", csvURL.deletingPathExtension().lastPathComponent)
        appendField("model", model)
        body.appendString("--\(boundary)\r\n")
        body.appendString("Content-Disposition: form-data; name=\"file\"; filename=\"\(csvURL.lastPathComponent)\"\r\n")
        body.appendString("Content-Type: text/csv\r\n\r\n")
        body.append(csvData)
        body.appendString("\r\n--\(boundary)--\r\n")

        var urlRequest = URLRequest(url: Self.endpoint(baseURL: baseURL, path: "/api/v1/dd-laminate/predict/u3-pt"))
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        urlRequest.httpBody = body
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

private extension Data {
    mutating func appendString(_ string: String) {
        append(Data(string.utf8))
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
