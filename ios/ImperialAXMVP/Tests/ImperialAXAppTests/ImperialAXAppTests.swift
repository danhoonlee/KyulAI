import XCTest
@testable import ImperialAXApp

final class ImperialAXAppTests: XCTestCase {
    private let sessionKey = "imperialax.auth.session.v1"
    private let sessionSavedAtKey = "imperialax.auth.saved_at.v1"

    private final class MemorySessionStore: SessionDataStore {
        var data: Data?
        func load() -> Data? { data }
        func save(_ data: Data) -> Bool {
            self.data = data
            return true
        }
        func delete() { data = nil }
    }

    private func makeSession() -> ImperialAXAuthSession {
        ImperialAXAuthSession(
            accessToken: "server-issued-token",
            tokenType: "bearer",
            user: ImperialAXAccountUser(
                id: "test-user",
                email: "test@imperialax.com",
                name: "Test Account",
                company: "ImperialAX"
            ),
            entitlements: ["module.laminate", "module.injection"]
        )
    }

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
          "access_token": "server-issued-token",
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

        XCTAssertEqual(session.accessToken, "server-issued-token")
        XCTAssertEqual(session.tokenType, "bearer")
        XCTAssertEqual(session.user.email, "demo@imperialax.com")
        XCTAssertEqual(session.entitlements.count, 2)
    }

    @MainActor
    func testExpiredStoredSessionIsClearedOnStartup() throws {
        let defaults = try makeIsolatedUserDefaults()
        let store = MemorySessionStore()
        store.data = try JSONEncoder().encode(makeSession())
        let now = Date(timeIntervalSince1970: 1_000_000)
        defaults.set(now.addingTimeInterval(-25 * 60 * 60), forKey: sessionSavedAtKey)

        let viewModel = ImperialAXHomeViewModel(
            userDefaults: defaults,
            sessionStore: store,
            sessionLifetime: 24 * 60 * 60,
            now: { now }
        )

        XCTAssertNil(viewModel.authSession)
        XCTAssertNil(store.data)
        XCTAssertNil(defaults.object(forKey: sessionSavedAtKey))
    }

    @MainActor
    func testLegacyStoredSessionGetsTimestampOnStartup() throws {
        let defaults = try makeIsolatedUserDefaults()
        let store = MemorySessionStore()
        try defaults.set(JSONEncoder().encode(makeSession()), forKey: sessionKey)
        let now = Date(timeIntervalSince1970: 1_000_000)

        let viewModel = ImperialAXHomeViewModel(
            userDefaults: defaults,
            sessionStore: store,
            sessionLifetime: 24 * 60 * 60,
            now: { now }
        )

        XCTAssertNotNil(viewModel.authSession)
        XCTAssertNotNil(store.data)
        XCTAssertNil(defaults.data(forKey: sessionKey))
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

    func testDemoLoginUsesDedicatedFixedAccountEndpoint() throws {
        let request = try ModuleCatalogClient.demoLoginRequest(
            baseURL: URL(string: "https://laminate.imperialax.com/anything")!
        )
        let payload = try XCTUnwrap(request.httpBody)
        let body = try XCTUnwrap(
            JSONSerialization.jsonObject(with: payload) as? [String: String]
        )

        XCTAssertEqual(request.httpMethod, "POST")
        XCTAssertEqual(
            request.url?.absoluteString,
            "https://laminate.imperialax.com/api/v1/modules/auth/demo-login"
        )
        XCTAssertEqual(body["email"], "demo@imperialax.com")
        XCTAssertEqual(body["password"], "")
    }

    func testWebLaunchUsesBearerRequestAndNeverPlacesSessionTokenInURL() throws {
        let request = try ModuleCatalogClient.launchCodeRequest(
            baseURL: URL(string: "https://laminate.imperialax.com")!,
            target: "admin",
            accessToken: "sensitive-session-token"
        )
        let payload = try XCTUnwrap(request.httpBody)
        let body = try XCTUnwrap(
            JSONSerialization.jsonObject(with: payload) as? [String: String]
        )

        XCTAssertEqual(request.httpMethod, "POST")
        XCTAssertEqual(
            request.url?.absoluteString,
            "https://laminate.imperialax.com/api/v1/modules/auth/launch-code"
        )
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer sensitive-session-token")
        XCTAssertFalse(request.url?.absoluteString.contains("sensitive-session-token") == true)
        XCTAssertEqual(body["target"], "admin")
    }

    private func makeIsolatedUserDefaults() throws -> UserDefaults {
        let suiteName = "ImperialAXAppTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defaults.removePersistentDomain(forName: suiteName)
        return defaults
    }
}
