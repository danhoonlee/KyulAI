import KyulAIDDLaminateCore
import SwiftUI

struct ContentViewV2: View {
    private enum ForecastMode: String, CaseIterable, Identifiable {
        case response
        case u3

        var id: String { rawValue }

        var title: String {
            switch self {
            case .response: "Response Forecast"
            case .u3: "u3 Forecast"
            }
        }

        var icon: String {
            switch self {
            case .response: "waveform.path.ecg"
            case .u3: "scope"
            }
        }
    }

    private enum DetailRoute: Hashable, Identifiable {
        case response(ResponsePredictionResult)
        case u3(U3PtPredictionResult)

        var id: String {
            switch self {
            case .response(let result):
                "response-\(result.modelKey)-\(result.predictedPt)-\(result.curve.count)"
            case .u3(let result):
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
    @State private var selectedMode: ForecastMode = .response
    @State private var selectedDetail: DetailRoute?
    @State private var isShowingSettings = false
    @State private var isShowingModelSheet = false

    private var selectedModel: ModelInfo? {
        switch selectedMode {
        case .response:
            viewModel.responseModels.first { $0.key == viewModel.selectedResponseModelKey }
        case .u3:
            viewModel.u3PtModels.first { $0.key == viewModel.selectedU3PtModelKey }
        }
    }

    private var currentModels: [ModelInfo] {
        switch selectedMode {
        case .response: viewModel.responseModels
        case .u3: viewModel.u3PtModels
        }
    }

    private var isKorean: Bool {
        settings.languageCode == "ko"
    }

    private func localText(en: String, ko: String) -> String {
        isKorean ? ko : en
    }

    private func forecastModeTitle(_ mode: ForecastMode) -> String {
        switch mode {
        case .response:
            localText(en: "Response Forecast", ko: "응답 예측")
        case .u3:
            localText(en: "u3 Forecast", ko: "u3 예측")
        }
    }

    private var appHeadlineTitle: String {
        localText(en: "C2ES\nLaminate Forecast", ko: "C2ES\n적층 예측")
    }

    private func localModelLabel(_ label: String) -> String {
        guard isKorean else { return label }
        switch label {
        case "Laminate Forecast - Machine Learning":
            return "적층 예측 - Machine Learning"
        case "Laminate Forecast - Deep Learning":
            return "적층 예측 - Deep Learning"
        case "u3 Forecast - Machine Learning":
            return "u3 예측 - Machine Learning"
        case "u3 Forecast - Deep Learning":
            return "u3 예측 - Deep Learning"
        default:
            return label
        }
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                header
                workflowStrip
                modePicker
                VStack(spacing: 14) {
                    inputPanel
                    resultPanel
                }
            }
            .padding(20)
        }
        #if os(iOS)
        .scrollDismissesKeyboard(.interactively)
        #endif
        .simultaneousGesture(TapGesture().onEnded { focusedField = nil })
        .background(WantedV2Theme.background.ignoresSafeArea())
        .navigationTitle(localText(en: "Laminate v2", ko: "적층 v2"))
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
                .foregroundStyle(WantedV2Theme.blue)
                .accessibilityLabel(L10n.t("language.toggle"))

                Button {
                    isShowingSettings = true
                } label: {
                    Image(systemName: "link")
                }
                .accessibilityLabel(L10n.t("api.settings.title"))
            }
        }
        .sheet(isPresented: $isShowingSettings) {
            NavigationStack {
                settingsSheet
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
        .sheet(isPresented: $isShowingModelSheet) {
            NavigationStack {
                modelSheet
                    .navigationTitle(L10n.t("choose.model"))
                    .appInlineNavigationTitle()
                    .toolbar {
                        ToolbarItem(placement: .confirmationAction) {
                            Button(L10n.t("done")) {
                                isShowingModelSheet = false
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
            case .response(let result):
                ResultDetailView(result: result)
            case .u3(let result):
                U3PtResultDetailView(result: result)
            }
        }
        .task {
            await autoCheckConnection()
        }
        .onChange(of: settings.apiBaseURL) {
            viewModel.resetReadiness()
            Task { await autoCheckConnection() }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .center, spacing: 12) {
                Text(localText(en: "Composite Laminate AI", ko: "복합재 적층 AI"))
                    .font(.caption.weight(.black))
                    .foregroundStyle(WantedV2Theme.blue)
                    .textCase(.uppercase)
                Spacer(minLength: 8)
                connectionBadge
            }
            Text(appHeadlineTitle)
                .font(.system(size: 32, weight: .black, design: .rounded))
                .foregroundStyle(WantedV2Theme.ink)
                .lineLimit(2)
                .minimumScaleFactor(0.78)
                .multilineTextAlignment(.leading)
                .fixedSize(horizontal: false, vertical: true)
            Text(localText(
                en: "Forecast laminate Type, Pt, and response curve from case and theta inputs.",
                ko: "Case와 theta 입력으로 적층 Type, Pt, 응답 곡선을 예측합니다."
            ))
                .font(.callout.weight(.semibold))
                .foregroundStyle(WantedV2Theme.muted)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(18)
        .background(WantedV2Theme.surface, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(WantedV2Theme.line, lineWidth: 1)
        )
        .shadow(color: .black.opacity(0.06), radius: 18, x: 0, y: 10)
    }

    private var workflowStrip: some View {
        VStack(spacing: 10) {
            workflowStep("01", localText(en: "Set case", ko: "Case 설정"), localText(en: "Choose stack family", ko: "적층 구조 선택"))
            workflowStep("02", localText(en: "Pick model", ko: "모델 선택"), localText(en: "ML default or DL check", ko: "ML 기본값 또는 DL 비교"))
            workflowStep("03", localText(en: "Review", ko: "결과 확인"), localText(en: "Pt, curve, XAI", ko: "Pt, 곡선, XAI"))
        }
    }

    private func workflowStep(_ index: String, _ title: String, _ subtitle: String) -> some View {
        HStack(alignment: .top, spacing: 10) {
            Text(index)
                .font(.caption.weight(.black))
                .foregroundStyle(.white)
                .frame(width: 30, height: 30)
                .background(WantedV2Theme.ink, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.caption.weight(.black))
                    .foregroundStyle(WantedV2Theme.ink)
                Text(subtitle)
                .font(.caption2.weight(.semibold))
                .foregroundStyle(WantedV2Theme.muted)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(WantedV2Theme.surface, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(WantedV2Theme.line, lineWidth: 1)
        )
    }

    private var modePicker: some View {
        Picker(localText(en: "Forecast Mode", ko: "예측 모드"), selection: $selectedMode) {
            ForEach(ForecastMode.allCases) { mode in
                Label(forecastModeTitle(mode), systemImage: mode.icon).tag(mode)
            }
        }
        .pickerStyle(.segmented)
    }

    private var inputPanel: some View {
        VStack(alignment: .leading, spacing: 16) {
            panelHeader(
                eyebrow: localText(en: "Forecast Setup", ko: "예측 설정"),
                title: selectedMode == .response
                    ? forecastModeTitle(.response)
                    : localText(en: "u3 Pt Forecast", ko: "u3 Pt 예측"),
                subtitle: selectedMode == .response
                    ? localText(en: "Predict Type, Pt, and full response curve.", ko: "Type, Pt, 전체 응답 곡선을 예측합니다.")
                    : localText(en: "Predict u3 Type, Pt, and an approximate curve.", ko: "u3 Type, Pt, 대략적인 곡선을 예측합니다.")
            )

            modelButton

            Picker("Case", selection: $viewModel.selectedCase) {
                ForEach(DDLaminateCase.allCases) { laminateCase in
                    Text(laminateCase.rawValue.replacingOccurrences(of: "Case", with: "Case ")).tag(laminateCase)
                }
            }
            .pickerStyle(.segmented)

            HStack(spacing: 12) {
                angleField(localText(en: "Theta 1", ko: "Theta 1"), text: $viewModel.theta1, field: .theta1)
                angleField(localText(en: "Theta 2", ko: "Theta 2"), text: $viewModel.theta2, field: .theta2)
            }

            DynamicPlyStackPreviewCard(
                laminateCase: viewModel.selectedCase,
                theta1Text: viewModel.theta1,
                theta2Text: viewModel.theta2,
                isKorean: isKorean
            )

            caseFormulaCard

            Button {
                focusedField = nil
                Task {
                    switch selectedMode {
                    case .response:
                        await predict()
                    case .u3:
                        await predictU3Pt()
                    }
                }
            } label: {
                HStack {
                    Image(systemName: selectedMode == .response ? "waveform.path.ecg" : "scope")
                    Text(primaryButtonTitle)
                    Spacer()
                    Image(systemName: "arrow.right")
                }
                .frame(maxWidth: .infinity)
            }
            .buttonStyle(WantedPrimaryButtonStyle())
            .disabled(primaryButtonDisabled)
        }
        .padding(18)
        .background(WantedV2Theme.surface, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(WantedV2Theme.line, lineWidth: 1)
        )
    }

    private var resultPanel: some View {
        VStack(alignment: .leading, spacing: 16) {
            switch selectedMode {
            case .response:
                if let result = viewModel.result {
                    responseResultPanel(result)
                } else {
                    emptyResultPanel
                }
            case .u3:
                if let result = viewModel.u3PtResult {
                    u3ResultPanel(result)
                } else {
                    emptyResultPanel
                }
            }
        }
        .padding(18)
        .background(WantedV2Theme.surface, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(WantedV2Theme.line, lineWidth: 1)
        )
    }

    private var modelButton: some View {
        Button {
            isShowingModelSheet = true
        } label: {
            HStack(alignment: .center, spacing: 12) {
                Image(systemName: selectedMode == .response ? "brain.head.profile" : "point.topleft.down.curvedto.point.bottomright.up")
                    .font(.headline.weight(.bold))
                    .foregroundStyle(WantedV2Theme.blue)
                    .frame(width: 42, height: 42)
                .background(WantedV2Theme.blueSoft, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                VStack(alignment: .leading, spacing: 5) {
                    Text(selectedModel.map { localModelLabel($0.displayLabel) } ?? localText(en: "Load models", ko: "모델 불러오기"))
                        .font(.system(size: 15, weight: .black))
                        .foregroundStyle(WantedV2Theme.ink)
                        .lineLimit(1)
                        .minimumScaleFactor(0.60)
                        .allowsTightening(true)
                    if isRecommendedModel(selectedModel) {
                        HStack {
                            badge(localText(en: "Recommended", ko: "추천"), tint: WantedV2Theme.green)
                        }
                    }
                    Text(selectedModel.map(modelDescription(for:)) ?? localText(en: "Connect to the API to load available models.", ko: "사용 가능한 모델을 불러오려면 API에 연결하세요."))
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(WantedV2Theme.muted)
                        .lineLimit(2)
                }
                .layoutPriority(1)
                Spacer(minLength: 8)
                Image(systemName: "chevron.up.chevron.down")
                    .font(.caption.weight(.black))
                    .foregroundStyle(WantedV2Theme.muted)
                    .fixedSize()
            }
            .padding(12)
            .background(WantedV2Theme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(WantedV2Theme.line, lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
    }

    private func angleField(_ title: String, text: Binding<String>, field: FocusedField) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text(title)
                    .font(.caption.weight(.black))
                    .foregroundStyle(WantedV2Theme.muted)
                Spacer(minLength: 8)
                Text(angleReadout(text.wrappedValue))
                    .font(.caption.monospacedDigit().weight(.black))
                    .foregroundStyle(WantedV2Theme.blue)
            }
            HStack {
                TextField("0", text: text)
                    .focused($focusedField, equals: field)
                    #if os(iOS)
                    .keyboardType(.numbersAndPunctuation)
                    #endif
                    .font(.title2.monospacedDigit().weight(.black))
                    .foregroundStyle(WantedV2Theme.ink)
                Text(localText(en: "deg", ko: "도"))
                    .font(.caption.weight(.bold))
                    .foregroundStyle(WantedV2Theme.muted)
            }
            .padding(.horizontal, 12)
            .frame(height: 54)
            .background(WantedV2Theme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(WantedV2Theme.line, lineWidth: 1)
            )
            Slider(value: angleBinding(text), in: -90...90, step: 1)
                .tint(WantedV2Theme.blue)
                .accessibilityLabel(localText(en: "\(title) slider", ko: "\(title) 슬라이더"))
                .accessibilityValue(angleReadout(text.wrappedValue))
                .accessibilityIdentifier(field == .theta1 ? "v2-theta1-slider" : "v2-theta2-slider")
        }
        .padding(12)
        .background(WantedV2Theme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(WantedV2Theme.line, lineWidth: 1)
        )
    }

    private func angleBinding(_ text: Binding<String>) -> Binding<Double> {
        Binding(
            get: { Self.clampedAngleValue(text.wrappedValue) },
            set: { text.wrappedValue = Self.angleInputString($0) }
        )
    }

    private func angleReadout(_ text: String) -> String {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard Double(trimmed) != nil else {
            return "—"
        }
        let value = Self.clampedAngleValue(trimmed)
        return "\(value > 0 ? "+" : "")\(Self.angleInputString(value))°"
    }

    private static func clampedAngleValue(_ text: String) -> Double {
        let value = Double(text.trimmingCharacters(in: .whitespacesAndNewlines)) ?? 0
        return min(90, max(-90, value)).rounded()
    }

    private static func angleInputString(_ value: Double) -> String {
        let rounded = min(90, max(-90, value)).rounded()
        return String(Int(rounded))
    }

    private var caseFormulaCard: some View {
        VStack(alignment: .leading, spacing: 7) {
            Text(localText(en: "Case formula", ko: "Case 공식"))
                .font(.caption.weight(.black))
                .foregroundStyle(WantedV2Theme.blue)
            Text(caseFormula)
                .font(.caption.weight(.semibold))
                .foregroundStyle(WantedV2Theme.muted)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(WantedV2Theme.blueSoft, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
    }

    private var caseFormula: String {
        switch viewModel.selectedCase {
        case .case2:
            "[[±θ1]/[±θ2]]4"
        case .case3:
            "[[±θ1]/[±θ2]/[∓θ1]/[∓θ2]]2"
        case .case4:
            "[([±θ1]/[±θ2])2 / ([∓θ1]/[∓θ2])2]"
        }
    }

    private var emptyResultPanel: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(localText(en: "No run yet", ko: "아직 실행 전"))
                .font(.caption.weight(.black))
                .foregroundStyle(WantedV2Theme.blue)
                .textCase(.uppercase)
            Text(localText(en: "Ready for input", ko: "입력 준비 완료"))
                .font(.system(size: 34, weight: .black, design: .rounded))
                .foregroundStyle(WantedV2Theme.ink)
            Text(localText(
                en: "Run a forecast to inspect predicted Type, Pt, curve shape, and top feature impacts.",
                ko: "예측을 실행하면 Type, Pt, 곡선 형태, 주요 feature 영향을 확인할 수 있습니다."
            ))
                .font(.callout.weight(.semibold))
                .foregroundStyle(WantedV2Theme.muted)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, minHeight: 230, alignment: .leading)
        .padding(18)
        .background(WantedV2Theme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(WantedV2Theme.line, style: StrokeStyle(lineWidth: 1, dash: [5, 4]))
        )
    }

    private func responseResultPanel(_ result: ResponsePredictionResult) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            resultHero(
                eyebrow: localText(en: "Prediction", ko: "예측 결과"),
                title: "Type \(result.predictedType)",
                detail: localModelLabel(result.displayModelLabel),
                side: result.confidence.percentText
            )
            metricsGrid([
                ("Pt", result.predictedPt.metricText(digits: 2)),
                (localText(en: "Pt disp.", ko: "Pt 변위"), result.predictedPtDisplacement?.metricText(digits: 5) ?? "-"),
                (localText(en: "Max force", ko: "최대 하중"), result.predictedMaxForce.metricText(digits: 2)),
                (localText(en: "Points", ko: "포인트"), "\(result.curve.count)"),
            ])
            CurveChartView(points: result.curve, predictedPt: result.predictedPt)
                .frame(height: 230)
            probabilityRows(result.sortedProbabilities, selectedType: result.predictedType)
            if let xai = result.xai {
                xaiPreview(xai)
            }
            detailButton(.response(result))
        }
    }

    private func u3ResultPanel(_ result: U3PtPredictionResult) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            resultHero(
                eyebrow: localText(en: "u3 Forecast", ko: "u3 예측"),
                title: result.predictedPt.metricText(digits: 2),
                detail: localModelLabel(result.displayModelLabel),
                side: result.predictedType.map { "Type \($0)" } ?? "Type -"
            )
            metricsGrid([
                ("Pt", result.predictedPt.metricText(digits: 2)),
                (localText(en: "Type conf.", ko: "Type 신뢰도"), result.confidence.percentText),
                (localText(en: "Max force", ko: "최대 하중"), result.predictedMaxForce.metricText(digits: 2)),
                (localText(en: "Points", ko: "포인트"), "\(result.curve.count)"),
            ])
            CurveChartView(points: result.curve, predictedPt: result.predictedPt, fitMode: .u3)
                .frame(height: 230)
            if let probabilities = result.probabilities {
                probabilityRows(probabilities.sorted { $0.key < $1.key }.map { ($0.key, $0.value) }, selectedType: result.predictedType)
            }
            if let xai = result.xai {
                xaiPreview(xai)
            }
            detailButton(.u3(result))
        }
    }

    private func resultHero(eyebrow: String, title: String, detail: String, side: String) -> some View {
        HStack(alignment: .top, spacing: 12) {
            VStack(alignment: .leading, spacing: 7) {
                Text(eyebrow)
                    .font(.caption.weight(.black))
                    .foregroundStyle(Color(red: 0.64, green: 0.75, blue: 1.0))
                    .textCase(.uppercase)
                Text(title)
                    .font(.system(size: 38, weight: .black, design: .rounded))
                    .foregroundStyle(.white)
                    .lineLimit(1)
                    .minimumScaleFactor(0.62)
                Text(detail)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.white.opacity(0.74))
                    .lineLimit(2)
            }
            Spacer()
            Text(side)
                .font(.headline.monospacedDigit().weight(.black))
                .foregroundStyle(Color(red: 0.54, green: 1.0, blue: 0.79))
                .padding(.horizontal, 10)
                .padding(.vertical, 7)
                .background(.white.opacity(0.10), in: Capsule())
        }
        .padding(16)
        .background(WantedV2Theme.ink, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
    }

    private func metricsGrid(_ metrics: [(String, String)]) -> some View {
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
            ForEach(metrics, id: \.0) { metric in
                VStack(alignment: .leading, spacing: 5) {
                    Text(metric.0)
                        .font(.caption.weight(.black))
                        .foregroundStyle(WantedV2Theme.muted)
                    Text(metric.1)
                        .font(.headline.monospacedDigit().weight(.black))
                        .foregroundStyle(WantedV2Theme.ink)
                        .lineLimit(1)
                        .minimumScaleFactor(0.7)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(12)
                .background(WantedV2Theme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            }
        }
    }

    private func probabilityRows(_ probabilities: [(label: String, value: Double)], selectedType: Int?) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(localText(en: "Class probability", ko: "분류 확률"))
                .font(.headline.weight(.black))
                .foregroundStyle(WantedV2Theme.ink)
            if probabilities.isEmpty {
                Text(localText(en: "No probability output for this model.", ko: "이 모델은 확률 출력을 제공하지 않습니다."))
                    .font(.callout)
                    .foregroundStyle(WantedV2Theme.muted)
            } else {
                ForEach(probabilities, id: \.label) { probability in
                    probabilityRow(label: probability.label, value: probability.value, selectedType: selectedType)
                }
            }
        }
    }

    private func probabilityRow(label: String, value: Double, selectedType: Int?) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(label.capitalized)
                    .font(.caption.weight(.black))
                    .foregroundStyle(WantedV2Theme.ink)
                Spacer()
                Text(Optional(value).percentText)
                    .font(.caption.monospacedDigit().weight(.black))
                    .foregroundStyle(WantedV2Theme.muted)
            }
            GeometryReader { proxy in
                Capsule()
                    .fill(WantedV2Theme.line.opacity(0.7))
                    .overlay(alignment: .leading) {
                        Capsule()
                            .fill(label == "type\(selectedType ?? -1)" ? WantedV2Theme.blue : WantedV2Theme.cyan.opacity(0.42))
                            .frame(width: max(6, proxy.size.width * min(max(value, 0), 1)))
                    }
            }
            .frame(height: 8)
        }
    }

    private func xaiPreview(_ xai: XAIExplanation) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Label(localText(en: "Top feature impact", ko: "주요 feature 영향"), systemImage: "sparkle.magnifyingglass")
                .font(.headline.weight(.black))
                .foregroundStyle(WantedV2Theme.ink)
            ForEach(Array(xai.topFeatures.prefix(5)), id: \.id) { feature in
                HStack(spacing: 10) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(feature.label)
                            .font(.caption.weight(.black))
                            .foregroundStyle(WantedV2Theme.ink)
                            .lineLimit(1)
                        Text(feature.category.capitalized)
                            .font(.caption2.weight(.bold))
                            .foregroundStyle(WantedV2Theme.muted)
                    }
                    Spacer()
                    Text(feature.importance.formatted(.percent.precision(.fractionLength(1))))
                        .font(.caption.monospacedDigit().weight(.black))
                        .foregroundStyle(WantedV2Theme.blue)
                }
                .padding(10)
                .background(WantedV2Theme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            }
        }
    }

    private func detailButton(_ route: DetailRoute) -> some View {
        Button {
            selectedDetail = route
        } label: {
            HStack {
                Text(localText(en: "Open full result", ko: "전체 결과 보기"))
                Spacer()
                Image(systemName: "chart.xyaxis.line")
            }
        }
        .buttonStyle(WantedSecondaryButtonStyle())
    }

    private func panelHeader(eyebrow: String, title: String, subtitle: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(eyebrow)
                .font(.caption.weight(.black))
                .foregroundStyle(WantedV2Theme.blue)
                .textCase(.uppercase)
            Text(title)
                .font(.title3.weight(.black))
                .foregroundStyle(WantedV2Theme.ink)
                .lineLimit(2)
                .minimumScaleFactor(0.82)
                .multilineTextAlignment(.leading)
                .fixedSize(horizontal: false, vertical: true)
            Text(subtitle)
                .font(.callout.weight(.semibold))
                .foregroundStyle(WantedV2Theme.muted)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private func badge(_ title: String, tint: Color) -> some View {
        Text(title)
            .font(.caption2.weight(.black))
            .foregroundStyle(tint)
            .padding(.horizontal, 7)
            .padding(.vertical, 4)
            .background(tint.opacity(0.12), in: Capsule())
    }

    private var connectionBadge: some View {
        let config = connectionStatus
        return HStack(spacing: 7) {
            Circle()
                .fill(config.color)
                .frame(width: 8, height: 8)
            Text(config.title)
                .font(.caption.weight(.black))
                .foregroundStyle(config.color)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 7)
        .background(config.color.opacity(0.10), in: Capsule())
        .lineLimit(1)
    }

    private var connectionStatus: (title: String, color: Color) {
        switch viewModel.connectionState {
        case .idle:
            (localText(en: "Not checked", ko: "미확인"), WantedV2Theme.muted)
        case .checking:
            (localText(en: "Checking", ko: "확인 중"), WantedV2Theme.blue)
        case .ready(let available):
            available
                ? (localText(en: "API ready", ko: "API 준비됨"), WantedV2Theme.green)
                : (localText(en: "Model missing", ko: "모델 없음"), WantedV2Theme.amber)
        case .failed:
            (localText(en: "Offline", ko: "오프라인"), WantedV2Theme.red)
        }
    }

    private var primaryButtonTitle: String {
        switch selectedMode {
        case .response:
            viewModel.isPredicting ? L10n.t("predicting") : localText(en: "Run Forecast", ko: "예측 실행")
        case .u3:
            viewModel.isPredictingU3Pt ? L10n.t("predicting") : localText(en: "Predict u3 Pt", ko: "u3 Pt 예측")
        }
    }

    private var primaryButtonDisabled: Bool {
        switch selectedMode {
        case .response:
            !viewModel.canPredict
        case .u3:
            !viewModel.canPredictU3Pt
        }
    }

    private var modelSheet: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                Text(localText(
                    en: "Pick the model style that fits this run. The recommended model is the stable default for quick forecasts.",
                    ko: "이번 예측에 맞는 모델 방식을 선택하세요. 추천 모델은 빠른 예측에 쓰기 좋은 안정적인 기본값입니다."
                ))
                    .font(.callout.weight(.semibold))
                    .foregroundStyle(WantedV2Theme.muted)
                    .fixedSize(horizontal: false, vertical: true)

                if currentModels.isEmpty {
                    Text(localText(en: "Connect to the API to load models.", ko: "모델을 불러오려면 API에 연결하세요."))
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(WantedV2Theme.muted)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(16)
                        .background(WantedV2Theme.surface, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                } else {
                    ForEach(currentModels) { model in
                        modelOption(model)
                    }
                }
            }
            .padding(20)
        }
        .background(WantedV2Theme.background.ignoresSafeArea())
    }

    private func modelOption(_ model: ModelInfo) -> some View {
        let selected = model.key == (selectedMode == .response ? viewModel.selectedResponseModelKey : viewModel.selectedU3PtModelKey)
        return Button {
            guard model.available else { return }
            switch selectedMode {
            case .response:
                viewModel.selectResponseModel(key: model.key)
            case .u3:
                viewModel.selectU3PtModel(key: model.key)
            }
            isShowingModelSheet = false
        } label: {
            HStack(alignment: .top, spacing: 12) {
                Image(systemName: modelIcon(for: model))
                    .font(.headline.weight(.bold))
                    .foregroundStyle(WantedV2Theme.blue)
                    .frame(width: 44, height: 44)
                    .background(WantedV2Theme.blueSoft, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                VStack(alignment: .leading, spacing: 8) {
                    Text(localModelLabel(model.displayLabel))
                        .font(.headline.weight(.black))
                        .foregroundStyle(WantedV2Theme.ink)
                        .lineLimit(1)
                        .minimumScaleFactor(0.68)
                        .allowsTightening(true)
                    HStack(spacing: 6) {
                        if isRecommendedModel(model) {
                            badge(localText(en: "Recommended", ko: "추천"), tint: WantedV2Theme.green)
                        }
                        badge(modelTag(for: model), tint: WantedV2Theme.blue)
                    }
                    Text(modelDescription(for: model))
                        .font(.callout.weight(.semibold))
                        .foregroundStyle(WantedV2Theme.muted)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .layoutPriority(1)
                Spacer(minLength: 8)
                if selected {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.title3)
                        .foregroundStyle(WantedV2Theme.green)
                        .fixedSize()
                }
            }
            .padding(16)
            .background(WantedV2Theme.surface, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(selected ? WantedV2Theme.blue : WantedV2Theme.line, lineWidth: selected ? 1.5 : 1)
            )
        }
        .buttonStyle(.plain)
        .disabled(!model.available)
        .opacity(model.available ? 1 : 0.5)
    }

    private var settingsSheet: some View {
        Form {
            Section(localText(en: "Web link", ko: "웹 링크")) {
                TextField(L10n.t("api.base.url"), text: $settings.apiBaseURL)
                    .focused($focusedField, equals: .apiBaseURL)
                    #if os(iOS)
                    .textInputAutocapitalization(.never)
                    .keyboardType(.URL)
                    .autocorrectionDisabled()
                    #endif
                HStack {
                    connectionBadge
                    Spacer()
                    Button(L10n.t("retry.action")) {
                        Task { await autoCheckConnection() }
                    }
                }
            }
        }
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
                selectedDetail = .response(result)
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
                selectedDetail = .u3(result)
            }
        } catch {
            viewModel.errorMessage = error.localizedDescription
        }
    }

    private func isRecommendedModel(_ model: ModelInfo?) -> Bool {
        model?.key == DDLaminateDefaults.responseModelKey || model?.key == DDLaminateDefaults.u3PtModelKey
    }

    private func modelIcon(for model: ModelInfo?) -> String {
        guard let model else { return "square.stack.3d.up" }
        let label = model.displayLabel.lowercased()
        if model.key.contains("goint") || label.contains("deep learning") || label.contains("nn") {
            return "brain.head.profile"
        }
        return "tree"
    }

    private func modelTag(for model: ModelInfo?) -> String {
        guard let model else { return localText(en: "Model", ko: "모델") }
        let label = model.displayLabel.lowercased()
        if model.key.contains("goint") || label.contains("deep learning") || label.contains("nn") {
            return localText(en: "Deep learning", ko: "딥러닝")
        }
        if model.key == DDLaminateDefaults.responseModelKey
            || model.key == DDLaminateDefaults.u3PtModelKey
            || label.contains("machine learning")
            || label.contains("extratrees") {
            return localText(en: "Fast", ko: "빠름")
        }
        return localText(en: "Experimental", ko: "실험적")
    }

    private func modelDescription(for model: ModelInfo) -> String {
        let label = model.displayLabel.lowercased()
        if model.key == DDLaminateDefaults.responseModelKey
            || model.key == DDLaminateDefaults.u3PtModelKey
            || label.contains("machine learning")
            || label.contains("extratrees") {
            return localText(
                en: "Fast machine-learning model recommended for routine laminate forecasts.",
                ko: "일반적인 적층 예측에 추천하는 빠른 Machine Learning 모델입니다."
            )
        }
        if model.key.contains("goint") || label.contains("goint") || label.contains("deep learning") {
            return localText(
                en: "Deep-learning model for comparison and experimental checks.",
                ko: "비교와 실험 확인에 사용하는 Deep Learning 모델입니다."
            )
        }
        return model.description.isEmpty
            ? localText(en: "Alternative laminate forecast model.", ko: "대체 적층 예측 모델입니다.")
            : model.description
    }

    private var errorBinding: Binding<Bool> {
        Binding(
            get: { viewModel.errorMessage != nil },
            set: { if !$0 { viewModel.errorMessage = nil } }
        )
    }

    private func friendlyErrorMessage(_ message: String?) -> String {
        let lowercased = (message ?? "").lowercased()
        if lowercased.contains("theta") || lowercased.contains("numeric") {
            return L10n.t("friendly.input")
        }
        if lowercased.contains("unavailable") || lowercased.contains("model") {
            return L10n.t("friendly.model")
        }
        if lowercased.contains("http") {
            return L10n.t("friendly.server")
        }
        return L10n.t("friendly.prediction")
    }
}

