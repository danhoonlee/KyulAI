import KyulAIDDLaminateApp
import KyulAIInjectionApp
import SwiftUI
#if os(iOS)
import UIKit
import WebKit
#endif

private enum LuveloxStyle {
    static let background = Color(red: 0.96, green: 0.97, blue: 0.99)
    static let surface = Color.white
    static let surfaceStrong = Color(red: 0.98, green: 0.99, blue: 1.0)
    static let ink = Color(red: 0.055, green: 0.067, blue: 0.086)
    static let muted = Color(red: 0.40, green: 0.45, blue: 0.53)
    static let line = Color(red: 0.87, green: 0.90, blue: 0.94)
    static let blue = Color(red: 0.13, green: 0.40, blue: 1.0)
    static let blueSoft = Color(red: 0.91, green: 0.94, blue: 1.0)
    static let teal = Color(red: 0.03, green: 0.56, blue: 0.61)
    static let tealSoft = Color(red: 0.89, green: 0.97, blue: 0.97)
    static let amber = Color(red: 0.76, green: 0.48, blue: 0.09)
    static let amberSoft = Color(red: 1.0, green: 0.96, blue: 0.87)
    static let green = Color(red: 0.0, green: 0.66, blue: 0.47)
    static let greenSoft = Color(red: 0.86, green: 0.97, blue: 0.94)
}

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
            modules = response.modules.map(Self.normalizedModuleCopy)
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

    func signUp(email: String, password: String, name: String, company: String) async {
        isLoading = true
        loginError = nil
        defer { isLoading = false }
        let normalizedEmail = email.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        let normalizedName = name.trimmingCharacters(in: .whitespacesAndNewlines)
        let normalizedCompany = company.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !normalizedEmail.isEmpty, !normalizedName.isEmpty, password.count >= 8 else {
            loginError = "Enter a name and a password with at least 8 characters."
            return
        }
        do {
            let session = try await client.signup(
                email: normalizedEmail,
                password: password,
                name: normalizedName,
                company: normalizedCompany.isEmpty ? nil : normalizedCompany
            )
            setSession(session)
        } catch {
            loginError = "Could not create this account. Try another email or password."
            return
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
                message: "Requested from Luvelox mobile app.",
                authSession: authSession
            )
            accessRequestMessage = response.message
        } catch {
            accessRequestMessage = "Request saved locally. We could not reach the Luvelox server right now."
        }
    }

    private func setSession(_ session: LuveloxAuthSession) {
        let normalizedSession = Self.normalizedSession(session)
        authSession = normalizedSession
        if let data = try? JSONEncoder().encode(normalizedSession) {
            userDefaults.set(data, forKey: sessionKey)
        }
    }

    private static func normalizedModuleCopy(_ module: LuveloxModule) -> LuveloxModule {
        let normalized: (name: String, shortName: String, category: String, summary: String, tags: [String], accessReason: String?)
        let route: LuveloxModuleRoute

        switch module.id {
        case "laminate":
            normalized = (
                "Laminate",
                "Laminate",
                "Composite",
                "Predict Type, Pt, and response curve.",
                ["Double-Double", "Pt", "Force-displacement"],
                "Available in the Luvelox MVP workspace."
            )
            route = module.route
        case "injection":
            normalized = (
                "Injection",
                "Injection",
                "Molding",
                "Predict sprue and filling pressure.",
                ["Moldex3D", "Sprue pressure", "Filling pressure"],
                "Available in the Luvelox MVP workspace."
            )
            route = module.route
        case "optimization":
            normalized = (
                "Optimization",
                "Optimize",
                "Design",
                "Rank promising design candidates.",
                ["DOE", "Ranking", "Design space"],
                "Planned module; not available in this workspace yet."
            )
            route = LuveloxModuleRoute(
                baseURL: module.route.baseURL,
                webURL: URL(string: "https://ai.luvelox.com")!,
                apiPrefix: module.route.apiPrefix,
                healthPath: module.route.healthPath,
                modelsPath: module.route.modelsPath,
                primaryPredictPath: module.route.primaryPredictPath
            )
        case "admin":
            normalized = (
                "Admin",
                "Admin",
                "Account",
                "Manage users and module access.",
                ["Users", "Access", "Admin"],
                "Visible only to Luvelox admin accounts."
            )
            route = LuveloxModuleRoute(
                baseURL: module.route.baseURL,
                webURL: URL(string: "https://ai.luvelox.com/admin.html")!,
                apiPrefix: module.route.apiPrefix,
                healthPath: module.route.healthPath,
                modelsPath: module.route.modelsPath,
                primaryPredictPath: module.route.primaryPredictPath
            )
        default:
            return module
        }

        return LuveloxModule(
            id: module.id,
            name: normalized.name,
            shortName: normalized.shortName,
            category: normalized.category,
            summary: normalized.summary,
            icon: module.icon,
            status: module.status,
            entitlementKey: module.entitlementKey,
            defaultEnabled: module.defaultEnabled,
            tags: normalized.tags,
            capabilities: module.capabilities,
            route: route,
            access: module.access,
            accessReason: normalized.accessReason
        )
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
            normalizedName = "Luvelox Account"
        default:
            normalizedName = session.user.name
        }
        let user = LuveloxAccountUser(
            id: session.user.id,
            email: session.user.email,
            name: normalizedName,
            company: session.user.company
        )
        var entitlements = session.entitlements
        if ["danlee@luvelox.com", "dannylee9295@gmail.com"].contains(session.user.email.lowercased()),
           !entitlements.contains("module.admin") {
            entitlements.append("module.admin")
        }
        return LuveloxAuthSession(
            accessToken: session.accessToken,
            tokenType: session.tokenType,
            user: user,
            entitlements: entitlements
        )
    }
}

