import KyulAIInjectionCore
import SwiftUI

public struct InjectionModuleView: View {
    @StateObject private var settings = AppSettings()
    @StateObject private var viewModel = PredictionViewModel()

    public init() {}

    public var body: some View {
        ContentView()
            .environmentObject(settings)
            .environmentObject(viewModel)
    }
}
