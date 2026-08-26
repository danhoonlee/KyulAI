import KyulAIDDLaminateCore
import SwiftUI

public struct DDLaminateModuleView: View {
    @StateObject private var settings = AppSettings()
    @StateObject private var viewModel: PredictionViewModel

    public init(accessToken: String? = nil) {
        _viewModel = StateObject(
            wrappedValue: PredictionViewModel(
                apiClient: DDLaminateAPIClient(bearerToken: accessToken)
            )
        )
    }

    public var body: some View {
        ContentViewV2()
        .environmentObject(settings)
        .environmentObject(viewModel)
    }
}