struct ContentView: View {
    @StateObject private var viewModel = LuveloxHomeViewModel()
    @State private var email = "demo@luvelox.com"
    @State private var password = ""
    @State private var signupName = ""
    @State private var signupCompany = ""
    @State private var authMode = AuthMode.login
    @State private var isAccountSheetPresented = false
    @State private var selectedLockedModule: LuveloxModule?

    private enum AuthMode {
        case login
        case signup
    }

    private var accountChipText: String {
        if let user = viewModel.authSession?.user {
            return "\(user.name) · \(viewModel.authSession?.entitlements.count ?? 0) modules"
        }
        return viewModel.statusText
    }

    var body: some View {
        NavigationStack {
            Group {
                if viewModel.authSession == nil {
                    loginScreen
                } else {
                    homeScreen
                }
            }
            .background(LuveloxStyle.background)
            .task {
                await viewModel.refresh()
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
            VStack(alignment: .leading, spacing: 14) {
                VStack(alignment: .leading, spacing: 16) {
                    Text("C2ES AI Workspace")
                        .font(.caption.weight(.heavy))
                        .foregroundStyle(LuveloxStyle.blue)
                        .textCase(.uppercase)
                    Text("C2ES\nForecast Workspace")
                        .font(.system(size: 42, weight: .black, design: .rounded))
                        .lineSpacing(0)
                        .foregroundStyle(LuveloxStyle.ink)
                        .minimumScaleFactor(0.78)
                    Text("Sign in once, then open the prediction module built for each engineering analysis.")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(LuveloxStyle.muted)
                        .fixedSize(horizontal: false, vertical: true)
                    LoginModulePreviewStrip()
                }
                .padding(18)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(LuveloxStyle.surface, in: RoundedRectangle(cornerRadius: 8))
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(LuveloxStyle.line))
                .shadow(color: Color.black.opacity(0.06), radius: 18, y: 10)

                VStack(alignment: .leading, spacing: 12) {
                    Text("Account")
                        .font(.caption.weight(.heavy))
                        .foregroundStyle(LuveloxStyle.blue)
                        .textCase(.uppercase)
                    Text(authMode == .signup ? "Create account" : "Sign in")
                        .font(.title2.weight(.black))
                    if authMode == .signup {
                        TextField("Name", text: $signupName)
                            .textContentType(.name)
                            .fieldStyle()
                        TextField("Company", text: $signupCompany)
                            .textContentType(.organizationName)
                            .fieldStyle()
                    }
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
                        Task {
                            if authMode == .signup {
                                await viewModel.signUp(
                                    email: email,
                                    password: password,
                                    name: signupName,
                                    company: signupCompany
                                )
                            } else {
                                await viewModel.signIn(email: email, password: password)
                            }
                        }
                    } label: {
                        HStack {
                            Text(viewModel.isLoading ? "Working" : authMode == .signup ? "Create account" : "Sign in")
                            Spacer()
                            Image(systemName: "arrow.right")
                        }
                        .font(.headline)
                        .foregroundStyle(.white)
                        .padding(.horizontal, 14)
                        .frame(height: 46)
                        .background(LuveloxStyle.ink, in: RoundedRectangle(cornerRadius: 8))
                    }
                    .disabled(viewModel.isLoading)

                    Button {
                        authMode = authMode == .signup ? .login : .signup
                        viewModel.loginError = nil
                    } label: {
                        Text(authMode == .signup ? "Use existing account" : "Create a new account")
                            .font(.subheadline.weight(.bold))
                            .frame(maxWidth: .infinity)
                            .frame(height: 42)
                    }
                    .foregroundStyle(LuveloxStyle.blue)
                    .background(LuveloxStyle.blueSoft, in: RoundedRectangle(cornerRadius: 8))
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
                    .foregroundStyle(LuveloxStyle.teal)
                    .background(LuveloxStyle.tealSoft, in: RoundedRectangle(cornerRadius: 8))
                    .disabled(viewModel.isLoading)

                    Text(authMode == .signup ? "Use at least 8 characters to create an account." : "New accounts include Laminate and Injection access.")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(LuveloxStyle.muted)
                }
                .padding(18)
                .background(LuveloxStyle.surface, in: RoundedRectangle(cornerRadius: 8))
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(LuveloxStyle.line))
                .shadow(color: Color.black.opacity(0.06), radius: 18, y: 10)
            }
            .padding(20)
        }
    }

    private var homeScreen: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                workspaceHero
                WorkspaceSummaryStrip()
                introBand
                moduleGrid
            }
            .padding(20)
        }
    }

    private var workspaceHero: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("C2ES AI Workspace")
                .font(.caption.weight(.heavy))
                .foregroundStyle(LuveloxStyle.blue)
                .textCase(.uppercase)
            Text("C2ES\nForecast Workspace")
                .font(.system(size: 42, weight: .black, design: .rounded))
                .lineSpacing(0)
                .foregroundStyle(LuveloxStyle.ink)
                .minimumScaleFactor(0.78)
            Text("Choose a module to open its prediction screen.")
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(LuveloxStyle.muted)

            HStack(spacing: 8) {
                Button {
                    isAccountSheetPresented = true
                } label: {
                    HStack(spacing: 8) {
                        Circle()
                            .fill(LuveloxStyle.green)
                            .frame(width: 9, height: 9)
                        Text(accountChipText)
                            .lineLimit(1)
                    }
                    .font(.caption.weight(.heavy))
                    .foregroundStyle(Color(red: 0.03, green: 0.47, blue: 0.34))
                    .padding(.horizontal, 12)
                    .frame(height: 38)
                    .background(LuveloxStyle.greenSoft, in: Capsule())
                }
                Button {
                    viewModel.signOut()
                } label: {
                    Text("Sign out")
                        .font(.caption.weight(.heavy))
                        .foregroundStyle(LuveloxStyle.muted)
                        .padding(.horizontal, 12)
                        .frame(height: 38)
                        .background(LuveloxStyle.surfaceStrong, in: Capsule())
                        .overlay(Capsule().stroke(LuveloxStyle.line))
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(18)
        .background(LuveloxStyle.surface, in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(LuveloxStyle.line))
        .shadow(color: Color.black.opacity(0.06), radius: 18, y: 10)
    }

    private var introBand: some View {
        HStack(alignment: .center, spacing: 12) {
            VStack(alignment: .leading, spacing: 5) {
                Text("Module workspace")
                    .font(.caption.weight(.heavy))
                    .foregroundStyle(Color(red: 0.51, green: 0.95, blue: 0.81))
                    .textCase(.uppercase)
                Text("Prediction modules")
                    .font(.title2.weight(.black))
                    .foregroundStyle(.white)
                Text("Open prediction modules from one account.")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(Color(red: 0.67, green: 0.71, blue: 0.78))
                    .lineLimit(2)
            }
            Spacer(minLength: 8)
            Button {
                Task { await viewModel.refresh() }
            } label: {
                Image(systemName: "arrow.clockwise")
                    .font(.headline.weight(.bold))
                    .foregroundStyle(LuveloxStyle.ink)
                    .frame(width: 44, height: 40)
                    .background(.white, in: RoundedRectangle(cornerRadius: 8))
            }
            .disabled(viewModel.isLoading)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .background(LuveloxStyle.ink, in: RoundedRectangle(cornerRadius: 8))
    }

    private var moduleGrid: some View {
        LazyVStack(spacing: 14) {
            ForEach(viewModel.modules) { module in
                ModuleCard(module: module, session: viewModel.authSession) {
                    viewModel.accessRequestMessage = nil
                    selectedLockedModule = module
                }
            }
        }
    }
}

private struct LoginModulePreviewStrip: View {
    private let items: [(letter: String, title: String, subtitle: String, color: Color, background: Color)] = [
        ("L", "Laminate", "Type, Pt, curve", LuveloxStyle.blue, LuveloxStyle.blueSoft),
        ("I", "Injection", "Sprue, filling", LuveloxStyle.teal, LuveloxStyle.tealSoft),
        ("O", "Optimization", "Coming soon", LuveloxStyle.amber, LuveloxStyle.amberSoft),
    ]

    var body: some View {
        HStack(spacing: 1) {
            ForEach(items, id: \.letter) { item in
                VStack(alignment: .leading, spacing: 5) {
                    Text(item.letter)
                        .font(.headline.weight(.black))
                        .foregroundStyle(item.color)
                        .frame(width: 32, height: 32)
                        .background(item.background, in: RoundedRectangle(cornerRadius: 8))
                    Text(item.title)
                        .font(.caption.weight(.black))
                        .foregroundStyle(LuveloxStyle.ink)
                        .lineLimit(1)
                    Text(item.subtitle)
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(LuveloxStyle.muted)
                        .lineLimit(1)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(10)
                .background(LuveloxStyle.surfaceStrong)
            }
        }
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(LuveloxStyle.line))
    }
}

private struct WorkspaceSummaryStrip: View {
    private let steps: [(number: String, title: String, subtitle: String)] = [
        ("01", "Account", "Demo access ready."),
        ("02", "Choose module", "Laminate, Injection, Optimization"),
        ("03", "Forecast", "Open a focused model workspace."),
    ]

    var body: some View {
        VStack(spacing: 1) {
            ForEach(steps, id: \.number) { step in
                HStack(spacing: 12) {
                    Text(step.number)
                        .font(.subheadline.weight(.black))
                        .foregroundStyle(.white)
                        .frame(width: 38, height: 38)
                        .background(LuveloxStyle.ink, in: RoundedRectangle(cornerRadius: 8))
                    VStack(alignment: .leading, spacing: 2) {
                        Text(step.title)
                            .font(.subheadline.weight(.black))
                            .foregroundStyle(LuveloxStyle.ink)
                        Text(step.subtitle)
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(LuveloxStyle.muted)
                            .lineLimit(1)
                    }
                    Spacer(minLength: 0)
                }
                .padding(12)
                .background(LuveloxStyle.surface)
            }
        }
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(LuveloxStyle.line))
        .shadow(color: Color.black.opacity(0.05), radius: 14, y: 8)
    }
}

