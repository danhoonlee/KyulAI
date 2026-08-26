import KyulAIInjectionCore
import SwiftUI

public struct InjectionModuleView: View {
    @StateObject private var settings = AppSettings()
    @StateObject private var viewModel: PredictionViewModel
    private let embedInNavigationStack: Bool

    public init(embedInNavigationStack: Bool = true, accessToken: String? = nil) {
        self.embedInNavigationStack = embedInNavigationStack
        _viewModel = StateObject(
            wrappedValue: PredictionViewModel(
                apiClient: InjectionAPIClient(bearerToken: accessToken)
            )
        )
    }

    public var body: some View {
        ContentView(wrapsInNavigationStack: embedInNavigationStack)
            .environmentObject(settings)
            .environmentObject(viewModel)
    }
}
