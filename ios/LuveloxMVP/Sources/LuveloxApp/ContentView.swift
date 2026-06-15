import KyulAIDDLaminateApp
import KyulAIInjectionApp
import SwiftUI
#if os(iOS)
import UIKit
#endif

@MainActor
final class LuveloxHomeViewModel: ObservableObject {
    @Published var modules: [LuveloxModule] = LuveloxFallbackCatalog.modules
    @Published var statusText = "Signed out"
    @Published var isLoading = false
    @Published var authSession: LuveloxAuthSession?
    @Published var loginError: String?
    @Published var accessRequestMessage: String?

    private let client: ModuleCatalogClient
    private let sessionKey = "luvelox.auth.session.v1"
    private let userDefaults: UserDefaults

    init(
        client: ModuleCatalogClient = ModuleCatalogClient(),
        userDefaults: UserDefaults = .standard
    ) {
        self.client = client
        self.userDefaults = userDefaults
        self.authSession = Self.loadSession(from: userDefaults, key: sessionKey)
        self.statusText = authSession == nil ? "Signed out" : "Loading workspace"
    }

    func refresh() async {
        guard let authSession else {
            modules = LuveloxFallbackCatalog.modules.map { module in
                LuveloxModule(
                    id: module.id,
                    name: module.name,
                    shortName: module.shortName,
                    category: module.category,
                    summary: module.summary,
                    icon: module.icon,
                    status: module.status,
                    entitlementKey: module.entitlementKey,
                    defaultEnabled: module.defaultEnabled,
                    tags: module.tags,
                    capabilities: module.capabilities,
                    route: module.route,
                    access: "locked",
                    accessReason: "Sign in to use this module."
                )
            }
            statusText = "Signed out"
            return
        }
        isLoading = true
        defer { isLoading = false }
        do {
            let response = try await client.fetchUserModules(authSession: authSession)
            modules = response.modules
            statusText = response.licenseMode == "entitled" ? "Account workspace" : "Demo workspace"
        } catch {
            modules = LuveloxFallbackCatalog.modules
            statusText = "Offline account"
        }
    }

    func signIn(email: String, password: String) async {
        isLoading = true
        loginError = nil
        defer { isLoading = false }
        let normalizedEmail = email.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        do {
            let session = try await client.demoLogin(email: normalizedEmail, password: password)
            setSession(session)
        } catch {
            if normalizedEmail == "danlee@luvelox.com" {
                setSession(.danlee)
            } else if normalizedEmail == "demo@luvelox.com" || normalizedEmail.isEmpty {
                setSession(.demo)
            } else {
                loginError = "Use demo@luvelox.com for the MVP account."
                return
            }
        }
        await refresh()
    }

    func signOut() {
        authSession = nil
        accessRequestMessage = nil
        userDefaults.removeObject(forKey: sessionKey)
        modules = LuveloxFallbackCatalog.modules.map { module in
            LuveloxModule(
                id: module.id,
                name: module.name,
                shortName: module.shortName,
                category: module.category,
                summary: module.summary,
                icon: module.icon,
                status: module.status,
                entitlementKey: module.entitlementKey,
                defaultEnabled: module.defaultEnabled,
                tags: module.tags,
                capabilities: module.capabilities,
                route: module.route,
                access: "locked",
                accessReason: "Sign in to use this module."
            )
        }
        statusText = "Signed out"
    }

    func requestAccess(to module: LuveloxModule) async {
        isLoading = true
        accessRequestMessage = nil
        defer { isLoading = false }
        do {
            let response = try await client.requestAccess(
                moduleId: module.id,
                message: "Requested from C2ES mobile app.",
                authSession: authSession
            )
            accessRequestMessage = response.message
        } catch {
            accessRequestMessage = "Request saved locally. We could not reach the C2ES server right now."
        }
    }

    private func setSession(_ session: LuveloxAuthSession) {
        let normalizedSession = Self.normalizedSession(session)
        authSession = normalizedSession
        if let data = try? JSONEncoder().encode(normalizedSession) {
            userDefaults.set(data, forKey: sessionKey)
        }
    }

    private static func loadSession(from userDefaults: UserDefaults, key: String) -> LuveloxAuthSession? {
        guard let data = userDefaults.data(forKey: key) else { return nil }
        guard let session = try? JSONDecoder().decode(LuveloxAuthSession.self, from: data) else { return nil }
        return normalizedSession(session)
    }

