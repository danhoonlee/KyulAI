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
        XCTAssertEqual(fixture.response.displayModelLabel, "Laminate Forecast - Machine Learning")
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
        let legacyU3Model = ModelInfo(
            key: "u3_forecast_physics",
            label: "u3 Forecast - Tree + Physics XAI",
            description: "legacy u3 model",
            inputMode: "u3_pt",
            path: "models/dd_laminate_u3_forecast_physics_v2/u3_forecast.joblib",
            available: true
        )
        let u3Models = [
            legacyU3Model,
            ModelInfo(
                key: "u3_forecast_physics_v2",
                label: "u3 Forecast - Machine Learning",
                description: "fixture u3 tree model",
                inputMode: "u3_pt",
                path: "models/dd_laminate_u3_forecast_physics_v3/u3_forecast.joblib",
                available: true
            ),
            ModelInfo(
                key: "u3_forecast_goint_physics_v2",
                label: "u3 Forecast - Deep Learning",
                description: "fixture u3 neural model",
                inputMode: "u3_pt",
                path: "models/dd_laminate_u3_forecast_physics_v3/u3_forecast_goint.pt",
                available: true
            ),
        ]
        let client = MockAPIClient(
            healthResponse: HealthResponse(status: "ok"),
            modelsResponse: DDLaminateModelsResponse(
                thetaModels: [],
                curveModels: [],
                responseModels: [model],
                u3PtModels: u3Models
            ),
            predictionResponse: try BundleFixtureLoader().loadResponsePredictionFixture().response
        )
        let userDefaults = try XCTUnwrap(UserDefaults(suiteName: "DDLaminateCoreTests.separatedRecentRuns"))
        userDefaults.removePersistentDomain(forName: "DDLaminateCoreTests.separatedRecentRuns")
        let viewModel = PredictionViewModel(apiClient: client, userDefaults: userDefaults)

        await viewModel.checkConnection(baseURL: URL(string: "http://127.0.0.1:8000")!)

        XCTAssertEqual(viewModel.connectionState, .ready(responseSurrogateAvailable: true))
        XCTAssertEqual(viewModel.responseModel?.key, DDLaminateDefaults.responseModelKey)
        XCTAssertEqual(viewModel.u3PtModels.map(\.key), DDLaminateDefaults.u3PtModelKeys)
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
        let userDefaults = try XCTUnwrap(UserDefaults(suiteName: "DDLaminateCoreTests.separatedRecentRuns"))
        userDefaults.removePersistentDomain(forName: "DDLaminateCoreTests.separatedRecentRuns")
        let viewModel = PredictionViewModel(apiClient: client, userDefaults: userDefaults)

        await viewModel.checkConnection(baseURL: URL(string: "http://127.0.0.1:8000")!)
        await viewModel.predict(baseURL: URL(string: "http://127.0.0.1:8000")!)

        XCTAssertEqual(viewModel.result?.predictedType, fixture.response.predictedType)
        XCTAssertEqual(viewModel.result?.curve.count, fixture.response.curve.count)
        XCTAssertEqual(viewModel.recentRuns.first?.curve.count, fixture.response.curve.count)
        XCTAssertNil(viewModel.errorMessage)
    }

    @MainActor
    func testViewModelRoundsThetaInputsBeforePrediction() async throws {
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
        let userDefaults = try XCTUnwrap(UserDefaults(suiteName: "DDLaminateCoreTests.integerThetaInputs"))
        userDefaults.removePersistentDomain(forName: "DDLaminateCoreTests.integerThetaInputs")
        let viewModel = PredictionViewModel(apiClient: client, userDefaults: userDefaults)
        viewModel.theta1 = "30.6"
        viewModel.theta2 = "-29.4"

        await viewModel.checkConnection(baseURL: URL(string: "http://127.0.0.1:8000")!)
        await viewModel.predict(baseURL: URL(string: "http://127.0.0.1:8000")!)

        XCTAssertEqual(viewModel.theta1, "31")
        XCTAssertEqual(viewModel.theta2, "-29")
        XCTAssertEqual(viewModel.recentRuns.first?.theta1Display, "31")
        XCTAssertEqual(viewModel.recentRuns.first?.theta2Display, "-29")
        XCTAssertNil(viewModel.errorMessage)
    }

    @MainActor
    func testViewModelSeparatesRecentRunsByForecastTab() async throws {
        let fixture = try BundleFixtureLoader().loadResponsePredictionFixture()
        let responseModel = ModelInfo(
            key: DDLaminateDefaults.responseModelKey,
            label: "Laminate Forecast - Machine Learning",
            description: "fixture response model",
            inputMode: "response",
            path: "models/response_surrogate.joblib",
            available: true
        )
        let u3Model = ModelInfo(
            key: DDLaminateDefaults.u3PtModelKey,
            label: "u3 Forecast - Machine Learning",
            description: "fixture u3 model",
            inputMode: "u3_pt",
            path: "models/dd_laminate_u3_forecast_physics_v3/u3_forecast.joblib",
            available: true
        )
        let u3Response = U3PtPredictionResult(
            predictedType: 2,
            confidence: 0.91,
            probabilities: ["type2": 0.91],
            predictedPt: 12345,
            predictedMaxDisplacement: 0.15,
            predictedMaxForce: 25000,
            curve: fixture.response.curve,
            modelKey: DDLaminateDefaults.u3PtModelKey,
            modelLabel: "u3 Forecast - Machine Learning",
            inputMode: "u3_pt",
            inputs: ["theta1": .double(30), "theta2": .double(-30), "case": .string("Case2")],
            notes: [],
            metrics: [:],
            xai: nil
        )
        let client = MockAPIClient(
            healthResponse: HealthResponse(status: "ok"),
            modelsResponse: DDLaminateModelsResponse(
                thetaModels: [],
                curveModels: [],
                responseModels: [responseModel],
                u3PtModels: [u3Model]
            ),
            predictionResponse: fixture.response,
            u3PtPredictionResponse: u3Response
        )
        let userDefaults = try XCTUnwrap(UserDefaults(suiteName: "DDLaminateCoreTests.separatedRecentRuns"))
        userDefaults.removePersistentDomain(forName: "DDLaminateCoreTests.separatedRecentRuns")
        let viewModel = PredictionViewModel(apiClient: client, userDefaults: userDefaults)

        await viewModel.checkConnection(baseURL: URL(string: "http://127.0.0.1:8000")!)
        await viewModel.predict(baseURL: URL(string: "http://127.0.0.1:8000")!)
        await viewModel.predictU3Forecast(baseURL: URL(string: "http://127.0.0.1:8000")!)

        XCTAssertEqual(viewModel.responseForecastRecentRuns.count, 1)
        XCTAssertEqual(viewModel.u3ForecastRecentRuns.count, 1)
        XCTAssertEqual(viewModel.responseForecastRecentRuns.first?.kind, .responseForecast)
        XCTAssertEqual(viewModel.u3ForecastRecentRuns.first?.kind, .u3Forecast)
        XCTAssertEqual(viewModel.responseForecastRecentRuns.first?.responseModelKey, DDLaminateDefaults.responseModelKey)
        XCTAssertEqual(viewModel.u3ForecastRecentRuns.first?.responseModelKey, DDLaminateDefaults.u3PtModelKey)
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
        XCTAssertEqual(viewModel.errorMessage, "The selected model (Laminate Forecast - Machine Learning) is unavailable. Check the API base URL or server.")
    }
}

