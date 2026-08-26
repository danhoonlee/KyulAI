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

struct ResultDetailView: View {
    let result: SpruePressurePredictionResult
    let recentRuns: [InjectionRecentRun]
    @EnvironmentObject private var settings: AppSettings
    @State private var selectedTab: ResultTab = .summary
    @State private var showsFillingPreview = false
    @State private var showsAllXaiFeatures = false
    @State private var assistantQuestion = "Why is the top XAI feature important in this prediction?"
    @State private var assistantAnswer: RagAnswerResponse?
    @State private var assistantErrorMessage: String?
    @State private var isAskingAssistant = false
    @FocusState private var isAssistantQuestionFocused: Bool

    private enum ResultTab: String, CaseIterable, Identifiable {
        case summary
        case sprueCurve
        case filling
        case xai
        case validation
        case history

        var id: String { rawValue }
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                resultTabs
                selectedTabContent
            }
            .padding(20)
        }
        .injectionScrollKeyboardDismissal()
        .background(AppTheme.background.ignoresSafeArea())
        .navigationTitle(L10n.t("result"))
        .appInlineNavigationTitle()
        .onAppear {
            syncAssistantQuestionForLanguage()
        }
        .onChange(of: settings.languageCode) {
            syncAssistantQuestionForLanguage()
        }
        .toolbar {
            ShareLink(item: result.shareSummaryText) {
                Image(systemName: "square.and.arrow.up")
            }
            #if os(iOS)
            ShareImageButton(
                fileName: "imperialax-injection-forecast",
                report: InjectionShareImageReportView(result: result)
            ) {
                Image(systemName: "photo")
            }
            #endif
        }
    }

    private var resultTabs: some View {
        LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 8), count: 3), spacing: 8) {
            ForEach(ResultTab.allCases) { tab in
                Button {
                    withAnimation(.easeInOut(duration: 0.16)) { selectedTab = tab }
                } label: {
                    Text(tabTitle(tab))
                        .font(.caption.weight(.bold))
                        .foregroundStyle(selectedTab == tab ? .white : AppTheme.muted)
                        .lineLimit(1)
                        .minimumScaleFactor(0.72)
                        .frame(maxWidth: .infinity, minHeight: 44)
                        .background(selectedTab == tab ? AppTheme.primary : AppTheme.card, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                        .overlay(RoundedRectangle(cornerRadius: 8, style: .continuous).stroke(AppTheme.primary.opacity(selectedTab == tab ? 0 : 0.12), lineWidth: 1))
                }
                .buttonStyle(.plain)
                .accessibilityAddTraits(selectedTab == tab ? .isSelected : [])
            }
        }
    }

    @ViewBuilder
    private var selectedTabContent: some View {
        switch selectedTab {
        case .summary:
            heroCard
            metricsGrid
            if !result.notes.isEmpty { notesCard }
        case .sprueCurve:
            curveCard
        case .filling:
            fillingCard
        case .xai:
            if let xai = result.xai {
                xaiCard(xai)
            } else {
                unavailableCard(en: "XAI is not available for this prediction.", ko: "이번 예측에서는 XAI를 제공하지 않습니다.")
            }
            assistantCard
        case .validation:
            validationCard
        case .history:
            historyCard
        }
    }

    private func tabTitle(_ tab: ResultTab) -> String {
        switch tab {
        case .summary: localText(en: "Summary", ko: "요약")
        case .sprueCurve: localText(en: "Sprue", ko: "스프루")
        case .filling: localText(en: "Filling", ko: "필링 분포")
        case .xai: "XAI"
        case .validation: localText(en: "Validation", ko: "검증")
        case .history: localText(en: "History", ko: "기록")
        }
    }

    private func unavailableCard(en: String, ko: String) -> some View {
        AppCard {
            Label(localText(en: en, ko: ko), systemImage: "info.circle")
                .font(.callout.weight(.semibold))
                .foregroundStyle(AppTheme.muted)
                .frame(maxWidth: .infinity, minHeight: 120, alignment: .center)
        }
    }

    private var heroCard: some View {
        AppCard {
            VStack(alignment: .leading, spacing: 14) {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 6) {
                        Text(L10n.t("peak.sprue.pressure"))
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(AppTheme.muted)
                        Text(result.predictedMaxPressureMPa.metricText(digits: 2))
                            .font(.system(size: 48, weight: .black, design: .rounded))
                            .foregroundStyle(AppTheme.ink)
                    }
                    Spacer()
                    Text("MPa")
                        .font(.title2.monospacedDigit().weight(.bold))
                        .foregroundStyle(AppTheme.accent)
                }
                Divider()
                VStack(alignment: .leading, spacing: 6) {
                    resultModelRow(L10n.t("sprue.model"), result.displayModelLabel)
                    resultModelRow(L10n.t("filling.model"), result.displayFillingModelLabel)
                }
            }
        }
    }

    private func resultModelRow(_ title: String, _ value: String) -> some View {
        HStack(spacing: 8) {
            Text(title)
                .font(.caption.weight(.semibold))
                .foregroundStyle(AppTheme.muted)
            Text(value)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(AppTheme.ink)
                .lineLimit(1)
                .minimumScaleFactor(0.78)
        }
    }

    private var metricsGrid: some View {
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
            metricCard(L10n.t("peak.time"), result.predictedMaxTimeS.metricText(digits: 3), "s")
            metricCard(L10n.t("curve.points"), "\(result.curve.count)", "samples")
            metricCard(L10n.t("geometry"), result.inputs["geometry_id"]?.stringValue ?? "-", "DOE")
            metricCard(L10n.t("process"), result.inputs["process_id"]?.stringValue ?? "-", "DOE")
        }
    }

    private func metricCard(_ title: String, _ value: String, _ unit: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.caption.weight(.semibold))
                .foregroundStyle(AppTheme.muted)
            Text(value)
                .font(.title3.monospacedDigit().weight(.bold))
                .foregroundStyle(AppTheme.ink)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
            Text(unit)
                .font(.caption2.weight(.semibold))
                .foregroundStyle(AppTheme.muted)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(AppTheme.card, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(AppTheme.primary.opacity(0.10), lineWidth: 1)
        )
    }

    private var curveCard: some View {
        AppCard {
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    Label(L10n.t("sprue.pressure.curve"), systemImage: "chart.xyaxis.line")
                        .font(.headline)
                        .foregroundStyle(AppTheme.ink)
                    Spacer()
                    Text(L10n.t("peak.marker"))
                        .font(.caption2.bold())
                        .foregroundStyle(AppTheme.danger)
                }
                Text(localText(
                    en: "The curve shows how sprue pressure changes over injection time. The marker identifies the predicted peak pressure.",
                    ko: "사출 시간에 따른 스프루 압력 변화를 보여주며, 마커는 예측 최대 압력 위치를 나타냅니다."
                ))
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(AppTheme.muted)
                PressureChartView(points: result.curve, maxPressure: result.predictedMaxPressureMPa)
                    .frame(height: 230)
            }
        }
    }

    private var fillingCard: some View {
        AppCard {
            VStack(alignment: .leading, spacing: 12) {
                Label(L10n.t("filling.pressure"), systemImage: "square.grid.3x3.fill")
                    .font(.headline)
                    .foregroundStyle(AppTheme.ink)
                Text(localText(
                    en: "The bars compare the predicted volume ratio across filling-pressure groups; longer bars indicate a larger share of the molded volume.",
                    ko: "필링 압력 그룹별 예측 체적 비율을 비교하며, 막대가 길수록 해당 압력 구간이 차지하는 체적이 큽니다."
                ))
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(AppTheme.muted)
                if let filling = result.bestFillingPressure {
                    HStack(spacing: 10) {
                        fillingMetric("Min", filling.stats["min_MPa"])
                        fillingMetric("Avg", filling.stats["avg_MPa"])
                        fillingMetric("Max", filling.stats["max_MPa"])
                    }
                    if !filling.bins.isEmpty {
                        FillingHistogramView(bins: filling.bins)
                            .frame(height: 220)
                        fillingPreviewToggle(filling)
                    }
                    Text(filling.note)
                        .font(.caption)
                        .foregroundStyle(AppTheme.muted)
                        .fixedSize(horizontal: false, vertical: true)
                } else {
                    Text(L10n.t("no.filling.summary"))
                        .font(.callout)
                        .foregroundStyle(AppTheme.muted)
                }
            }
        }
    }

    private var assistantCard: some View {
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
                    if isAskingAssistant {
                        ProgressView()
                    }
                }

                TextEditor(text: $assistantQuestion)
                    .font(.callout)
                    .foregroundStyle(AppTheme.ink)
                    .frame(minHeight: 82)
                    .focused($isAssistantQuestionFocused)
                    .padding(8)
                    .scrollContentBackground(.hidden)
                    .background(AppTheme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: 8, style: .continuous)
                            .stroke(AppTheme.primary.opacity(0.12), lineWidth: 1)
                    )

                Button {
                    isAssistantQuestionFocused = false
                    dismissInjectionKeyboard()
                    Task { await askAssistant() }
                } label: {
                    Label(
                        isAskingAssistant
                            ? localText(en: "Asking", ko: "질문 중")
                            : localText(en: "Ask Injection AI", ko: "Injection AI에 질문"),
                        systemImage: "sparkles"
                    )
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(SecondaryButtonStyle())
                .disabled(isAskingAssistant)

                if let assistantAnswer {
                    InjectionAssistantAnswerBlock(answer: assistantAnswer, isKorean: settings.languageCode == "ko")
                        .onTapGesture {
                            isAssistantQuestionFocused = false
                            dismissInjectionKeyboard()
                        }
                }

                if let assistantErrorMessage {
                    Text(assistantErrorMessage)
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(AppTheme.danger)
                        .onTapGesture {
                            isAssistantQuestionFocused = false
                            dismissInjectionKeyboard()
                        }
                }
            }
            .background(
                Color.clear
                    .contentShape(Rectangle())
                    .onTapGesture {
                        isAssistantQuestionFocused = false
                        dismissInjectionKeyboard()
                    }
            )
        }
    }

    private func xaiCard(_ xai: InjectionXAIExplanation) -> some View {
        AppCard {
            VStack(alignment: .leading, spacing: 12) {
                HStack(alignment: .firstTextBaseline) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Injection XAI")
                            .font(.caption.weight(.black))
                            .foregroundStyle(AppTheme.primary)
                        Text(injectionXaiTitle(xai, isKorean: settings.languageCode == "ko"))
                            .font(.headline.weight(.black))
                            .foregroundStyle(AppTheme.ink)
                    }
                    Spacer()
                    Text(injectionXaiMethod(xai, isKorean: settings.languageCode == "ko"))
                        .font(.caption2.weight(.black))
                        .foregroundStyle(AppTheme.muted)
                        .lineLimit(1)
                }

                if !xai.summary.isEmpty {
                    Text(injectionXaiSummary(xai, isKorean: settings.languageCode == "ko"))
                        .font(.callout.weight(.semibold))
                        .foregroundStyle(AppTheme.muted)
                        .fixedSize(horizontal: false, vertical: true)
                }

                VStack(spacing: 10) {
                    ForEach(Array(xai.topFeatures.prefix(5))) { feature in
                        xaiFeatureRow(feature)
                    }
                }
                if xai.topFeatures.count > 5 {
                    DisclosureGroup(
                        isExpanded: $showsAllXaiFeatures,
                        content: {
                            VStack(spacing: 10) {
                                ForEach(Array(xai.topFeatures.dropFirst(5))) { feature in
                                    xaiFeatureRow(feature)
                                }
                            }
                            .padding(.top, 10)
                        },
                        label: {
                            Text(showsAllXaiFeatures
                                 ? localText(en: "Hide additional features", ko: "추가 Feature 숨기기")
                                 : localText(en: "Show \(xai.topFeatures.count - 5) more features", ko: "나머지 \(xai.topFeatures.count - 5)개 Feature 보기"))
                                .font(.subheadline.weight(.bold))
                                .foregroundStyle(AppTheme.primary)
                                .frame(minHeight: 44, alignment: .leading)
                        }
                    )
                    .tint(AppTheme.primary)
                }
            }
        }
    }

    private func xaiFeatureRow(_ feature: InjectionXAIFeature) -> some View {
        let percent = min(1, max(0, feature.importance))
        return VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(injectionXaiFeatureLabel(feature, isKorean: settings.languageCode == "ko"))
                        .font(.subheadline.weight(.black))
                        .foregroundStyle(AppTheme.ink)
                        .lineLimit(1)
                        .minimumScaleFactor(0.76)
                    Text(feature.category)
                        .font(.caption2.weight(.bold))
                        .foregroundStyle(AppTheme.muted)
                }
                Spacer()
                Text(feature.importance.formatted(.percent.precision(.fractionLength(1))))
                    .font(.subheadline.monospacedDigit().weight(.black))
                    .foregroundStyle(AppTheme.primary)
            }

            GeometryReader { proxy in
                ZStack(alignment: .leading) {
                    Capsule().fill(AppTheme.primary.opacity(0.08))
                    Capsule()
                        .fill(AppTheme.primary)
                        .frame(width: proxy.size.width * percent)
                }
            }
            .frame(height: 7)

            if !feature.explanation.isEmpty {
                Text(injectionXaiFeatureExplanation(feature, isKorean: settings.languageCode == "ko"))
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(AppTheme.muted)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(12)
        .background(AppTheme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(AppTheme.primary.opacity(0.10), lineWidth: 1)
        )
    }

    private var validationCard: some View {
        AppCard {
            VStack(alignment: .leading, spacing: 12) {
                Label(localText(en: "Prediction validation", ko: "예측 검증"), systemImage: "checkmark.seal")
                    .font(.headline.weight(.black))
                    .foregroundStyle(AppTheme.ink)
                Text(localText(
                    en: "This run records the selected DOE and model metadata. Measured-reference error metrics are not returned by the current prediction API, so no validation score is fabricated here.",
                    ko: "이번 실행의 DOE와 모델 정보는 확인할 수 있습니다. 현재 예측 API는 실측값 대비 오차를 반환하지 않으므로 임의의 검증 점수는 표시하지 않습니다."
                ))
                    .font(.callout.weight(.semibold))
                    .foregroundStyle(AppTheme.muted)
                    .fixedSize(horizontal: false, vertical: true)
                Divider()
                resultModelRow(L10n.t("geometry"), result.inputs["geometry_id"]?.stringValue ?? "-")
                resultModelRow(L10n.t("process"), result.inputs["process_id"]?.stringValue ?? "-")
                resultModelRow(L10n.t("sprue.model"), result.displayModelLabel)
                resultModelRow(L10n.t("filling.model"), result.displayFillingModelLabel)
            }
        }
    }

    private var historyCard: some View {
        AppCard {
            VStack(alignment: .leading, spacing: 12) {
                Label(localText(en: "Recent input runs", ko: "최근 입력 기록"), systemImage: "clock.arrow.circlepath")
                    .font(.headline.weight(.black))
                    .foregroundStyle(AppTheme.ink)
                if recentRuns.isEmpty {
                    Text(localText(en: "No saved runs yet.", ko: "저장된 실행 기록이 아직 없습니다."))
                        .font(.callout.weight(.semibold))
                        .foregroundStyle(AppTheme.muted)
                } else {
                    ForEach(recentRuns) { run in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(run.displayTitle)
                                .font(.subheadline.weight(.black))
                                .foregroundStyle(AppTheme.ink)
                            Text(run.displaySubtitle)
                                .font(.caption.monospacedDigit().weight(.semibold))
                                .foregroundStyle(AppTheme.muted)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(12)
                        .background(AppTheme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                    }
                }
            }
        }
    }

    @ViewBuilder
    private func fillingPreviewToggle(_ filling: FillingPressureSummary) -> some View {
        if showsFillingPreview {
            FillingAnimationView(summary: filling, inputs: result.inputs)
                .frame(maxWidth: .infinity)
                .aspectRatio(760.0 / 360.0, contentMode: .fit)
        } else {
            Button {
                showsFillingPreview = true
            } label: {
                Label(L10n.t("show.filling.preview"), systemImage: "play.rectangle")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(SecondaryButtonStyle())
        }
    }

    private func fillingMetric(_ title: String, _ value: Double?) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.caption2.weight(.semibold))
                .foregroundStyle(AppTheme.muted)
            Text(value?.metricText(digits: 2) ?? "-")
                .font(.subheadline.monospacedDigit().weight(.bold))
                .foregroundStyle(AppTheme.ink)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var notesCard: some View {
        AppCard {
            VStack(alignment: .leading, spacing: 12) {
                Label(L10n.t("notes"), systemImage: "exclamationmark.triangle.fill")
                    .font(.headline)
                    .foregroundStyle(AppTheme.warning)
                ForEach(result.notes, id: \.self) { note in
                    Text(localizedInjectionNote(note, isKorean: settings.languageCode == "ko"))
                        .font(.callout)
                        .foregroundStyle(AppTheme.ink)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
    }

    private func askAssistant() async {
        let query = assistantQuestion.trimmingCharacters(in: .whitespacesAndNewlines)
        guard query.count >= 2 else {
            assistantErrorMessage = localText(en: "Enter a question.", ko: "질문을 입력해 주세요.")
            return
        }
        isAskingAssistant = true
        assistantErrorMessage = nil
        defer { isAskingAssistant = false }
        do {
            let baseURL = try BaseURLValidator.parse(settings.apiBaseURL)
            assistantAnswer = try await InjectionAPIClient().answerRag(
                baseURL: baseURL,
                request: RagAnswerRequest(
                    query: query,
                    topK: 3,
                    useLLM: true,
                    language: settings.languageCode,
                    predictionContext: assistantPredictionContext
                )
            )
        } catch {
            assistantErrorMessage = localText(
                en: "Assistant failed: \(error.localizedDescription)",
                ko: "Assistant 응답에 실패했습니다: \(error.localizedDescription)"
            )
        }
    }

    private var assistantPredictionContext: JSONValue {
        var payload: [String: JSONValue] = [
            "mode": .string("Injection Forecast"),
            "inputs": .object(result.inputs),
            "model_key": .string(result.modelKey),
            "model_label": .string(result.displayModelLabel),
            "filling_model_key": .string(result.fillingModelKey),
            "filling_model_label": .string(result.displayFillingModelLabel),
            "predicted_max_pressure_MPa": .double(result.predictedMaxPressureMPa),
            "predicted_max_time_s": .double(result.predictedMaxTimeS),
            "curve_points": .double(Double(result.curve.count)),
        ]
        if let fillingMax = result.bestFillingPressure?.stats["max_MPa"] {
            payload["predicted_filling_max_MPa"] = .double(fillingMax)
        }
        if let xai = result.xai {
            payload["xai"] = .object([
                "title": .string(xai.title),
                "summary": .string(xai.summary),
                "method": .string(xai.method),
                "feature_set": .string(xai.featureSet),
                "top_features": .array(xai.topFeatures.map { feature in
                    .object([
                        "name": .string(feature.name),
                        "label": .string(injectionXaiFeatureLabel(feature, isKorean: settings.languageCode == "ko")),
                        "category": .string(feature.category),
                        "importance": .double(feature.importance),
                        "local_sensitivity": .double(feature.localSensitivity),
                        "local_value": feature.localValue.map(JSONValue.double) ?? .null,
                        "perturbation": .string(feature.perturbation),
                        "explanation": .string(injectionXaiFeatureExplanation(feature, isKorean: settings.languageCode == "ko")),
                    ])
                }),
            ])
        }
        return .object(payload)
    }

    private func localText(en: String, ko: String) -> String {
        settings.languageCode == "ko" ? ko : en
    }

    private func syncAssistantQuestionForLanguage() {
        let englishDefault = "Why is the top XAI feature important in this prediction?"
        let koreanDefault = "가장 큰 XAI 영향 인자가 왜 중요한지 설명해줘."
        let current = assistantQuestion.trimmingCharacters(in: .whitespacesAndNewlines)
        if settings.languageCode == "ko", current.isEmpty || current == englishDefault {
            assistantQuestion = koreanDefault
        } else if settings.languageCode != "ko", current.isEmpty || current == koreanDefault {
            assistantQuestion = englishDefault
        }
    }
}

extension SpruePressurePredictionResult {
    var shareSummaryText: String {
        var lines = [
            "ImperialAX Injection Forecast",
            "",
            "MODEL",
            "• Sprue: \(displayModelLabel)",
            "• Filling: \(displayFillingModelLabel)",
            "",
            "INPUTS",
        ]
        lines.append(contentsOf: shareInputSummaryLines.map { "• \($0)" })
        lines.append(contentsOf: [
            "",
            "RESULTS",
            "• Peak sprue pressure: \(predictedMaxPressureMPa.metricText(digits: 2)) MPa",
            "• Peak time: \(predictedMaxTimeS.metricText(digits: 3)) s",
        ])
        if let fillingMax = bestFillingPressure?.stats["max_MPa"] {
            lines.append("• Filling pressure max: \(fillingMax.metricText(digits: 2)) MPa")
        }

        lines.append(contentsOf: [
            "",
            "CHART",
            "• Pressure curve: \(curve.count) points",
            "",
            "GRAPH",
            "• Peak marker: \(predictedMaxTimeS.metricText(digits: 3)) s / \(predictedMaxPressureMPa.metricText(digits: 2)) MPa",
        ])
        if let binCount = bestFillingPressure?.bins.count, binCount > 0 {
            lines.append("• Filling histogram: \(binCount) bins")
        }

        return lines.joined(separator: "\n").trimmingCharacters(in: .newlines)
    }

    private var shareInputSummaryLines: [String] {
        [
            inputValue("geometry_id").map { "Geometry: \($0)" },
            inputValue("process_id").map { "Process: \($0)" },
            joinedValues(
                title: "Size (L x W x t)",
                keys: ["L_mm", "W_mm", "t_mm"],
                separator: " x ",
                suffix: " mm"
            ),
            joinedValues(
                title: "Diameter / radius",
                keys: ["D_mm", "R_mm"],
                separator: " / ",
                suffix: " mm"
            ),
            gateLine,
            joinedValues(
                title: "Temperatures (melt / mold)",
                keys: ["melt_temp_C", "mold_temp_C"],
                separator: " / ",
                suffix: " C"
            ),
            inputValue("injection_time_s", digits: 3).map { "Injection time: \($0) s" },
            packingLine,
        ].compactMap { $0 }
    }

    private var gateLine: String? {
        guard let gateType = inputValue("gate_type") else { return nil }
        let size = joinedValues(
            title: nil,
            keys: ["gate_size_width_mm", "gate_size_height_mm"],
            separator: " x ",
            suffix: " mm"
        )
        return "Gate: " + ([gateType, size].compactMap { $0 }).joined(separator: ", ")
    }

    private var packingLine: String? {
        guard let pressure = inputValue("packing_pressure_MPa") else { return nil }
        if let time = inputValue("packing_time_s", digits: 3) {
            return "Packing: \(pressure) MPa for \(time) s"
        }
        return "Packing pressure: \(pressure) MPa"
    }

    private func joinedValues(
        title: String?,
        keys: [String],
        separator: String,
        suffix: String
    ) -> String? {
        let values = keys.compactMap { inputValue($0) }
        guard values.count == keys.count else { return nil }
        let body = values.joined(separator: separator) + suffix
        return title.map { "\($0): \(body)" } ?? body
    }

    private func inputValue(_ key: String, digits: Int = 4) -> String? {
        inputs[key]?.shareTextValue(digits: digits)
    }
}

private extension JSONValue {
    func shareTextValue(digits: Int) -> String? {
        switch self {
        case .string(let value):
            value
        case .double(let value):
            value.formatted(.number.precision(.fractionLength(0...digits)))
        case .bool(let value):
            String(value)
        case .array, .object, .null:
            nil
        }
    }
}

private struct FillingHistogramView: View {
    let bins: [FillingPressureBin]

    var body: some View {
        GeometryReader { proxy in
            let layout = HistogramLayout(size: proxy.size)
            let maxVolume = max(bins.map(\.volumeRatioPct).max() ?? 1, 0.000001)
            let minPressure = bins.map(\.fromMPa).min() ?? 0
            let maxPressure = bins.map(\.toMPa).max() ?? 1

            ZStack {
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .fill(AppTheme.field)

                axisGrid(layout: layout, maxVolume: maxVolume)

                ForEach(bins) { bin in
                    let bar = layout.barRect(
                        index: max(0, bin.group - 1),
                        count: bins.count,
                        value: bin.volumeRatioPct,
                        maxValue: maxVolume
                    )
                    RoundedRectangle(cornerRadius: 4, style: .continuous)
                        .fill(AppTheme.primary.opacity(0.78))
                        .frame(width: bar.width, height: bar.height)
                        .position(x: bar.midX, y: bar.midY)
                }

                axisLabels(
                    layout: layout,
                    maxVolume: maxVolume,
                    minPressure: minPressure,
                    maxPressure: maxPressure
                )
            }
        }
    }

    private func axisGrid(layout: HistogramLayout, maxVolume: Double) -> some View {
        ZStack {
            Path { path in
                path.move(to: CGPoint(x: layout.left, y: layout.bottom))
                path.addLine(to: CGPoint(x: layout.right, y: layout.bottom))
                path.move(to: CGPoint(x: layout.left, y: layout.top))
                path.addLine(to: CGPoint(x: layout.left, y: layout.bottom))

                for tick in [0.0, maxVolume / 2, maxVolume] {
                    let y = layout.y(value: tick, maxValue: maxVolume)
                    path.move(to: CGPoint(x: layout.left, y: y))
                    path.addLine(to: CGPoint(x: layout.right, y: y))
                }
            }
            .stroke(AppTheme.muted.opacity(0.24), style: StrokeStyle(lineWidth: 1, dash: [3, 5]))

            Path { path in
                path.move(to: CGPoint(x: layout.left, y: layout.bottom))
                path.addLine(to: CGPoint(x: layout.right, y: layout.bottom))
                path.move(to: CGPoint(x: layout.left, y: layout.top))
                path.addLine(to: CGPoint(x: layout.left, y: layout.bottom))
            }
            .stroke(AppTheme.muted.opacity(0.55), lineWidth: 1)
        }
    }

    private func axisLabels(
        layout: HistogramLayout,
        maxVolume: Double,
        minPressure: Double,
        maxPressure: Double
    ) -> some View {
        ZStack {
            ForEach(Array([0.0, maxVolume / 2, maxVolume].enumerated()), id: \.offset) { _, tick in
                Text(tick.metricText(digits: tick >= 10 ? 0 : 1))
                    .font(.system(size: 10, weight: .semibold, design: .rounded).monospacedDigit())
                    .foregroundStyle(AppTheme.muted)
                    .frame(width: layout.left - 8, alignment: .trailing)
                    .position(x: (layout.left - 8) / 2, y: layout.y(value: tick, maxValue: maxVolume))
            }

            Text(minPressure.metricText(digits: 1))
                .font(.system(size: 10, weight: .semibold, design: .rounded).monospacedDigit())
                .foregroundStyle(AppTheme.muted)
                .position(x: layout.left, y: layout.bottom + 14)

            Text(maxPressure.metricText(digits: 1))
                .font(.system(size: 10, weight: .semibold, design: .rounded).monospacedDigit())
                .foregroundStyle(AppTheme.muted)
                .position(x: layout.right, y: layout.bottom + 14)

            Text(L10n.t("axis.pressure.bin"))
                .font(.system(size: 10, weight: .bold, design: .rounded))
                .foregroundStyle(AppTheme.muted)
                .position(x: (layout.left + layout.right) / 2, y: layout.size.height - 8)

            Text(L10n.t("axis.volume"))
                .font(.system(size: 10, weight: .bold, design: .rounded))
                .foregroundStyle(AppTheme.muted)
                .position(x: layout.left + 34, y: layout.top - 9)
        }
    }
}

private struct HistogramLayout {
    let size: CGSize

    var left: CGFloat { 48 }
    var right: CGFloat { max(left + 1, size.width - 14) }
    var top: CGFloat { 28 }
    var bottom: CGFloat { max(top + 1, size.height - 34) }

    func y(value: Double, maxValue: Double) -> CGFloat {
        bottom - CGFloat(value / maxValue) * (bottom - top)
    }

    func barRect(index: Int, count: Int, value: Double, maxValue: Double) -> CGRect {
        let countValue = max(count, 1)
        let slot = (right - left) / CGFloat(countValue)
        let width = max(4, slot * 0.72)
        let x = left + CGFloat(index) * slot + (slot - width) / 2
        let topY = y(value: value, maxValue: maxValue)
        return CGRect(x: x, y: topY, width: width, height: bottom - topY)
    }
}

private struct FillingAnimationView: View {
    let summary: FillingPressureSummary
    let inputs: [String: JSONValue]

    private let duration: TimeInterval = 2.8
    private let previewProgress = 0.65
    @State private var isPlaying = false
    @State private var playbackStartedAt = Date()
    @State private var playbackID = 0

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Label(L10n.t("filling.animation"), systemImage: "play.circle.fill")
                    .font(.subheadline.weight(.bold))
                    .foregroundStyle(AppTheme.ink)
                Spacer()
                Text(summary.sampleID)
                    .font(.caption2.monospaced())
                    .foregroundStyle(AppTheme.muted)
            }

            ZStack(alignment: .bottomTrailing) {
                animationCanvas
                Button {
                    if isPlaying {
                        playbackID += 1
                        isPlaying = false
                    } else {
                        playOnce()
                    }
                } label: {
                    Image(systemName: isPlaying ? "stop.fill" : "play.fill")
                        .font(.caption.weight(.bold))
                        .foregroundStyle(.white)
                        .frame(width: 34, height: 34)
                        .background(AppTheme.ink.opacity(0.82), in: Circle())
                }
                .buttonStyle(.plain)
                .padding(10)
            }
        }
    }

    @ViewBuilder
    private var animationCanvas: some View {
        if isPlaying {
            TimelineView(.periodic(from: playbackStartedAt, by: 1.0 / 15.0)) { timeline in
                let elapsed = timeline.date.timeIntervalSince(playbackStartedAt)
                drawingSurface(progress: min(1, max(0, elapsed / duration)))
            }
        } else {
            drawingSurface(progress: previewProgress)
        }
    }

    private func drawingSurface(progress: Double) -> some View {
        Canvas(rendersAsynchronously: true) { context, size in
            var scaledContext = context
            scaledContext.scaleBy(x: size.width / 760.0, y: size.height / 360.0)
            draw(context: &scaledContext, size: CGSize(width: 760, height: 360), progress: progress)
        }
        .background(AppTheme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(Color.black.opacity(0.06), lineWidth: 1)
        )
    }

    private func playOnce() {
        guard !isPlaying else { return }
        playbackStartedAt = Date()
        playbackID += 1
        let currentPlaybackID = playbackID
        isPlaying = true
        Task { @MainActor in
            try? await Task.sleep(nanoseconds: UInt64(duration * 1_000_000_000))
            if playbackID == currentPlaybackID {
                isPlaying = false
            }
        }
    }

    private func draw(context: inout GraphicsContext, size: CGSize, progress: Double) {
        guard size.width > 20, size.height > 20 else { return }

        let length = max(input("L_mm", fallback: 154.01), 1)
        let width = max(input("W_mm", fallback: 97.42), 1)
        let diameter = max(input("D_mm", fallback: 17.61), 1)
        let gateWidth = max(input("gate_size_width_mm", fallback: 10), 1)
        let margin: CGFloat = 54
        let maxPartWidth = max(1, size.width - margin * 2)
        let maxPartHeight = max(1, size.height - 92)
        let scale = min(maxPartWidth / CGFloat(length), maxPartHeight / CGFloat(width))
        let partSize = CGSize(width: CGFloat(length) * scale, height: CGFloat(width) * scale)
        let origin = CGPoint(x: (size.width - partSize.width) / 2, y: (size.height - partSize.height) / 2 + 10)
        let partRect = CGRect(origin: origin, size: partSize)
        let holeRadius = max(CGFloat(diameter) * scale / 2, 3)
        let holeCenter = CGPoint(x: partRect.midX, y: partRect.midY)
        let front = min(1.06, progress * 1.18)
        let maxPressure = max(summary.stats["max_MPa"] ?? 1, 0.000001)
        let partPath = fillingPartPath(partRect: partRect, holeCenter: holeCenter, holeRadius: holeRadius)

        var clippedContext = context
        clippedContext.clip(to: partPath, style: FillStyle(eoFill: true))
        let step: CGFloat = 5
        var y = partRect.minY
        while y < partRect.maxY {
            var x = partRect.minX
            while x < partRect.maxX {
                let localX = Double((x - partRect.minX) / max(partRect.width, 1))
                let localY = abs(Double((y - partRect.midY) / max(partRect.height / 2, 1)))
                if localX <= front {
                    let gateHotspot = exp(-((localX / 0.16) * (localX / 0.16) + (localY / 0.46) * (localY / 0.46)))
                    let wake = max(0, 1 - (front - localX) * 2.2) * 0.18
                    let fraction = max(0, min(1, pow(localX, 1.45) - gateHotspot * 0.08 - wake))
                    let pressure = pressureFromDistribution(fraction: fraction)
                    let normalized = max(0, min(1, pressure / maxPressure))
                    let rect = CGRect(x: x, y: y, width: step + 1, height: step + 1)
                    clippedContext.fill(Path(rect), with: .color(fillingColor(normalized)))
                }
                x += step
            }
            y += step
        }

        context.stroke(Path(partRect), with: .color(AppTheme.muted.opacity(0.72)), lineWidth: 1.5)
        context.fill(Path(ellipseIn: CGRect(
            x: holeCenter.x - holeRadius,
            y: holeCenter.y - holeRadius,
            width: holeRadius * 2,
            height: holeRadius * 2
        )), with: .color(AppTheme.card.opacity(0.94)))
        context.stroke(Path(ellipseIn: CGRect(
            x: holeCenter.x - holeRadius,
            y: holeCenter.y - holeRadius,
            width: holeRadius * 2,
            height: holeRadius * 2
        )), with: .color(AppTheme.muted.opacity(0.72)), lineWidth: 1.5)

        let gateHeight = max(CGFloat(gateWidth) * scale, 12)
        let gateRect = CGRect(x: partRect.minX - 24, y: partRect.midY - gateHeight / 2, width: 24, height: gateHeight)
        context.fill(Path(gateRect), with: .color(AppTheme.danger))

        let pressureText = Text("\(((summary.stats["max_MPa"] ?? 0) * min(progress * 1.1, 1)).metricText(digits: 1)) MPa")
            .font(.caption.monospacedDigit().weight(.bold))
            .foregroundStyle(AppTheme.ink)
        context.draw(pressureText, at: CGPoint(x: partRect.maxX, y: size.height - 15), anchor: .trailing)
    }

    private func fillingPartPath(partRect: CGRect, holeCenter: CGPoint, holeRadius: CGFloat) -> Path {
        var path = Path()
        path.addRect(partRect)
        path.addEllipse(in: CGRect(
            x: holeCenter.x - holeRadius,
            y: holeCenter.y - holeRadius,
            width: holeRadius * 2,
            height: holeRadius * 2
        ))
        return path
    }

    private func input(_ key: String, fallback: Double) -> Double {
        inputs[key]?.doubleValue ?? fallback
    }

    private func pressureFromDistribution(fraction: Double) -> Double {
        let bins = summary.bins.sorted { $0.centerMPa > $1.centerMPa }
        let total = max(bins.reduce(0.0) { $0 + $1.volumeRatioPct }, 0.000001)
        let target = max(0, min(100, fraction * 100))
        var cumulative = 0.0
        for bin in bins {
            cumulative += bin.volumeRatioPct / total * 100
            if target <= cumulative {
                return bin.centerMPa
            }
        }
        return bins.last?.centerMPa ?? 0
    }

    private func fillingColor(_ value: Double) -> Color {
        let stops: [(Double, (Double, Double, Double))] = [
            (0.0, (0.027, 0.294, 0.847)),
            (0.25, (0.0, 0.573, 1.0)),
            (0.42, (0.071, 0.875, 0.890)),
            (0.56, (0.0, 0.831, 0.357)),
            (0.70, (0.847, 0.918, 0.0)),
            (0.84, (1.0, 0.541, 0.0)),
            (1.0, (0.831, 0.0, 0.0)),
        ]
        let value = max(0, min(1, value))
        for index in 0..<(stops.count - 1) {
            let start = stops[index]
            let end = stops[index + 1]
            if value >= start.0, value <= end.0 {
                let t = (value - start.0) / max(0.000001, end.0 - start.0)
                return Color(
                    red: start.1.0 + (end.1.0 - start.1.0) * t,
                    green: start.1.1 + (end.1.1 - start.1.1) * t,
                    blue: start.1.2 + (end.1.2 - start.1.2) * t
                )
            }
        }
        return Color(red: 0.831, green: 0, blue: 0)
    }
}
