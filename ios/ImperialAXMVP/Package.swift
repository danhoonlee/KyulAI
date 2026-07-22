// swift-tools-version: 6.0

import PackageDescription

let package = Package(
    name: "ImperialAXMVP",
    defaultLocalization: "en",
    platforms: [
        .iOS(.v17),
        .macOS(.v14),
    ],
    products: [
        .executable(
            name: "ImperialAXPreviewApp",
            targets: ["ImperialAXApp"]
        ),
    ],
    dependencies: [
        .package(path: "../DDLaminateMVP"),
        .package(path: "../InjectionMVP"),
    ],
    targets: [
        .executableTarget(
            name: "ImperialAXApp",
            dependencies: [
                .product(name: "KyulAIDDLaminateCore", package: "DDLaminateMVP"),
                .product(name: "KyulAIDDLaminateApp", package: "DDLaminateMVP"),
                .product(name: "KyulAIInjectionCore", package: "InjectionMVP"),
                .product(name: "KyulAIInjectionApp", package: "InjectionMVP"),
            ]
        ),
        .testTarget(
            name: "ImperialAXAppTests",
            dependencies: ["ImperialAXApp"]
        ),
    ]
)
