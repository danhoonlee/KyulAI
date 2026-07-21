import KyulAIDDLaminateCore
import SwiftUI

struct ContentView: View {
    private enum InputMode: String, CaseIterable, Identifiable {
        case forecast
        case u3

        var id: String { rawValue }
    }

    private enum DetailRoute: Hashable, Identifiable {
        case response(ResponsePredictionResult, DesignSpaceResponse?)
        case u3(U3PtPredictionResult, DesignSpaceResponse?)

        var id: String {
            switch self {
            case .response(let result, _):
                "response-\(result.modelKey)-\(result.predictedPt)-\(result.curve.count)"
            case .u3(let result, _):
                "u3-\(result.modelKey)-\(result.predictedPt)-\(result.curve.count)"
            }
        }
    }

    private enum FocusedField: Hashable {
        case theta1
        case theta2
        case apiBaseURL
    }

    @EnvironmentObject private var settings: AppSettings
    @EnvironmentObject private var viewModel: PredictionViewModel
    @FocusState private var focusedField: FocusedField?
    @State private var selectedDetail: DetailRoute?
    @State private var selectedInputMode: InputMode = .forecast
    @State private var isShowingSettings = false
    @State private var isShowingResponseModelPicker = false
    @State private var isShowingU3ModelPicker = false
    @State private var isShowingComparison = false
    @State private var isShowingRecentDelete = false
    @State private var comparisonSelectionIDs: [String] = []

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                header
                inputModePicker
                selectedInputCard
                recentResultsCard
                selectedLatestResultCard
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
        .sheet(isPresented: $isShowingU3ModelPicker) {
            NavigationStack {
                u3ModelSelectionSheet
                    .navigationTitle(L10n.t("choose.model"))
                    .appInlineNavigationTitle()
                    .toolbar {
                        ToolbarItem(placement: .confirmationAction) {
                            Button(L10n.t("done")) {
                                isShowingU3ModelPicker = false
                            }
                        }
                    }
            }
        }
        .sheet(isPresented: $isShowingComparison) {
            NavigationStack {
                DDLaminateComparisonView(
                    runs: currentRecentRuns,
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
                RecentDeleteView(runs: currentRecentRuns) { selectedIDs in
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
        .navigationDestination(item: $selectedDetail) { route in
            switch route {
            case .response(let result, let designSpace):
                ResultDetailView(result: result, designSpace: designSpace)
                    .environmentObject(settings)
            case .u3(let result, let designSpace):
                U3PtResultDetailView(result: result, designSpace: designSpace)
                    .environmentObject(settings)
            }
        }
        .task {
            await autoCheckConnection()
        }
        .onChange(of: settings.apiBaseURL) {
            viewModel.resetReadiness()
            Task { await autoCheckConnection() }
        }
        .onChange(of: selectedInputMode) {
            comparisonSelectionIDs = []
        }
    }

    private var currentRecentRuns: [DDLaminateRecentRun] {
        switch selectedInputMode {
        case .forecast:
            viewModel.responseForecastRecentRuns
        case .u3:
            viewModel.u3ForecastRecentRuns
        }
    }

    @ViewBuilder
    private var selectedInputCard: some View {
        switch selectedInputMode {
        case .forecast:
            forecastCard
        case .u3:
            u3PtCard
        }
    }

    @ViewBuilder
    private var selectedLatestResultCard: some View {
        switch selectedInputMode {
        case .forecast:
            if let result = viewModel.result {
                latestResultCard(result)
            }
        case .u3:
            if let result = viewModel.u3PtResult {
                u3PtResultCard(result)
            }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(appHeadlineTitle)
                .font(.system(size: 34, weight: .bold, design: .rounded))
                .foregroundStyle(
                    LinearGradient(colors: [AppTheme.ink, AppTheme.primary], startPoint: .leading, endPoint: .trailing)
                )
                .lineLimit(2)
                .minimumScaleFactor(0.82)
                .multilineTextAlignment(.leading)
                .fixedSize(horizontal: false, vertical: true)
            Text(L10n.t("app.subtitle"))
                .font(.callout)
                .foregroundStyle(AppTheme.muted)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(.top, 8)
    }

    private var inputModePicker: some View {
        Picker(L10n.t("prediction.mode"), selection: $selectedInputMode) {
            Label(L10n.t("response.forecast"), systemImage: "waveform.path.ecg")
                .tag(InputMode.forecast)
            Label(L10n.t("u3.forecast"), systemImage: "scope")
                .tag(InputMode.u3)
        }
        .pickerStyle(.segmented)
    }

    private var forecastCard: some View {
        AppCard {
            VStack(alignment: .leading, spacing: 18) {
                HStack {
                    Label(L10n.t("response.forecast"), systemImage: "slider.horizontal.3")
                        .font(.headline)
                        .foregroundStyle(AppTheme.ink)
                    Spacer()
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

    private var u3PtCard: some View {
        AppCard {
            VStack(alignment: .leading, spacing: 18) {
                HStack {
                    Label(localText(en: "u3 Pt Forecast", ko: "u3 Pt 예측"), systemImage: "point.topleft.down.curvedto.point.bottomright.up")
                        .font(.headline)
                        .foregroundStyle(AppTheme.ink)
                    Spacer()
                    Text(localText(en: "Type predicted", ko: "Type 예측"))
                        .font(.caption.bold())
                        .foregroundStyle(AppTheme.primary)
                        .padding(.horizontal, 9)
                        .padding(.vertical, 5)
                        .background(AppTheme.primary.opacity(0.1), in: Capsule())
                }

                u3ModelMenu

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
                    Task { await predictU3Pt() }
                } label: {
                    HStack {
                        if viewModel.isPredictingU3Pt {
                            ProgressView()
                                .tint(.white)
                        } else {
                            Image(systemName: "scope")
                        }
                        Text(viewModel.isPredictingU3Pt ? L10n.t("predicting") : localText(en: "Predict u3 Pt", ko: "u3 Pt 예측"))
                            .fontWeight(.bold)
                    }
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(PrimaryButtonStyle())
                .disabled(!viewModel.canPredictU3Pt)
            }
        }
    }

    private var u3ModelMenu: some View {
        let selectedModel = viewModel.u3PtModels.first { $0.key == viewModel.selectedU3PtModelKey }
        let title = selectedModel?.displayLabel ?? viewModel.selectedU3PtModelKey
        return VStack(alignment: .leading, spacing: 8) {
            Button {
                isShowingU3ModelPicker = true
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
                        Text(selectedModel.map { modelDescription(for: $0) } ?? localText(en: "Connect to the API to load u3 Pt models.", ko: "API에 연결하면 u3 Pt 모델을 불러옵니다."))
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

    private func recentRunTitle(_ run: DDLaminateRecentRun, index: Int) -> String {
        let prefix = index == 0 ? "\(index + 1). \(L10n.t("recent.latest"))" : "\(index + 1)."
        return "\(prefix) \(run.displayTitle) · \(run.displaySubtitle)"
    }

    @ViewBuilder
    private var recentResultsCard: some View {
        if !currentRecentRuns.isEmpty {
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

                        if currentRecentRuns.count >= 2 {
                            Button {
                                comparisonSelectionIDs = Array(currentRecentRuns.prefix(2).map(\.id))
                                isShowingComparison = true
                            } label: {
                                Label(L10n.t("compare"), systemImage: "rectangle.split.2x1")
                                    .font(.caption.weight(.bold))
                            }
                            .buttonStyle(.plain)
                            .foregroundStyle(AppTheme.primary)
                        }
                    }

                    ForEach(Array(currentRecentRuns.enumerated()), id: \.element.id) { index, run in
                        recentRunRow(run, index: index)
                        if index < currentRecentRuns.count - 1 {
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
                    Text("Theta 1 \(run.theta1Display) deg · Theta 2 \(run.theta2Display) deg")
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
                        modelOptionCard(
                            model,
                            isSelected: model.key == viewModel.selectedResponseModelKey
                        ) {
                            viewModel.selectResponseModel(key: model.key)
                            isShowingResponseModelPicker = false
                        }
                    }
                }
            }
            .padding(20)
        }
        .background(AppTheme.background.ignoresSafeArea())
    }

    private var u3ModelSelectionSheet: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                Text(L10n.t("model.selection.hint"))
                    .font(.callout)
                    .foregroundStyle(AppTheme.muted)
                    .fixedSize(horizontal: false, vertical: true)
                    .padding(.bottom, 2)

                if viewModel.u3PtModels.isEmpty {
                    AppCard {
                        Text(L10n.t("model.loading"))
                            .font(.subheadline)
                            .foregroundStyle(AppTheme.muted)
                    }
                } else {
                    ForEach(viewModel.u3PtModels) { model in
                        modelOptionCard(
                            model,
                            isSelected: model.key == viewModel.selectedU3PtModelKey
                        ) {
                            viewModel.selectU3PtModel(key: model.key)
                            isShowingU3ModelPicker = false
                        }
                    }
                }
            }
            .padding(20)
        }
        .background(AppTheme.background.ignoresSafeArea())
    }

    private func modelOptionCard(_ model: ModelInfo, isSelected: Bool, onSelect: @escaping () -> Void) -> some View {
        return Button {
            guard model.available else { return }
            onSelect()
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
        model?.key == DDLaminateDefaults.responseModelKey || model?.key == DDLaminateDefaults.u3PtModelKey
    }

    private func modelTag(for model: ModelInfo?) -> String {
        guard let model else { return L10n.t("model.loading") }
        let label = model.displayLabel.lowercased()
        if model.key.contains("goint") || label.contains("nn") {
            return L10n.t("model.tag.deep")
        }
        if model.key == DDLaminateDefaults.responseModelKey
            || model.key == DDLaminateDefaults.u3PtModelKey
            || label.contains("machine learning")
            || label.contains("extratrees") {
            return L10n.t("model.tag.fast")
        }
        return L10n.t("model.tag.experimental")
    }

    private func modelDescription(for model: ModelInfo?) -> String {
        guard let model else { return L10n.t("model.loading") }
        let label = model.displayLabel.lowercased()
        if model.key == DDLaminateDefaults.responseModelKey
            || model.key == DDLaminateDefaults.u3PtModelKey
            || label.contains("machine learning")
            || label.contains("extratrees") {
            return L10n.t("model.description.extratrees")
        }
        if model.key.contains("goint") || label.contains("goint") || label.contains("deep learning") {
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

                if let agreement = result.teacherStudent {
                    TeacherStudentAgreementCard(agreement: agreement)
                }

                CurveChartView(points: result.curve, predictedPt: result.predictedPt, curveFit: result.curveFit)
                    .frame(height: 270)

                HStack(spacing: 10) {
                    Button {
                        selectedDetail = .response(result, viewModel.responseDesignSpace)
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
                        fileName: "c2es-laminate-forecast",
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

    private func u3PtResultCard(_ result: U3PtPredictionResult) -> some View {
        AppCard {
            VStack(alignment: .leading, spacing: 16) {
                HStack(alignment: .firstTextBaseline) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(localText(en: "u3 Pt Result", ko: "u3 Pt 결과"))
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(AppTheme.muted)
                        Text("Pt \(result.predictedPt.metricText(digits: 2))")
                            .font(.system(size: 32, weight: .bold, design: .rounded))
                            .foregroundStyle(AppTheme.ink)
                    }
                    Spacer()
                    VStack(alignment: .trailing, spacing: 6) {
                        if let predictedType = result.predictedType {
                            Text("Type \(predictedType)")
                                .font(.caption.weight(.bold))
                                .foregroundStyle(AppTheme.danger)
                                .padding(.horizontal, 9)
                                .padding(.vertical, 5)
                                .background(AppTheme.danger.opacity(0.1), in: Capsule())
                        }
                        Text(result.displayModelLabel)
                            .font(.caption.weight(.bold))
                            .foregroundStyle(AppTheme.primary)
                            .padding(.horizontal, 9)
                            .padding(.vertical, 5)
                            .background(AppTheme.primary.opacity(0.1), in: Capsule())
                    }
                }

                HStack(spacing: 10) {
                    if let confidence = result.confidence {
                        miniMetric(localText(en: "Type Conf.", ko: "Type 신뢰도"), Optional(confidence).percentText)
                    }
                    miniMetric(L10n.t("max.force"), result.predictedMaxForce.metricText(digits: 1))
                    miniMetric("Max. Disp.", result.predictedMaxDisplacement.metricText(digits: 5))
                }

                CurveChartView(points: result.curve, predictedPt: result.predictedPt, fitMode: .u3, curveFit: result.curveFit)
                    .frame(height: 270)

                Button {
                    selectedDetail = .u3(result, viewModel.u3DesignSpace)
                } label: {
                    Label(L10n.t("open.full.result"), systemImage: "chart.xyaxis.line")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(SecondaryButtonStyle())

                if !result.notes.isEmpty {
                    VStack(alignment: .leading, spacing: 6) {
                        ForEach(result.notes, id: \.self) { note in
                            Text("• \(note)")
                                .font(.caption)
                                .foregroundStyle(AppTheme.muted)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }
            }
        }
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
                settingsConnectionStatusRow
                Text(L10n.t("external.url.hint"))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var settingsConnectionStatusRow: some View {
        HStack(alignment: .center, spacing: 10) {
            statusIcon
            VStack(alignment: .leading, spacing: 2) {
                Text(settingsConnectionTitle)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(AppTheme.ink)
                if let detail = connectionDetail {
                    Text(detail)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }
            }
            Spacer()
            if connectionIsFailed {
                Button {
                    Task { await autoCheckConnection() }
                } label: {
                    Label(L10n.t("retry.action"), systemImage: "arrow.clockwise")
                        .labelStyle(.iconOnly)
                }
                .buttonStyle(.borderless)
            }
        }
        .padding(.vertical, 4)
        .accessibilityElement(children: .combine)
    }

    private var statusIcon: some View {
        let config = statusConfig
        return Image(systemName: config.icon)
            .font(.subheadline.weight(.semibold))
            .foregroundStyle(config.color)
            .frame(width: 28, height: 28)
            .background(config.color.opacity(0.12), in: Circle())
    }

    private var settingsConnectionTitle: String {
        switch viewModel.connectionState {
        case .idle:
            L10n.t("api.not.checked")
        case .checking:
            L10n.t("checking.api")
        case .ready(let available):
            available ? L10n.t("api.connected") : L10n.t("model.unavailable")
        case .failed:
            L10n.t("connection.failed")
        }
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
                selectedDetail = .response(result, viewModel.responseDesignSpace)
            }
        } catch {
            viewModel.errorMessage = error.localizedDescription
        }
    }

    private func predictU3Pt() async {
        do {
            let url = try BaseURLValidator.parse(settings.apiBaseURL)
            await viewModel.predictU3Forecast(baseURL: url)
            if let result = viewModel.u3PtResult, viewModel.errorMessage == nil {
                selectedDetail = .u3(result, viewModel.u3DesignSpace)
            }
        } catch {
            viewModel.errorMessage = error.localizedDescription
        }
    }

    private func localText(en: String, ko: String) -> String {
        settings.languageCode == "ko" ? ko : en
    }

    private var appHeadlineTitle: String {
        localText(en: "C2ES Laminate Forecast", ko: "C2ES 적층 예측")
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

                    Button {
                        selectedIDs = Set(runs.map(\.id))
                    } label: {
                        Label(L10n.t("recent.delete.select.all"), systemImage: "checkmark.circle")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(SecondaryButtonStyle())
                    .disabled(runs.isEmpty || selectedIDs.count == runs.count)

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
                                            Text("\(run.displayModelLabel) · Theta \(run.theta1Display) / \(run.theta2Display) · Pt \(run.predictedPt?.metricText(digits: 2) ?? "-")")
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
