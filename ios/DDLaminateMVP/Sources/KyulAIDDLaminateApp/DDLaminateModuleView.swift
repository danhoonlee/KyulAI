import KyulAIDDLaminateCore
import SwiftUI

public struct DDLaminateModuleView: View {
    @StateObject private var settings = AppSettings()
    @StateObject private var viewModel = PredictionViewModel()

    public init() {}

    public var body: some View {
        ContentViewV2()
        .environmentObject(settings)
        .environmentObject(viewModel)
    }
}
