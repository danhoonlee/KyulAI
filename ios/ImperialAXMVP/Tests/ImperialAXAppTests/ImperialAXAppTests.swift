import XCTest
@testable import ImperialAXApp

final class ImperialAXAppTests: XCTestCase {
    private let sessionKey = "imperialax.auth.session.v1"
    private let sessionSavedAtKey = "imperialax.auth.saved_at.v1"

    func testModuleContractDecodesServerShape() throws {
        let json = """
        {
          "brand": "ImperialAX",
          "license_mode": "demo",
          "user": null,
          "modules": [
            {
              "id": "laminate",
              "name": "Laminate",
              "short_name": "Laminate",
              "category": "Composite",
              "summary": "Predict laminate response.",
              "icon": "layers",
              "status": "active",
              "entitlement_key": "module.laminate",
              "default_enabled": true,
              "tags": ["Pt"],
              "capabilities": ["curve_chart"],
              "route": {
                "base_url": "https://laminate.imperialax.com",
                "web_url": "https://laminate.imperialax.com",
                "api_prefix": "/api/v1/dd-laminate",
                "health_path": "/health",
                "models_path": "/api/v1/dd-laminate/models",
                "primary_predict_path": "/api/v1/dd-laminate/predict/response"
              },
              "access": "granted",
              "access_reason": "Enabled"
            }
          ]
        }
        """.data(using: .utf8)!

        let response = try JSONDecoder().decode(ImperialAXUserModulesResponse.self, from: json)

        XCTAssertEqual(response.brand, "ImperialAX")
        XCTAssertEqual(response.licenseMode, "demo")
        XCTAssertNil(response.user)
        XCTAssertEqual(response.modules.first?.id, "laminate")
        XCTAssertEqual(response.modules.first?.route.modelsPath, "/api/v1/dd-laminate/models")
        XCTAssertEqual(response.modules.first?.isGranted, true)
    }

    func testAuthSessionDecodesDemoLoginResponse() throws {
        let json = """
        {
          "access_token": "demo-token",
          "token_type": "bearer",
          "user": {
            "id": "demo-user",
            "email": "demo@imperialax.com",
            "name": "Demo Account",
            "company": "ImperialAX MVP"
          },
          "entitlements": ["module.laminate", "module.injection"]
        }
        """.data(using: .utf8)!

        let session = try JSONDecoder().decode(ImperialAXAuthSession.self, from: json)

        XCTAssertEqual(session.accessToken, "demo-token")
        XCTAssertEqual(session.tokenType, "bearer")
        XCTAssertEqual(session.user.email, "demo@imperialax.com")
        XCTAssertEqual(session.entitlements.count, 2)
    }

    @MainActor
    func testExpiredStoredSessionIsClearedOnStartup() throws {
        let defaults = try makeIsolatedUserDefaults()
        try defaults.set(JSONEncoder().encode(ImperialAXAuthSession.demo), forKey: sessionKey)
        let now = Date(timeIntervalSince1970: 1_000_000)
        defaults.set(now.addingTimeInterval(-25 * 60 * 60), forKey: sessionSavedAtKey)

        let viewModel = ImperialAXHomeViewModel(
            userDefaults: defaults,
            sessionLifetime: 24 * 60 * 60,
            now: { now }
        )

        XCTAssertNil(viewModel.authSession)
        XCTAssertNil(defaults.data(forKey: sessionKey))
        XCTAssertNil(defaults.object(forKey: sessionSavedAtKey))
    }

    @MainActor
    func testLegacyStoredSessionGetsTimestampOnStartup() throws {
        let defaults = try makeIsolatedUserDefaults()
        try defaults.set(JSONEncoder().encode(ImperialAXAuthSession.demo), forKey: sessionKey)
        let now = Date(timeIntervalSince1970: 1_000_000)

        let viewModel = ImperialAXHomeViewModel(
            userDefaults: defaults,
            sessionLifetime: 24 * 60 * 60,
            now: { now }
        )

        XCTAssertNotNil(viewModel.authSession)
        XCTAssertEqual(defaults.object(forKey: sessionSavedAtKey) as? Date, now)
    }

    func testAccessRequestResponseDecodesServerShape() throws {
        let json = """
        {
          "status": "received",
          "module_id": "optimization",
          "message": "Access request received.",
          "user": {
            "id": "demo-user",
            "email": "demo@imperialax.com",
            "name": "Demo Account",
            "company": "ImperialAX MVP"
          }
        }
        """.data(using: .utf8)!

        let response = try JSONDecoder().decode(ImperialAXAccessRequestResponse.self, from: json)

        XCTAssertEqual(response.status, "received")
        XCTAssertEqual(response.moduleId, "optimization")
        XCTAssertEqual(response.user?.email, "demo@imperialax.com")
    }

    func testCatalogEndpointBuildsStableURL() {
        let url = ModuleCatalogClient.endpoint(
            baseURL: URL(string: "https://laminate.imperialax.com/anything")!,
            path: "/api/v1/modules/me"
        )

        XCTAssertEqual(url.absoluteString, "https://laminate.imperialax.com/api/v1/modules/me")
    }

    private func makeIsolatedUserDefaults() throws -> UserDefaults {
        let suiteName = "ImperialAXAppTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defaults.removePersistentDomain(forName: suiteName)
        return defaults
    }
}
