import Foundation

public enum ModuleCatalogError: Error, Equatable {
    case unauthorized
    case invalidResponse
}

public struct ModuleCatalogClient: Sendable {
    public let baseURL: URL
    public let session: URLSession

    public init(
        baseURL: URL = URL(string: "https://laminate.imperialax.com")!,
        session: URLSession = .shared
    ) {
        self.baseURL = baseURL
        self.session = session
    }

    public func fetchUserModules() async throws -> ImperialAXUserModulesResponse {
        let url = Self.endpoint(baseURL: baseURL, path: "/api/v1/modules/me")
        let (data, response) = try await session.data(from: url)
        guard let httpResponse = response as? HTTPURLResponse else { throw ModuleCatalogError.invalidResponse }
        if httpResponse.statusCode == 401 || httpResponse.statusCode == 403 {
            throw ModuleCatalogError.unauthorized
        }
        guard (200..<300).contains(httpResponse.statusCode) else { throw ModuleCatalogError.invalidResponse }
        return try JSONDecoder().decode(ImperialAXUserModulesResponse.self, from: data)
    }

    public func fetchUserModules(authSession: ImperialAXAuthSession?) async throws -> ImperialAXUserModulesResponse {
        let url = Self.endpoint(baseURL: baseURL, path: "/api/v1/modules/me")
        var request = URLRequest(url: url)
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let authSession {
            request.setValue("\(authSession.tokenType.capitalized) \(authSession.accessToken)", forHTTPHeaderField: "Authorization")
        }
        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else { throw ModuleCatalogError.invalidResponse }
        if httpResponse.statusCode == 401 || httpResponse.statusCode == 403 {
            throw ModuleCatalogError.unauthorized
        }
        guard (200..<300).contains(httpResponse.statusCode) else { throw ModuleCatalogError.invalidResponse }
        return try JSONDecoder().decode(ImperialAXUserModulesResponse.self, from: data)
    }

    public func login(email: String, password: String) async throws -> ImperialAXAuthSession {
        let url = Self.endpoint(baseURL: baseURL, path: "/api/v1/modules/auth/login")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.httpBody = try JSONEncoder().encode(["email": email, "password": password])
        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse, (200..<300).contains(httpResponse.statusCode) else {
            throw URLError(.userAuthenticationRequired)
        }
        return try JSONDecoder().decode(ImperialAXAuthSession.self, from: data)
    }

    public func demoLogin() async throws -> ImperialAXAuthSession {
        let request = try Self.demoLoginRequest(baseURL: baseURL)
        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse, (200..<300).contains(httpResponse.statusCode) else {
            throw URLError(.userAuthenticationRequired)
        }
        return try JSONDecoder().decode(ImperialAXAuthSession.self, from: data)
    }

    static func demoLoginRequest(baseURL: URL) throws -> URLRequest {
        let url = Self.endpoint(baseURL: baseURL, path: "/api/v1/modules/auth/demo-login")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.httpBody = try JSONEncoder().encode([
            "email": "demo@imperialax.com",
            "password": "",
        ])
        return request
    }

    public func signup(email: String, password: String, name: String, company: String?) async throws -> ImperialAXAuthSession {
        let url = Self.endpoint(baseURL: baseURL, path: "/api/v1/modules/auth/signup")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        let payload = ImperialAXSignupPayload(email: email, password: password, name: name, company: company)
        request.httpBody = try JSONEncoder().encode(payload)
        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse, (200..<300).contains(httpResponse.statusCode) else {
            throw URLError(.userAuthenticationRequired)
        }
        return try JSONDecoder().decode(ImperialAXAuthSession.self, from: data)
    }

    public func requestAccess(
        moduleId: String,
        message: String = "",
        authSession: ImperialAXAuthSession?
    ) async throws -> ImperialAXAccessRequestResponse {
        let url = Self.endpoint(baseURL: baseURL, path: "/api/v1/modules/request-access")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let authSession {
            request.setValue("\(authSession.tokenType.capitalized) \(authSession.accessToken)", forHTTPHeaderField: "Authorization")
        }
        let payload = ImperialAXAccessRequestPayload(moduleId: moduleId, message: message)
        request.httpBody = try JSONEncoder().encode(payload)
        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse, (200..<300).contains(httpResponse.statusCode) else {
            throw URLError(.badServerResponse)
        }
        return try JSONDecoder().decode(ImperialAXAccessRequestResponse.self, from: data)
    }

    public func createLaunchURL(
        target: String,
        authSession: ImperialAXAuthSession
    ) async throws -> URL {
        var request = try Self.launchCodeRequest(
            baseURL: baseURL,
            target: target,
            accessToken: authSession.accessToken,
            tokenType: authSession.tokenType
        )
        request.timeoutInterval = 10
        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse,
              (200..<300).contains(httpResponse.statusCode) else {
            throw URLError(.userAuthenticationRequired)
        }
        return try JSONDecoder().decode(ImperialAXLaunchCodeResponse.self, from: data).launchURL
    }

    static func launchCodeRequest(
        baseURL: URL,
        target: String,
        accessToken: String,
        tokenType: String = "bearer"
    ) throws -> URLRequest {
        let url = Self.endpoint(baseURL: baseURL, path: "/api/v1/modules/auth/launch-code")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue("\(tokenType.capitalized) \(accessToken)", forHTTPHeaderField: "Authorization")
        request.httpBody = try JSONEncoder().encode(["target": target])
        return request
    }

    public static func endpoint(baseURL: URL, path: String) -> URL {
        var components = URLComponents(url: baseURL, resolvingAgainstBaseURL: false)!
        components.path = path
        components.query = nil
        return components.url!
    }
}