private struct DynamicPlyStackPreviewCard: View {
    let laminateCase: DDLaminateCase
    let theta1Text: String
    let theta2Text: String
    let isKorean: Bool

    private var theta1: Double { Self.clampedAngle(theta1Text) }
    private var theta2: Double { Self.clampedAngle(theta2Text) }
    private var sequence: [PreviewPly] {
        Self.buildSequence(laminateCase: laminateCase, theta1: theta1, theta2: theta2)
    }

    private func localText(en: String, ko: String) -> String {
        isKorean ? ko : en
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(localText(en: "Live laminate preview", ko: "실시간 적층 미리보기"))
                        .font(.caption.weight(.black))
                        .foregroundStyle(WantedV2Theme.blue)
                        .textCase(.uppercase)
                    Text(localText(en: "Angle-aware ply stack", ko: "각도 반영 ply stack"))
                        .font(.subheadline.weight(.black))
                        .foregroundStyle(WantedV2Theme.ink)
                }
                Spacer()
                Text(isKorean ? "Ply \(sequence.count)개" : "\(sequence.count) plies")
                    .font(.caption.monospacedDigit().weight(.black))
                    .foregroundStyle(WantedV2Theme.blue)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 5)
                    .background(WantedV2Theme.blueSoft, in: Capsule())
            }

            PlyStackCanvas(sequence: sequence)
                .frame(height: 210)
                .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .stroke(WantedV2Theme.line, lineWidth: 1)
                )

            HStack(spacing: 8) {
                stackLegend("θ1", color: Color(red: 0.41, green: 0.49, blue: 0.83))
                stackLegend("θ2", color: Color(red: 0.74, green: 0.56, blue: 0.44))
                stackLegend("+", color: WantedV2Theme.green)
                stackLegend("-", color: WantedV2Theme.red)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(12)
        .background(WantedV2Theme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(WantedV2Theme.line, lineWidth: 1)
        )
        .accessibilityElement(children: .combine)
        .accessibilityLabel(
            localText(
                en: "Angle-aware laminate stack preview, \(sequence.count) plies",
                ko: "각도 반영 적층 미리보기, Ply \(sequence.count)개"
            )
        )
    }

    private func stackLegend(_ title: String, color: Color) -> some View {
        HStack(spacing: 5) {
            RoundedRectangle(cornerRadius: 3, style: .continuous)
                .fill(color)
                .frame(width: 11, height: 11)
            Text(title)
                .font(.caption2.weight(.black))
                .foregroundStyle(WantedV2Theme.muted)
        }
        .padding(.horizontal, 7)
        .padding(.vertical, 5)
        .background(WantedV2Theme.surface, in: Capsule())
        .overlay(Capsule().stroke(WantedV2Theme.line, lineWidth: 1))
    }

    private static func clampedAngle(_ text: String) -> Double {
        let value = Double(text.trimmingCharacters(in: .whitespacesAndNewlines)) ?? 0
        return min(90, max(-90, value)).rounded()
    }

    private static func anglePair(_ angle: Double, family: PreviewPly.Family) -> [PreviewPly] {
        [PreviewPly(angle: angle, family: family), PreviewPly(angle: -angle, family: family)]
    }

    private static func inversePair(_ angle: Double, family: PreviewPly.Family) -> [PreviewPly] {
        [PreviewPly(angle: -angle, family: family), PreviewPly(angle: angle, family: family)]
    }

    private static func repeated(_ pattern: [PreviewPly], count: Int) -> [PreviewPly] {
        Array(repeating: pattern, count: count).flatMap { $0 }
    }

    private static func buildSequence(laminateCase: DDLaminateCase, theta1: Double, theta2: Double) -> [PreviewPly] {
        let theta1Pair = anglePair(theta1, family: .theta1)
        let theta2Pair = anglePair(theta2, family: .theta2)
        let theta1Inverse = inversePair(theta1, family: .theta1)
        let theta2Inverse = inversePair(theta2, family: .theta2)

        switch laminateCase {
        case .case3:
            return repeated(theta1Pair + theta2Pair + theta1Inverse + theta2Inverse, count: 2)
        case .case4:
            return repeated(theta1Pair + theta2Pair, count: 2)
                + repeated(theta1Inverse + theta2Inverse, count: 2)
        case .case2:
            return repeated(theta1Pair + theta2Pair, count: 4)
        }
    }
}

