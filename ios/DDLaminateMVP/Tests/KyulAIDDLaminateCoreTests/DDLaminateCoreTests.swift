import XCTest
@testable import KyulAIDDLaminateCore

final class DDLaminateCoreTests: XCTestCase {
    func testFixtureDecodesForSwiftUICodableContract() throws {
        let fixture = try BundleFixtureLoader().loadResponsePredictionFixture()

        XCTAssertEqual(fixture.endpoint, "/api/v1/dd-laminate/predict/response")
        XCTAssertEqual(fixture.method, "POST")
        XCTAssertEqual(fixture.request.theta1, 30)
        XCTAssertEqual(fixture.request.theta2, -30)
        XCTAssertEqual(fixture.request.case, .case2)
        XCTAssertEqual(fixture.request.model, DDLaminateDefaults.responseModelKey)
        XCTAssertEqual(fixture.response.modelKey, DDLaminateDefaults.responseModelKey)
        XCTAssertEqual(fixture.response.displayModelLabel, "ExtraTrees + PCA")
        XCTAssertEqual(fixture.response.inputMode, "response")
        XCTAssertEqual(fixture.response.predictedType, 2)
        XCTAssertEqual(fixture.response.inputs["case"], .string("Case2"))
        XCTAssertFalse(fixture.response.curve.isEmpty)
        XCTAssertEqual(fixture.response.curve.first?.displacement, 0)
        XCTAssertEqual(fixture.response.curve.first?.force, 0)
    }

    func testLegacyLaminateModelLabelsAreDisplayedAsAlgorithmNames() {
        let model = ModelInfo(
            key: DDLaminateDefaults.responseModelKey,
            label: "Laminate Forecast - Cases 2/3/4",
            description: "legacy server label",
            inputMode: "response",
            path: "models/response_surrogate.joblib",
            available: true
        )

        XCTAssertEqual(model.displayLabel, "ExtraTrees + PCA")
    }

    func testBaseURLValidatorAcceptsHttpAndHttpsHosts() throws {
        XCTAssertEqual(try BaseURLValidator.parse("http://192.168.0.10:8000").host, "192.168.0.10")
        XCTAssertEqual(try BaseURLValidator.parse("https://demo.example.com").scheme, "https")
        XCTAssertThrowsError(try BaseURLValidator.parse("localhost:8000"))
        XCTAssertThrowsError(try BaseURLValidator.parse("file:///tmp/api"))
    }

    func testAPIClientEndpointPreservesNestedAPIPaths() throws {
        let baseURL = try XCTUnwrap(URL(string: "http://127.0.0.1:8000"))

        XCTAssertEqual(
            DDLaminateAPIClient.endpoint(baseURL: baseURL, path: "/api/v1/dd-laminate/models").absoluteString,
            "http://127.0.0.1:8000/api/v1/dd-laminate/models"
        )
        XCTAssertEqual(
            DDLaminateAPIClient.endpoint(baseURL: baseURL, path: "/api/v1/dd-laminate/predict/response").absoluteString,
            "http://127.0.0.1:8000/api/v1/dd-laminate/predict/response"
        )
    }

    @MainActor
    func testViewModelUsesFixturePreviewData() {
        let viewModel = PredictionViewModel()
        viewModel.loadFixturePreview()

        XCTAssertEqual(viewModel.theta1, "30")
        XCTAssertEqual(viewModel.theta2, "-30")
        XCTAssertEqual(viewModel.selectedCase, .case2)
        XCTAssertEqual(viewModel.result?.modelKey, DDLaminateDefaults.responseModelKey)
        XCTAssertNil(viewModel.errorMessage)
    }

    @MainActor
    func testViewModelHealthAndModelsReadiness() async throws {
        let model = ModelInfo(
            key: DDLaminateDefaults.responseModelKey,
            label: "ExtraTrees + PCA",
            description: "fixture model",
            inputMode: "response",
            path: "models/response_surrogate.joblib",
            available: true
        )
        let client = MockAPIClient(
            healthResponse: HealthResponse(status: "ok"),
            modelsResponse: DDLaminateModelsResponse(
                thetaModels: [],
                curveModels: [],
                responseModels: [model]
            ),
            predictionResponse: try BundleFixtureLoader().loadResponsePredictionFixture().response
        )
        let viewModel = PredictionViewModel(apiClient: client)

        await viewModel.checkConnection(baseURL: URL(string: "http://127.0.0.1:8000")!)

        XCTAssertEqual(viewModel.connectionState, .ready(responseSurrogateAvailable: true))
        XCTAssertEqual(viewModel.responseModel?.key, DDLaminateDefaults.responseModelKey)
        XCTAssertTrue(viewModel.canPredict)
    }

