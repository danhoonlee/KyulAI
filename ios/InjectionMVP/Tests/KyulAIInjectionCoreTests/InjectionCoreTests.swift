import XCTest
@testable import KyulAIInjectionCore

final class InjectionCoreTests: XCTestCase {
    func testEndpointComposition() throws {
        let baseURL = try XCTUnwrap(URL(string: "https://injection.luvelox.com/"))

        XCTAssertEqual(
            InjectionAPIClient.endpoint(baseURL: baseURL, path: "/api/v1/simple-injection/models").absoluteString,
            "https://injection.luvelox.com/api/v1/simple-injection/models"
        )
        XCTAssertEqual(
            InjectionAPIClient.endpoint(baseURL: baseURL, path: "/api/v1/simple-injection/predict/sprue-pressure").absoluteString,
            "https://injection.luvelox.com/api/v1/simple-injection/predict/sprue-pressure"
        )
    }

    func testRequestEncodingUsesBackendContractKeys() throws {
        let request = SpruePressurePredictionRequest(
            geometryID: "G01",
            processID: "P01",
            Lmm: 154.01,
            Wmm: 97.42,
            tmm: 2.207,
            Dmm: 17.61,
            Rmm: 8.805,
            gateType: "edge_gate",
            gateSizeWidthMm: 10,
            gateSizeHeightMm: 1.5,
            meltTempC: 226.1,
            moldTempC: 61.7,
            injectionTimeS: 2.47,
            packingPressureMPa: 69.0,
            packingTimeS: 4.731
        )

        let data = try JSONEncoder().encode(request)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])

        XCTAssertEqual(object["geometry_id"] as? String, "G01")
        XCTAssertEqual(object["process_id"] as? String, "P01")
        XCTAssertEqual(object["model"] as? String, InjectionDefaults.sprueModelKey)
        XCTAssertEqual(object["filling_model"] as? String, InjectionDefaults.fillingModelKey)
        XCTAssertEqual(object["L_mm"] as? Double, 154.01)
        XCTAssertEqual(object["packing_pressure_MPa"] as? Double, 69.0)
    }

    func testRequestEncodingUsesSelectedModelKeys() throws {
        let request = SpruePressurePredictionRequest(
            geometryID: "G02",
            processID: "P04",
            model: "sprue_deeponet",
            fillingModel: "filling_goint",
            Lmm: 154.01,
            Wmm: 97.42,
            tmm: 2.207,
            Dmm: 17.61,
            Rmm: 8.805,
            gateType: "edge_gate",
            gateSizeWidthMm: 10,
            gateSizeHeightMm: 1.5,
            meltTempC: 226.1,
            moldTempC: 61.7,
            injectionTimeS: 2.47,
            packingPressureMPa: 69.0,
            packingTimeS: 4.731
        )

        let data = try JSONEncoder().encode(request)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])

        XCTAssertEqual(object["model"] as? String, "sprue_deeponet")
        XCTAssertEqual(object["filling_model"] as? String, "filling_goint")
    }

    func testPredictionResultDecodesNestedMetricsFromAPIResponse() throws {
        let json = """
        {
          "model_key": "sprue_classical",
          "model_label": "ExtraTrees + PCA",
          "filling_model_key": "filling_classical",
          "filling_model_label": "ExtraTrees histogram",
          "predicted_max_time_s": 22.0529,
          "predicted_max_pressure_MPa": 69.0,
          "curve": [
            {"time_s": 0.0, "sprue_pressure_MPa": 0.0},
            {"time_s": 3.299, "sprue_pressure_MPa": 69.0}
          ],
          "inputs": {
            "geometry_id": "G01",
            "process_id": "P01",
            "L_mm": 154.01
          },
          "metrics": {
            "cv_mode": "grouped",
            "fold_scores": [
              {
                "fold": 1,
                "n_val": 120,
                "shape_corr_mean": 0.996
              }
            ],
            "mean_curve_pressure_rmse": 2.55
          },
          "notes": [
            "Current model is trained on the full 300 planned Moldex3D runs."
          ],
          "validation_warnings": [],
          "filling_pressure": null,
          "predicted_filling_pressure": {
            "sample_id": "G01_P01",
            "source_file": "predicted_filling_pressure_surrogate",
            "stats": {
              "min_MPa": 0.0,
              "max_MPa": 35.98,
              "avg_MPa": 13.74,
              "sd_MPa": 9.618
            },
            "bins": [
              {
                "group": 1,
                "from_MPa": 0.0,
                "to_MPa": 3.598,
                "center_MPa": 1.799,
                "count": 0,
                "volume_ratio_pct": 21.678
              }
            ],
            "note": "Predicted filling pressure histogram summary; spatial mesh coordinates are not included.",
            "animation_url": null
          }
        }
        """

        let result = try JSONDecoder().decode(SpruePressurePredictionResult.self, from: Data(json.utf8))

        XCTAssertEqual(result.predictedMaxPressureMPa, 69.0)
        XCTAssertEqual(result.displayModelLabel, "ExtraTrees + PCA")
        XCTAssertEqual(result.displayFillingModelLabel, "ExtraTrees histogram")
        XCTAssertEqual(result.bestFillingPressure?.stats["max_MPa"], 35.98)
        XCTAssertEqual(result.inputs["geometry_id"]?.stringValue, "G01")
        if case .array(let foldScores)? = result.metrics["fold_scores"] {
            XCTAssertEqual(foldScores.count, 1)
        } else {
            XCTFail("Expected nested fold_scores array to decode.")
        }
    }

    func testModelDisplayLabelsRemoveRolePrefixes() {
        let sprue = ModelInfo(
            key: "sprue_classical",
            label: "Sprue Pressure - Classical ML + PCA",
            description: "fixture",
            path: "fixture",
            available: true
        )
        let filling = ModelInfo(
            key: "filling_classical",
            label: "Filling Pressure: GOInt",
            description: "fixture",
            path: "fixture",
            available: true
        )
        let alreadyClean = ModelInfo(
            key: "sprue_clean",
            label: "DeepONet",
            description: "fixture",
            path: "fixture",
            available: true
        )

        XCTAssertEqual(sprue.displayLabel, "ExtraTrees + PCA")
        XCTAssertEqual(filling.displayLabel, "GOInt")
        XCTAssertEqual(alreadyClean.displayLabel, "DeepONet")
    }

    @MainActor
    func testViewModelConnectionLoadsDoeDefaults() async {
        let model = ModelInfo(
            key: InjectionDefaults.sprueModelKey,
            label: "Classical Sprue Pressure",
            description: "fixture",
            path: "fixture",
            available: true
        )
        let fillingModel = ModelInfo(
            key: InjectionDefaults.fillingModelKey,
            label: "Classical Filling Pressure",
            description: "fixture",
            path: "fixture",
            available: true
        )
        let geometry = DoeOption(id: "G09", values: [
            "L_mm": .double(150),
            "W_mm": .double(90),
            "t_mm": .double(2.1),
            "D_mm": .double(16),
            "R_mm": .double(8),
            "gate_type": .string("edge_gate"),
            "gate_size_width_mm": .double(11),
            "gate_size_height_mm": .double(1.7),
        ])
        let process = DoeOption(id: "P03", values: [
            "melt_temp_C": .double(230),
            "mold_temp_C": .double(60),
            "injection_time_s": .double(2.5),
            "packing_pressure_MPa": .double(70),
            "packing_time_s": .double(4.5),
        ])
        let viewModel = PredictionViewModel(apiClient: MockAPIClient(
            modelsResponse: InjectionModelsResponse(spruePressureModels: [model], fillingPressureModels: [fillingModel]),
            doeResponse: InjectionDoeResponse(geometries: [geometry], processes: [process])
        ))

        await viewModel.checkConnection(baseURL: URL(string: InjectionDefaults.fallbackBaseURL)!)

        XCTAssertEqual(viewModel.geometryID, "G09")
        XCTAssertEqual(viewModel.processID, "P03")
        XCTAssertEqual(viewModel.sprueModels.map(\.key), [InjectionDefaults.sprueModelKey])
        XCTAssertEqual(viewModel.fillingModels.map(\.key), [InjectionDefaults.fillingModelKey])
        XCTAssertEqual(viewModel.Lmm, "150")
        XCTAssertEqual(viewModel.meltTempC, "230")
        XCTAssertEqual(viewModel.connectionState, .ready(sprueModelAvailable: true))
    }

    @MainActor
    func testPredictionStoresSpruePressureResult() async {
        let result = SpruePressurePredictionResult(
            modelKey: InjectionDefaults.sprueModelKey,
            modelLabel: "Classical Sprue Pressure",
            fillingModelKey: InjectionDefaults.fillingModelKey,
            fillingModelLabel: "Classical Filling Pressure",
            predictedMaxTimeS: 1.23,
            predictedMaxPressureMPa: 91.2,
            curve: [SpruePressurePoint(timeS: 0, spruePressureMPa: 10)],
            inputs: ["geometry_id": .string("G01"), "process_id": .string("P01")],
            metrics: [:],
            notes: [],
            validationWarnings: [],
            fillingPressure: nil,
            predictedFillingPressure: nil
        )
        let model = ModelInfo(
            key: InjectionDefaults.sprueModelKey,
            label: "Classical Sprue Pressure",
            description: "fixture",
            path: "fixture",
            available: true
        )
        let fillingModel = ModelInfo(
            key: InjectionDefaults.fillingModelKey,
            label: "Classical Filling Pressure",
            description: "fixture",
            path: "fixture",
            available: true
        )
        let viewModel = PredictionViewModel(apiClient: MockAPIClient(
            modelsResponse: InjectionModelsResponse(spruePressureModels: [model], fillingPressureModels: [fillingModel]),
            doeResponse: InjectionDoeResponse(geometries: [], processes: []),
            predictionResult: result
        ))

        await viewModel.checkConnection(baseURL: URL(string: InjectionDefaults.fallbackBaseURL)!)
        await viewModel.predict(baseURL: URL(string: InjectionDefaults.fallbackBaseURL)!)

        XCTAssertEqual(viewModel.result?.predictedMaxPressureMPa, 91.2)
        XCTAssertNil(viewModel.errorMessage)
    }

    @MainActor
    func testPredictionUsesSelectedModelKeys() async {
        let sprueDefault = ModelInfo(
            key: InjectionDefaults.sprueModelKey,
            label: "Classical Sprue Pressure",
            description: "fixture",
            path: "fixture",
            available: true
        )
        let sprueDeepONet = ModelInfo(
            key: "sprue_deeponet",
            label: "Sprue pressure - DeepONet",
            description: "fixture",
            path: "fixture",
            available: true
        )
        let fillingDefault = ModelInfo(
            key: InjectionDefaults.fillingModelKey,
            label: "Classical Filling Pressure",
            description: "fixture",
            path: "fixture",
            available: true
        )
        let fillingGOInt = ModelInfo(
            key: "filling_goint",
            label: "Filling pressure - GOInt",
            description: "fixture",
            path: "fixture",
            available: true
        )
        let apiClient = RecordingAPIClient(
            modelsResponse: InjectionModelsResponse(
                spruePressureModels: [sprueDefault, sprueDeepONet],
                fillingPressureModels: [fillingDefault, fillingGOInt]
            ),
            doeResponse: InjectionDoeResponse(geometries: [], processes: [])
        )
        let viewModel = PredictionViewModel(apiClient: apiClient)

        await viewModel.checkConnection(baseURL: URL(string: InjectionDefaults.fallbackBaseURL)!)
        viewModel.selectSprueModel(key: "sprue_deeponet")
        viewModel.selectFillingModel(key: "filling_goint")
        await viewModel.predict(baseURL: URL(string: InjectionDefaults.fallbackBaseURL)!)

        XCTAssertEqual(apiClient.lastRequest?.model, "sprue_deeponet")
        XCTAssertEqual(apiClient.lastRequest?.fillingModel, "filling_goint")
        XCTAssertNil(viewModel.errorMessage)
    }
}

