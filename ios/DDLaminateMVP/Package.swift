// swift-tools-version: 6.0

import PackageDescription

let package = Package(
    name: "KyulAIDDLaminateMVP",
    defaultLocalization: "en",
    platforms: [
        .iOS(.v17),
        .macOS(.v14),
    ],
    products: [
        .library(
            name: "KyulAIDDLaminateCore",
            targets: ["KyulAIDDLaminateCore"]
        ),
        .library(
            name: "KyulAIDDLaminateApp",
            targets: ["KyulAIDDLaminateApp"]
        ),
        .executable(
            name: "KyulAIDDLaminatePreviewApp",
            targets: ["KyulAIDDLaminatePreview"]
        ),
    ],
    targets: [
        .target(
            name: "KyulAIDDLaminateCore",
            resources: [
                .process("Resources"),
            ]
        ),
        .target(
            name: "KyulAIDDLaminateApp",
            dependencies: ["KyulAIDDLaminateCore"],
            resources: [
                .process("Resources"),
            ]
        ),
        .executableTarget(
            name: "KyulAIDDLaminatePreview",
            dependencies: ["KyulAIDDLaminateApp"]
        ),
        .testTarget(
            name: "KyulAIDDLaminateCoreTests",
            dependencies: ["KyulAIDDLaminateCore"]
        ),
    ]
)
