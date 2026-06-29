import KyulAIInjectionCore
import SwiftUI
#if os(iOS)
import UIKit
#endif

#if os(iOS)
private func dismissInjectionKeyboard() {
    UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
}
#else
private func dismissInjectionKeyboard() {}
#endif

private extension View {
    @ViewBuilder
    func injectionScrollKeyboardDismissal() -> some View {
        #if os(iOS)
        self.scrollDismissesKeyboard(.interactively)
        #else
        self
        #endif
    }
}

struct ContentView: View {
    @EnvironmentObject private var settings: AppSettings
    @EnvironmentObject private var viewModel: PredictionViewModel
    private let wrapsInNavigationStack: Bool
    @State private var selectedResult: SpruePressurePredictionResult?
    @State private var isShowingResult = false
    @State private var isShowingSettings = false

    init(wrapsInNavigationStack: Bool = true) {
        self.wrapsInNavigationStack = wrapsInNavigationStack
    }

    var body: some View {
        if wrapsInNavigationStack {
            NavigationStack {
                content
            }
        } else {
            content
        }
    }

    private var content: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                header
                workflowStrip
                if connectionNeedsAttention {
                    connectionIssueCard
                }
                forecastCard
                if let result = viewModel.result {
                    latestResultCard(result)
                    assistantCard
                }
                historyCard
            }
            .padding(20)
        }
        .injectionScrollKeyboardDismissal()
        .background(AppTheme.background.ignoresSafeArea())
        .appInlineNavigationTitle()
        .toolbar {
            ToolbarItemGroup(placement: toolbarTrailingPlacement) {
                Button {
                    settings.toggleLanguage()
                } label: {
                    Label(settings.languageCode.uppercased(), systemImage: "globe")
                        .labelStyle(.titleAndIcon)
                }
                .font(.caption.weight(.black))
                .foregroundStyle(AppTheme.primary)
                .accessibilityLabel(L10n.t("language.toggle"))

                Button {
                    isShowingSettings = true
                } label: {
                    Image(systemName: "link")
                }
                .accessibilityLabel(L10n.t("api.settings"))
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
                    .environmentObject(settings)
            }
        }
        .task { await autoCheckConnection() }
        .onChange(of: settings.apiBaseURL) {
            viewModel.resetReadiness()
            Task { await autoCheckConnection() }
        }
    }

    private var isKorean: Bool {
        settings.languageCode == "ko"
    }

    private func localText(en: String, ko: String) -> String {
        isKorean ? ko : en
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .center, spacing: 12) {
                Text(localText(en: "Injection Forecast AI", ko: "사출 예측 AI"))
                    .font(.caption.weight(.black))
                    .foregroundStyle(AppTheme.primary)
                    .textCase(.uppercase)
                Spacer(minLength: 8)
                connectionBadge
            }
            Text(L10n.t("app.title"))
                .font(.system(size: 32, weight: .black, design: .rounded))
                .foregroundStyle(AppTheme.ink)
                .lineLimit(2)
                .minimumScaleFactor(0.78)
                .multilineTextAlignment(.leading)
                .fixedSize(horizontal: false, vertical: true)
            Text(L10n.t("app.subtitle"))
                .font(.callout.weight(.semibold))
                .foregroundStyle(AppTheme.muted)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(18)
        .background(AppTheme.card, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(AppTheme.line, lineWidth: 1)
        )
        .shadow(color: .black.opacity(0.06), radius: 18, x: 0, y: 10)
    }

    private var workflowStrip: some View {
        VStack(spacing: 10) {
            workflowStep("01", localText(en: "Set DOE", ko: "DOE 설정"), localText(en: "Choose geometry and process", ko: "형상과 공정 선택"))
            workflowStep("02", localText(en: "Preview", ko: "미리보기"), localText(en: "Check dimensions and controls", ko: "치수와 제어값 확인"))
            workflowStep("03", localText(en: "Review", ko: "결과 확인"), localText(en: "Pressure, curve, filling", ko: "압력, 곡선, 충전"))
        }
    }

    private func workflowStep(_ index: String, _ title: String, _ subtitle: String) -> some View {
        HStack(alignment: .top, spacing: 10) {
            Text(index)
                .font(.caption.weight(.black))
                .foregroundStyle(.white)
                .frame(width: 30, height: 30)
                .background(AppTheme.ink, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.caption.weight(.black))
                    .foregroundStyle(AppTheme.ink)
                Text(subtitle)
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(AppTheme.muted)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(AppTheme.card, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(AppTheme.line, lineWidth: 1)
        )
    }

    private var connectionIssueCard: some View {
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
                Text(connectionBadgeText)
                    .font(.caption2.weight(.black))
                    .foregroundStyle(statusConfig.color)
                    .padding(.horizontal, 9)
                    .padding(.vertical, 5)
                    .background(statusConfig.color.opacity(0.12), in: Capsule())
            }
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
                    Label(L10n.t("settings.action"), systemImage: "link")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(SecondaryButtonStyle())
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

                shapePreviewCard
                processDetailsCard
                geometryDetailsCard

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

    private var shapePreviewCard: some View {
        InjectionDetailSection(title: localText(en: "Shape Preview", ko: "형상 미리보기")) {
            InjectionShapePreviewCard(
                geometryID: viewModel.geometryID,
                gateType: viewModel.gateType,
                length: sanitizedDimension(viewModel.Lmm, fallback: 154.01),
                width: sanitizedDimension(viewModel.Wmm, fallback: 97.42),
                thickness: sanitizedDimension(viewModel.tmm, fallback: 2.207),
                holeDiameter: sanitizedDimension(viewModel.Dmm, fallback: 17.61),
                gateWidth: sanitizedDimension(viewModel.gateWidth, fallback: 10.0),
                gateHeight: sanitizedDimension(viewModel.gateHeight, fallback: 1.5)
            )
        }
    }

    private func sanitizedDimension(_ value: String, fallback: Double) -> Double {
        let parsed = Double(value.trimmingCharacters(in: .whitespacesAndNewlines)) ?? fallback
        guard parsed.isFinite, parsed > 0 else { return fallback }
        return min(max(parsed, 0.001), 10_000)
    }

    private func previewChip(_ title: String, _ value: String, _ unit: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title)
                .font(.caption2.weight(.black))
                .foregroundStyle(AppTheme.muted)
            Text("\(value) \(unit)")
                .font(.caption2.monospacedDigit().weight(.black))
                .foregroundStyle(AppTheme.ink)
                .lineLimit(1)
                .minimumScaleFactor(0.68)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(8)
        .background(Color.white.opacity(0.86), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(AppTheme.primary.opacity(0.10), lineWidth: 1)
        )
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

    private var processDetailsCard: some View {
        InjectionDetailSection(title: L10n.t("process.details")) {
            LazyVGrid(columns: detailColumns, spacing: 8) {
                detailInputCard("Melt temp", value: $viewModel.meltTempC, unit: "C", range: 180...320, digits: 1)
                detailInputCard("Mold temp", value: $viewModel.moldTempC, unit: "C", range: 20...130, digits: 1)
                detailInputCard("Packing pressure", value: $viewModel.packingPressureMPa, unit: "MPa", range: 10...130, digits: 1)
                detailInputCard("Injection time", value: $viewModel.injectionTimeS, unit: "s", range: 0.2...4.0, digits: 3)
            }
            detailInputCard("Packing time", value: $viewModel.packingTimeS, unit: "s", range: 0.2...8.0, digits: 3)
        }
    }

    private var geometryDetailsCard: some View {
        InjectionDetailSection(title: L10n.t("geometry.details")) {
            LazyVGrid(columns: detailColumns, spacing: 8) {
                detailInputCard("L", value: $viewModel.Lmm, unit: "mm", range: 20...140, digits: 1)
                detailInputCard("W", value: $viewModel.Wmm, unit: "mm", range: 20...120, digits: 1)
                detailInputCard("Thickness", value: $viewModel.tmm, unit: "mm", range: 0.5...5, digits: 2)
                detailInputCard("Hole D", value: $viewModel.Dmm, unit: "mm", range: 0...80, digits: 1)
                detailInputCard("Hole R", value: $viewModel.Rmm, unit: "mm", range: 0...40, digits: 1)
                detailInputCard("Gate width", value: $viewModel.gateWidth, unit: "mm", range: 0...30, digits: 1)
            }
            detailTextCard("Gate type", value: $viewModel.gateType)
            detailInputCard("Gate height", value: $viewModel.gateHeight, unit: "mm", range: 0...5, digits: 2)
        }
    }

    private var detailColumns: [GridItem] {
        [GridItem(.flexible(), spacing: 8), GridItem(.flexible(), spacing: 8)]
    }

    private func detailInputCard(
        _ title: String,
        value: Binding<String>,
        unit: String,
        range: ClosedRange<Double>,
        digits: Int
    ) -> some View {
        let readout = numericReadout(value.wrappedValue, unit: unit, digits: digits)
        let percent = boundedPercent(value.wrappedValue, in: range)
        return HStack(alignment: .center, spacing: 10) {
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.caption2.weight(.heavy))
                    .foregroundStyle(AppTheme.muted)
                    .lineLimit(1)
                    .minimumScaleFactor(0.72)
                Text(readout)
                    .font(.caption.monospacedDigit().weight(.heavy))
                    .foregroundStyle(AppTheme.primary)
                    .lineLimit(1)
                    .minimumScaleFactor(0.7)
                progressBar(percent: percent)
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            TextField(title, text: value)
                .font(.subheadline.monospacedDigit().weight(.heavy))
                .foregroundStyle(AppTheme.ink)
                .multilineTextAlignment(.center)
                .numericInputStyle()
                .frame(width: 78, height: 34)
                .padding(.horizontal, 8)
                .background(Color.white, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .stroke(AppTheme.primary.opacity(0.16), lineWidth: 1)
                )
        }
        .padding(8)
        .background(AppTheme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(AppTheme.primary.opacity(0.08), lineWidth: 1)
        )
    }

    private func detailTextCard(_ title: String, value: Binding<String>) -> some View {
        HStack(alignment: .center, spacing: 10) {
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.caption2.weight(.heavy))
                    .foregroundStyle(AppTheme.muted)
                Text(value.wrappedValue.isEmpty ? "-" : value.wrappedValue)
                    .font(.caption.weight(.heavy))
                    .foregroundStyle(AppTheme.primary)
                    .lineLimit(1)
                    .minimumScaleFactor(0.72)
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            TextField(title, text: value)
                .font(.subheadline.weight(.heavy))
                .foregroundStyle(AppTheme.ink)
                .autocorrectionDisabled()
                .frame(width: 148, height: 34)
                .padding(.horizontal, 8)
                .background(Color.white, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .stroke(AppTheme.primary.opacity(0.16), lineWidth: 1)
                )
        }
        .padding(8)
        .background(AppTheme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(AppTheme.primary.opacity(0.08), lineWidth: 1)
        )
    }

    private func progressBar(percent: Double) -> some View {
        GeometryReader { proxy in
            ZStack(alignment: .leading) {
                Capsule().fill(AppTheme.primary.opacity(0.08))
                Capsule()
                    .fill(
                        LinearGradient(
                            colors: [AppTheme.primary, AppTheme.accent],
                            startPoint: .leading,
                            endPoint: .trailing
                        )
                    )
                    .frame(width: proxy.size.width * percent)
            }
        }
        .frame(height: 5)
    }

    private func numericReadout(_ value: String, unit: String, digits: Int) -> String {
        guard let numeric = Double(value) else {
            return "- \(unit)"
        }
        return "\(numeric.metricText(digits: digits)) \(unit)"
    }

    private func boundedPercent(_ value: String, in range: ClosedRange<Double>) -> Double {
        guard let numeric = Double(value), range.upperBound > range.lowerBound else {
            return 0
        }
        return min(1, max(0, (numeric - range.lowerBound) / (range.upperBound - range.lowerBound)))
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

                if let xai = result.xai {
                    xaiCard(xai)
                }

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

    private func xaiCard(_ xai: InjectionXAIExplanation) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline) {
                VStack(alignment: .leading, spacing: 3) {
                    Text("Injection XAI")
                        .font(.caption.weight(.black))
                        .foregroundStyle(AppTheme.primary)
                    Text(injectionXaiTitle(xai, isKorean: isKorean))
                        .font(.subheadline.weight(.black))
                        .foregroundStyle(AppTheme.ink)
                }
                Spacer()
                Text(injectionXaiMethod(xai, isKorean: isKorean))
                    .font(.caption2.weight(.black))
                    .foregroundStyle(AppTheme.muted)
                    .lineLimit(1)
            }

            if !xai.summary.isEmpty {
                Text(injectionXaiSummary(xai, isKorean: isKorean))
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(AppTheme.muted)
                    .fixedSize(horizontal: false, vertical: true)
            }

            VStack(spacing: 8) {
                ForEach(Array(xai.topFeatures.prefix(5))) { feature in
                    xaiFeatureRow(feature)
                }
            }
        }
        .padding(12)
        .background(AppTheme.field.opacity(0.78), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(AppTheme.primary.opacity(0.12), lineWidth: 1)
        )
    }

    private func xaiFeatureRow(_ feature: InjectionXAIFeature) -> some View {
        let percent = min(1, max(0, feature.importance))
        return VStack(alignment: .leading, spacing: 5) {
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Text(injectionXaiFeatureLabel(feature, isKorean: isKorean))
                    .font(.caption.weight(.black))
                    .foregroundStyle(AppTheme.ink)
                    .lineLimit(1)
                    .minimumScaleFactor(0.76)
                Spacer()
                Text(feature.importance.formatted(.percent.precision(.fractionLength(1))))
                    .font(.caption.monospacedDigit().weight(.black))
                    .foregroundStyle(AppTheme.primary)
            }
            progressBar(percent: percent)
            if !feature.explanation.isEmpty {
                Text(injectionXaiFeatureExplanation(feature, isKorean: isKorean))
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(AppTheme.muted)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private var assistantCard: some View {
        InjectionAssistantCard(
            initialQuestion: assistantInitialQuestion,
            answer: viewModel.assistantAnswer,
            errorMessage: viewModel.assistantErrorMessage.map(friendlyErrorMessage),
            isAsking: viewModel.isAskingAssistant,
            isKorean: isKorean,
            ask: { question in
                await askAssistant(question: question)
            }
        )
    }

    private var assistantInitialQuestion: String {
        let defaultQuestion = "Why is melt temperature influential in this prediction?"
        let current = viewModel.assistantQuestion.trimmingCharacters(in: .whitespacesAndNewlines)
        if current.isEmpty || current == defaultQuestion {
            return localText(
                en: defaultQuestion,
                ko: "수지 온도가 예측 Sprue Pressure에 왜 영향을 주나요?"
            )
        }
        return current
    }

    private var historyCard: some View {
        AppCard {
            VStack(alignment: .leading, spacing: 12) {
                HStack(alignment: .firstTextBaseline) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(localText(en: "Prediction history", ko: "예측 기록"))
                            .font(.headline.weight(.black))
                            .foregroundStyle(AppTheme.ink)
                        Text(localText(en: "Tap a card to reuse its DOE setup.", ko: "카드를 누르면 이전 DOE 설정을 다시 불러옵니다."))
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(AppTheme.muted)
                    }
                    Spacer()
                    Text("\(viewModel.recentRuns.count)")
                        .font(.caption.monospacedDigit().weight(.black))
                        .foregroundStyle(AppTheme.primary)
                        .padding(.horizontal, 9)
                        .padding(.vertical, 5)
                        .background(AppTheme.primary.opacity(0.1), in: Capsule())
                }

                if viewModel.recentRuns.isEmpty {
                    Text(localText(
                        en: "Run an Injection forecast and recent prediction cards will appear here.",
                        ko: "Injection 예측을 실행하면 최근 예측 카드가 여기에 표시됩니다."
                    ))
                    .font(.callout.weight(.semibold))
                    .foregroundStyle(AppTheme.muted)
                    .fixedSize(horizontal: false, vertical: true)
                } else {
                    VStack(spacing: 8) {
                        ForEach(Array(viewModel.recentRuns.enumerated()), id: \.element.id) { index, run in
                            historyRunCard(run, index: index)
                        }
                    }

                    Button(role: .destructive) {
                        viewModel.clearRecentRuns()
                    } label: {
                        Label(localText(en: "Clear history", ko: "기록 삭제"), systemImage: "trash")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(SecondaryButtonStyle())
                }
            }
        }
    }

    private func historyRunCard(_ run: InjectionRecentRun, index: Int) -> some View {
        Button {
            viewModel.applyRecentRun(run)
        } label: {
            VStack(alignment: .leading, spacing: 8) {
                HStack(spacing: 8) {
                    Text(index == 0 ? localText(en: "Latest", ko: "최신") : "#\(index + 1)")
                        .font(.caption2.weight(.black))
                        .foregroundStyle(index == 0 ? AppTheme.success : AppTheme.primary)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background((index == 0 ? AppTheme.success : AppTheme.primary).opacity(0.12), in: Capsule())
                    Text(run.displayTitle)
                        .font(.subheadline.weight(.black))
                        .foregroundStyle(AppTheme.ink)
                    Spacer(minLength: 8)
                    Image(systemName: "arrow.uturn.backward")
                        .font(.caption.weight(.black))
                        .foregroundStyle(AppTheme.primary)
                }
                Text(run.displaySubtitle)
                    .font(.caption.monospacedDigit().weight(.semibold))
                    .foregroundStyle(AppTheme.muted)
                    .lineLimit(1)
                    .minimumScaleFactor(0.78)
                HStack(spacing: 6) {
                    historyChip(localText(en: "Sprue", ko: "스프루"), run.sprueModelKey)
                    historyChip(localText(en: "Filling", ko: "충전"), run.fillingModelKey)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(12)
            .background(AppTheme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(index == 0 ? AppTheme.success.opacity(0.35) : AppTheme.primary.opacity(0.10), lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
    }

    private func historyChip(_ title: String, _ value: String) -> some View {
        Text("\(title): \(value)")
            .font(.caption2.weight(.black))
            .foregroundStyle(AppTheme.primary)
            .lineLimit(1)
            .minimumScaleFactor(0.72)
            .padding(.horizontal, 7)
            .padding(.vertical, 4)
            .background(AppTheme.primary.opacity(0.08), in: Capsule())
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

    private var connectionBadge: some View {
        HStack(spacing: 6) {
            Image(systemName: statusConfig.icon)
                .font(.caption.weight(.black))
            Text(connectionBadgeText)
                .font(.caption.weight(.black))
                .lineLimit(1)
        }
        .foregroundStyle(statusConfig.color)
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(statusConfig.color.opacity(0.12), in: Capsule())
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

    private var connectionBadgeText: String {
        switch viewModel.connectionState {
        case .idle:
            localText(en: "API", ko: "API")
        case .checking:
            localText(en: "Checking", ko: "확인 중")
        case .ready(let available):
            available ? localText(en: "Connected", ko: "연결됨") : localText(en: "Model issue", ko: "모델 확인")
        case .failed:
            localText(en: "Offline", ko: "오프라인")
        }
    }

    private var connectionNeedsAttention: Bool {
        switch viewModel.connectionState {
        case .ready(let available):
            !available
        case .failed:
            true
        case .idle, .checking:
            false
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

    private func askAssistant(question: String) async {
        do {
            let url = try BaseURLValidator.parse(settings.apiBaseURL)
            await viewModel.askAssistant(baseURL: url, language: settings.languageCode, question: question)
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

func injectionXaiTitle(_ xai: InjectionXAIExplanation, isKorean: Bool) -> String {
    if isKorean {
        return "예측 영향 인자"
    }
    return xai.title.isEmpty ? "Feature influence" : xai.title
}

func injectionXaiMethod(_ xai: InjectionXAIExplanation, isKorean: Bool) -> String {
    if isKorean {
        return "형상 + 공정 + 게이트 + 파생 유동 descriptor"
    }
    return xai.featureSet.isEmpty ? xai.method : xai.featureSet
}

func injectionXaiSummary(_ xai: InjectionXAIExplanation, isKorean: Bool) -> String {
    if isKorean {
        return "현재 선택한 Injection 입력에서 형상, 공정, 게이트, 파생 유동 feature를 하나씩 변화시켜 Sprue Pressure 곡선과 Filling Pressure 분포가 얼마나 변하는지 계산한 설명입니다."
    }
    return xai.summary
}

func injectionXaiFeatureLabel(_ feature: InjectionXAIFeature, isKorean: Bool) -> String {
    if !isKorean {
        return feature.label.isEmpty ? feature.name : feature.label
    }
    if feature.name.hasPrefix("gate_type__") {
        return "게이트 타입: \(feature.name.replacingOccurrences(of: "gate_type__", with: ""))"
    }
    return injectionXaiFeatureCopy(feature.name)?.label ?? (feature.label.isEmpty ? feature.name : feature.label)
}

func injectionXaiFeatureExplanation(_ feature: InjectionXAIFeature, isKorean: Bool) -> String {
    if !isKorean {
        return feature.explanation
    }
    if feature.name.hasPrefix("gate_type__") {
        return "게이트 타입을 구분하기 위한 one-hot feature입니다. 입구 경계 조건 차이를 모델이 구분하는 데 사용됩니다."
    }
    return injectionXaiFeatureCopy(feature.name)?.explanation ?? feature.explanation
}

func localizedInjectionNote(_ note: String, isKorean: Bool) -> String {
    guard isKorean else { return note }
    switch note {
    case "Current model is trained on 360 Moldex3D cases covering G01-G42.":
        return "현재 모델은 G01-G42 범위의 360개 Moldex3D DOE 케이스로 학습되었습니다."
    case "Use the classical surrogate as the practical default for this Simple Injection DOE set.":
        return "이 Simple Injection DOE 세트에서는 Machine Learning surrogate를 기본 모델로 사용하는 것이 가장 실용적입니다."
    case "The GointMLP-style model is a deep-learning baseline and is less stable than the classical surrogate on this DOE set.":
        return "GointMLP-style 모델은 딥러닝 baseline이며, 이 DOE 세트에서는 Machine Learning surrogate보다 안정성이 낮을 수 있습니다."
    case "The DeepONet model is an operator-learning research model for smoother curve behavior on user-edited DOE conditions.":
        return "DeepONet 모델은 사용자가 수정한 DOE 조건에서 더 부드러운 곡선 거동을 보기 위한 operator-learning 연구 모델입니다."
    default:
        return note
    }
}

private func injectionXaiFeatureCopy(_ name: String) -> (label: String, explanation: String)? {
    let copy: [String: (String, String)] = [
        "L_mm": ("길이", "전체 제품 길이입니다. 유동 거리가 길어지면 필요한 압력이 커지고 압력 곡선의 시간 위치가 달라질 수 있습니다."),
        "W_mm": ("폭", "전체 제품 폭입니다. 투영 면적과 유동 가능한 영역을 바꿉니다."),
        "t_mm": ("두께", "제품 두께입니다. 두꺼운 캐비티는 대체로 유동 저항을 낮추고, 얇은 구간은 압력 민감도를 키울 수 있습니다."),
        "D_mm": ("홀 직경", "중앙 홀의 직경입니다. 순 유동 면적을 줄이고 홀 주변의 충전 경로를 바꿉니다."),
        "R_mm": ("홀 반경", "중앙 홀의 반경입니다. 홀 직경과 함께 사용되며 유효 단면에 영향을 줍니다."),
        "gate_size_width_mm": ("게이트 폭", "게이트 개구부의 폭입니다. 게이트 면적이 커지면 입구 부근의 국부 압력 손실이 줄어들 수 있습니다."),
        "gate_size_height_mm": ("게이트 높이", "게이트 개구부의 높이입니다. 게이트 면적과 제한 정도를 직접 바꿉니다."),
        "melt_temp_C": ("수지 온도", "수지 온도입니다. 온도가 높아지면 일반적으로 점도가 낮아져 필요한 압력이 줄어들 수 있습니다."),
        "mold_temp_C": ("금형 온도", "금형 온도입니다. 냉각 속도, 점도 증가, 벽면 근처 유동 저항에 영향을 줍니다."),
        "injection_time_s": ("사출 시간", "충전 시간 조건입니다. 빠른 사출은 peak pressure를 높일 수 있고, 느린 사출은 압력 곡선 형태를 바꿉니다."),
        "packing_pressure_MPa": ("보압", "보압 설정값입니다. 충전 후반부 압력 수준과 peak pressure 응답에 영향을 줄 수 있습니다."),
        "packing_time_s": ("보압 시간", "보압 유지 시간입니다. 주로 충전 이후 후반 압력 거동에 영향을 줍니다."),
        "area_mm2": ("제품 면적", "길이와 폭으로 계산한 제품 면적입니다."),
        "hole_area_mm2": ("홀 면적", "중앙 홀 때문에 제거되는 면적입니다."),
        "net_area_mm2": ("순 면적", "전체 면적에서 홀 면적을 뺀 유효 면적입니다."),
        "volume_mm3": ("제품 부피", "순 면적과 두께로 계산한 캐비티 부피입니다."),
        "aspect_ratio": ("형상비", "길이와 폭의 비율입니다. 유동 영역이 얼마나 길쭉한지 나타냅니다."),
        "hole_diameter_ratio": ("홀 직경 비율", "홀 직경을 제품의 짧은 변 기준으로 정규화한 값입니다."),
        "gate_area_mm2": ("게이트 면적", "게이트 폭과 높이로 계산한 게이트 단면적입니다."),
        "gate_to_thickness_ratio": ("게이트/두께 비율", "제품 두께 대비 게이트 높이의 비율입니다."),
        "flow_length_to_thickness": ("유동 길이/두께 비율", "유동 경로가 두께에 비해 얼마나 긴지 나타내는 지표입니다. 값이 커지면 충전 압력 민감도가 커지는 경우가 많습니다."),
        "process_total_time_s": ("총 공정 시간", "사출 시간과 보압 시간을 더한 값입니다."),
    ]
    return copy[name]
}

private struct InjectionShapePreviewCard: View {
    let geometryID: String
    let gateType: String
    let length: Double
    let width: Double
    let thickness: Double
    let holeDiameter: Double
    let gateWidth: Double
    let gateHeight: Double

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline) {
                VStack(alignment: .leading, spacing: 3) {
                    Text("DOE-driven geometry")
                        .font(.headline.weight(.black))
                        .foregroundStyle(AppTheme.ink)
                    Text("\(geometryID) · \(gateType)")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(AppTheme.muted)
                }
                Spacer()
                Text("\(length.metricText(digits: 1)) × \(width.metricText(digits: 1)) mm")
                    .font(.caption.monospacedDigit().weight(.black))
                    .foregroundStyle(AppTheme.primary)
                    .padding(.horizontal, 9)
                    .padding(.vertical, 5)
                    .background(AppTheme.primary.opacity(0.10), in: Capsule())
            }

            InjectionShapePreviewView(
                length: length,
                width: width,
                thickness: thickness,
                holeDiameter: holeDiameter,
                gateWidth: gateWidth,
                gateHeight: gateHeight
            )
            .frame(height: 210)

            HStack(spacing: 8) {
                previewChip("L", length.metricText(digits: 1), "mm")
                previewChip("W", width.metricText(digits: 1), "mm")
                previewChip("T", thickness.metricText(digits: 2), "mm")
                previewChip("D", holeDiameter.metricText(digits: 1), "mm")
            }
        }
    }

    private func previewChip(_ title: String, _ value: String, _ unit: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title)
                .font(.caption2.weight(.black))
                .foregroundStyle(AppTheme.muted)
            Text("\(value) \(unit)")
                .font(.caption2.monospacedDigit().weight(.black))
                .foregroundStyle(AppTheme.ink)
                .lineLimit(1)
                .minimumScaleFactor(0.68)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(8)
        .background(Color.white.opacity(0.86), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(AppTheme.primary.opacity(0.10), lineWidth: 1)
        )
    }
}

private struct InjectionDetailSection<Content: View>: View {
    let title: String
    let content: Content

    init(title: String, @ViewBuilder content: () -> Content) {
        self.title = title
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.caption.weight(.heavy))
                .foregroundStyle(AppTheme.muted)
            content
        }
        .padding(8)
        .background(Color.white.opacity(0.72), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(AppTheme.primary.opacity(0.10), lineWidth: 1)
        )
    }
}

private struct InjectionShapePreviewView: View {
    let length: Double
    let width: Double
    let thickness: Double
    let holeDiameter: Double
    let gateWidth: Double
    let gateHeight: Double

    var body: some View {
        GeometryReader { proxy in
            previewContent(size: proxy.size)
        }
        .background(
            LinearGradient(
                colors: [
                    Color(red: 0.95, green: 0.98, blue: 1.0),
                    AppTheme.primary.opacity(0.18)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            ),
            in: RoundedRectangle(cornerRadius: 8, style: .continuous)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(AppTheme.primary.opacity(0.18), lineWidth: 1)
        )
    }

    private func previewContent(size: CGSize) -> some View {
        guard size.width.isFinite, size.height.isFinite, size.width > 1, size.height > 1 else {
            return AnyView(Color.clear)
        }
        let layout = makeLayout(size: size)
        return AnyView(
            ZStack {
                InjectionPreviewGrid()
                    .stroke(AppTheme.primary.opacity(0.08), lineWidth: 1)

                RoundedRectangle(cornerRadius: 5, style: .continuous)
                    .fill(
                        LinearGradient(
                            colors: [
                                Color(red: 0.91, green: 0.95, blue: 0.97),
                                Color(red: 0.72, green: 0.80, blue: 0.86)
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 5, style: .continuous)
                            .stroke(AppTheme.ink.opacity(0.34), lineWidth: 1.4)
                    )
                    .frame(width: layout.plate.width, height: layout.plate.height)
                    .position(x: layout.plate.midX, y: layout.plate.midY)

                Circle()
                    .fill(AppTheme.primary.opacity(0.72))
                    .overlay(Circle().stroke(Color.white.opacity(0.84), lineWidth: 1.6))
                    .frame(width: layout.holeRadius * 2, height: layout.holeRadius * 2)
                    .position(layout.holeCenter)

                RoundedRectangle(cornerRadius: 3, style: .continuous)
                    .fill(AppTheme.accent.opacity(0.92))
                    .overlay(
                        RoundedRectangle(cornerRadius: 3, style: .continuous)
                            .stroke(Color.white.opacity(0.68), lineWidth: 1)
                    )
                    .frame(width: layout.gate.width, height: layout.gate.height)
                    .position(x: layout.gate.midX, y: layout.gate.midY)

                InjectionFlowGuide(layout: layout)
                    .stroke(AppTheme.accent.opacity(0.85), style: StrokeStyle(lineWidth: 1.8, dash: [5, 4]))

                dimensionLabel("L \(layout.length.metricText(digits: 1)) mm")
                    .position(x: layout.plate.midX, y: layout.plate.maxY + 20)
                dimensionLabel("W \(layout.width.metricText(digits: 1)) mm")
                    .rotationEffect(.degrees(-90))
                    .position(x: layout.plate.minX - 30, y: layout.plate.midY)
                dimensionLabel("D \(layout.holeDiameter.metricText(digits: 1)) mm")
                    .position(x: layout.holeCenter.x, y: layout.holeCenter.y + layout.holeRadius + 16)
                dimensionLabel("Gate \(layout.gateWidth.metricText(digits: 1)) mm")
                    .position(x: layout.gate.midX, y: layout.gate.minY - 13)
            }
            .frame(width: size.width, height: size.height)
        )
    }

    private func dimensionLabel(_ text: String) -> some View {
        Text(text)
            .font(.system(size: 10, weight: .black, design: .rounded).monospacedDigit())
            .foregroundStyle(AppTheme.ink.opacity(0.72))
    }

    private func makeLayout(size: CGSize) -> InjectionPreviewLayout {
        let length = safeDimension(length, fallback: 154.01)
        let width = safeDimension(width, fallback: 97.42)
        let holeDiameter = safeDimension(holeDiameter, fallback: 17.61)
        let gateWidth = safeDimension(gateWidth, fallback: 10.0)
        let gateHeight = safeDimension(gateHeight, fallback: 1.5)
        let margin = min(size.width, size.height) * 0.15
        let usableWidth = max(size.width - margin * 2, 1)
        let usableHeight = max(size.height - margin * 2, 1)
        let scale = min(usableWidth / max(length, 1), usableHeight / max(width, 1))
        let plateWidth = CGFloat(length * scale)
        let plateHeight = CGFloat(width * scale)
        let plate = CGRect(
            x: (size.width - plateWidth) / 2,
            y: (size.height - plateHeight) / 2,
            width: plateWidth,
            height: plateHeight
        )
        let holeRadius = CGFloat(max(holeDiameter * scale / 2, 3))
        let holeCenter = CGPoint(x: plate.midX, y: plate.midY)
        let gateH = CGFloat(max(gateWidth * scale, 12))
        let gateW = CGFloat(max(gateHeight * scale * 4.0, 16))
        let gate = CGRect(x: plate.minX - gateW * 0.82, y: plate.midY - gateH / 2, width: gateW, height: gateH)
        return InjectionPreviewLayout(
            length: length,
            width: width,
            holeDiameter: holeDiameter,
            gateWidth: gateWidth,
            plate: plate,
            holeCenter: holeCenter,
            holeRadius: holeRadius,
            gate: gate
        )
    }

    private func safeDimension(_ value: Double, fallback: Double) -> Double {
        guard value.isFinite, value > 0 else { return fallback }
        return min(max(value, 0.001), 10_000)
    }
}

private struct InjectionPreviewLayout {
    let length: Double
    let width: Double
    let holeDiameter: Double
    let gateWidth: Double
    let plate: CGRect
    let holeCenter: CGPoint
    let holeRadius: CGFloat
    let gate: CGRect
}

private struct InjectionPreviewGrid: Shape {
    func path(in rect: CGRect) -> Path {
        var path = Path()
        let step: CGFloat = 24
        var x = rect.minX
        while x <= rect.maxX {
            path.move(to: CGPoint(x: x, y: rect.minY))
            path.addLine(to: CGPoint(x: x, y: rect.maxY))
            x += step
        }
        var y = rect.minY
        while y <= rect.maxY {
            path.move(to: CGPoint(x: rect.minX, y: y))
            path.addLine(to: CGPoint(x: rect.maxX, y: y))
            y += step
        }
        return path
    }
}

private struct InjectionFlowGuide: Shape {
    let layout: InjectionPreviewLayout

    func path(in rect: CGRect) -> Path {
        var path = Path()
        path.move(to: CGPoint(x: layout.gate.maxX, y: layout.gate.midY))
        path.addCurve(
            to: CGPoint(x: layout.holeCenter.x - layout.holeRadius * 1.2, y: layout.holeCenter.y),
            control1: CGPoint(x: layout.plate.minX + layout.plate.width * 0.12, y: layout.plate.midY + layout.plate.height * 0.18),
            control2: CGPoint(x: layout.plate.minX + layout.plate.width * 0.25, y: layout.plate.midY - layout.plate.height * 0.12)
        )
        return path
    }
}

private struct InjectionAssistantCard: View {
    let initialQuestion: String
    let answer: RagAnswerResponse?
    let errorMessage: String?
    let isAsking: Bool
    let isKorean: Bool
    let ask: (String) async -> Void

    @State private var question: String
    @FocusState private var isQuestionFocused: Bool

    init(
        initialQuestion: String,
        answer: RagAnswerResponse?,
        errorMessage: String?,
        isAsking: Bool,
        isKorean: Bool,
        ask: @escaping (String) async -> Void
    ) {
        self.initialQuestion = initialQuestion
        self.answer = answer
        self.errorMessage = errorMessage
        self.isAsking = isAsking
        self.isKorean = isKorean
        self.ask = ask
        _question = State(initialValue: initialQuestion)
    }

    var body: some View {
        AppCard {
            VStack(alignment: .leading, spacing: 12) {
                HStack(alignment: .firstTextBaseline) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Injection AI Assistant")
                            .font(.caption.weight(.black))
                            .foregroundStyle(AppTheme.primary)
                        Text(localText(en: "Ask about this prediction", ko: "현재 예측에 대해 질문하기"))
                            .font(.headline.weight(.black))
                            .foregroundStyle(AppTheme.ink)
                    }
                    Spacer()
                    if isAsking {
                        ProgressView()
                    }
                }

                TextEditor(text: $question)
                    .font(.callout)
                    .foregroundStyle(AppTheme.ink)
                    .frame(minHeight: 82)
                    .focused($isQuestionFocused)
                    .padding(8)
                    .scrollContentBackground(.hidden)
                    .background(AppTheme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: 8, style: .continuous)
                            .stroke(AppTheme.primary.opacity(0.12), lineWidth: 1)
                    )

                Button {
                    isQuestionFocused = false
                    dismissInjectionKeyboard()
                    Task { await ask(question) }
                } label: {
                    Label(
                        isAsking
                            ? localText(en: "Asking", ko: "질문 중")
                            : localText(en: "Ask Injection AI", ko: "Injection AI에 질문"),
                        systemImage: "sparkles"
                    )
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(SecondaryButtonStyle())
                .disabled(isAsking)

                if let answer {
                    InjectionAssistantAnswerBlock(answer: answer, isKorean: isKorean)
                        .onTapGesture {
                            isQuestionFocused = false
                            dismissInjectionKeyboard()
                        }
                }

                if let errorMessage {
                    Text(errorMessage)
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(AppTheme.danger)
                        .onTapGesture {
                            isQuestionFocused = false
                            dismissInjectionKeyboard()
                        }
                }
            }
            .background(
                Color.clear
                    .contentShape(Rectangle())
                    .onTapGesture {
                        isQuestionFocused = false
                        dismissInjectionKeyboard()
                    }
            )
        }
        .onChange(of: initialQuestion) {
            let englishDefault = "Why is melt temperature influential in this prediction?"
            let koreanDefault = "수지 온도가 예측 Sprue Pressure에 왜 영향을 주나요?"
            let current = question.trimmingCharacters(in: .whitespacesAndNewlines)
            if current.isEmpty || current == englishDefault || current == koreanDefault {
                question = initialQuestion
            }
        }
    }

    private func localText(en: String, ko: String) -> String {
        isKorean ? ko : en
    }
}

extension Double {
    func metricText(digits: Int) -> String {
        formatted(.number.precision(.fractionLength(0...digits)))
    }
}

struct InjectionAssistantAnswerBlock: View {
    let answer: RagAnswerResponse
    let isKorean: Bool

    private var paragraphs: [String] {
        let normalized = answer.answer.replacingOccurrences(of: "\r\n", with: "\n")
        let chunks = normalized
            .components(separatedBy: "\n\n")
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
        return chunks.isEmpty ? [answer.answer] : chunks
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .firstTextBaseline) {
                Label("Injection AI", systemImage: "sparkles")
                    .font(.subheadline.weight(.black))
                    .foregroundStyle(AppTheme.ink)
                Spacer()
                Text(answer.usedLLM ? "LLM" : answer.model)
                    .font(.caption2.weight(.black))
                    .foregroundStyle(AppTheme.primary)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(AppTheme.primary.opacity(0.1), in: Capsule())
            }

            VStack(alignment: .leading, spacing: 8) {
                ForEach(Array(paragraphs.enumerated()), id: \.offset) { index, paragraph in
                    InjectionAssistantParagraphCard(
                        title: index == 0 ? localText(en: "Summary", ko: "요약") : "\(localText(en: "Reasoning", ko: "해석")) \(index)",
                        text: paragraph,
                        isLead: index == 0
                    )
                }
            }

            if answer.retrievalCount > 0 {
                HStack(spacing: 6) {
                    Image(systemName: "books.vertical.fill")
                    Text(localText(
                        en: "Grounded by \(answer.retrievalCount) retrieved source\(answer.retrievalCount == 1 ? "" : "s")",
                        ko: "\(answer.retrievalCount)개 근거 자료를 참고했습니다."
                    ))
                }
                .font(.caption2.weight(.bold))
                .foregroundStyle(AppTheme.muted)
            }
        }
        .padding(12)
        .background(
            LinearGradient(
                colors: [Color.white.opacity(0.92), AppTheme.field.opacity(0.78)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            ),
            in: RoundedRectangle(cornerRadius: 8, style: .continuous)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(AppTheme.primary.opacity(0.16), lineWidth: 1)
        )
    }

    private func localText(en: String, ko: String) -> String {
        isKorean ? ko : en
    }
}

private struct InjectionAssistantParagraphCard: View {
    let title: String
    let text: String
    let isLead: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            Text(title)
                .font(.caption2.weight(.black))
                .foregroundStyle(isLead ? AppTheme.success : AppTheme.primary)
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background((isLead ? AppTheme.success : AppTheme.primary).opacity(0.10), in: Capsule())

            Text(text)
                .font(.callout.weight(isLead ? .semibold : .regular))
                .lineSpacing(4)
                .foregroundStyle(AppTheme.ink)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(10)
        .background(isLead ? AppTheme.success.opacity(0.06) : Color.white.opacity(0.78), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke((isLead ? AppTheme.success : AppTheme.primary).opacity(isLead ? 0.16 : 0.10), lineWidth: 1)
        )
    }
}

enum AppTheme {
    static let background = LinearGradient(
        colors: [
            Color(red: 0.953, green: 0.965, blue: 0.976),
            Color(red: 0.986, green: 0.973, blue: 0.955)
        ],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )
    static let card = Color.white
    static let field = Color(red: 0.941, green: 0.953, blue: 0.969)
    static let line = Color(red: 0.812, green: 0.865, blue: 0.922)
    static let ink = Color(red: 0.055, green: 0.075, blue: 0.118)
    static let muted = Color(red: 0.365, green: 0.420, blue: 0.510)
    static let primary = Color(red: 0.000, green: 0.451, blue: 0.737)
    static let accent = Color(red: 0.922, green: 0.390, blue: 0.111)
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
                    .stroke(AppTheme.line, lineWidth: 1)
            )
            .shadow(color: .black.opacity(0.06), radius: 18, x: 0, y: 10)
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