private struct PreviewPly: Hashable {
    enum Family {
        case theta1
        case theta2
    }

    let angle: Double
    let family: Family
}

private struct PlyStackCanvas: View {
    let sequence: [PreviewPly]

    var body: some View {
        Canvas { context, size in
            let scale = min(size.width / 1160, size.height / 760)
            let offset = CGPoint(
                x: (size.width - 1160 * scale) / 2,
                y: (size.height - 760 * scale) / 2
            )

            func point(_ x: Double, _ y: Double) -> CGPoint {
                CGPoint(x: offset.x + x * scale, y: offset.y + y * scale)
            }

            func path(_ points: [(Double, Double)]) -> Path {
                var path = Path()
                guard let first = points.first else { return path }
                path.move(to: point(first.0, first.1))
                for next in points.dropFirst() {
                    path.addLine(to: point(next.0, next.1))
                }
                path.closeSubpath()
                return path
            }

            func strokeLine(from start: (Double, Double), to end: (Double, Double), color: Color, width: Double, opacity: Double = 1) {
                var line = Path()
                line.move(to: point(start.0, start.1))
                line.addLine(to: point(end.0, end.1))
                context.stroke(line, with: .color(color.opacity(opacity)), lineWidth: width * scale)
            }

            context.fill(
                Path(roundedRect: CGRect(x: offset.x + 34 * scale, y: offset.y + 34 * scale, width: 1092 * scale, height: 700 * scale), cornerRadius: 8 * scale),
                with: .linearGradient(
                    Gradient(colors: [
                        Color(red: 0.11, green: 0.20, blue: 0.31),
                        Color(red: 0.19, green: 0.29, blue: 0.40),
                        Color(red: 0.54, green: 0.60, blue: 0.66)
                    ]),
                    startPoint: point(34, 34),
                    endPoint: point(1126, 734)
                )
            )

            [
                ((118.0, 42.0), (992.0, 524.0)),
                ((70.0, 94.0), (944.0, 576.0)),
                ((22.0, 146.0), (896.0, 628.0)),
                ((214.0, 660.0), (1088.0, 178.0)),
                ((48.0, 536.0), (742.0, 150.0)),
                ((122.0, 578.0), (816.0, 192.0)),
                ((196.0, 620.0), (890.0, 234.0)),
                ((270.0, 662.0), (964.0, 276.0)),
            ].forEach { line in
                strokeLine(from: line.0, to: line.1, color: .white, width: 1, opacity: 0.18)
            }

            let baseTop = path([(98, 456), (574, 704), (1018, 458), (542, 210)])
            let baseLeft = path([(98, 456), (574, 704), (574, 728), (98, 480)])
            let baseRight = path([(574, 704), (1018, 458), (1018, 482), (574, 728)])
            context.fill(baseTop, with: .color(Color(red: 0.72, green: 0.59, blue: 0.50)))
            context.fill(baseLeft, with: .color(Color(red: 0.78, green: 0.65, blue: 0.56)))
            context.fill(baseRight, with: .color(Color(red: 0.60, green: 0.46, blue: 0.37)))
            context.stroke(baseTop, with: .color(.white.opacity(0.18)), lineWidth: 1 * scale)

            for (index, ply) in sequence.enumerated() {
                drawPly(ply, index: index, context: &context, scale: scale, offset: offset)
            }
        }
    }

