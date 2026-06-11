import KyulAIDDLaminateCore
import SwiftUI

struct ContentView: View {
    private enum FocusedField: Hashable {
        case theta1
        case theta2
        case apiBaseURL
    }

    @EnvironmentObject private var settings: AppSettings
    @EnvironmentObject private var viewModel: PredictionViewModel
    @FocusState private var focusedField: FocusedField?
    @State private var selectedResult: ResponsePredictionResult?
    @State private var isShowingSettings = false
    @State private var isShowingResponseModelPicker = false
    @State private var isShowingComparison = false
    @State private var isShowingRecentDelete = false
    @State private var comparisonSelectionIDs: [String] = []

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    header
                    connectionCard
                    forecastCard
                    recentResultsCard
                    if let result = viewModel.result {
                        latestResultCard(result)
                    }
                }
                .padding(20)
            }
            #if os(iOS)
            .scrollDismissesKeyboard(.interactively)
            #endif
            .simultaneousGesture(TapGesture().onEnded {
                focusedField = nil
            })
            .background(AppTheme.background.ignoresSafeArea())
            .appInlineNavigationTitle()
            .toolbar {
                ToolbarItemGroup(placement: toolbarTrailingPlacement) {
                    Button {
                        settings.toggleLanguage()
                    } label: {
                        HStack(spacing: 4) {
                            Image(systemName: "globe")
                            Text(settings.languageCode.uppercased())
                                .font(.caption.weight(.black))
                        }
                        .foregroundStyle(AppTheme.primary)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 5)
                        .background(AppTheme.primary.opacity(0.10), in: Capsule())
                    }
                    .accessibilityLabel(L10n.t("language.toggle"))

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
                        .navigationTitle(L10n.t("api.settings.title"))
                        .appInlineNavigationTitle()
                        .toolbar {
                            ToolbarItem(placement: .confirmationAction) {
                                Button(L10n.t("done")) {
                                    isShowingSettings = false
                                }
                            }
                        }
                }
            }
            .sheet(isPresented: $isShowingResponseModelPicker) {
                NavigationStack {
                    modelSelectionSheet
                        .navigationTitle(L10n.t("choose.model"))
                        .appInlineNavigationTitle()
                        .toolbar {
                            ToolbarItem(placement: .confirmationAction) {
                                Button(L10n.t("done")) {
                                    isShowingResponseModelPicker = false
                                }
                            }
                        }
                }
            }
            .sheet(isPresented: $isShowingComparison) {
                NavigationStack {
                    DDLaminateComparisonView(
                        runs: viewModel.recentRuns,
                        selectedIDs: $comparisonSelectionIDs
                    )
                    .navigationTitle(L10n.t("compare.results"))
                    .appInlineNavigationTitle()
                    .toolbar {
                        ToolbarItem(placement: .confirmationAction) {
                            Button(L10n.t("done")) {
                                isShowingComparison = false
                            }
                        }
                    }
                }
            }
            .sheet(isPresented: $isShowingRecentDelete) {
                NavigationStack {
                    RecentDeleteView(runs: viewModel.recentRuns) { selectedIDs in
                        viewModel.deleteRecentRuns(ids: selectedIDs)
                        isShowingRecentDelete = false
                    }
                    .navigationTitle(L10n.t("recent.delete.title"))
                    .appInlineNavigationTitle()
                    .toolbar {
                        ToolbarItem(placement: .cancellationAction) {
                            Button(L10n.t("done")) {
                                isShowingRecentDelete = false
                            }
                        }
                    }
                }
            }
            .alert(L10n.t("prediction.error"), isPresented: errorBinding) {
                Button(L10n.t("ok"), role: .cancel) { viewModel.errorMessage = nil }
            } message: {
                Text(friendlyErrorMessage(viewModel.errorMessage))
            }
            .navigationDestination(item: $selectedResult) { result in
                ResultDetailView(result: result)
            }
            .task {
                await autoCheckConnection()
            }
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
            VStack(alignment: .leading, spacing: 14) {
                HStack(alignment: .center, spacing: 12) {
                    statusIcon
                    VStack(alignment: .leading, spacing: 3) {
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
                                .lineLimit(3)
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

                if let model = viewModel.responseModel {
                    Divider()
                    VStack(alignment: .leading, spacing: 4) {
                        Text(model.displayLabel)
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(AppTheme.ink)
                        Text(model.description)
                            .font(.caption)
                            .foregroundStyle(AppTheme.muted)
                            .fixedSize(horizontal: false, vertical: true)
                    }
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
    }

    private var forecastCard: some View {
        AppCard {
            VStack(alignment: .leading, spacing: 18) {
                HStack {
                    Label(L10n.t("forecast.inputs"), systemImage: "slider.horizontal.3")
                        .font(.headline)
                        .foregroundStyle(AppTheme.ink)
                    Spacer()
                    if !viewModel.recentRuns.isEmpty {
                        recentRunsMenu
                    }
                    Text(viewModel.selectedCase.rawValue)
                        .font(.caption.bold())
                        .foregroundStyle(AppTheme.primary)
                        .padding(.horizontal, 9)
                        .padding(.vertical, 5)
                        .background(AppTheme.primary.opacity(0.1), in: Capsule())
                }

                responseModelCard

                Picker("Case", selection: $viewModel.selectedCase) {
                    ForEach(DDLaminateCase.allCases) { laminateCase in
                        Text(laminateCase.rawValue).tag(laminateCase)
                    }
                }
                .pickerStyle(.segmented)

                HStack(spacing: 12) {
                    numericField(title: "Theta 1", value: $viewModel.theta1, field: .theta1)
                    numericField(title: "Theta 2", value: $viewModel.theta2, field: .theta2)
                }

                Button {
                    focusedField = nil
                    Task { await predict() }
                } label: {
                    HStack {
                        if viewModel.isPredicting {
                            ProgressView()
                                .tint(.white)
                        } else {
                            Image(systemName: "waveform.path.ecg")
                        }
                        Text(viewModel.isPredicting ? L10n.t("predicting") : L10n.t("predict.forecast"))
                            .fontWeight(.bold)
                    }
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(PrimaryButtonStyle())
                .disabled(!viewModel.canPredict)

                if !viewModel.canPredict && !viewModel.isPredicting {
                    Text(L10n.t("readiness.before.prediction"))
                        .font(.caption)
                        .foregroundStyle(AppTheme.muted)
                }
            }
        }
    }

    private var recentRunsMenu: some View {
        Menu {
            ForEach(Array(viewModel.recentRuns.enumerated()), id: \.element.id) { index, run in
                Button {
                    viewModel.applyRecentRun(run)
                } label: {
                    Text(recentRunTitle(run, index: index))
                }
            }
            Divider()
            Button(role: .destructive) {
                isShowingRecentDelete = true
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

    private func recentRunTitle(_ run: DDLaminateRecentRun, index: Int) -> String {
        let prefix = index == 0 ? "\(index + 1). \(L10n.t("recent.latest"))" : "\(index + 1)."
        return "\(prefix) \(run.displayTitle) · \(run.displaySubtitle)"
    }

    @ViewBuilder
    private var recentResultsCard: some View {
        if !viewModel.recentRuns.isEmpty {
            AppCard {
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Label(L10n.t("recent.results"), systemImage: "clock")
                            .font(.headline)
                            .foregroundStyle(AppTheme.ink)
                        Spacer()
                        Button(role: .destructive) {
                            isShowingRecentDelete = true
                        } label: {
                            Image(systemName: "trash")
                                .font(.caption.weight(.bold))
                        }
                        .buttonStyle(.plain)
                        .foregroundStyle(AppTheme.danger)

                        if viewModel.recentRuns.count >= 2 {
                            Button {
                                comparisonSelectionIDs = Array(viewModel.recentRuns.prefix(2).map(\.id))
                                isShowingComparison = true
                            } label: {
                                Label(L10n.t("compare"), systemImage: "rectangle.split.2x1")
                                    .font(.caption.weight(.bold))
                            }
                            .buttonStyle(.plain)
                            .foregroundStyle(AppTheme.primary)
                        }
                    }

                    ForEach(Array(viewModel.recentRuns.enumerated()), id: \.element.id) { index, run in
                        recentRunRow(run, index: index)
                        if index < viewModel.recentRuns.count - 1 {
                            Divider()
                        }
                    }
                }
            }
        }
    }

    private func recentRunRow(_ run: DDLaminateRecentRun, index: Int) -> some View {
        Button {
            viewModel.applyRecentRun(run)
        } label: {
            HStack(alignment: .center, spacing: 12) {
                Text(index == 0 ? "\(index + 1)\n\(L10n.t("recent.latest"))" : "\(index + 1)")
                    .font(.caption2.weight(.black))
                    .multilineTextAlignment(.center)
                    .foregroundStyle(index == 0 ? AppTheme.primary : AppTheme.muted)
                    .frame(width: 42, height: 42)
                    .background((index == 0 ? AppTheme.primary : AppTheme.muted).opacity(0.10), in: Circle())

                VStack(alignment: .leading, spacing: 5) {
                    HStack(spacing: 8) {
                        Text(run.selectedCase.rawValue)
                            .font(.subheadline.weight(.bold))
                            .foregroundStyle(AppTheme.ink)
                        Text(run.displayModelLabel)
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(AppTheme.primary)
                    }
                    Text("Theta 1 \(run.theta1) deg · Theta 2 \(run.theta2) deg")
                        .font(.caption)
                        .foregroundStyle(AppTheme.muted)
                    HStack(spacing: 8) {
                        recentBadge(run.predictedType.map { L10n.f("type.format", $0) } ?? L10n.t("recent.no.result"))
                        recentBadge(run.confidence.percentText)
                        recentBadge("Pt \(run.predictedPt?.metricText(digits: 2) ?? "-")")
                    }
                }
                Spacer()
                Image(systemName: "arrow.uturn.forward")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(AppTheme.primary)
            }
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }

    private func recentBadge(_ text: String) -> some View {
        Text(text)
            .font(.caption2.monospacedDigit().weight(.bold))
            .foregroundStyle(AppTheme.ink)
            .lineLimit(1)
            .minimumScaleFactor(0.75)
            .padding(.horizontal, 7)
            .padding(.vertical, 4)
            .background(AppTheme.field, in: Capsule())
    }

    private var responseModelCard: some View {
        let selectedModel = viewModel.responseModels.first { $0.key == viewModel.selectedResponseModelKey }
        let title = selectedModel?.displayLabel ?? viewModel.selectedResponseModelKey
        return VStack(alignment: .leading, spacing: 8) {
            Text(L10n.t("response.model"))
                .font(.caption.weight(.semibold))
                .foregroundStyle(AppTheme.muted)
            Button {
                isShowingResponseModelPicker = true
            } label: {
                HStack(alignment: .center, spacing: 12) {
                    Image(systemName: modelIcon(for: selectedModel))
                        .font(.headline)
                        .foregroundStyle(AppTheme.primary)
                        .frame(width: 38, height: 38)
                        .background(AppTheme.primary.opacity(0.10), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                    VStack(alignment: .leading, spacing: 6) {
                        HStack(spacing: 6) {
                            Text(title)
                                .font(.subheadline.weight(.bold))
                                .foregroundStyle(AppTheme.ink)
                                .lineLimit(1)
                                .minimumScaleFactor(0.78)
                            if isRecommendedModel(selectedModel) {
                                modelBadge(L10n.t("model.recommended"), color: AppTheme.success)
                            }
                        }
                        Text(modelDescription(for: selectedModel))
                            .font(.caption)
                            .foregroundStyle(AppTheme.muted)
                            .lineLimit(2)
                            .minimumScaleFactor(0.86)
                    }
                    Spacer()
                    Image(systemName: "chevron.up.chevron.down")
                        .font(.caption.weight(.bold))
                        .foregroundStyle(AppTheme.primary)
                }
                .padding(12)
                .background(AppTheme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .stroke(AppTheme.primary.opacity(0.12), lineWidth: 1)
                )
                .contentShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            }
            .buttonStyle(.plain)
        }
    }

    private var modelSelectionSheet: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                Text(L10n.t("model.selection.hint"))
                    .font(.callout)
                    .foregroundStyle(AppTheme.muted)
                    .fixedSize(horizontal: false, vertical: true)
                    .padding(.bottom, 2)

                if viewModel.responseModels.isEmpty {
                    AppCard {
                        Text(L10n.t("model.loading"))
                            .font(.subheadline)
                            .foregroundStyle(AppTheme.muted)
                    }
                } else {
                    ForEach(viewModel.responseModels) { model in
                        modelOptionCard(model)
                    }
                }
            }
            .padding(20)
        }
        .background(AppTheme.background.ignoresSafeArea())
    }

    private func modelOptionCard(_ model: ModelInfo) -> some View {
        let isSelected = model.key == viewModel.selectedResponseModelKey
        return Button {
            guard model.available else { return }
            viewModel.selectResponseModel(key: model.key)
            isShowingResponseModelPicker = false
        } label: {
            VStack(alignment: .leading, spacing: 12) {
                HStack(alignment: .center, spacing: 12) {
                    Image(systemName: modelIcon(for: model))
                        .font(.headline)
                        .foregroundStyle(model.available ? AppTheme.primary : AppTheme.muted)
                        .frame(width: 42, height: 42)
                        .background((model.available ? AppTheme.primary : AppTheme.muted).opacity(0.10), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                    VStack(alignment: .leading, spacing: 5) {
                        Text(model.displayLabel)
                            .font(.headline)
                            .foregroundStyle(model.available ? AppTheme.ink : AppTheme.muted)
                        HStack(spacing: 6) {
                            if isRecommendedModel(model) {
                                modelBadge(L10n.t("model.recommended"), color: AppTheme.success)
                            }
                            modelBadge(modelTag(for: model), color: AppTheme.primary)
                            if !model.available {
                                modelBadge(L10n.t("model.missing"), color: AppTheme.danger)
                            }
                        }
                    }
                    Spacer()
                    if isSelected {
                        Image(systemName: "checkmark.circle.fill")
                            .font(.title3)
                            .foregroundStyle(AppTheme.success)
                    }
                }
                Text(modelDescription(for: model))
                    .font(.subheadline)
                    .foregroundStyle(AppTheme.muted)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .padding(14)
            .background(AppTheme.card, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(isSelected ? AppTheme.primary.opacity(0.65) : AppTheme.primary.opacity(0.10), lineWidth: isSelected ? 2 : 1)
            )
            .opacity(model.available ? 1 : 0.55)
            .contentShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        }
        .buttonStyle(.plain)
        .disabled(!model.available)
    }

    private func modelBadge(_ text: String, color: Color) -> some View {
        Text(text)
            .font(.caption2.weight(.black))
            .foregroundStyle(color)
            .lineLimit(1)
            .padding(.horizontal, 7)
            .padding(.vertical, 4)
            .background(color.opacity(0.12), in: Capsule())
    }

    private func modelIcon(for model: ModelInfo?) -> String {
        guard let model else { return "cpu" }
        return model.key.contains("goint") || model.displayLabel.lowercased().contains("nn") ? "brain.head.profile" : "tree"
    }

    private func isRecommendedModel(_ model: ModelInfo?) -> Bool {
        model?.key == DDLaminateDefaults.responseModelKey
    }

    private func modelTag(for model: ModelInfo?) -> String {
        guard let model else { return L10n.t("model.loading") }
        let label = model.displayLabel.lowercased()
        if model.key.contains("goint") || label.contains("nn") {
            return L10n.t("model.tag.deep")
        }
        if model.key == DDLaminateDefaults.responseModelKey || label.contains("extratrees") {
            return L10n.t("model.tag.fast")
        }
        return L10n.t("model.tag.experimental")
    }

    private func modelDescription(for model: ModelInfo?) -> String {
        guard let model else { return L10n.t("model.loading") }
        let label = model.displayLabel.lowercased()
        if model.key == DDLaminateDefaults.responseModelKey || label.contains("extratrees") {
            return L10n.t("model.description.extratrees")
        }
        if model.key.contains("goint") || label.contains("goint") {
            return L10n.t("model.description.goint")
        }
        return model.description.isEmpty ? L10n.t("model.description.generic") : model.description
    }

    private func numericField(title: String, value: Binding<String>, field: FocusedField) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.caption.weight(.semibold))
                .foregroundStyle(AppTheme.muted)
            HStack(alignment: .firstTextBaseline, spacing: 6) {
                TextField(title, text: value)
                    .font(.title3.monospacedDigit().weight(.bold))
                    .foregroundStyle(AppTheme.ink)
                    .focused($focusedField, equals: field)
                    .submitLabel(.done)
                    .onSubmit {
                        focusedField = nil
                    }
                    .numericInputStyle()
                Text("deg")
                    .font(.caption)
                    .foregroundStyle(AppTheme.muted)
            }
            .padding(12)
            .background(AppTheme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(AppTheme.primary.opacity(0.12), lineWidth: 1)
            )
        }
    }

    private func latestResultCard(_ result: ResponsePredictionResult) -> some View {
        AppCard {
            VStack(alignment: .leading, spacing: 16) {
                HStack(alignment: .firstTextBaseline) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(L10n.t("latest.result"))
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(AppTheme.muted)
                        Text(L10n.f("type.format", result.predictedType))
                            .font(.system(size: 34, weight: .bold, design: .rounded))
                            .foregroundStyle(AppTheme.ink)
                    }
                    Spacer()
                    Text(result.confidence.percentText)
                        .font(.title3.monospacedDigit().weight(.bold))
                        .foregroundStyle(AppTheme.primary)
                }

                HStack(spacing: 10) {
                    miniMetric("Pt", result.predictedPt.metricText(digits: 2))
                    miniMetric(L10n.t("max.force"), result.predictedMaxForce.metricText(digits: 1))
                    miniMetric(L10n.t("pt.disp"), result.predictedPtDisplacement?.metricText(digits: 5) ?? "-")
                }

                Divider()

                InterpretationSummaryView(result: result, maxLines: 2)

                CurveChartView(points: result.curve, predictedPt: result.predictedPt)
                    .frame(height: 190)

                HStack(spacing: 10) {
                    Button {
                        selectedResult = result
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
                        fileName: "luvelox-laminate-forecast",
                        report: LaminateShareImageReportView(result: result)
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
    }

    private var settingsView: some View {
        Form {
            Section(L10n.t("base.url")) {
                TextField(L10n.t("api.base.url"), text: $settings.apiBaseURL)
                    .focused($focusedField, equals: .apiBaseURL)
                    .submitLabel(.done)
                    .onSubmit {
                        focusedField = nil
                    }
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
        if lowercased.contains("theta") || lowercased.contains("numeric") {
            return L10n.t("friendly.input")
        }
        if lowercased.contains("unavailable") || lowercased.contains("model") || lowercased.contains("response_surrogate") {
            return L10n.t("friendly.model")
        }
        return L10n.t(defaultKey)
    }
}

extension Optional where Wrapped == Double {
    var percentText: String {
        guard let value = self else { return "-" }
        return value.formatted(.percent.precision(.fractionLength(1)))
    }
}

extension Double {
    func metricText(digits: Int) -> String {
        formatted(.number.precision(.fractionLength(0...digits)))
    }
}

private struct RecentDeleteView: View {
    let runs: [DDLaminateRecentRun]
    let onDelete: (Set<String>) -> Void
    @State private var selectedIDs: Set<String> = []

    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    Text(L10n.t("recent.delete.select"))
                        .font(.callout)
                        .foregroundStyle(AppTheme.muted)
                        .fixedSize(horizontal: false, vertical: true)

                    AppCard {
                        VStack(alignment: .leading, spacing: 0) {
                            ForEach(Array(runs.enumerated()), id: \.element.id) { index, run in
                                Button {
                                    toggle(run)
                                } label: {
                                    HStack(spacing: 12) {
                                        Image(systemName: selectedIDs.contains(run.id) ? "checkmark.circle.fill" : "circle")
                                            .foregroundStyle(selectedIDs.contains(run.id) ? AppTheme.danger : AppTheme.muted)
                                        VStack(alignment: .leading, spacing: 4) {
                                            Text(index == 0 ? "\(index + 1). \(L10n.t("recent.latest"))" : "\(index + 1). \(run.displayTitle)")
                                                .font(.subheadline.weight(.bold))
                                                .foregroundStyle(AppTheme.ink)
                                            Text("\(run.displayModelLabel) · Theta \(run.theta1) / \(run.theta2) · Pt \(run.predictedPt?.metricText(digits: 2) ?? "-")")
                                                .font(.caption)
                                                .foregroundStyle(AppTheme.muted)
                                        }
                                        Spacer()
                                    }
                                    .padding(.vertical, 10)
                                    .contentShape(Rectangle())
                                }
                                .buttonStyle(.plain)
                                if index < runs.count - 1 {
                                    Divider()
                                }
                            }
                        }
                    }
                }
                .padding(20)
            }

            Button(role: .destructive) {
                onDelete(selectedIDs)
            } label: {
                Text(L10n.f("recent.delete.count", selectedIDs.count))
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(PrimaryButtonStyle())
            .disabled(selectedIDs.isEmpty)
            .opacity(selectedIDs.isEmpty ? 0.45 : 1)
            .padding(20)
            .background(AppTheme.card)
        }
        .background(AppTheme.background.ignoresSafeArea())
    }

    private func toggle(_ run: DDLaminateRecentRun) {
        if selectedIDs.contains(run.id) {
            selectedIDs.remove(run.id)
        } else {
            selectedIDs.insert(run.id)
        }
    }
}

enum AppTheme {
    static let background = LinearGradient(
        colors: [
            Color(red: 0.949, green: 0.969, blue: 0.969),
            Color(red: 0.969, green: 0.980, blue: 0.976)
        ],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )
    static let card = Color.white
    static let field = Color(red: 0.933, green: 0.961, blue: 0.957)
    static let ink = Color(red: 0.047, green: 0.075, blue: 0.082)
    static let muted = Color(red: 0.357, green: 0.431, blue: 0.447)
    static let primary = Color(red: 0.000, green: 0.520, blue: 0.500)
    static let accent = Color(red: 0.050, green: 0.220, blue: 0.260)
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
                    .stroke(AppTheme.primary.opacity(0.10), lineWidth: 1)
            )
            .shadow(color: AppTheme.accent.opacity(0.08), radius: 18, x: 0, y: 10)
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
                        AppTheme.accent.opacity(configuration.isPressed ? 0.84 : 1),
                        AppTheme.primary.opacity(configuration.isPressed ? 0.80 : 0.95)
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

struct IconButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundStyle(AppTheme.primary)
            .frame(width: 36, height: 36)
            .background(
                AppTheme.primary.opacity(configuration.isPressed ? 0.18 : 0.1),
                in: Circle()
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
