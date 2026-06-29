import SwiftUI
import KyulAIInjectionCore

#Preview {
    ContentView()
        .environmentObject(AppSettings())
        .environmentObject(PredictionViewModel())
}