    private func drawPly(_ ply: PreviewPly, index: Int, context: inout GraphicsContext, scale: Double, offset: CGPoint) {
        let originX = 555 - Double(index) * 30
        let originY = 470 - Double(index) * 28

        func point(_ x: Double, _ y: Double) -> CGPoint {
            CGPoint(x: offset.x + (originX + x) * scale, y: offset.y + (originY + y) * scale)
        }

        func path(_ points: [(Double, Double)]) -> Path {
            var path = Path()
            guard let first = points.first else { return path }
            path.move(to: point(first.0, first.1))
            for next in points.dropFirst() {
                path.addLine(to: point(next.0, next.1))
            }
            path.closeSubpath()
            return path
        }

        let palette = palette(for: ply.family)
        let top = path([(0, 130), (138, 210), (420, 52), (282, -28)])
        let left = path([(0, 130), (138, 210), (138, 230), (0, 150)])
        let right = path([(138, 210), (420, 52), (420, 72), (138, 230)])

        context.fill(left, with: .color(palette.sideA))
        context.fill(right, with: .color(palette.sideB))
        context.fill(
            top,
            with: .linearGradient(
                Gradient(colors: [palette.topA, palette.topB]),
                startPoint: point(0, 130),
                endPoint: point(420, 52)
            )
        )
        context.stroke(top, with: .color(palette.edge), lineWidth: 1.3 * scale)

        drawAngleHatch(for: ply, clippedTo: top, context: &context, scale: scale, offset: offset, originX: originX, originY: originY)

        let labelX = 426.0
        let labelY = 36.0
        var leader = Path()
        leader.move(to: point(400, 61))
        leader.addLine(to: point(labelX, labelY + 15))
        context.stroke(leader, with: .color(Color.yellow.opacity(0.84)), lineWidth: 2.0 * scale)

        let labelRect = CGRect(
            x: point(labelX, labelY).x,
            y: point(labelX, labelY).y,
            width: 126 * scale,
            height: 34 * scale
        )
        context.fill(Path(roundedRect: labelRect, cornerRadius: 7 * scale), with: .color(Color(red: 0.06, green: 0.13, blue: 0.20).opacity(0.96)))
        context.stroke(Path(roundedRect: labelRect, cornerRadius: 7 * scale), with: .color(.yellow.opacity(0.86)), lineWidth: 1.4 * scale)
        context.draw(
            Text("Ply-\(index + 1)")
                .font(.system(size: 22 * scale, weight: .black))
                .foregroundStyle(.yellow),
            at: CGPoint(x: labelRect.minX + 11 * scale, y: labelRect.midY),
            anchor: .leading
        )
    }