    @MainActor
    func testViewModelPredictsWithMockClient() async throws {
        let fixture = try BundleFixtureLoader().loadResponsePredictionFixture()
        let model = ModelInfo(
            key: DDLaminateDefaults.responseModelKey,
            label: "ExtraTrees + PCA",
            description: "fixture model",
            inputMode: "response",
            path: "models/response_surrogate.joblib",
            available: true
        )
        let client = MockAPIClient(
            healthResponse: HealthResponse(status: "ok"),
            modelsResponse: DDLaminateModelsResponse(thetaModels: [], curveModels: [], responseModels: [model]),
            predictionResponse: fixture.response
        )
        let viewModel = PredictionViewModel(apiClient: client)

        await viewModel.checkConnection(baseURL: URL(string: "http://127.0.0.1:8000")!)
        await viewModel.predict(baseURL: URL(string: "http://127.0.0.1:8000")!)

        XCTAssertEqual(viewModel.result?.predictedType, fixture.response.predictedType)
        XCTAssertEqual(viewModel.result?.curve.count, fixture.response.curve.count)
        XCTAssertEqual(viewModel.recentRuns.first?.curve.count, fixture.response.curve.count)
        XCTAssertNil(viewModel.errorMessage)
    }

    @MainActor
    func testViewModelChecksReadinessBeforePrediction() async throws {
        let fixture = try BundleFixtureLoader().loadResponsePredictionFixture()
        let model = ModelInfo(
            key: DDLaminateDefaults.responseModelKey,
            label: "ExtraTrees + PCA",
            description: "fixture model",
            inputMode: "response",
            path: "models/response_surrogate.joblib",
            available: true
        )
        let client = MockAPIClient(
            healthResponse: HealthResponse(status: "ok"),
            modelsResponse: DDLaminateModelsResponse(thetaModels: [], curveModels: [], responseModels: [model]),
            predictionResponse: fixture.response
        )
        let viewModel = PredictionViewModel(apiClient: client)

        await viewModel.predict(baseURL: URL(string: "http://127.0.0.1:8000")!)

        XCTAssertEqual(viewModel.connectionState, .ready(responseSurrogateAvailable: true))
        XCTAssertEqual(viewModel.result?.predictedType, fixture.response.predictedType)
        XCTAssertNil(viewModel.errorMessage)
    }

    @MainActor
    func testViewModelReportsUnavailableModelBeforePrediction() async throws {
        let fixture = try BundleFixtureLoader().loadResponsePredictionFixture()
        let client = MockAPIClient(
            healthResponse: HealthResponse(status: "ok"),
            modelsResponse: DDLaminateModelsResponse(thetaModels: [], curveModels: [], responseModels: []),
            predictionResponse: fixture.response
        )
        let viewModel = PredictionViewModel(apiClient: client)

        await viewModel.predict(baseURL: URL(string: "http://127.0.0.1:8000")!)

        XCTAssertNil(viewModel.result)
        XCTAssertEqual(viewModel.errorMessage, "The selected model (ExtraTrees + PCA) is unavailable. Check the API base URL or server.")
    }
}

private struct MockAPIClient: DDLaminateAPIClientProtocol {
    let healthResponse: HealthResponse
    let modelsResponse: DDLaminateModelsResponse
    let predictionResponse: ResponsePredictionResult

    func health(baseURL: URL) async throws -> HealthResponse {
        healthResponse
    }

    func models(baseURL: URL) async throws -> DDLaminateModelsResponse {
        modelsResponse
    }

    func predictResponse(
        baseURL: URL,
        request: ResponsePredictionRequest
    ) async throws -> ResponsePredictionResult {
        predictionResponse
    }
}
