import KyulAIDDLaminateCore
import SwiftUI

#Preview("Fixture result") {
    let settings = AppSettings()
    let viewModel = PredictionViewModel()
    viewModel.loadFixturePreview()
    return ContentView()
        .environmentObject(settings)
        .environmentObject(viewModel)
}