    private func drawAngleHatch(
        for ply: PreviewPly,
        clippedTo top: Path,
        context: inout GraphicsContext,
        scale: Double,
        offset: CGPoint,
        originX: Double,
        originY: Double
    ) {
        let hatchColor = ply.angle >= 0 ? WantedV2Theme.green : WantedV2Theme.red
        let radians = -ply.angle * .pi / 180
        let direction = CGVector(dx: cos(radians), dy: sin(radians))
        let normal = CGVector(dx: -direction.dy, dy: direction.dx)
        let center = CGPoint(x: 210, y: 91)
        let lineLength = 560.0
        let hatchSpacing = 24.0

        func point(_ local: CGPoint) -> CGPoint {
            CGPoint(
                x: offset.x + (originX + local.x) * scale,
                y: offset.y + (originY + local.y) * scale
            )
        }

        context.drawLayer { layerContext in
            layerContext.clip(to: top)
            for step in -18...18 {
                let distance = Double(step) * hatchSpacing
                let midpoint = CGPoint(
                    x: center.x + normal.dx * distance,
                    y: center.y + normal.dy * distance
                )
                let start = CGPoint(
                    x: midpoint.x - direction.dx * lineLength / 2,
                    y: midpoint.y - direction.dy * lineLength / 2
                )
                let end = CGPoint(
                    x: midpoint.x + direction.dx * lineLength / 2,
                    y: midpoint.y + direction.dy * lineLength / 2
                )
                var hatch = Path()
                hatch.move(to: point(start))
                hatch.addLine(to: point(end))
                layerContext.stroke(
                    hatch,
                    with: .color(hatchColor.opacity(0.82)),
                    lineWidth: 3 * scale
                )
            }
        }
    }

