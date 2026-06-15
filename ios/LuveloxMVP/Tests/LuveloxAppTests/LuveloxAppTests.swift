import XCTest
@testable import LuveloxApp

final class LuveloxAppTests: XCTestCase {
    func testModuleContractDecodesServerShape() throws {
        let json = """
        {
          "brand": "C2ES",
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
                "base_url": "https://laminate.luvelox.com",
                "web_url": "https://laminate.luvelox.com",
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

        let response = try JSONDecoder().decode(LuveloxUserModulesResponse.self, from: json)

        XCTAssertEqual(response.brand, "C2ES")
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
            "email": "demo@luvelox.com",
            "name": "Demo Account",
            "company": "C2ES MVP"
          },
          "entitlements": ["module.laminate", "module.injection"]
        }
        """.data(using: .utf8)!

        let session = try JSONDecoder().decode(LuveloxAuthSession.self, from: json)

        XCTAssertEqual(session.accessToken, "demo-token")
        XCTAssertEqual(session.tokenType, "bearer")
        XCTAssertEqual(session.user.email, "demo@luvelox.com")
        XCTAssertEqual(session.entitlements.count, 2)
    }

    func testAccessRequestResponseDecodesServerShape() throws {
        let json = """
        {
          "status": "received",
          "module_id": "optimization",
          "message": "Access request received.",
          "user": {
            "id": "demo-user",
            "email": "demo@luvelox.com",
            "name": "Demo Account",
            "company": "C2ES MVP"
          }
        }
        """.data(using: .utf8)!

        let response = try JSONDecoder().decode(LuveloxAccessRequestResponse.self, from: json)

        XCTAssertEqual(response.status, "received")
        XCTAssertEqual(response.moduleId, "optimization")
        XCTAssertEqual(response.user?.email, "demo@luvelox.com")
    }

    func testCatalogEndpointBuildsStableURL() {
        let url = ModuleCatalogClient.endpoint(
            baseURL: URL(string: "https://laminate.luvelox.com/anything")!,
            path: "/api/v1/modules/me"
        )

        XCTAssertEqual(url.absoluteString, "https://laminate.luvelox.com/api/v1/modules/me")
    }
}
