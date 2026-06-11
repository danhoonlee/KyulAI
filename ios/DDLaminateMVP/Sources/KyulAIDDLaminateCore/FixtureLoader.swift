import Foundation

public protocol FixtureLoading: Sendable {
    func loadResponsePredictionFixture() throws -> ResponsePredictionFixture
}

public struct BundleFixtureLoader: FixtureLoading {
    private let bundle: Bundle

    public init() {
        self.bundle = .module
    }

    public init(bundle: Bundle) {
        self.bundle = bundle
    }

    public func loadResponsePredictionFixture() throws -> ResponsePredictionFixture {
        guard let url = bundle.url(forResource: "predict_response_case2", withExtension: "json") else {
            throw CocoaError(.fileNoSuchFile)
        }
        let data = try Data(contentsOf: url)
        return try JSONDecoder().decode(ResponsePredictionFixture.self, from: data)
    }
}