    private static func normalizedSession(_ session: LuveloxAuthSession) -> LuveloxAuthSession {
        let normalizedName: String
        switch session.user.name.trimmingCharacters(in: .whitespacesAndNewlines) {
        case "Luvelox Demo", "C2ES Demo":
            normalizedName = "Demo Account"
        case "Luvelox Account":
            normalizedName = "C2ES Account"
        default:
            normalizedName = session.user.name
        }
        let user = LuveloxAccountUser(
            id: session.user.id,
            email: session.user.email,
            name: normalizedName,
            company: session.user.company
        )
        return LuveloxAuthSession(
            accessToken: session.accessToken,
            tokenType: session.tokenType,
            user: user,
            entitlements: session.entitlements
        )
    }
}

struct ContentView: View {
    @StateObject private var viewModel = LuveloxHomeViewModel()
    @State private var email = "demo@luvelox.com"
    @State private var password = ""
    @State private var isAccountSheetPresented = false
    @State private var selectedLockedModule: LuveloxModule?

    var body: some View {
        NavigationStack {
            Group {
                if viewModel.authSession == nil {
                    loginScreen
                } else {
                    homeScreen
                }
            }
            .background(Color(red: 0.97, green: 0.98, blue: 0.99))
            .task {
                await viewModel.refresh()
            }
            .toolbar {
                ToolbarItem {
                    if viewModel.authSession == nil {
                        EmptyView()
                    } else {
                        Menu {
                            Button {
                                isAccountSheetPresented = true
                            } label: {
                                Label("Account details", systemImage: "person.text.rectangle")
                            }
                            Button {
                                Task { await viewModel.refresh() }
                            } label: {
                                Label("Refresh modules", systemImage: "arrow.clockwise")
                            }
                            Button(role: .destructive) {
                                viewModel.signOut()
                            } label: {
                                Label("Sign out", systemImage: "rectangle.portrait.and.arrow.right")
                            }
                        } label: {
                            Image(systemName: "person.crop.circle")
                        }
                        .disabled(viewModel.isLoading)
                        .accessibilityLabel("Account")
                    }
                }
            }
            .sheet(isPresented: $isAccountSheetPresented) {
                AccountDetailsSheet(
                    session: viewModel.authSession,
                    modules: viewModel.modules,
                    onRefresh: {
                        Task { await viewModel.refresh() }
                    },
                    onSignOut: {
                        isAccountSheetPresented = false
                        viewModel.signOut()
                    }
                )
            }
            .sheet(item: $selectedLockedModule) { module in
                LockedModuleSheet(
                    module: module,
                    requestMessage: viewModel.accessRequestMessage,
                    isLoading: viewModel.isLoading,
                    onRequestAccess: {
                        Task { await viewModel.requestAccess(to: module) }
                    }
                )
            }
        }
    }

    private var loginScreen: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                Spacer(minLength: 24)
                VStack(alignment: .leading, spacing: 10) {
                    Text("C2ES")
                        .font(.system(size: 54, weight: .black, design: .rounded))
                        .foregroundStyle(Color(red: 0.09, green: 0.13, blue: 0.18))
                    Text("Sign in to your CAE-AI workspace")
                        .font(.title3.weight(.semibold))
                    Text("Use a C2ES account to open licensed prediction modules from one app.")
                        .font(.body)
                        .foregroundStyle(.secondary)
                }

                VStack(alignment: .leading, spacing: 14) {
                    Text("Account")
                        .font(.headline)
                    TextField("Email", text: $email)
                        #if os(iOS)
                        .textInputAutocapitalization(.never)
                        .keyboardType(.emailAddress)
                        #endif
                        .autocorrectionDisabled()
                        .fieldStyle()
                    SecureField("Password", text: $password)
                        .fieldStyle()
                    if let loginError = viewModel.loginError {
                        Text(loginError)
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.red)
                    }
                    Button {
                        Task { await viewModel.signIn(email: email, password: password) }
                    } label: {
                        HStack {
                            Text(viewModel.isLoading ? "Signing in" : "Sign in")
                            Spacer()
                            Image(systemName: "arrow.right")
                        }
                        .font(.headline)
                        .foregroundStyle(.white)
                        .padding(.horizontal, 14)
                        .frame(height: 46)
                        .background(Color(red: 0.09, green: 0.13, blue: 0.18), in: RoundedRectangle(cornerRadius: 8))
                    }
                    .disabled(viewModel.isLoading)

