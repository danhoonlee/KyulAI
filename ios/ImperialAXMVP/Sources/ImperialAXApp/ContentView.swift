import KyulAIDDLaminateApp
import KyulAIInjectionApp
import SwiftUI
#if os(iOS)
import UIKit
import WebKit
#endif

private enum ImperialAXStyle {
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
final class ImperialAXHomeViewModel: ObservableObject {
    @Published var modules: [ImperialAXModule] = ImperialAXFallbackCatalog.modules
    @Published var statusText = "Signed out"
    @Published var isLoading = false
    @Published var authSession: ImperialAXAuthSession?
    @Published var loginError: String?
    @Published var accessRequestMessage: String?

    private let client: ModuleCatalogClient
    private let sessionKey = "imperialax.auth.session.v1"
    private let sessionSavedAtKey = "imperialax.auth.saved_at.v1"
    private let sessionLifetime: TimeInterval
    private let now: () -> Date
    private let userDefaults: UserDefaults
    private let sessionStore: SessionDataStore
    private static let defaultSessionLifetime: TimeInterval = 24 * 60 * 60

    init(
        client: ModuleCatalogClient = ModuleCatalogClient(),
        userDefaults: UserDefaults = .standard,
        sessionStore: SessionDataStore = KeychainSessionDataStore(),
        sessionLifetime: TimeInterval = ImperialAXHomeViewModel.defaultSessionLifetime,
        now: @escaping () -> Date = Date.init
    ) {
        self.client = client
        self.userDefaults = userDefaults
        self.sessionStore = sessionStore
        self.sessionLifetime = sessionLifetime
        self.now = now
        self.authSession = Self.loadSession(
            from: userDefaults,
            store: sessionStore,
            key: sessionKey,
            savedAtKey: sessionSavedAtKey,
            sessionLifetime: sessionLifetime,
            now: now()
        )
        self.statusText = authSession == nil ? "Signed out" : "Loading workspace"
    }

