import KyulAIDDLaminateApp
import KyulAIInjectionApp
import SwiftUI

@MainActor
final class LuveloxHomeViewModel: ObservableObject {
    @Published var modules: [LuveloxModule] = LuveloxFallbackCatalog.modules
    @Published var statusText = "MVP workspace"
    @Published var isLoading = false

    private let client: ModuleCatalogClient

    init(client: ModuleCatalogClient = ModuleCatalogClient()) {
        self.client = client
    }

    func refresh() async {
        isLoading = true
        defer { isLoading = false }
        do {
            let response = try await client.fetchUserModules()
            modules = response.modules
            statusText = response.licenseMode == "entitled" ? "Entitled workspace" : "MVP workspace"
        } catch {
            modules = LuveloxFallbackCatalog.modules
            statusText = "Offline catalog"
        }
    }
}

struct ContentView: View {
    @StateObject private var viewModel = LuveloxHomeViewModel()

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    header
                    introBand
                    moduleGrid
                }
                .padding(20)
            }
            .background(Color(red: 0.97, green: 0.98, blue: 0.99))
            .task {
                await viewModel.refresh()
            }
            .toolbar {
                ToolbarItem {
                    Button {
                        Task { await viewModel.refresh() }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .disabled(viewModel.isLoading)
                    .accessibilityLabel("Refresh modules")
                }
            }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Unified CAE-AI Workspace")
                .font(.caption.weight(.bold))
                .foregroundStyle(.teal)
                .textCase(.uppercase)
            Text("Luvelox")
                .font(.system(size: 54, weight: .black, design: .rounded))
                .foregroundStyle(Color(red: 0.09, green: 0.13, blue: 0.18))
            HStack(spacing: 8) {
                Circle()
                    .fill(Color.green)
                    .frame(width: 9, height: 9)
                Text(viewModel.statusText)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.secondary)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(.white.opacity(0.9), in: Capsule())
        }
    }

    private var introBand: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Prediction modules")
                .font(.title2.weight(.bold))
            Text("Open Laminate, Injection, and future CAE-AI modules from one Luvelox account.")
                .font(.body)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(18)
        .background(.white, in: RoundedRectangle(cornerRadius: 8))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(Color.black.opacity(0.08))
        )
    }

    private var moduleGrid: some View {
        LazyVStack(spacing: 14) {
            ForEach(viewModel.modules) { module in
                ModuleCard(module: module)
            }
        }
    }
}

struct ModuleCard: View {
    let module: LuveloxModule

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .center, spacing: 12) {
                icon
                VStack(alignment: .leading, spacing: 3) {
                    Text(module.category.uppercased())
                        .font(.caption2.weight(.heavy))
                        .foregroundStyle(.teal)
                    Text(module.name)
                        .font(.title3.weight(.bold))
                }
                Spacer()
                Text(module.isGranted ? "Available" : "Locked")
                    .font(.caption.weight(.heavy))
                    .foregroundStyle(module.isGranted ? .teal : .secondary)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(module.isGranted ? Color.teal.opacity(0.12) : Color.gray.opacity(0.14), in: Capsule())
            }

            Text(module.summary)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)

            tags
            capabilities

            moduleAction
        }
        .padding(18)
        .background(.white, in: RoundedRectangle(cornerRadius: 8))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(Color.black.opacity(0.08))
        )
    }

    @ViewBuilder
    private var moduleAction: some View {
        if module.id == "laminate", module.isGranted {
            NavigationLink {
                DDLaminateModuleView()
            } label: {
                actionLabel(title: "Open Laminate", systemImage: "arrow.right", enabled: true)
            }
        } else if module.id == "injection", module.isGranted {
            NavigationLink {
                InjectionModuleView()
            } label: {
                actionLabel(title: "Open Injection", systemImage: "arrow.right", enabled: true)
            }
        } else {
            Link(destination: module.route.webURL) {
                actionLabel(
                    title: module.isGranted ? "Open \(module.shortName)" : "Request access",
                    systemImage: "arrow.up.right",
                    enabled: module.isGranted
                )
            }
            .disabled(!module.isGranted)
        }
    }

    private var icon: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 8)
                .fill(Color.teal.opacity(0.12))
                .frame(width: 48, height: 48)
            Image(systemName: symbolName)
                .font(.title3.weight(.bold))
                .foregroundStyle(.teal)
        }
    }

    private var symbolName: String {
        switch module.icon {
        case "layers": "square.3.layers.3d"
        case "gauge": "gauge.with.dots.needle.bottom.50percent"
        default: "sparkles"
        }
    }

    private var tags: some View {
        FlowLayout(spacing: 8) {
            ForEach(module.tags, id: \.self) { tag in
                Text(tag)
                    .font(.caption.weight(.bold))
                    .foregroundStyle(Color(red: 0.78, green: 0.31, blue: 0.11))
                    .padding(.horizontal, 9)
                    .padding(.vertical, 6)
                    .background(Color(red: 1.0, green: 0.94, blue: 0.90), in: Capsule())
            }
        }
    }

    private var capabilities: some View {
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 8) {
            ForEach(module.capabilities.prefix(4), id: \.self) { capability in
                Text(capability.replacingOccurrences(of: "_", with: " "))
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, minHeight: 32)
                    .background(Color(red: 0.97, green: 0.98, blue: 0.99), in: RoundedRectangle(cornerRadius: 8))
            }
        }
    }

    private func actionLabel(title: String, systemImage: String, enabled: Bool) -> some View {
        HStack {
            Text(title)
            Spacer()
            Image(systemName: systemImage)
        }
        .font(.headline)
        .foregroundStyle(.white)
        .padding(.horizontal, 14)
        .frame(height: 44)
        .background(enabled ? Color(red: 0.09, green: 0.13, blue: 0.18) : Color.gray, in: RoundedRectangle(cornerRadius: 8))
    }
}

struct FlowLayout<Content: View>: View {
    let spacing: CGFloat
    @ViewBuilder var content: Content

    var body: some View {
        ViewThatFits(in: .horizontal) {
            HStack(spacing: spacing) { content }
            VStack(alignment: .leading, spacing: spacing) { content }
        }
    }
}

#Preview {
    ContentView()
}
