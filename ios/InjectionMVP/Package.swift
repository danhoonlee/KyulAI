// swift-tools-version: 6.0

import PackageDescription

let package = Package(
    name: "KyulAIInjectionMVP",
    defaultLocalization: "en",
    platforms: [
        .iOS(.v17),
        .macOS(.v14),
    ],
    products: [
        .library(
            name: "KyulAIInjectionCore",
            targets: ["KyulAIInjectionCore"]
        ),
        .library(
            name: "KyulAIInjectionApp",
            targets: ["KyulAIInjectionApp"]
        ),
        .executable(
            name: "KyulAIInjectionPreviewApp",
            targets: ["KyulAIInjectionPreview"]
        ),
    ],
    targets: [
        .target(
            name: "KyulAIInjectionCore"
        ),
        .target(
            name: "KyulAIInjectionApp",
            dependencies: ["KyulAIInjectionCore"],
            resources: [
                .process("Resources"),
            ]
        ),
        .executableTarget(
            name: "KyulAIInjectionPreview",
            dependencies: ["KyulAIInjectionApp"]
        ),
        .testTarget(
            name: "KyulAIInjectionCoreTests",
            dependencies: ["KyulAIInjectionCore"]
        ),
    ]
)