private struct MockAPIClient: InjectionAPIClientProtocol {
    var modelsResponse: InjectionModelsResponse
    var doeResponse: InjectionDoeResponse
    var predictionResult: SpruePressurePredictionResult = SpruePressurePredictionResult(
        modelKey: InjectionDefaults.sprueModelKey,
        modelLabel: "Classical Sprue Pressure",
        fillingModelKey: InjectionDefaults.fillingModelKey,
        fillingModelLabel: "Classical Filling Pressure",
        predictedMaxTimeS: 1,
        predictedMaxPressureMPa: 80,
        curve: [],
        inputs: [:],
        metrics: [:],
        notes: [],
        validationWarnings: [],
        fillingPressure: nil,
        predictedFillingPressure: nil
    )

    func health(baseURL: URL) async throws -> HealthResponse {
        HealthResponse(status: "ok")
    }

    func models(baseURL: URL) async throws -> InjectionModelsResponse {
        modelsResponse
    }

    func doe(baseURL: URL) async throws -> InjectionDoeResponse {
        doeResponse
    }

    func predictSpruePressure(baseURL: URL, request: SpruePressurePredictionRequest) async throws -> SpruePressurePredictionResult {
        predictionResult
    }
}

private final class RecordingAPIClient: InjectionAPIClientProtocol, @unchecked Sendable {
    let modelsResponse: InjectionModelsResponse
    let doeResponse: InjectionDoeResponse
    let predictionResult: SpruePressurePredictionResult
    nonisolated(unsafe) var lastRequest: SpruePressurePredictionRequest?