    private func palette(for family: PreviewPly.Family) -> (topA: Color, topB: Color, sideA: Color, sideB: Color, edge: Color) {
        switch family {
        case .theta1:
            (
                Color(red: 0.60, green: 0.66, blue: 0.93),
                Color(red: 0.40, green: 0.48, blue: 0.83),
                Color(red: 0.50, green: 0.56, blue: 0.83),
                Color(red: 0.37, green: 0.44, blue: 0.73),
                Color(red: 0.31, green: 0.38, blue: 0.67)
            )
        case .theta2:
            (
                Color(red: 0.88, green: 0.74, blue: 0.63),
                Color(red: 0.74, green: 0.56, blue: 0.44),
                Color(red: 0.79, green: 0.65, blue: 0.55),
                Color(red: 0.65, green: 0.49, blue: 0.39),
                Color(red: 0.56, green: 0.41, blue: 0.31)
            )
        }
    }
}

private enum WantedV2Theme {
    static let background = LinearGradient(
        colors: [
            Color(red: 0.976, green: 0.982, blue: 0.988),
            Color(red: 0.925, green: 0.945, blue: 0.961)
        ],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )
    static let surface = Color.white
    static let field = Color(red: 0.965, green: 0.975, blue: 0.984)
    static let ink = Color(red: 0.063, green: 0.071, blue: 0.082)
    static let muted = Color(red: 0.388, green: 0.443, blue: 0.502)
    static let line = Color(red: 0.855, green: 0.890, blue: 0.925)
    static let blue = Color(red: 0.086, green: 0.388, blue: 1.0)
    static let blueSoft = Color(red: 0.914, green: 0.941, blue: 1.0)
    static let cyan = Color(red: 0.043, green: 0.654, blue: 0.788)
    static let green = Color(red: 0.039, green: 0.624, blue: 0.412)
    static let amber = Color(red: 0.718, green: 0.475, blue: 0.122)
    static let red = Color(red: 0.851, green: 0.176, blue: 0.125)
}

private struct WantedPrimaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.headline.weight(.black))
            .foregroundStyle(.white)
            .padding(.horizontal, 14)
            .padding(.vertical, 15)
            .background(
                LinearGradient(
                    colors: [
                        WantedV2Theme.ink.opacity(configuration.isPressed ? 0.86 : 1),
                        WantedV2Theme.blue.opacity(configuration.isPressed ? 0.76 : 0.98)
                    ],
                    startPoint: .leading,
                    endPoint: .trailing
                ),
                in: RoundedRectangle(cornerRadius: 8, style: .continuous)
            )
            .opacity(configuration.isPressed ? 0.9 : 1)
    }
}

private struct WantedSecondaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.headline.weight(.black))
            .foregroundStyle(WantedV2Theme.blue)
            .padding(.horizontal, 14)
            .padding(.vertical, 13)
            .background(
                WantedV2Theme.blue.opacity(configuration.isPressed ? 0.16 : 0.10),
                in: RoundedRectangle(cornerRadius: 8, style: .continuous)
            )
    }
}
