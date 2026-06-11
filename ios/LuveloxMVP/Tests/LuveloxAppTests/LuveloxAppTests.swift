import XCTest
@testable import LuveloxApp

final class LuveloxAppTests: XCTestCase {
    func testModuleContractDecodesServerShape() throws {
        let json = """
        {
          "brand": "Luvelox",
          "license_mode": "demo",
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

        XCTAssertEqual(response.brand, "Luvelox")
        XCTAssertEqual(response.licenseMode, "demo")
        XCTAssertEqual(response.modules.first?.id, "laminate")
        XCTAssertEqual(response.modules.first?.route.modelsPath, "/api/v1/dd-laminate/models")
        XCTAssertEqual(response.modules.first?.isGranted, true)
    }

    func testCatalogEndpointBuildsStableURL() {
        let url = ModuleCatalogClient.endpoint(
            baseURL: URL(string: "https://laminate.luvelox.com/anything")!,
            path: "/api/v1/modules/me"
        )

        XCTAssertEqual(url.absoluteString, "https://laminate.luvelox.com/api/v1/modules/me")
    }
}