    init(
        modelsResponse: InjectionModelsResponse,
        doeResponse: InjectionDoeResponse,
        predictionResult: SpruePressurePredictionResult = SpruePressurePredictionResult(
            modelKey: InjectionDefaults.sprueModelKey,
            modelLabel: "Classical Sprue Pressure",
            fillingModelKey: InjectionDefaults.fillingModelKey,
            fillingModelLabel: "Classical Filling Pressure",
            predictedMaxTimeS: 1,
            predictedMaxPressureMPa: 80,
            curve: [],
            inputs: [:],
            metrics: [:],
            notes: [],
            validationWarnings: [],
            fillingPressure: nil,
            predictedFillingPressure: nil
        )
    ) {
        self.modelsResponse = modelsResponse
        self.doeResponse = doeResponse
        self.predictionResult = predictionResult
    }

    func health(baseURL: URL) async throws -> HealthResponse {
        HealthResponse(status: "ok")
    }

    func models(baseURL: URL) async throws -> InjectionModelsResponse {
        modelsResponse
    }

    func doe(baseURL: URL) async throws -> InjectionDoeResponse {
        doeResponse
    }

    func predictSpruePressure(baseURL: URL, request: SpruePressurePredictionRequest) async throws -> SpruePressurePredictionResult {
        lastRequest = request
        return predictionResult
    }
}