                    Button {
                        email = "demo@luvelox.com"
                        password = ""
                        Task { await viewModel.signIn(email: email, password: password) }
                    } label: {
                        Text("Continue with demo account")
                            .font(.subheadline.weight(.bold))
                            .frame(maxWidth: .infinity)
                            .frame(height: 42)
                    }
                    .foregroundStyle(.teal)
                    .background(Color.teal.opacity(0.10), in: RoundedRectangle(cornerRadius: 8))
                    .disabled(viewModel.isLoading)
                }
                .padding(18)
                .background(.white, in: RoundedRectangle(cornerRadius: 8))
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.black.opacity(0.08)))

                Text("MVP accounts: demo@luvelox.com or danlee@luvelox.com")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding(20)
        }
    }

    private var homeScreen: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                header
                Button {
                    isAccountSheetPresented = true
                } label: {
                    accountBand
                }
                .buttonStyle(.plain)
                introBand
                moduleGrid
            }
            .padding(20)
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Unified CAE-AI Workspace")
                .font(.caption.weight(.bold))
                .foregroundStyle(.teal)
                .textCase(.uppercase)
            Text("C2ES")
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

    private var accountBand: some View {
        HStack(spacing: 12) {
            ZStack {
                Circle()
                    .fill(Color.teal.opacity(0.12))
                    .frame(width: 42, height: 42)
                Image(systemName: "person.fill")
                    .foregroundStyle(.teal)
            }
            VStack(alignment: .leading, spacing: 2) {
                Text(viewModel.authSession?.user.name ?? "C2ES Account")
                    .font(.headline)
                Text(viewModel.authSession?.user.email ?? "")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Text("\(viewModel.authSession?.entitlements.count ?? 0) modules")
                .font(.caption.weight(.heavy))
                .foregroundStyle(.teal)
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(Color.teal.opacity(0.12), in: Capsule())
        }
        .padding(16)
        .background(.white, in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.black.opacity(0.08)))
    }

    private var introBand: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Prediction modules")
                .font(.title2.weight(.bold))
            Text("Open Laminate, Injection, and future CAE-AI modules from one C2ES account.")
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
                ModuleCard(module: module) {
                    viewModel.accessRequestMessage = nil
                    selectedLockedModule = module
                }
            }
        }
    }
}

struct ModuleCard: View {
    let module: LuveloxModule
    let onRequestAccess: () -> Void

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
            Button {
                if module.isGranted {
                    #if os(iOS)
                    UIApplication.shared.open(module.route.webURL)
                    #endif
                } else {
                    onRequestAccess()
                }
            } label: {
                actionLabel(
                    title: module.isGranted ? "Open \(module.shortName)" : "Request access",
                    systemImage: module.isGranted ? "arrow.up.right" : "lock.open",
                    enabled: true
                )
            }
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

struct AccountDetailsSheet: View {
    let session: LuveloxAuthSession?
    let modules: [LuveloxModule]
    let onRefresh: () -> Void
    let onSignOut: () -> Void
    @Environment(\.dismiss) private var dismiss

    private var grantedModules: [LuveloxModule] {
        modules.filter(\.isGranted)
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    accountHeader
                    entitlementSummary
                    moduleAccessList
                }
                .padding(20)
            }
            .background(Color(red: 0.97, green: 0.98, blue: 0.99))
            .navigationTitle("Account")
            #if os(iOS)
            .navigationBarTitleDisplayMode(.inline)
            #endif
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Done") { dismiss() }
                }
                ToolbarItem {
                    Button {
                        onRefresh()
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .accessibilityLabel("Refresh")
                }
            }
        }
        #if os(iOS)
        .presentationDetents([.medium, .large])
        #endif
    }

    private var accountHeader: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(session?.user.name ?? "C2ES Account")
                .font(.title2.weight(.bold))
            Text(session?.user.email ?? "No active session")
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(.secondary)
            if let company = session?.user.company {
                Text(company)
                    .font(.caption.weight(.bold))
                    .foregroundStyle(.teal)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(Color.teal.opacity(0.12), in: Capsule())
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(18)
        .background(.white, in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.black.opacity(0.08)))
    }

    private var entitlementSummary: some View {
        HStack(spacing: 12) {
            summaryTile(title: "Licensed", value: "\(grantedModules.count)")
            summaryTile(title: "Visible", value: "\(modules.count)")
        }
    }

    private func summaryTile(title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(value)
                .font(.title.weight(.black))
                .foregroundStyle(Color(red: 0.09, green: 0.13, blue: 0.18))
            Text(title)
                .font(.caption.weight(.bold))
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .background(.white, in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.black.opacity(0.08)))
    }

    private var moduleAccessList: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Module access")
                .font(.headline)
            ForEach(modules) { module in
                HStack(spacing: 12) {
                    Image(systemName: module.isGranted ? "checkmark.seal.fill" : "lock.fill")
                        .foregroundStyle(module.isGranted ? .teal : .secondary)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(module.name)
                            .font(.subheadline.weight(.bold))
                        Text(module.accessReason ?? module.entitlementKey)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                    Text(module.isGranted ? "On" : "Locked")
                        .font(.caption.weight(.heavy))
                        .foregroundStyle(module.isGranted ? .teal : .secondary)
                }
                .padding(12)
                .background(Color(red: 0.97, green: 0.98, blue: 0.99), in: RoundedRectangle(cornerRadius: 8))
            }
            Button(role: .destructive) {
                onSignOut()
            } label: {
                Label("Sign out", systemImage: "rectangle.portrait.and.arrow.right")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .frame(height: 44)
            }
            .buttonStyle(.bordered)
        }
        .padding(18)
        .background(.white, in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.black.opacity(0.08)))
    }
}