private struct MockAPIClient: DDLaminateAPIClientProtocol {
    let healthResponse: HealthResponse
    let modelsResponse: DDLaminateModelsResponse
    let predictionResponse: ResponsePredictionResult
    let u3PtPredictionResponse: U3PtPredictionResult?

    init(
        healthResponse: HealthResponse,
        modelsResponse: DDLaminateModelsResponse,
        predictionResponse: ResponsePredictionResult,
        u3PtPredictionResponse: U3PtPredictionResult? = nil
    ) {
        self.healthResponse = healthResponse
        self.modelsResponse = modelsResponse
        self.predictionResponse = predictionResponse
        self.u3PtPredictionResponse = u3PtPredictionResponse
    }

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

    func predictU3Forecast(
        baseURL: URL,
        request: U3ForecastPredictionRequest
    ) async throws -> U3PtPredictionResult {
        if let u3PtPredictionResponse {
            return u3PtPredictionResponse
        }
        throw DDLaminateAPIError.fileRead("No u3 Forecast fixture configured.")
    }

    func predictU3Pt(
        baseURL: URL,
        case laminateCase: DDLaminateCase,
        theta1: Double,
        theta2: Double,
        u3Bucket: String,
        model: String,
        csvURL: URL
    ) async throws -> U3PtPredictionResult {
        if let u3PtPredictionResponse {
            return u3PtPredictionResponse
        }
        throw DDLaminateAPIError.fileRead("No u3 Pt fixture configured.")
    }
}
