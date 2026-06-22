import KyulAIDDLaminateCore
import SwiftUI

public struct DDLaminateModuleView: View {
    @StateObject private var settings = AppSettings()
    @StateObject private var viewModel = PredictionViewModel()
    @AppStorage("kyulai.ddLaminate.designVersion") private var designVersion = "v2"

    public init() {}

    public var body: some View {
        VStack(spacing: 0) {
            Picker("Design version", selection: $designVersion) {
                Text("v2").tag("v2")
                Text("Classic").tag("classic")
            }
            .pickerStyle(.segmented)
            .padding(.horizontal, 16)
            .padding(.top, 10)
            .padding(.bottom, 8)
            .background(Color.white.opacity(0.94))

            Group {
                if designVersion == "v2" {
                    ContentViewV2()
                } else {
                    ContentView()
                }
            }
        }
        .environmentObject(settings)
        .environmentObject(viewModel)
    }
}