struct LockedModuleSheet: View {
    let module: LuveloxModule
    let requestMessage: String?
    let isLoading: Bool
    let onRequestAccess: () -> Void
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    VStack(alignment: .leading, spacing: 10) {
                        Text(module.category.uppercased())
                            .font(.caption.weight(.heavy))
                            .foregroundStyle(.teal)
                        Text(module.name)
                            .font(.largeTitle.weight(.black))
                        Text(module.summary)
                            .font(.body)
                            .foregroundStyle(.secondary)
                    }
                    .padding(18)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(.white, in: RoundedRectangle(cornerRadius: 8))
                    .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.black.opacity(0.08)))

                    VStack(alignment: .leading, spacing: 10) {
                        Text("Access")
                            .font(.headline)
                        Text(module.accessReason ?? "This module requires a C2ES license.")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                        Text("Entitlement: \(module.entitlementKey)")
                            .font(.caption.weight(.bold))
                            .foregroundStyle(.secondary)
                    }
                    .padding(18)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(.white, in: RoundedRectangle(cornerRadius: 8))
                    .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.black.opacity(0.08)))

                    VStack(alignment: .leading, spacing: 12) {
                        Text("Included capabilities")
                            .font(.headline)
                        ForEach(module.capabilities, id: \.self) { capability in
                            Label(capability.replacingOccurrences(of: "_", with: " "), systemImage: "checkmark.circle")
                                .font(.subheadline.weight(.semibold))
                                .foregroundStyle(.secondary)
                        }
                    }
                    .padding(18)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(.white, in: RoundedRectangle(cornerRadius: 8))
                    .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.black.opacity(0.08)))

                    Button {
                        onRequestAccess()
                    } label: {
                        HStack {
                            Text(isLoading ? "Sending request" : "Request access")
                            Spacer()
                            Image(systemName: "paperplane.fill")
                        }
                        .font(.headline)
                        .foregroundStyle(.white)
                        .padding(.horizontal, 14)
                        .frame(height: 46)
                        .background(Color(red: 0.09, green: 0.13, blue: 0.18), in: RoundedRectangle(cornerRadius: 8))
                    }
                    .disabled(isLoading)

                    if let requestMessage {
                        Text(requestMessage)
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(.teal)
                            .padding(14)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(Color.teal.opacity(0.10), in: RoundedRectangle(cornerRadius: 8))
                    }
                }
                .padding(20)
            }
            .background(Color(red: 0.97, green: 0.98, blue: 0.99))
            .navigationTitle("Module access")
            #if os(iOS)
            .navigationBarTitleDisplayMode(.inline)
            #endif
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Done") { dismiss() }
                }
            }
        }
        #if os(iOS)
        .presentationDetents([.medium, .large])
        #endif
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

private extension View {
    func fieldStyle() -> some View {
        self
            .font(.body.weight(.semibold))
            .padding(.horizontal, 12)
            .frame(height: 46)
            .background(Color(red: 0.96, green: 0.98, blue: 0.99), in: RoundedRectangle(cornerRadius: 8))
    }
}

#Preview {
    ContentView()
}