struct ModuleCard: View {
    let module: LuveloxModule
    let session: LuveloxAuthSession?
    let onRequestAccess: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .center, spacing: 12) {
                icon
                VStack(alignment: .leading, spacing: 3) {
                    Text(module.category.uppercased())
                        .font(.caption2.weight(.heavy))
                        .foregroundStyle(accentColor)
                    Text(module.name)
                        .font(.title3.weight(.bold))
                        .lineLimit(1)
                }
                Spacer()
                Text(module.isGranted ? "Available" : "Locked")
                    .font(.caption.weight(.heavy))
                    .foregroundStyle(module.isGranted ? Color(red: 0.03, green: 0.47, blue: 0.34) : LuveloxStyle.muted)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(module.isGranted ? LuveloxStyle.greenSoft : Color(red: 0.93, green: 0.95, blue: 0.97), in: Capsule())
            }

            Text(module.summary)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(LuveloxStyle.muted)
                .lineLimit(2)

            tags
            capabilities

            moduleAction
        }
        .padding(18)
        .background(module.isGranted ? LuveloxStyle.surface : LuveloxStyle.surfaceStrong, in: RoundedRectangle(cornerRadius: 8))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(LuveloxStyle.line)
        )
        .shadow(color: Color.black.opacity(0.05), radius: 14, y: 8)
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
        } else if module.id == "admin", module.isGranted, let url = adminURL {
            #if os(iOS)
            NavigationLink {
                AdminWebView(url: url)
                    .navigationTitle("Admin")
                    .navigationBarTitleDisplayMode(.inline)
            } label: {
                actionLabel(title: "Open Admin", systemImage: "arrow.right", enabled: true)
            }
            #else
            EmptyView()
            #endif
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
                .fill(iconBackground)
                .frame(width: 48, height: 48)
            Image(systemName: symbolName)
                .font(.title3.weight(.bold))
                .foregroundStyle(module.isGranted ? accentColor : LuveloxStyle.muted)
        }
    }

    private var symbolName: String {
        switch module.icon {
        case "layers": "square.3.layers.3d"
        case "gauge": "gauge.with.dots.needle.bottom.50percent"
        case "shield": "shield.lefthalf.filled"
        default: "sparkles"
        }
    }

    private var accentColor: Color {
        if !module.isGranted {
            return LuveloxStyle.muted
        }
        switch module.id {
        case "admin":
            return LuveloxStyle.green
        case "injection":
            return LuveloxStyle.teal
        case "optimization":
            return LuveloxStyle.amber
        default:
            return LuveloxStyle.blue
        }
    }

    private var iconBackground: Color {
        if !module.isGranted {
            return Color(red: 0.93, green: 0.95, blue: 0.97)
        }
        switch module.id {
        case "admin":
            return LuveloxStyle.greenSoft
        case "injection":
            return LuveloxStyle.tealSoft
        case "optimization":
            return LuveloxStyle.amberSoft
        default:
            return LuveloxStyle.blueSoft
        }
    }

    private var tags: some View {
        FlowLayout(spacing: 8) {
            ForEach(module.tags, id: \.self) { tag in
                Text(tag)
                    .font(.caption.weight(.bold))
                    .foregroundStyle(accentColor)
                    .padding(.horizontal, 9)
                    .padding(.vertical, 6)
                    .background(iconBackground, in: Capsule())
            }
        }
    }

    private var capabilities: some View {
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 8) {
            ForEach(module.capabilities.prefix(4), id: \.self) { capability in
                Text(capability.replacingOccurrences(of: "_", with: " "))
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(LuveloxStyle.muted)
                    .frame(maxWidth: .infinity, minHeight: 32)
                    .background(LuveloxStyle.surfaceStrong, in: RoundedRectangle(cornerRadius: 8))
                    .overlay(RoundedRectangle(cornerRadius: 8).stroke(LuveloxStyle.line))
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
        .background(enabled ? LuveloxStyle.ink : Color.gray, in: RoundedRectangle(cornerRadius: 8))
    }

    private var adminURL: URL? {
        guard let session else { return nil }
        var components = URLComponents(url: module.route.webURL, resolvingAgainstBaseURL: false)
        components?.queryItems = [URLQueryItem(name: "session_token", value: session.accessToken)]
        return components?.url
    }
}

#if os(iOS)
struct AdminWebView: UIViewRepresentable {
    let url: URL

    func makeUIView(context: Context) -> WKWebView {
        WKWebView()
    }

    func updateUIView(_ webView: WKWebView, context: Context) {
        if webView.url != url {
            webView.load(URLRequest(url: url))
        }
    }
}
#endif

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
            Text(session?.user.name ?? "Luvelox Account")
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
                        Text(module.accessReason ?? "This module requires a Luvelox license.")
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
