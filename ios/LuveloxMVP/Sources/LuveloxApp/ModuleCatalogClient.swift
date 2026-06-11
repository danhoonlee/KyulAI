import Foundation

public struct ModuleCatalogClient: Sendable {
    public let baseURL: URL
    public let session: URLSession

    public init(
        baseURL: URL = URL(string: "https://laminate.luvelox.com")!,
        session: URLSession = .shared
    ) {
        self.baseURL = baseURL
        self.session = session
    }

    public func fetchUserModules() async throws -> LuveloxUserModulesResponse {
        let url = Self.endpoint(baseURL: baseURL, path: "/api/v1/modules/me")
        let (data, response) = try await session.data(from: url)
        guard let httpResponse = response as? HTTPURLResponse, (200..<300).contains(httpResponse.statusCode) else {
            throw URLError(.badServerResponse)
        }
        return try JSONDecoder().decode(LuveloxUserModulesResponse.self, from: data)
    }

    public static func endpoint(baseURL: URL, path: String) -> URL {
        var components = URLComponents(url: baseURL, resolvingAgainstBaseURL: false)!
        components.path = path
        components.query = nil
        return components.url!
    }
}
