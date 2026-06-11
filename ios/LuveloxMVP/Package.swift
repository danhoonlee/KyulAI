// swift-tools-version: 6.0

import PackageDescription

let package = Package(
    name: "LuveloxMVP",
    defaultLocalization: "en",
    platforms: [
        .iOS(.v17),
        .macOS(.v14),
    ],
    products: [
        .executable(
            name: "LuveloxPreviewApp",
            targets: ["LuveloxApp"]
        ),
    ],
    dependencies: [
        .package(path: "../DDLaminateMVP"),
        .package(path: "../InjectionMVP"),
    ],
    targets: [
        .executableTarget(
            name: "LuveloxApp",
            dependencies: [
                .product(name: "KyulAIDDLaminateCore", package: "DDLaminateMVP"),
                .product(name: "KyulAIDDLaminateApp", package: "DDLaminateMVP"),
                .product(name: "KyulAIInjectionCore", package: "InjectionMVP"),
                .product(name: "KyulAIInjectionApp", package: "InjectionMVP"),
            ]
        ),
        .testTarget(
            name: "LuveloxAppTests",
            dependencies: ["LuveloxApp"]
        ),
    ]
)