    func refresh() async {
        guard !expireSessionIfNeeded() else { return }
        guard let authSession else {
            modules = ImperialAXFallbackCatalog.modules.map { module in
                ImperialAXModule(
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
            if case ModuleCatalogError.unauthorized = error {
                signOut()
                loginError = "Your session expired. Please sign in again."
                return
            }
            modules = ImperialAXFallbackCatalog.modules
            statusText = "Offline account"
        }
    }

    func signIn(email: String, password: String) async {
        isLoading = true
        loginError = nil
        defer { isLoading = false }
        let trimmedEmail = email.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        guard !trimmedEmail.isEmpty, !password.isEmpty else {
            loginError = "Enter your email and password."
            return
        }
        do {
            let session = try await client.login(email: trimmedEmail, password: password)
            setSession(session)
        } catch {
            loginError = "Check your email and password."
            return
        }
        await refresh()
    }

    func signInDemo() async {
        isLoading = true
        loginError = nil
        defer { isLoading = false }
        do {
            let session = try await client.demoLogin()
            setSession(session)
        } catch {
            loginError = "The demo workspace is temporarily unavailable."
            return
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
        loginError = nil
        accessRequestMessage = nil
        sessionStore.delete()
        userDefaults.removeObject(forKey: sessionKey)
        userDefaults.removeObject(forKey: sessionSavedAtKey)
        modules = ImperialAXFallbackCatalog.modules.map { module in
            ImperialAXModule(
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

    func requestAccess(to module: ImperialAXModule) async {
        guard !expireSessionIfNeeded() else { return }
        isLoading = true
        accessRequestMessage = nil
        defer { isLoading = false }
        do {
            let response = try await client.requestAccess(
                moduleId: module.id,
                message: "Requested from ImperialAX mobile app.",
                authSession: authSession
            )
            accessRequestMessage = response.message
        } catch {
            accessRequestMessage = "Request saved locally. We could not reach the ImperialAX server right now."
        }
    }

    private func setSession(_ session: ImperialAXAuthSession) {
        let normalizedSession = Self.normalizedSession(session)
        authSession = normalizedSession
        if let data = try? JSONEncoder().encode(normalizedSession) {
            sessionStore.save(data)
            userDefaults.removeObject(forKey: sessionKey)
            userDefaults.set(now(), forKey: sessionSavedAtKey)
        }
    }

    @discardableResult
    func expireSessionIfNeeded() -> Bool {
        guard let authSession else { return false }
        if let expiresAt = authSession.expiresAt,
           let expiry = Self.parseServerDate(expiresAt),
           now() >= expiry {
            signOut()
            loginError = "Session expired. Please sign in again."
            return true
        }
        guard let savedAt = userDefaults.object(forKey: sessionSavedAtKey) as? Date else {
            userDefaults.set(now(), forKey: sessionSavedAtKey)
            return false
        }
        guard Self.isSessionExpired(savedAt: savedAt, now: now(), sessionLifetime: sessionLifetime) else {
            return false
        }
        signOut()
        loginError = "Session expired. Please sign in again."
        return true
    }

    private static func loadSession(
        from userDefaults: UserDefaults,
        store: SessionDataStore,
        key: String,
        savedAtKey: String,
        sessionLifetime: TimeInterval,
        now: Date
    ) -> ImperialAXAuthSession? {
        let secureData = store.load()
        let legacyData = userDefaults.data(forKey: key)
        guard let data = secureData ?? legacyData else { return nil }
        if secureData == nil, legacyData != nil {
            store.save(data)
            userDefaults.removeObject(forKey: key)
        }
        guard let session = try? JSONDecoder().decode(ImperialAXAuthSession.self, from: data) else { return nil }
        if let expiresAt = session.expiresAt,
           let expiry = Self.parseServerDate(expiresAt),
           now >= expiry {
            store.delete()
            userDefaults.removeObject(forKey: key)
            userDefaults.removeObject(forKey: savedAtKey)
            return nil
        }
        if let savedAt = userDefaults.object(forKey: savedAtKey) as? Date {
            if isSessionExpired(savedAt: savedAt, now: now, sessionLifetime: sessionLifetime) {
                store.delete()
                userDefaults.removeObject(forKey: key)
                userDefaults.removeObject(forKey: savedAtKey)
                return nil
            }
        } else {
            userDefaults.set(now, forKey: savedAtKey)
        }
        return normalizedSession(session)
    }

    private static func parseServerDate(_ value: String) -> Date? {
        let fractional = ISO8601DateFormatter()
        fractional.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return fractional.date(from: value) ?? ISO8601DateFormatter().date(from: value)
    }

    private static func isSessionExpired(savedAt: Date, now: Date, sessionLifetime: TimeInterval) -> Bool {
        now.timeIntervalSince(savedAt) >= sessionLifetime
    }

    private static func normalizedSession(_ session: ImperialAXAuthSession) -> ImperialAXAuthSession {
        let legacyBrand = "Lu" + "velox"
        let normalizedName: String
        switch session.user.name.trimmingCharacters(in: .whitespacesAndNewlines) {
        case "\(legacyBrand) Demo", "ImperialAX Demo":
            normalizedName = "Demo Account"
        case "\(legacyBrand) Account", "ImperialAX Account":
            normalizedName = "ImperialAX Account"
        default:
            normalizedName = session.user.name
        }
        let user = ImperialAXAccountUser(
            id: session.user.id,
            email: session.user.email,
            name: normalizedName,
            company: session.user.company
        )
        return ImperialAXAuthSession(
            accessToken: session.accessToken,
            tokenType: session.tokenType,
            expiresAt: session.expiresAt,
            user: user,
            entitlements: session.entitlements
        )
    }
}

struct ContentView: View {
    @Environment(\.scenePhase) private var scenePhase
    @StateObject private var viewModel = ImperialAXHomeViewModel()
    @State private var email = ""
    @State private var password = ""
    @State private var isPasswordVisible = false
    @State private var signupName = ""
    @State private var signupCompany = ""
    @State private var authMode = AuthMode.login
    @State private var isAccountSheetPresented = false
    @State private var selectedLockedModule: ImperialAXModule?

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
            .background(ImperialAXStyle.background)
            .task {
                await viewModel.refresh()
            }
            .onChange(of: scenePhase) { _, phase in
                if phase == .active {
                    viewModel.expireSessionIfNeeded()
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
            VStack(alignment: .leading, spacing: 14) {
                VStack(alignment: .leading, spacing: 16) {
                    Text("ImperialAX AI Workspace")
                        .font(.caption.weight(.heavy))
                        .foregroundStyle(ImperialAXStyle.blue)
                        .textCase(.uppercase)
                    Text("ImperialAX\nForecast Workspace")
                        .font(.system(size: 42, weight: .black, design: .rounded))
                        .lineSpacing(0)
                        .foregroundStyle(ImperialAXStyle.ink)
                        .minimumScaleFactor(0.78)
                    Text("Sign in once, then open the prediction module built for each engineering analysis.")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(ImperialAXStyle.muted)
                        .fixedSize(horizontal: false, vertical: true)
                    LoginModulePreviewStrip()
                }
                .padding(18)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(ImperialAXStyle.surface, in: RoundedRectangle(cornerRadius: 8))
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(ImperialAXStyle.line))
                .shadow(color: Color.black.opacity(0.06), radius: 18, y: 10)

                VStack(alignment: .leading, spacing: 12) {
                    Text("Account")
                        .font(.caption.weight(.heavy))
                        .foregroundStyle(ImperialAXStyle.blue)
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
                    TextField("demo@imperialax.com", text: $email)
                        #if os(iOS)
                        .textInputAutocapitalization(.never)
                        .keyboardType(.emailAddress)
                        #endif
                        .autocorrectionDisabled()
                        .fieldStyle()
                    PasswordEntryField(
                        placeholder: "Password",
                        text: $password,
                        isVisible: $isPasswordVisible
                    )
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
                        .background(ImperialAXStyle.ink, in: RoundedRectangle(cornerRadius: 8))
                    }
                    .disabled(viewModel.isLoading)

                    Button {
                        authMode = authMode == .signup ? .login : .signup
                        viewModel.loginError = nil
                    } label: {
                        Text(authMode == .signup ? "Use existing account" : "Create a new account")
                            .font(.subheadline.weight(.bold))
                            .frame(maxWidth: .infinity)
                            .frame(height: 44)
                    }
                    .foregroundStyle(ImperialAXStyle.blue)
                    .background(ImperialAXStyle.blueSoft, in: RoundedRectangle(cornerRadius: 8))
                    .disabled(viewModel.isLoading)

                    demoLoginAction

                    Text(authMode == .signup ? "Use at least 8 characters to create an account." : "New accounts include Laminate and Injection access.")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(ImperialAXStyle.muted)
                }
                .padding(18)
                .background(ImperialAXStyle.surface, in: RoundedRectangle(cornerRadius: 8))
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(ImperialAXStyle.line))
                .shadow(color: Color.black.opacity(0.06), radius: 18, y: 10)
            }
            .padding(20)
        }
    }

    @ViewBuilder
    private var demoLoginAction: some View {
        if authMode == .login {
            Button {
                Task { await viewModel.signInDemo() }
            } label: {
                HStack(spacing: 8) {
                    Image(systemName: "play.circle.fill")
                    Text("Try demo workspace")
                }
                .font(.subheadline.weight(.bold))
                .frame(maxWidth: .infinity)
                .frame(height: 44)
            }
            .foregroundStyle(ImperialAXStyle.blue)
            .background(ImperialAXStyle.surface, in: RoundedRectangle(cornerRadius: 8))
            .overlay(RoundedRectangle(cornerRadius: 8).stroke(ImperialAXStyle.blue.opacity(0.28)))
            .disabled(viewModel.isLoading)
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
            Text("ImperialAX AI Workspace")
                .font(.caption.weight(.heavy))
                .foregroundStyle(ImperialAXStyle.blue)
                .textCase(.uppercase)
            Text("ImperialAX\nForecast Workspace")
                .font(.system(size: 42, weight: .black, design: .rounded))
                .lineSpacing(0)
                .foregroundStyle(ImperialAXStyle.ink)
                .minimumScaleFactor(0.78)
            Text("Choose a module to open its prediction screen.")
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(ImperialAXStyle.muted)

            HStack(spacing: 8) {
                Button {
                    isAccountSheetPresented = true
                } label: {
                    HStack(spacing: 8) {
                        Circle()
                            .fill(ImperialAXStyle.green)
                            .frame(width: 9, height: 9)
                        Text(accountChipText)
                            .lineLimit(1)
                    }
                    .font(.caption.weight(.heavy))
                    .foregroundStyle(Color(red: 0.03, green: 0.47, blue: 0.34))
                    .padding(.horizontal, 12)
                    .frame(height: 44)
                    .background(ImperialAXStyle.greenSoft, in: Capsule())
                }
                Button {
                    viewModel.signOut()
                } label: {
                    Text("Sign out")
                        .font(.caption.weight(.heavy))
                        .foregroundStyle(ImperialAXStyle.muted)
                        .padding(.horizontal, 12)
                        .frame(height: 44)
                        .background(ImperialAXStyle.surfaceStrong, in: Capsule())
                        .overlay(Capsule().stroke(ImperialAXStyle.line))
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(18)
        .background(ImperialAXStyle.surface, in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(ImperialAXStyle.line))
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
            VStack(alignment: .trailing, spacing: 6) {
                Button {
                    Task { await viewModel.refresh() }
                } label: {
                    HStack(spacing: 8) {
                        if viewModel.isLoading {
                            ProgressView()
                                .controlSize(.small)
                        } else {
                            Image(systemName: "arrow.clockwise")
                        }
                        Text(viewModel.isLoading ? "Refreshing" : "Refresh")
                    }
                    .font(.subheadline.weight(.heavy))
                    .foregroundStyle(ImperialAXStyle.ink)
                    .padding(.horizontal, 12)
                    .frame(height: 44)
                    .background(.white, in: RoundedRectangle(cornerRadius: 8))
                }
                Text(viewModel.statusText)
                    .font(.caption2.weight(.bold))
                    .foregroundStyle(Color(red: 0.67, green: 0.71, blue: 0.78))
                    .lineLimit(1)
            }
            .disabled(viewModel.isLoading)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .background(ImperialAXStyle.ink, in: RoundedRectangle(cornerRadius: 8))
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

private struct PasswordEntryField: View {
    let placeholder: String
    @Binding var text: String
    @Binding var isVisible: Bool

    var body: some View {
        HStack(spacing: 8) {
            Group {
                if isVisible {
                    TextField(placeholder, text: $text)
                } else {
                    SecureField(placeholder, text: $text)
                }
            }
            .textContentType(.password)
            #if os(iOS)
            .textInputAutocapitalization(.never)
            #endif
            .autocorrectionDisabled()

            Button {
                isVisible.toggle()
            } label: {
                Image(systemName: isVisible ? "eye.slash" : "eye")
                    .font(.subheadline.weight(.bold))
                    .foregroundStyle(ImperialAXStyle.blue)
                    .frame(width: 44, height: 44)
                    .background(ImperialAXStyle.blueSoft, in: RoundedRectangle(cornerRadius: 8))
            }
            .accessibilityLabel(isVisible ? "Hide password" : "Show password")
        }
        .font(.body.weight(.semibold))
        .padding(.leading, 12)
        .padding(.trailing, 8)
        .frame(height: 50)
        .background(Color(red: 0.96, green: 0.98, blue: 0.99), in: RoundedRectangle(cornerRadius: 8))
    }
}

private struct LoginModulePreviewStrip: View {
    private let items: [(letter: String, title: String, subtitle: String, color: Color, background: Color)] = [
        ("L", "Laminate", "Type, Pt, curve", ImperialAXStyle.blue, ImperialAXStyle.blueSoft),
        ("I", "Injection", "Sprue, filling", ImperialAXStyle.teal, ImperialAXStyle.tealSoft),
        ("O", "Optimization", "Design search", ImperialAXStyle.amber, ImperialAXStyle.amberSoft),
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
                        .foregroundStyle(ImperialAXStyle.ink)
                        .lineLimit(1)
                    Text(item.subtitle)
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(ImperialAXStyle.muted)
                        .lineLimit(1)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(10)
                .background(ImperialAXStyle.surfaceStrong)
            }
        }
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(ImperialAXStyle.line))
    }
}

private struct WorkspaceSummaryStrip: View {
    private let steps: [(number: String, title: String, subtitle: String)] = [
        ("01", "Account", "Sign in once to open your modules."),
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
                        .background(ImperialAXStyle.ink, in: RoundedRectangle(cornerRadius: 8))
                    VStack(alignment: .leading, spacing: 2) {
                        Text(step.title)
                            .font(.subheadline.weight(.black))
                            .foregroundStyle(ImperialAXStyle.ink)
                        Text(step.subtitle)
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(ImperialAXStyle.muted)
                            .lineLimit(1)
                    }
                    Spacer(minLength: 0)
                }
                .padding(12)
                .background(ImperialAXStyle.surface)
            }
        }
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(ImperialAXStyle.line))
        .shadow(color: Color.black.opacity(0.05), radius: 14, y: 8)
    }
}

struct ModuleCard: View {
    let module: ImperialAXModule
    let session: ImperialAXAuthSession?
    let onRequestAccess: () -> Void

