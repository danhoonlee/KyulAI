import KyulAIInjectionCore
import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var settings: AppSettings
    @EnvironmentObject private var viewModel: PredictionViewModel
    @State private var selectedResult: SpruePressurePredictionResult?
    @State private var isShowingResult = false
    @State private var isShowingSettings = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    header
                    connectionCard
                    forecastCard
                    if let result = viewModel.result {
                        latestResultCard(result)
                    }
                }
                .padding(20)
            }
            .background(AppTheme.background.ignoresSafeArea())
            .appInlineNavigationTitle()
            .toolbar {
                ToolbarItem(placement: toolbarTrailingPlacement) {
                    Button {
                        isShowingSettings = true
                    } label: {
                        Image(systemName: "ellipsis.circle")
                    }
                }
            }
            .sheet(isPresented: $isShowingSettings) {
                NavigationStack {
                    settingsView
                        .navigationTitle(L10n.t("api.settings"))
                        .appInlineNavigationTitle()
                        .toolbar {
                            ToolbarItem(placement: .confirmationAction) {
                                Button(L10n.t("done")) { isShowingSettings = false }
                            }
                        }
                }
            }
            .alert(L10n.t("prediction.error"), isPresented: errorBinding) {
                Button(L10n.t("ok"), role: .cancel) { viewModel.errorMessage = nil }
            } message: {
                Text(friendlyErrorMessage(viewModel.errorMessage))
            }
            .navigationDestination(isPresented: $isShowingResult) {
                if let selectedResult {
                    ResultDetailView(result: selectedResult)
                }
            }
            .task { await autoCheckConnection() }
            .onChange(of: settings.apiBaseURL) {
                viewModel.resetReadiness()
                Task { await autoCheckConnection() }
            }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(L10n.t("app.title"))
                .font(.system(size: 34, weight: .bold, design: .rounded))
                .foregroundStyle(
                    LinearGradient(colors: [AppTheme.ink, AppTheme.primary], startPoint: .leading, endPoint: .trailing)
                )
            Text(L10n.t("app.subtitle"))
                .font(.callout)
                .foregroundStyle(AppTheme.muted)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(.top, 8)
    }

    private var connectionCard: some View {
        AppCard {
            HStack(alignment: .top, spacing: 12) {
                statusIcon
                VStack(alignment: .leading, spacing: 5) {
                    if let title = connectionTitle {
                        Text(title)
                            .font(.headline)
                            .foregroundStyle(AppTheme.ink)
                    }
                    if connectionIsFailed {
                        Text(settings.apiBaseURL)
                            .font(.caption.monospaced())
                            .foregroundStyle(AppTheme.muted)
                            .lineLimit(1)
                            .truncationMode(.middle)
                    }
                    if let detail = connectionDetail {
                        Text(detail)
                            .font(.caption)
                            .foregroundStyle(AppTheme.muted)
                    }
                    if let sprue = viewModel.sprueModel {
                        Text("\(L10n.t("sprue.prefix")): \(sprue.displayLabel)")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(AppTheme.accent)
                            .lineLimit(1)
                            .truncationMode(.tail)
                    }
                    if let filling = viewModel.fillingModel {
                        Text("\(L10n.t("filling.prefix")): \(filling.displayLabel)")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(AppTheme.accent)
                            .lineLimit(1)
                            .truncationMode(.tail)
                    }
                }
                Spacer()
                Text(L10n.t("auto"))
                    .font(.caption2.weight(.bold))
                    .foregroundStyle(AppTheme.success)
                    .padding(.horizontal, 9)
                    .padding(.vertical, 5)
                    .background(AppTheme.success.opacity(0.12), in: Capsule())
            }
            if connectionIsFailed {
                HStack(spacing: 10) {
                    Button {
                        Task { await autoCheckConnection() }
                    } label: {
                        Label(L10n.t("retry.action"), systemImage: "arrow.clockwise")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(SecondaryButtonStyle())

                    Button {
                        isShowingSettings = true
                    } label: {
                        Label(L10n.t("settings.action"), systemImage: "gearshape")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(SecondaryButtonStyle())
                }
            }
        }
    }

    private var forecastCard: some View {
        AppCard {
            VStack(alignment: .leading, spacing: 18) {
                HStack {
                    Label(L10n.t("injection.inputs"), systemImage: "slider.horizontal.3")
                        .font(.headline)
                        .foregroundStyle(AppTheme.ink)
                    Spacer()
                    if !viewModel.recentRuns.isEmpty {
                        recentRunsMenu
                    }
                    Text("\(viewModel.geometryID) / \(viewModel.processID)")
                        .font(.caption.bold())
                        .foregroundStyle(AppTheme.primary)
                        .padding(.horizontal, 9)
                        .padding(.vertical, 5)
                        .background(AppTheme.primary.opacity(0.1), in: Capsule())
                }

                VStack(alignment: .leading, spacing: 12) {
                    modelPicker(L10n.t("sprue.model"), selection: Binding(get: {
                        viewModel.selectedSprueModelKey
                    }, set: {
                        viewModel.selectSprueModel(key: $0)
                    }), models: viewModel.sprueModels)
                    modelPicker(L10n.t("filling.model"), selection: Binding(get: {
                        viewModel.selectedFillingModelKey
                    }, set: {
                        viewModel.selectFillingModel(key: $0)
                    }), models: viewModel.fillingModels)
                }

                HStack(spacing: 12) {
                    optionPicker(L10n.t("geometry"), selection: Binding(get: {
                        viewModel.geometryID
                    }, set: {
                        viewModel.selectGeometry(id: $0)
                    }), values: viewModel.geometries.map(\.id))
                    optionPicker(L10n.t("process"), selection: Binding(get: {
                        viewModel.processID
                    }, set: {
                        viewModel.selectProcess(id: $0)
                    }), values: viewModel.processes.map(\.id))
                }

                VStack(alignment: .leading, spacing: 10) {
                    Text(L10n.t("geometry"))
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(AppTheme.muted)
                    LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                        numericField("L", value: $viewModel.Lmm, unit: "mm")
                        numericField("W", value: $viewModel.Wmm, unit: "mm")
                        numericField("t", value: $viewModel.tmm, unit: "mm")
                        numericField("D", value: $viewModel.Dmm, unit: "mm")
                        numericField("R", value: $viewModel.Rmm, unit: "mm")
                    }
                }

                VStack(alignment: .leading, spacing: 10) {
                    Text("Gate")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(AppTheme.muted)
                    LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                        textField("Type", value: $viewModel.gateType)
                        numericField("Width", value: $viewModel.gateWidth, unit: "mm")
                        numericField("Height", value: $viewModel.gateHeight, unit: "mm")
                    }
                }

                VStack(alignment: .leading, spacing: 10) {
                    Text(L10n.t("process"))
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(AppTheme.muted)
                    LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                        numericField("Melt", value: $viewModel.meltTempC, unit: "C")
                        numericField("Mold", value: $viewModel.moldTempC, unit: "C")
                        numericField("Inject", value: $viewModel.injectionTimeS, unit: "s")
                        numericField("Packing", value: $viewModel.packingPressureMPa, unit: "MPa")
                        numericField("Pack Time", value: $viewModel.packingTimeS, unit: "s")
                    }
                }

                Button {
                    Task { await predict() }
                } label: {
                    HStack {
                        if viewModel.isPredicting {
                            ProgressView().tint(.white)
                        } else {
                            Image(systemName: "gauge.with.dots.needle.67percent")
                        }
                        Text(viewModel.isPredicting ? L10n.t("predicting") : L10n.t("predict.pressure"))
                            .fontWeight(.bold)
                    }
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(PrimaryButtonStyle())
                .disabled(!viewModel.canPredict)
            }
        }
    }

    private var recentRunsMenu: some View {
        Menu {
            ForEach(viewModel.recentRuns) { run in
                Button {
                    viewModel.applyRecentRun(run)
                } label: {
                    Text("\(run.displayTitle) · \(run.displaySubtitle)")
                }
            }
            Divider()
            Button(role: .destructive) {
                viewModel.clearRecentRuns()
            } label: {
                Label(L10n.t("recent.clear"), systemImage: "trash")
            }
        } label: {
            Label(L10n.t("recent.inputs"), systemImage: "clock.arrow.circlepath")
                .font(.caption.weight(.bold))
                .labelStyle(.iconOnly)
                .foregroundStyle(AppTheme.primary)
                .frame(width: 32, height: 32)
                .background(AppTheme.primary.opacity(0.1), in: Circle())
        }
    }

    private func modelPicker(_ title: String, selection: Binding<String>, models: [ModelInfo]) -> some View {
        let selectedModel = models.first { $0.key == selection.wrappedValue }
        let selectedTitle = selectedModel?.displayLabel ?? selection.wrappedValue
        return VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.caption.weight(.semibold))
                .foregroundStyle(AppTheme.muted)
            Menu {
                if models.isEmpty {
                    Button(selection.wrappedValue) { }
                        .disabled(true)
                } else {
                    ForEach(models) { model in
                        Button {
                            selection.wrappedValue = model.key
                        } label: {
                            HStack {
                                Text(model.displayLabel)
                                if model.key == selection.wrappedValue {
                                    Image(systemName: "checkmark")
                                }
                            }
                        }
                        .disabled(!model.available)
                    }
                }
            } label: {
                pickerFieldLabel(selectedTitle)
            }
            .buttonStyle(.plain)
            Text(selectedModel?.description ?? L10n.t("model.loading"))
                .font(.caption2)
                .foregroundStyle(AppTheme.muted)
                .lineLimit(2)
                .minimumScaleFactor(0.86)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func optionPicker(_ title: String, selection: Binding<String>, values: [String]) -> some View {
        let choices = values.isEmpty ? [selection.wrappedValue] : values
        return VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.caption.weight(.semibold))
                .foregroundStyle(AppTheme.muted)
            Menu {
                ForEach(choices, id: \.self) { value in
                    Button {
                        selection.wrappedValue = value
                    } label: {
                        HStack {
                            Text(value)
                            if value == selection.wrappedValue {
                                Image(systemName: "checkmark")
                            }
                        }
                    }
                }
            } label: {
                pickerFieldLabel(selection.wrappedValue)
            }
            .buttonStyle(.plain)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func pickerFieldLabel(_ title: String) -> some View {
        HStack(spacing: 8) {
            Text(title)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(AppTheme.ink)
                .lineLimit(1)
                .minimumScaleFactor(0.78)
            Spacer(minLength: 8)
            Image(systemName: "chevron.up.chevron.down")
                .font(.caption2.weight(.bold))
                .foregroundStyle(AppTheme.muted)
        }
        .frame(maxWidth: .infinity, minHeight: 22, alignment: .leading)
        .padding(12)
        .background(AppTheme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .contentShape(Rectangle())
    }

    private func numericField(_ title: String, value: Binding<String>, unit: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(.caption2.weight(.semibold))
                .foregroundStyle(AppTheme.muted)
            HStack(alignment: .firstTextBaseline, spacing: 5) {
                TextField(title, text: value)
                    .font(.subheadline.monospacedDigit().weight(.bold))
                    .foregroundStyle(AppTheme.ink)
                    .numericInputStyle()
                Text(unit)
                    .font(.caption2)
                    .foregroundStyle(AppTheme.muted)
            }
        }
        .padding(10)
        .background(AppTheme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
    }

    private func textField(_ title: String, value: Binding<String>) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(.caption2.weight(.semibold))
                .foregroundStyle(AppTheme.muted)
            TextField(title, text: value)
                .font(.subheadline.weight(.bold))
                .foregroundStyle(AppTheme.ink)
                .autocorrectionDisabled()
        }
        .padding(10)
        .background(AppTheme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
    }

    private func latestResultCard(_ result: SpruePressurePredictionResult) -> some View {
        AppCard {
            VStack(alignment: .leading, spacing: 16) {
                HStack(alignment: .firstTextBaseline) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(L10n.t("latest.result"))
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(AppTheme.muted)
                        Text(result.predictedMaxPressureMPa.metricText(digits: 2))
                            .font(.system(size: 34, weight: .bold, design: .rounded))
                            .foregroundStyle(AppTheme.ink)
                    }
                    Spacer()
                    Text("MPa")
                        .font(.title3.weight(.bold))
                        .foregroundStyle(AppTheme.accent)
                }

                HStack(spacing: 10) {
                    miniMetric(L10n.t("peak.time"), result.predictedMaxTimeS.metricText(digits: 3) + " s")
                    miniMetric(L10n.t("curve"), "\(result.curve.count) pts")
                    miniMetric(L10n.t("filling.prefix"), result.bestFillingPressure?.stats["max_MPa"]?.metricText(digits: 2) ?? "-")
                }

                PressureChartView(points: result.curve, maxPressure: result.predictedMaxPressureMPa)
                    .frame(height: 190)

                HStack(spacing: 10) {
                    Button {
                        selectedResult = result
                        isShowingResult = true
                    } label: {
                        Label(L10n.t("open.full.result"), systemImage: "chart.xyaxis.line")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(SecondaryButtonStyle())

                    ShareLink(item: result.shareSummaryText) {
                        Label(L10n.t("share.result"), systemImage: "square.and.arrow.up")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(SecondaryButtonStyle())

                    #if os(iOS)
                    ShareImageButton(
                        fileName: "c2es-injection-forecast",
                        report: InjectionShareImageReportView(result: result)
                    ) {
                        Label(L10n.t("share.image"), systemImage: "photo")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(SecondaryButtonStyle())
                    #endif
                }
            }
        }
    }

    private func miniMetric(_ title: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.caption2.weight(.semibold))
                .foregroundStyle(AppTheme.muted)
            Text(value)
                .font(.subheadline.monospacedDigit().weight(.bold))
                .foregroundStyle(AppTheme.ink)
                .lineLimit(1)
                .minimumScaleFactor(0.72)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(10)
        .background(AppTheme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(AppTheme.primary.opacity(0.12), lineWidth: 1)
        )
    }

    private var settingsView: some View {
        Form {
            Section(L10n.t("base.url")) {
                TextField(L10n.t("api.base.url"), text: $settings.apiBaseURL)
                    .urlInputStyle()
                Text(L10n.t("external.url.hint"))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var statusIcon: some View {
        let config = statusConfig
        return Image(systemName: config.icon)
            .font(.headline)
            .foregroundStyle(config.color)
            .frame(width: 36, height: 36)
            .background(config.color.opacity(0.12), in: Circle())
    }

    private var connectionTitle: String? {
        switch viewModel.connectionState {
        case .idle:
            L10n.t("api.not.checked")
        case .checking:
            L10n.t("checking.api")
        case .ready(let available):
            available ? nil : L10n.t("model.unavailable")
        case .failed:
            L10n.t("connection.failed")
        }
    }

    private var connectionDetail: String? {
        switch viewModel.connectionState {
        case .idle:
            L10n.t("readiness.auto")
        case .checking:
            L10n.t("checking.detail")
        case .ready(let available):
            available ? nil : L10n.t("model.unavailable.detail")
        case .failed(let message):
            friendlyConnectionMessage(message)
        }
    }

    private var connectionIsFailed: Bool {
        if case .failed = viewModel.connectionState { return true }
        return false
    }

    private var statusConfig: (icon: String, color: Color) {
        switch viewModel.connectionState {
        case .idle:
            ("circle", AppTheme.muted)
        case .checking:
            ("hourglass", AppTheme.primary)
        case .ready(let available):
            available ? ("checkmark.circle.fill", AppTheme.success) : ("exclamationmark.triangle.fill", AppTheme.warning)
        case .failed:
            ("xmark.octagon.fill", AppTheme.danger)
        }
    }

    private var errorBinding: Binding<Bool> {
        Binding(
            get: { viewModel.errorMessage != nil },
            set: { if !$0 { viewModel.errorMessage = nil } }
        )
    }

    private var toolbarTrailingPlacement: ToolbarItemPlacement {
        #if os(iOS)
        .topBarTrailing
        #else
        .automatic
        #endif
    }

    private func autoCheckConnection() async {
        guard viewModel.connectionState != .checking else { return }
        do {
            let url = try BaseURLValidator.parse(settings.apiBaseURL)
            await viewModel.checkConnection(baseURL: url)
        } catch {
            viewModel.resetReadiness()
        }
    }

    private func predict() async {
        do {
            let url = try BaseURLValidator.parse(settings.apiBaseURL)
            await viewModel.predict(baseURL: url)
            if let result = viewModel.result, viewModel.errorMessage == nil {
                selectedResult = result
                isShowingResult = true
            }
        } catch {
            viewModel.errorMessage = error.localizedDescription
        }
    }

    private func friendlyConnectionMessage(_ message: String?) -> String {
        friendlyMessage(message, defaultKey: "friendly.offline")
    }

    private func friendlyErrorMessage(_ message: String?) -> String {
        friendlyMessage(message, defaultKey: "friendly.prediction")
    }

    private func friendlyMessage(_ message: String?, defaultKey: String) -> String {
        let lowercased = (message ?? "").lowercased()
        if lowercased.contains("invalid api base url") || lowercased.contains("unsupported url") {
            return L10n.t("friendly.invalid.url")
        }
        if lowercased.contains("timed out") || lowercased.contains("timeout") {
            return L10n.t("friendly.timeout")
        }
        if lowercased.contains("offline") || lowercased.contains("could not connect") || lowercased.contains("cannot connect") || lowercased.contains("network connection") {
            return L10n.t("friendly.offline")
        }
        if lowercased.contains("http") {
            return L10n.t("friendly.server")
        }
        if lowercased.contains("decode") || lowercased.contains("decoding") {
            return L10n.t("friendly.decode")
        }
        if lowercased.contains("valid positive") || lowercased.contains("numeric") {
            return L10n.t("friendly.input")
        }
        if lowercased.contains("unavailable") || lowercased.contains("model") {
            return L10n.t("friendly.model")
        }
        return L10n.t(defaultKey)
    }
}

extension Double {
    func metricText(digits: Int) -> String {
        formatted(.number.precision(.fractionLength(0...digits)))
    }
}

enum AppTheme {
    static let background = LinearGradient(
        colors: [
            Color(red: 0.953, green: 0.965, blue: 0.976),
            Color(red: 0.984, green: 0.957, blue: 0.941)
        ],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )
    static let card = Color.white
    static let field = Color(red: 0.941, green: 0.953, blue: 0.969)
    static let ink = Color(red: 0.055, green: 0.075, blue: 0.118)
    static let muted = Color(red: 0.365, green: 0.420, blue: 0.510)
    static let primary = Color(red: 0.145, green: 0.333, blue: 0.820)
    static let accent = Color(red: 0.918, green: 0.298, blue: 0.129)
    static let success = Color(red: 0.020, green: 0.588, blue: 0.412)
    static let warning = Color(red: 0.851, green: 0.467, blue: 0.024)
    static let danger = Color(red: 0.863, green: 0.149, blue: 0.149)
}

struct AppCard<Content: View>: View {
    @ViewBuilder let content: Content

    var body: some View {
        content
            .padding(16)
            .background(AppTheme.card, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(AppTheme.primary.opacity(0.08), lineWidth: 1)
            )
            .shadow(color: AppTheme.primary.opacity(0.08), radius: 18, x: 0, y: 10)
    }
}

struct PrimaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.headline)
            .foregroundStyle(.white)
            .padding(.vertical, 14)
            .background(
                LinearGradient(
                    colors: [
                        AppTheme.primary.opacity(configuration.isPressed ? 0.84 : 1),
                        AppTheme.accent.opacity(configuration.isPressed ? 0.74 : 0.9)
                    ],
                    startPoint: .leading,
                    endPoint: .trailing
                ),
                in: RoundedRectangle(cornerRadius: 8, style: .continuous)
            )
            .opacity(configuration.isPressed ? 0.88 : 1)
    }
}

struct SecondaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.subheadline.weight(.bold))
            .foregroundStyle(AppTheme.primary)
            .padding(.vertical, 12)
            .background(
                AppTheme.primary.opacity(configuration.isPressed ? 0.16 : 0.1),
                in: RoundedRectangle(cornerRadius: 8, style: .continuous)
            )
    }
}

extension View {
    @ViewBuilder
    func appInlineNavigationTitle() -> some View {
        #if os(iOS)
        self.navigationBarTitleDisplayMode(.inline)
        #else
        self
        #endif
    }
}

private extension View {
    @ViewBuilder
    func urlInputStyle() -> some View {
        #if os(iOS)
        self
            .textInputAutocapitalization(.never)
            .keyboardType(.URL)
            .autocorrectionDisabled()
        #else
        self
        #endif
    }

    @ViewBuilder
    func numericInputStyle() -> some View {
        #if os(iOS)
        self.keyboardType(.numbersAndPunctuation)
        #else
        self
        #endif
    }
}