    @ViewBuilder
    var body: some View {
        if module.id == "laminate", module.isGranted {
            NavigationLink {
                DDLaminateModuleView(accessToken: session?.accessToken)
            } label: {
                cardContent
            }
            .buttonStyle(.plain)
            .accessibilityHint("Open Laminate")
        } else if module.id == "injection", module.isGranted {
            NavigationLink {
                InjectionModuleView(
                    embedInNavigationStack: false,
                    accessToken: session?.accessToken
                )
            } label: {
                cardContent
            }
            .buttonStyle(.plain)
            .accessibilityHint("Open Injection")
        } else {
            cardContent
        }
    }

    private var cardContent: some View {
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
                    .foregroundStyle(module.isGranted ? Color(red: 0.03, green: 0.47, blue: 0.34) : ImperialAXStyle.muted)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(module.isGranted ? ImperialAXStyle.greenSoft : Color(red: 0.93, green: 0.95, blue: 0.97), in: Capsule())
            }

            Text(module.summary)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(ImperialAXStyle.muted)
                .lineLimit(2)

            tags
            capabilities

            moduleAction
        }
        .padding(18)
        .background(module.isGranted ? ImperialAXStyle.surface : ImperialAXStyle.surfaceStrong, in: RoundedRectangle(cornerRadius: 8))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(ImperialAXStyle.line)
        )
        .shadow(color: Color.black.opacity(0.05), radius: 14, y: 8)
    }

    @ViewBuilder
    private var moduleAction: some View {
        if module.id == "laminate", module.isGranted {
            actionLabel(title: "Open Laminate", systemImage: "arrow.right", enabled: true)
        } else if module.id == "injection", module.isGranted {
            actionLabel(title: "Open Injection", systemImage: "arrow.right", enabled: true)
        } else if ["admin", "optimization"].contains(module.id), module.isGranted, let session {
            #if os(iOS)
            NavigationLink {
                SecureModuleWebView(module: module, session: session)
                    .navigationTitle(module.name)
                    .navigationBarTitleDisplayMode(.inline)
            } label: {
                actionLabel(title: "Open \(module.shortName)", systemImage: "arrow.right", enabled: true)
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
                .foregroundStyle(module.isGranted ? accentColor : ImperialAXStyle.muted)
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
            return ImperialAXStyle.muted
        }
        switch module.id {
        case "admin":
            return ImperialAXStyle.green
        case "injection":
            return ImperialAXStyle.teal
        case "optimization":
            return ImperialAXStyle.amber
        default:
            return ImperialAXStyle.blue
        }
    }

    private var iconBackground: Color {
        if !module.isGranted {
            return Color(red: 0.93, green: 0.95, blue: 0.97)
        }
        switch module.id {
        case "admin":
            return ImperialAXStyle.greenSoft
        case "injection":
            return ImperialAXStyle.tealSoft
        case "optimization":
            return ImperialAXStyle.amberSoft
        default:
            return ImperialAXStyle.blueSoft
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
                    .foregroundStyle(ImperialAXStyle.muted)
                    .frame(maxWidth: .infinity, minHeight: 32)
                    .background(ImperialAXStyle.surfaceStrong, in: RoundedRectangle(cornerRadius: 8))
                    .overlay(RoundedRectangle(cornerRadius: 8).stroke(ImperialAXStyle.line))
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
        .background(enabled ? ImperialAXStyle.ink : Color.gray, in: RoundedRectangle(cornerRadius: 8))
    }

}

#if os(iOS)
private struct SecureModuleWebView: View {
    let module: ImperialAXModule
    let session: ImperialAXAuthSession
    @State private var launchURL: URL?
    @State private var errorMessage: String?

    var body: some View {
        Group {
            if let launchURL {
                AdminWebView(url: launchURL)
            } else if let errorMessage {
                ContentUnavailableView(
                    "Could not open \(module.name)",
                    systemImage: "exclamationmark.triangle",
                    description: Text(errorMessage)
                )
            } else {
                ProgressView("Opening securely…")
            }
        }
        .task {
            guard launchURL == nil, errorMessage == nil else { return }
            do {
                launchURL = try await ModuleCatalogClient().createLaunchURL(
                    target: module.id,
                    authSession: session
                )
            } catch {
                errorMessage = "Your session may have expired. Sign in and try again."
            }
        }
    }
}

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
    let session: ImperialAXAuthSession?
    let modules: [ImperialAXModule]
    let onRefresh: () -> Void
    let onSignOut: () -> Void
    @Environment(\.dismiss) private var dismiss

    private var grantedModules: [ImperialAXModule] {
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
            Text(session?.user.name ?? "ImperialAX Account")
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
    let module: ImperialAXModule
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
                        Text(module.accessReason ?? "This module requires an ImperialAX license.")
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
            .frame(height: 50)
            .background(Color(red: 0.96, green: 0.98, blue: 0.99), in: RoundedRectangle(cornerRadius: 8))
    }
}

#Preview {
    ContentView()
}
