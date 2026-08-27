import KyulAIDDLaminateCore
import SwiftUI
#if os(iOS)
import UIKit
#endif

#if os(iOS)
private func dismissKeyboard() {
    UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
}
#else
private func dismissKeyboard() {}
#endif

private extension View {
    @ViewBuilder
    func laminateScrollKeyboardDismissal() -> some View {
        #if os(iOS)
        self.scrollDismissesKeyboard(.interactively)
        #else
        self
        #endif
    }
}

private enum ResultDetailTheme {
    static let background = LinearGradient(
        colors: [
            Color(red: 0.976, green: 0.982, blue: 0.988),
            Color(red: 0.925, green: 0.945, blue: 0.961)
        ],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )
    static let card = Color.white
    static let field = Color(red: 0.965, green: 0.975, blue: 0.984)
    static let ink = Color(red: 0.063, green: 0.071, blue: 0.082)
    static let muted = Color(red: 0.388, green: 0.443, blue: 0.502)
    static let line = Color(red: 0.855, green: 0.890, blue: 0.925)
    static let primary = Color(red: 0.086, green: 0.388, blue: 1.0)
    static let accent = Color(red: 0.043, green: 0.654, blue: 0.788)
    static let success = Color(red: 0.039, green: 0.624, blue: 0.412)
    static let warning = Color(red: 0.718, green: 0.475, blue: 0.122)
    static let danger = Color(red: 0.851, green: 0.176, blue: 0.125)
    static let blueSoft = Color(red: 0.914, green: 0.941, blue: 1.0)
}

private struct ResultDetailCard<Content: View>: View {
    @ViewBuilder let content: Content

    var body: some View {
        content
            .padding(16)
            .background(ResultDetailTheme.card, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(ResultDetailTheme.line, lineWidth: 1)
            )
            .shadow(color: .black.opacity(0.045), radius: 14, x: 0, y: 8)
    }
}

private struct ResultDetailSecondaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.headline.weight(.black))
            .foregroundStyle(ResultDetailTheme.primary)
            .padding(.horizontal, 14)
            .padding(.vertical, 13)
            .background(
                ResultDetailTheme.primary.opacity(configuration.isPressed ? 0.16 : 0.10),
                in: RoundedRectangle(cornerRadius: 8, style: .continuous)
            )
    }
}

struct ResultDetailView: View {
    let result: ResponsePredictionResult
    let designSpace: DesignSpaceResponse?
    @EnvironmentObject private var settings: AppSettings

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                heroCard
                metricsGrid
                if let uncertainty = result.uncertainty {
                    PredictionUncertaintyCard(uncertainty: uncertainty)
                }
                if let agreement = result.teacherStudent {
                    TeacherStudentAgreementCard(agreement: agreement)
                }
                curveCard
                interpretationCard
                probabilityCard
                if let xai = result.xai {
                    XAIExplanationCard(xai: xai)
                }
                if let designSpace {
                    ResearchInsightCard(insight: designSpace)
                }
                LaminateAssistantCard(
                    title: localText(en: "Laminate AI Assistant", ko: "적층 AI Assistant"),
                    defaultQuestion: localText(
                        en: "Explain this prediction using the XAI result.",
                        ko: "XAI 결과를 바탕으로 이번 예측을 설명해줘."
                    ),
                    baseURL: settings.parsedBaseURL,
                    languageCode: settings.languageCode,
                    predictionContext: result.assistantContext(mode: "Laminate Response")
                )
                if !result.notes.isEmpty {
                    notesCard
                }
            }
            .padding(20)
        }
        .laminateScrollKeyboardDismissal()
        .background(ResultDetailTheme.background.ignoresSafeArea())
        .navigationTitle(L10n.t("result"))
        .appInlineNavigationTitle()
        .toolbar {
            ShareLink(item: result.shareSummaryText) {
                Image(systemName: "square.and.arrow.up")
            }
            #if os(iOS)
            ShareImageButton(
                fileName: "imperialax-laminate-forecast",
                report: LaminateShareImageReportView(result: result)
            ) {
                Image(systemName: "photo")
            }
            #endif
        }
    }

    private var heroCard: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(alignment: .top, spacing: 14) {
                VStack(alignment: .leading, spacing: 7) {
                    Text(localText(en: "Forecast result", ko: "예측 결과"))
                        .font(.caption.weight(.black))
                        .foregroundStyle(Color(red: 0.64, green: 0.75, blue: 1.0))
                        .textCase(.uppercase)
                    Text(L10n.f("type.format", result.predictedType))
                        .font(.system(size: 48, weight: .black, design: .rounded))
                        .foregroundStyle(.white)
                        .lineLimit(1)
                        .minimumScaleFactor(0.72)
                    Text(result.displayModelLabel)
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.white.opacity(0.74))
                        .lineLimit(2)
                }
                Spacer(minLength: 8)
                VStack(alignment: .trailing, spacing: 4) {
                    Text(localText(en: "Predicted Pt", ko: "예측 Pt"))
                        .font(.caption2.weight(.black))
                        .foregroundStyle(.white.opacity(0.62))
                    Text(result.predictedPt.metricText(digits: 2))
                        .font(.title2.monospacedDigit().weight(.black))
                        .foregroundStyle(Color(red: 0.54, green: 1.0, blue: 0.79))
                        .lineLimit(1)
                        .minimumScaleFactor(0.58)
                }
            }

            HStack(spacing: 8) {
                heroBadge(title: L10n.t("confidence"), value: result.confidence.percentText)
                heroBadge(title: localText(en: "Mode", ko: "모드"), value: result.inputMode.uppercased())
                heroBadge(title: localText(en: "Points", ko: "포인트"), value: "\(result.curve.count)")
            }
        }
        .padding(18)
        .background(
            LinearGradient(
                colors: [
                    ResultDetailTheme.ink,
                    ResultDetailTheme.primary.opacity(0.92)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            ),
            in: RoundedRectangle(cornerRadius: 8, style: .continuous)
        )
        .shadow(color: .black.opacity(0.10), radius: 18, x: 0, y: 10)
    }

    private func heroBadge(title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(title)
                .font(.caption2.weight(.black))
                .foregroundStyle(.white.opacity(0.58))
                .lineLimit(1)
            Text(value)
                .font(.caption.monospacedDigit().weight(.black))
                .foregroundStyle(.white)
                .lineLimit(1)
                .minimumScaleFactor(0.68)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 10)
        .padding(.vertical, 9)
        .background(.white.opacity(0.10), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
    }

    private var metricsGrid: some View {
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
            metricCard(L10n.t("predicted.pt"), result.predictedPt.metricText(digits: 2), "force")
            metricCard(L10n.t("max.force"), result.predictedMaxForce.metricText(digits: 2), "force")
            metricCard(L10n.t("pt.displacement"), result.predictedPtDisplacement?.metricText(digits: 5) ?? "-", "disp.")
            metricCard(L10n.t("curve.points"), "\(result.curve.count)", "samples")
        }
    }

    private func metricCard(_ title: String, _ value: String, _ unit: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.caption.weight(.black))
                .foregroundStyle(ResultDetailTheme.muted)
            Text(value)
                .font(.title3.monospacedDigit().weight(.bold))
                .foregroundStyle(ResultDetailTheme.ink)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
            Text(unit)
                .font(.caption2.weight(.semibold))
                .foregroundStyle(ResultDetailTheme.muted)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(ResultDetailTheme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(ResultDetailTheme.line, lineWidth: 1)
        )
    }

    private func localText(en: String, ko: String) -> String {
        let languageCode = UserDefaults.standard.string(forKey: "kyulai.ddLaminate.languageCode")
            ?? (Locale.current.language.languageCode?.identifier == "ko" ? "ko" : "en")
        return languageCode == "ko" ? ko : en
    }

    private var curveCard: some View {
        ResultDetailCard {
            VStack(alignment: .leading, spacing: 12) {
                sectionHeader(
                    title: L10n.t("response.curve"),
                    subtitle: localText(en: "Predicted curve with Pt marker", ko: "Pt 위치가 표시된 예측 곡선"),
                    icon: "chart.xyaxis.line"
                )
                CurveChartView(points: result.curve, predictedPt: result.predictedPt, curveFit: result.curveFit)
                    .frame(height: 390)
            }
        }
    }

    private var interpretationCard: some View {
        ResultDetailCard {
            VStack(alignment: .leading, spacing: 12) {
                sectionHeader(
                    title: L10n.t("interpretation"),
                    subtitle: localText(en: "Quick reading from predicted values", ko: "예측값 기반 빠른 해석"),
                    icon: "text.magnifyingglass"
                )
                InterpretationSummaryView(result: result, showsHeader: false)
            }
        }
    }

    private var probabilityCard: some View {
        ResultDetailCard {
            VStack(alignment: .leading, spacing: 14) {
                sectionHeader(
                    title: L10n.t("class.probabilities"),
                    subtitle: localText(en: "Model confidence by Type", ko: "Type별 모델 신뢰도"),
                    icon: "chart.bar.fill"
                )
                if result.sortedProbabilities.isEmpty {
                    Text(L10n.t("no.probabilities"))
                        .font(.callout)
                        .foregroundStyle(ResultDetailTheme.muted)
                } else {
                    ForEach(result.sortedProbabilities, id: \.label) { probability in
                        probabilityRow(label: probability.label, value: probability.value)
                    }
                }
            }
        }
    }

    private func probabilityRow(label: String, value: Double) -> some View {
        VStack(alignment: .leading, spacing: 7) {
            HStack {
                Text(label.capitalized)
                    .font(.subheadline.weight(.bold))
                    .foregroundStyle(ResultDetailTheme.ink)
                Spacer()
                Text(Optional(value).percentText)
                    .font(.subheadline.monospacedDigit().weight(.bold))
                    .foregroundStyle(ResultDetailTheme.muted)
            }
            GeometryReader { proxy in
                ZStack(alignment: .leading) {
                    Capsule()
                        .fill(ResultDetailTheme.field)
                    Capsule()
                        .fill(label == "type\(result.predictedType)" ? ResultDetailTheme.primary : ResultDetailTheme.accent.opacity(0.28))
                        .frame(width: max(6, proxy.size.width * min(max(value, 0), 1)))
                }
            }
            .frame(height: 8)
        }
    }

    private func sectionHeader(title: String, subtitle: String, icon: String) -> some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: icon)
                .font(.subheadline.weight(.black))
                .foregroundStyle(ResultDetailTheme.primary)
                .frame(width: 34, height: 34)
                .background(ResultDetailTheme.blueSoft, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            VStack(alignment: .leading, spacing: 3) {
                Text(title)
                    .font(.headline.weight(.black))
                    .foregroundStyle(ResultDetailTheme.ink)
                Text(subtitle)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(ResultDetailTheme.muted)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private var notesCard: some View {
        ResultDetailCard {
            VStack(alignment: .leading, spacing: 12) {
                Label(L10n.t("notes"), systemImage: "exclamationmark.triangle.fill")
                    .font(.headline)
                    .foregroundStyle(ResultDetailTheme.warning)
                ForEach(result.notes, id: \.self) { note in
                    Text(note)
                        .font(.callout)
                        .foregroundStyle(ResultDetailTheme.ink)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
    }
}

struct U3PtResultDetailView: View {
    let result: U3PtPredictionResult
    let designSpace: DesignSpaceResponse?
    @EnvironmentObject private var settings: AppSettings

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                heroCard
                metricsGrid
                if let uncertainty = result.uncertainty {
                    PredictionUncertaintyCard(uncertainty: uncertainty)
                }
                curveCard
                if let xai = result.xai {
                    XAIExplanationCard(xai: xai)
                }
                if let designSpace {
                    ResearchInsightCard(insight: designSpace)
                }
                LaminateAssistantCard(
                    title: localText(en: "u3 AI Assistant", ko: "u3 AI Assistant"),
                    defaultQuestion: localText(
                        en: "Explain why this u3 Pt forecast was predicted.",
                        ko: "이번 u3 Pt 예측이 왜 이렇게 나왔는지 설명해줘."
                    ),
                    baseURL: settings.parsedBaseURL,
                    languageCode: settings.languageCode,
                    predictionContext: result.assistantContext(mode: "u3 Forecast")
                )
                if !result.notes.isEmpty {
                    notesCard
                }
            }
            .padding(20)
        }
        .laminateScrollKeyboardDismissal()
        .background(ResultDetailTheme.background.ignoresSafeArea())
        .navigationTitle(L10n.t("u3.result"))
        .appInlineNavigationTitle()
    }

    private var heroCard: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(alignment: .top, spacing: 14) {
                VStack(alignment: .leading, spacing: 7) {
                    Text(localText(en: "u3 Forecast result", ko: "u3 예측 결과"))
                        .font(.caption.weight(.black))
                        .foregroundStyle(Color(red: 0.64, green: 0.75, blue: 1.0))
                        .textCase(.uppercase)
                    Text(result.predictedPt.metricText(digits: 2))
                        .font(.system(size: 44, weight: .black, design: .rounded))
                        .foregroundStyle(.white)
                        .lineLimit(1)
                        .minimumScaleFactor(0.64)
                    Text(result.displayModelLabel)
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.white.opacity(0.74))
                        .lineLimit(2)
                }
                Spacer(minLength: 8)
                VStack(alignment: .trailing, spacing: 4) {
                    Text(localText(en: "Predicted Type", ko: "예측 Type"))
                        .font(.caption2.weight(.black))
                        .foregroundStyle(.white.opacity(0.62))
                    Text(result.predictedType.map { "Type \($0)" } ?? "Type -")
                        .font(.title3.weight(.black))
                        .foregroundStyle(Color(red: 0.54, green: 1.0, blue: 0.79))
                        .lineLimit(1)
                }
            }

            HStack(spacing: 8) {
                heroBadge(title: localText(en: "Confidence", ko: "신뢰도"), value: result.confidence.percentText)
                heroBadge(title: localText(en: "Mode", ko: "모드"), value: result.inputMode.uppercased())
                heroBadge(title: localText(en: "Points", ko: "포인트"), value: "\(result.curve.count)")
            }
        }
        .padding(18)
        .background(
            LinearGradient(
                colors: [
                    ResultDetailTheme.ink,
                    ResultDetailTheme.primary.opacity(0.92)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            ),
            in: RoundedRectangle(cornerRadius: 8, style: .continuous)
        )
        .shadow(color: .black.opacity(0.10), radius: 18, x: 0, y: 10)
    }

    private func heroBadge(title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(title)
                .font(.caption2.weight(.black))
                .foregroundStyle(.white.opacity(0.58))
                .lineLimit(1)
            Text(value)
                .font(.caption.monospacedDigit().weight(.black))
                .foregroundStyle(.white)
                .lineLimit(1)
                .minimumScaleFactor(0.68)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 10)
        .padding(.vertical, 9)
        .background(.white.opacity(0.10), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
    }

    private var metricsGrid: some View {
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
            metricCard(L10n.t("predicted.pt"), result.predictedPt.metricText(digits: 2), "force")
            metricCard(localText(en: "u3 Type", ko: "u3 Type"), result.predictedType.map { "Type \($0)" } ?? "-", "class")
            metricCard(localText(en: "Type confidence", ko: "Type 신뢰도"), result.confidence.percentText, "prob.")
            metricCard(L10n.t("max.force"), result.predictedMaxForce.metricText(digits: 2), "force")
            metricCard(L10n.t("max.displacement"), result.predictedMaxDisplacement.metricText(digits: 5), "disp.")
        }
    }

    private func metricCard(_ title: String, _ value: String, _ unit: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.caption.weight(.black))
                .foregroundStyle(ResultDetailTheme.muted)
            Text(value)
                .font(.title3.monospacedDigit().weight(.bold))
                .foregroundStyle(ResultDetailTheme.ink)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
            Text(unit)
                .font(.caption2.weight(.semibold))
                .foregroundStyle(ResultDetailTheme.muted)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(ResultDetailTheme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(ResultDetailTheme.line, lineWidth: 1)
        )
    }

    private func localText(en: String, ko: String) -> String {
        let languageCode = UserDefaults.standard.string(forKey: "kyulai.ddLaminate.languageCode")
            ?? (Locale.current.language.languageCode?.identifier == "ko" ? "ko" : "en")
        return languageCode == "ko" ? ko : en
    }

    private var curveCard: some View {
        ResultDetailCard {
            VStack(alignment: .leading, spacing: 12) {
                sectionHeader(
                    title: L10n.t("u3.response.curve"),
                    subtitle: localText(en: "Approximate u3 response with Pt marker", ko: "Pt 위치가 표시된 u3 예측 곡선"),
                    icon: "chart.xyaxis.line"
                )
                CurveChartView(points: result.curve, predictedPt: result.predictedPt, fitMode: .u3, curveFit: result.curveFit)
                    .frame(height: 390)
            }
        }
    }

    private var notesCard: some View {
        ResultDetailCard {
            VStack(alignment: .leading, spacing: 12) {
                Label(L10n.t("notes"), systemImage: "exclamationmark.triangle.fill")
                    .font(.headline)
                    .foregroundStyle(ResultDetailTheme.warning)
                ForEach(result.notes, id: \.self) { note in
                    Text(note)
                        .font(.callout)
                        .foregroundStyle(ResultDetailTheme.ink)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
    }

    private func sectionHeader(title: String, subtitle: String, icon: String) -> some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: icon)
                .font(.subheadline.weight(.black))
                .foregroundStyle(ResultDetailTheme.primary)
                .frame(width: 34, height: 34)
                .background(ResultDetailTheme.blueSoft, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            VStack(alignment: .leading, spacing: 3) {
                Text(title)
                    .font(.headline.weight(.black))
                    .foregroundStyle(ResultDetailTheme.ink)
                Text(subtitle)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(ResultDetailTheme.muted)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

}

private struct LaminateAssistantCard: View {
    let title: String
    let defaultQuestion: String
    let baseURL: URL?
    let languageCode: String
    let predictionContext: [String: String]

    @State private var question = ""
    @State private var answer = ""
    @State private var isAsking = false
    @State private var errorMessage: String?
    @FocusState private var isQuestionFocused: Bool

    private var displayedQuestion: Binding<String> {
        Binding(
            get: { question },
            set: { question = $0 }
        )
    }

    var body: some View {
        ResultDetailCard {
            VStack(alignment: .leading, spacing: 12) {
                Label(title, systemImage: "sparkles")
                    .font(.headline.weight(.black))
                    .foregroundStyle(ResultDetailTheme.ink)
                Text(localText(en: "Ask a research question about this prediction, XAI, or the laminate response.", ko: "이번 예측, XAI, 적층 응답에 대해 질문할 수 있습니다."))
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(ResultDetailTheme.muted)
                    .fixedSize(horizontal: false, vertical: true)

                TextField(defaultQuestion, text: displayedQuestion, axis: .vertical)
                    .lineLimit(3...6)
                    .focused($isQuestionFocused)
                    .submitLabel(.done)
                    .onSubmit {
                        isQuestionFocused = false
                        dismissKeyboard()
                    }
                    .font(.callout)
                    .padding(12)
                    .background(ResultDetailTheme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: 8, style: .continuous)
                            .stroke(ResultDetailTheme.line, lineWidth: 1)
                    )

                Button {
                    isQuestionFocused = false
                    dismissKeyboard()
                    Task { await ask() }
                } label: {
                    HStack {
                        if isAsking {
                            ProgressView()
                        } else {
                            Image(systemName: "paperplane.fill")
                        }
                        Text(isAsking ? localText(en: "Asking...", ko: "질문 중...") : localText(en: "Ask Assistant", ko: "Assistant에게 질문"))
                    }
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(ResultDetailSecondaryButtonStyle())
                .disabled(isAsking)

                if let errorMessage {
                    Text(errorMessage)
                        .font(.caption.weight(.bold))
                        .foregroundStyle(ResultDetailTheme.danger)
                        .fixedSize(horizontal: false, vertical: true)
                        .onTapGesture {
                            isQuestionFocused = false
                            dismissKeyboard()
                        }
                }
                if !answer.isEmpty {
                    Text(answer)
                        .font(.callout)
                        .foregroundStyle(ResultDetailTheme.ink)
                        .lineSpacing(3)
                        .fixedSize(horizontal: false, vertical: true)
                        .padding(12)
                        .background(Color.white.opacity(0.76), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                        .onTapGesture {
                            isQuestionFocused = false
                            dismissKeyboard()
                        }
                }
            }
            .background(
                Color.clear
                    .contentShape(Rectangle())
                    .onTapGesture {
                        isQuestionFocused = false
                        dismissKeyboard()
                    }
            )
        }
    }

    private func ask() async {
        guard let baseURL else {
            errorMessage = localText(en: "Set a valid API URL first.", ko: "먼저 올바른 API URL을 설정해 주세요.")
            return
        }
        let resolvedQuestion = question.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            ? defaultQuestion
            : question.trimmingCharacters(in: .whitespacesAndNewlines)
        isAsking = true
        errorMessage = nil
        defer { isAsking = false }
        do {
            let response = try await DDLaminateAPIClient().answerRag(
                baseURL: baseURL,
                request: RagAnswerRequest(
                    query: resolvedQuestion,
                    topK: 3,
                    useLLM: true,
                    language: languageCode,
                    predictionContext: predictionContext
                )
            )
            answer = response.answer
        } catch {
            errorMessage = localText(en: "Assistant failed: \(error.localizedDescription)", ko: "Assistant 호출 실패: \(error.localizedDescription)")
        }
    }

    private func localText(en: String, ko: String) -> String {
        languageCode == "ko" ? ko : en
    }
}

private extension ResponsePredictionResult {
    func assistantContext(mode: String) -> [String: String] {
        var context = sharedAssistantContext(
            mode: mode,
            predictedType: "Type \(predictedType)",
            predictedPt: predictedPt,
            predictedMaxDisplacement: predictedMaxDisplacement,
            predictedMaxForce: predictedMaxForce,
            modelKey: modelKey,
            modelLabel: displayModelLabel,
            inputMode: inputMode,
            inputs: inputs,
            xai: xai
        )
        context["probabilities"] = sortedProbabilities
            .map { "\($0.label)=\($0.value.formatted(.percent.precision(.fractionLength(1))))" }
            .joined(separator: ", ")
        return context
    }
}

private extension U3PtPredictionResult {
    func assistantContext(mode: String) -> [String: String] {
        sharedAssistantContext(
            mode: mode,
            predictedType: predictedType.map { "Type \($0)" } ?? "Type -",
            predictedPt: predictedPt,
            predictedMaxDisplacement: predictedMaxDisplacement,
            predictedMaxForce: predictedMaxForce,
            modelKey: modelKey,
            modelLabel: displayModelLabel,
            inputMode: inputMode,
            inputs: inputs,
            xai: xai
        )
    }
}

private func sharedAssistantContext(
    mode: String,
    predictedType: String,
    predictedPt: Double,
    predictedMaxDisplacement: Double,
    predictedMaxForce: Double,
    modelKey: String,
    modelLabel: String,
    inputMode: String,
    inputs: [String: JSONValue],
    xai: XAIExplanation?
) -> [String: String] {
    let topFeatures = xai?.topFeatures.prefix(8).map { feature in
        "\(feature.label): importance \(feature.importance.formatted(.percent.precision(.fractionLength(1)))), category \(feature.category), explanation \(feature.explanation)"
    }.joined(separator: " | ") ?? ""
    var context: [String: String] = [
        "mode": mode,
        "model_key": modelKey,
        "model_label": modelLabel,
        "input_mode": inputMode,
        "predicted_type": predictedType,
        "predicted_pt": predictedPt.metricText(digits: 2),
        "predicted_max_displacement": predictedMaxDisplacement.metricText(digits: 5),
        "predicted_max_force": predictedMaxForce.metricText(digits: 2),
        "inputs": inputs
            .sorted { $0.key < $1.key }
            .map { "\($0.key)=\($0.value.assistantText)" }
            .joined(separator: ", "),
    ]
    if let xai {
        context["xai_title"] = xai.title
        context["xai_summary"] = xai.summary
        context["xai_method"] = xai.method
        context["xai_feature_set"] = xai.featureSet
        context["xai_top_features"] = topFeatures
    }
    return context
}

private extension JSONValue {
    var assistantText: String {
        switch self {
        case .string(let string):
            return string
        case .double(let double):
            return double.metricText(digits: 5)
        case .bool(let bool):
            return bool ? "true" : "false"
        case .null:
            return "null"
        }
    }
}

struct ResearchInsightCard: View {
    let insight: DesignSpaceResponse

    private var topCandidate: DesignSpaceRecommendation? {
        insight.recommendations.first
    }

    var body: some View {
        ResultDetailCard {
            VStack(alignment: .leading, spacing: 14) {
                Label(localText(en: "Research insight", ko: "연구 인사이트"), systemImage: "point.3.connected.trianglepath.dotted")
                    .font(.headline)
                    .foregroundStyle(ResultDetailTheme.ink)

                if let topCandidate {
                    VStack(alignment: .leading, spacing: 10) {
                        comparisonRows(topCandidate)
                        scoreBreakdown(topCandidate)
                        if !insight.mapPoints.isEmpty {
                            DesignSpaceMapView(insight: insight, topCandidate: topCandidate)
                        }
                    }
                } else {
                    Text(localText(en: "No candidate recommendation is available for this point.", ko: "이 입력점에 대한 추천 후보가 없습니다."))
                        .font(.callout)
                        .foregroundStyle(ResultDetailTheme.muted)
                }

                if !insight.caseInsights.isEmpty {
                    VStack(alignment: .leading, spacing: 10) {
                        Text(localText(en: "Case behavior zones", ko: "Case별 유리 영역"))
                            .font(.subheadline.weight(.bold))
                            .foregroundStyle(ResultDetailTheme.ink)
                        ForEach(insight.caseInsights.prefix(3)) { item in
                            caseInsightRow(item)
                        }
                    }
                }

                ForEach(insight.notes.prefix(2), id: \.self) { note in
                    Text(note)
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(ResultDetailTheme.muted)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
    }

    private func comparisonRows(_ candidate: DesignSpaceRecommendation) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(localText(en: "Current input vs top candidate", ko: "현재 입력 vs 추천 후보"))
                .font(.subheadline.weight(.bold))
                .foregroundStyle(ResultDetailTheme.ink)
            insightRow(
                title: localText(en: "Current input", ko: "현재 입력"),
                subtitle: inputSummary,
                metric: localText(en: "Design-space point", ko: "Design-space 위치"),
                tint: ResultDetailTheme.muted
            )
            insightRow(
                title: localText(en: "Top candidate", ko: "추천 후보"),
                subtitle: "\(caseLabel(candidate.case)) · θ₁ \(angleText(candidate.theta1)) · θ₂ \(angleText(candidate.theta2))",
                metric: "\(localText(en: "Expected Pt", ko: "예상 Pt")) \(candidate.expectedPt.metricText(digits: 2)) · \(typeText(candidate.observedType))",
                tint: ResultDetailTheme.primary
            )
        }
    }

    private func insightRow(title: String, subtitle: String, metric: String, tint: Color) -> some View {
        HStack(alignment: .top, spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.caption.weight(.bold))
                    .foregroundStyle(tint)
                Text(subtitle)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(ResultDetailTheme.ink)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 8)
            Text(metric)
                .font(.caption2.weight(.bold))
                .foregroundStyle(ResultDetailTheme.muted)
                .multilineTextAlignment(.trailing)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(10)
        .background(ResultDetailTheme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
    }

    private func scoreBreakdown(_ candidate: DesignSpaceRecommendation) -> some View {
        let items: [(String, Double)] = [
            (localText(en: "Pt", ko: "Pt"), candidate.scoreComponents.pt),
            (localText(en: "Type", ko: "Type"), candidate.scoreComponents.type),
            (localText(en: "Distance", ko: "거리"), candidate.scoreComponents.proximity),
            (localText(en: "Total", ko: "총점"), candidate.score),
        ]
        return VStack(alignment: .leading, spacing: 8) {
            Text(localText(en: "Recommendation score", ko: "추천 점수"))
                .font(.caption.weight(.bold))
                .foregroundStyle(ResultDetailTheme.muted)
            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 8) {
                ForEach(items, id: \.0) { item in
                    VStack(alignment: .leading, spacing: 4) {
                        Text(item.0)
                            .font(.caption2.weight(.bold))
                            .foregroundStyle(ResultDetailTheme.muted)
                        Text(item.1.formatted(.percent.precision(.fractionLength(1))))
                            .font(.caption.monospacedDigit().weight(.black))
                            .foregroundStyle(ResultDetailTheme.primary)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(9)
                    .background(ResultDetailTheme.primary.opacity(0.08), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                }
            }
        }
    }

    private func caseInsightRow(_ item: DesignSpaceCaseInsight) -> some View {
        let tint = caseAccent(item.case)
        return VStack(alignment: .leading, spacing: 11) {
            HStack(alignment: .center, spacing: 8) {
                Text(caseLabel(item.case))
                    .font(.caption.weight(.black))
                    .foregroundStyle(.white)
                    .padding(.horizontal, 9)
                    .padding(.vertical, 5)
                    .background(tint, in: Capsule())
                Text(focusKindLabel(item.focusKind))
                    .font(.caption2.weight(.bold))
                    .foregroundStyle(tint)
                    .lineLimit(1)
                Spacer(minLength: 8)
                Text(item.focusRate.formatted(.percent.precision(.fractionLength(1))))
                    .font(.caption.monospacedDigit().weight(.black))
                    .foregroundStyle(tint)
            }

            VStack(alignment: .leading, spacing: 6) {
                Text(localText(en: "Theta range", ko: "Theta 범위"))
                    .font(.caption2.weight(.black))
                    .foregroundStyle(ResultDetailTheme.muted)
                HStack(spacing: 8) {
                    thetaRangeChip(label: "θ₁", lower: item.theta1Min, upper: item.theta1Max, tint: tint)
                    thetaRangeChip(label: "θ₂", lower: item.theta2Min, upper: item.theta2Max, tint: tint)
                }
            }

            HStack(alignment: .firstTextBaseline, spacing: 10) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(localText(en: "Best Pt", ko: "최고 Pt"))
                        .font(.caption2.weight(.bold))
                        .foregroundStyle(ResultDetailTheme.muted)
                    Text(item.bestPt?.metricText(digits: 2) ?? "-")
                        .font(.caption.monospacedDigit().weight(.black))
                        .foregroundStyle(ResultDetailTheme.ink)
                }
                Spacer(minLength: 8)
                VStack(alignment: .trailing, spacing: 2) {
                    Text(typeText(item.bestType))
                        .font(.caption.weight(.black))
                        .foregroundStyle(tint)
                    Text("\(item.focusCount)/\(item.count)")
                        .font(.caption2.monospacedDigit().weight(.bold))
                        .foregroundStyle(ResultDetailTheme.muted)
                }
            }
        }
        .padding(12)
        .background(
            LinearGradient(
                colors: [
                    tint.opacity(0.16),
                    tint.opacity(0.07)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            ),
            in: RoundedRectangle(cornerRadius: 8, style: .continuous)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(tint.opacity(0.34), lineWidth: 1)
        )
    }

    private func thetaRangeChip(label: String, lower: Double?, upper: Double?, tint: Color) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(label)
                .font(.caption2.weight(.black))
                .foregroundStyle(tint)
            Text(rangeText(lower, upper))
                .font(.caption.monospacedDigit().weight(.black))
                .foregroundStyle(ResultDetailTheme.ink)
                .lineLimit(1)
                .minimumScaleFactor(0.72)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(Color.white.opacity(0.82), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(tint.opacity(0.22), lineWidth: 1)
        )
    }

    private func caseAccent(_ laminateCase: DDLaminateCase) -> Color {
        switch laminateCase {
        case .case2:
            return ResultDetailTheme.primary
        case .case3:
            return ResultDetailTheme.accent
        case .case4:
            return ResultDetailTheme.warning
        }
    }

    private var inputSummary: String {
        let theta1 = inputDouble("theta1").map(angleText) ?? "-"
        let theta2 = inputDouble("theta2").map(angleText) ?? "-"
        let caseName = inputString("case").map(caseDisplayLabel) ?? "-"
        return "\(caseName) · θ₁ \(theta1) · θ₂ \(theta2)"
    }

    private func inputDouble(_ key: String) -> Double? {
        guard let value = insight.inputs[key] else { return nil }
        switch value {
        case .double(let double):
            return double
        case .string(let string):
            return Double(string)
        case .bool, .null:
            return nil
        }
    }

    private func inputString(_ key: String) -> String? {
        guard let value = insight.inputs[key] else { return nil }
        switch value {
        case .string(let string):
            return string
        case .double(let double):
            return double.metricText(digits: 0)
        case .bool(let bool):
            return bool ? "true" : "false"
        case .null:
            return nil
        }
    }

    private func rangeText(_ lower: Double?, _ upper: Double?) -> String {
        guard let lower, let upper else { return "-" }
        return "\(angleText(lower)) ~ \(angleText(upper))"
    }

    private func typeText(_ value: Int?) -> String {
        guard let value else { return "Type -" }
        return "Type \(value)"
    }

    private func angleText(_ value: Double) -> String {
        value.formatted(.number.sign(strategy: .always()).precision(.fractionLength(0))) + "°"
    }

    private func caseLabel(_ laminateCase: DDLaminateCase) -> String {
        caseDisplayLabel(laminateCase.rawValue)
    }

    private func caseDisplayLabel(_ rawValue: String) -> String {
        switch rawValue {
        case "Case2":
            return "Case 2"
        case "Case3":
            return "Case 3"
        case "Case4":
            return "Case 4"
        default:
            return rawValue
        }
    }

    private func focusKindLabel(_ rawValue: String) -> String {
        switch rawValue {
        case "type1":
            return localText(en: "Type 1 zone", ko: "Type 1 영역")
        case "high_pt":
            return localText(en: "High Pt zone", ko: "높은 Pt 영역")
        default:
            return rawValue
        }
    }

    private func localText(en: String, ko: String) -> String {
        let languageCode = UserDefaults.standard.string(forKey: "kyulai.ddLaminate.languageCode")
            ?? (Locale.current.language.languageCode?.identifier == "ko" ? "ko" : "en")
        return languageCode == "ko" ? ko : en
    }
}

private struct DesignSpaceMapView: View {
    let insight: DesignSpaceResponse
    let topCandidate: DesignSpaceRecommendation?

    @State private var selectedPoint: DesignSpacePoint?

    private let mapSize = CGSize(width: 540, height: 230)

    private var currentTheta1: Double? {
        inputDouble("theta1")
    }

    private var currentTheta2: Double? {
        inputDouble("theta2")
    }

    private var currentCase: DDLaminateCase? {
        inputString("case").flatMap(DDLaminateCase.init(rawValue:))
    }

    private var maxPt: Double {
        max(insight.mapPoints.map(\.pt).max() ?? 1, 1)
    }

    private var nearbyPoints: [DesignSpacePoint] {
        Array(insight.mapPoints.sorted { $0.distance < $1.distance }.prefix(6))
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(localText(en: "Design-space map", ko: "Design-space 맵"))
                    .font(.caption.weight(.bold))
                    .foregroundStyle(ResultDetailTheme.muted)
                Spacer()
                Text(localText(en: "Tap dots or rows · scroll map", ko: "점을 누르거나 목록 선택 · 맵 스크롤"))
                    .font(.caption2.weight(.bold))
                    .foregroundStyle(ResultDetailTheme.primary)
            }

            ScrollView(.horizontal, showsIndicators: true) {
                Canvas { context, size in
                    drawMap(context: &context, size: size)
                }
                .frame(width: mapSize.width, height: mapSize.height)
                .contentShape(Rectangle())
                .highPriorityGesture(
                    SpatialTapGesture()
                        .onEnded { value in
                            selectedPoint = nearestPoint(to: value.location, size: mapSize)
                        }
                )
                .padding(8)
                .background(ResultDetailTheme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            }
            .frame(maxWidth: .infinity)

            selectedPointPanel
            nearestPointRows

            LazyVGrid(columns: [GridItem(.adaptive(minimum: 86), spacing: 8)], alignment: .leading, spacing: 6) {
                legendItem(label: "Type 1", color: ResultDetailTheme.success)
                legendItem(label: "Type 2", color: ResultDetailTheme.primary)
                legendItem(label: "Type 3", color: ResultDetailTheme.danger)
                legendItem(label: localText(en: "Current", ko: "현재 입력"), color: Color.purple)
                legendItem(label: localText(en: "Candidate", ko: "추천 후보"), color: ResultDetailTheme.accent)
            }
        }
        .onAppear {
            if selectedPoint == nil {
                selectedPoint = nearbyPoints.first
            }
        }
    }

    @ViewBuilder
    private var selectedPointPanel: some View {
        if let selectedPoint {
            VStack(alignment: .leading, spacing: 4) {
                Text("\(caseLabel(selectedPoint.case)) · \(selectedPoint.testId)")
                    .font(.caption.weight(.black))
                    .foregroundStyle(ResultDetailTheme.ink)
                Text("θ₁ \(angleText(selectedPoint.theta1)) · θ₂ \(angleText(selectedPoint.theta2)) · Pt \(selectedPoint.pt.metricText(digits: 2)) · \(typeText(selectedPoint.type))")
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(ResultDetailTheme.muted)
                    .fixedSize(horizontal: false, vertical: true)
                Text("\(localText(en: "Distance", ko: "거리")) \(selectedPoint.distance.metricText(digits: 2))")
                    .font(.caption2.monospacedDigit().weight(.semibold))
                    .foregroundStyle(ResultDetailTheme.muted)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(10)
            .background(ResultDetailTheme.primary.opacity(0.08), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(typeColor(selectedPoint.type).opacity(0.32), lineWidth: 1)
            )
        } else {
            Text(localText(
                en: "Tap a dot to inspect Case, θ values, Pt, Type, and Test ID.",
                ko: "점을 누르면 Case, θ 값, Pt, Type, Test ID를 확인할 수 있습니다."
            ))
            .font(.caption2.weight(.semibold))
            .foregroundStyle(ResultDetailTheme.muted)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(10)
            .background(ResultDetailTheme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        }
    }

    @ViewBuilder
    private var nearestPointRows: some View {
        if !nearbyPoints.isEmpty {
            VStack(alignment: .leading, spacing: 6) {
                Text(localText(en: "Nearest experiment points", ko: "가까운 실험 포인트"))
                    .font(.caption2.weight(.bold))
                    .foregroundStyle(ResultDetailTheme.muted)
                ForEach(Array(nearbyPoints.enumerated()), id: \.offset) { _, point in
                    Button {
                        selectedPoint = point
                    } label: {
                        HStack(spacing: 8) {
                            Circle()
                                .fill(typeColor(point.type))
                                .frame(width: 8, height: 8)
                            VStack(alignment: .leading, spacing: 2) {
                                Text("\(caseLabel(point.case)) · \(point.testId)")
                                    .font(.caption2.weight(.black))
                                    .foregroundStyle(ResultDetailTheme.ink)
                                Text("θ₁ \(angleText(point.theta1)) · θ₂ \(angleText(point.theta2)) · Pt \(point.pt.metricText(digits: 2))")
                                    .font(.caption2.monospacedDigit().weight(.semibold))
                                    .foregroundStyle(ResultDetailTheme.muted)
                                    .lineLimit(1)
                                    .minimumScaleFactor(0.78)
                            }
                            Spacer(minLength: 8)
                            Text(typeText(point.type))
                                .font(.caption2.weight(.bold))
                                .foregroundStyle(typeColor(point.type))
                        }
                        .padding(.horizontal, 10)
                        .padding(.vertical, 8)
                        .background(
                            pointKey(point) == selectedPoint.map { pointKey($0) }
                                ? ResultDetailTheme.primary.opacity(0.12)
                                : ResultDetailTheme.field,
                            in: RoundedRectangle(cornerRadius: 8, style: .continuous)
                        )
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private func drawMap(context: inout GraphicsContext, size: CGSize) {
        let padding = EdgeInsets(top: 16, leading: 34, bottom: 30, trailing: 14)
        let plot = CGRect(
            x: padding.leading,
            y: padding.top,
            width: max(1, size.width - padding.leading - padding.trailing),
            height: max(1, size.height - padding.top - padding.bottom)
        )

        var plotBackground = Path()
        plotBackground.addRect(plot)
        context.fill(plotBackground, with: .color(Color.white.opacity(0.74)))

        for tick in stride(from: -90, through: 90, by: 45) {
            var grid = Path()
            grid.move(to: CGPoint(x: x(Double(tick), in: plot), y: plot.minY))
            grid.addLine(to: CGPoint(x: x(Double(tick), in: plot), y: plot.maxY))
            grid.move(to: CGPoint(x: plot.minX, y: y(Double(tick), in: plot)))
            grid.addLine(to: CGPoint(x: plot.maxX, y: y(Double(tick), in: plot)))
            context.stroke(grid, with: .color(ResultDetailTheme.muted.opacity(0.16)), lineWidth: 1)

            context.draw(
                Text("\(tick)")
                    .font(.caption2)
                    .foregroundStyle(ResultDetailTheme.muted),
                at: CGPoint(x: x(Double(tick), in: plot), y: plot.maxY + 13),
                anchor: .center
            )
            context.draw(
                Text("\(tick)")
                    .font(.caption2)
                    .foregroundStyle(ResultDetailTheme.muted),
                at: CGPoint(x: plot.minX - 9, y: y(Double(tick), in: plot)),
                anchor: .trailing
            )
        }

        var border = Path()
        border.addRect(plot)
        context.stroke(border, with: .color(ResultDetailTheme.muted.opacity(0.35)), lineWidth: 1)

        for point in insight.mapPoints {
            let pointCenter = pointCenter(point, plot: plot)
            let sameCase = currentCase.map { $0 == point.case } ?? true
            let radius = 2.3 + 3.2 * clamp(point.pt / maxPt)
            var dot = Path()
            dot.addEllipse(in: CGRect(
                x: pointCenter.x - radius,
                y: pointCenter.y - radius,
                width: radius * 2,
                height: radius * 2
            ))
            context.fill(
                dot,
                with: .color(typeColor(point.type).opacity(sameCase ? 0.72 : 0.22))
            )
        }

        if let selectedPoint {
            let center = pointCenter(selectedPoint, plot: plot)
            var selection = Path()
            selection.addEllipse(in: CGRect(x: center.x - 12, y: center.y - 12, width: 24, height: 24))
            context.stroke(selection, with: .color(ResultDetailTheme.ink.opacity(0.62)), lineWidth: 2.2)
        }

        if let topCandidate {
            drawCandidate(
                context: &context,
                center: CGPoint(x: x(topCandidate.theta1, in: plot), y: y(topCandidate.theta2, in: plot))
            )
        }

        if let currentTheta1, let currentTheta2 {
            drawCurrentInput(
                context: &context,
                center: CGPoint(x: x(currentTheta1, in: plot), y: y(currentTheta2, in: plot))
            )
        }

        context.draw(
            Text("θ₁")
                .font(.caption2.weight(.bold))
                .foregroundStyle(ResultDetailTheme.muted),
            at: CGPoint(x: plot.midX, y: size.height - 5),
            anchor: .center
        )
        context.draw(
            Text("θ₂")
                .font(.caption2.weight(.bold))
                .foregroundStyle(ResultDetailTheme.muted),
            at: CGPoint(x: 10, y: plot.midY),
            anchor: .center
        )
    }

    private func nearestPoint(to location: CGPoint, size: CGSize) -> DesignSpacePoint? {
        let padding = EdgeInsets(top: 16, leading: 34, bottom: 30, trailing: 14)
        let plot = CGRect(
            x: padding.leading,
            y: padding.top,
            width: max(1, size.width - padding.leading - padding.trailing),
            height: max(1, size.height - padding.top - padding.bottom)
        )
        let nearest = insight.mapPoints
            .map { point in
                let center = pointCenter(point, plot: plot)
                return (point, hypot(center.x - location.x, center.y - location.y))
            }
            .min { $0.1 < $1.1 }
        guard let nearest, nearest.1 <= 48 else { return nil }
        return nearest.0
    }

    private func pointKey(_ point: DesignSpacePoint) -> String {
        "\(point.case.rawValue)-\(point.testId)-\(point.theta1)-\(point.theta2)"
    }

    private func pointCenter(_ point: DesignSpacePoint, plot: CGRect) -> CGPoint {
        CGPoint(x: x(point.theta1, in: plot), y: y(point.theta2, in: plot))
    }

    private func x(_ value: Double, in plot: CGRect) -> CGFloat {
        plot.minX + CGFloat(clamp((value + 90) / 180)) * plot.width
    }

    private func y(_ value: Double, in plot: CGRect) -> CGFloat {
        plot.maxY - CGFloat(clamp((value + 90) / 180)) * plot.height
    }

    private func drawCurrentInput(context: inout GraphicsContext, center: CGPoint) {
        var halo = Path()
        halo.addEllipse(in: CGRect(x: center.x - 9, y: center.y - 9, width: 18, height: 18))
        context.fill(halo, with: .color(Color.white.opacity(0.92)))
        context.stroke(halo, with: .color(Color.purple.opacity(0.35)), lineWidth: 5)

        var marker = Path()
        marker.addEllipse(in: CGRect(x: center.x - 5, y: center.y - 5, width: 10, height: 10))
        context.fill(marker, with: .color(Color.purple))
    }

    private func drawCandidate(context: inout GraphicsContext, center: CGPoint) {
        let radius: CGFloat = 8
        var diamond = Path()
        diamond.move(to: CGPoint(x: center.x, y: center.y - radius))
        diamond.addLine(to: CGPoint(x: center.x + radius, y: center.y))
        diamond.addLine(to: CGPoint(x: center.x, y: center.y + radius))
        diamond.addLine(to: CGPoint(x: center.x - radius, y: center.y))
        diamond.closeSubpath()
        context.fill(diamond, with: .color(Color.white.opacity(0.90)))
        context.stroke(diamond, with: .color(ResultDetailTheme.accent), lineWidth: 2.4)
    }

    private func legendItem(label: String, color: Color) -> some View {
        HStack(spacing: 6) {
            Circle()
                .fill(color)
                .frame(width: 8, height: 8)
            Text(label)
                .font(.caption2.weight(.semibold))
                .foregroundStyle(ResultDetailTheme.muted)
                .lineLimit(1)
        }
    }

    private func typeColor(_ type: Int?) -> Color {
        switch type {
        case 1:
            return ResultDetailTheme.success
        case 2:
            return ResultDetailTheme.primary
        case 3:
            return ResultDetailTheme.danger
        default:
            return ResultDetailTheme.muted
        }
    }

    private func typeText(_ value: Int?) -> String {
        guard let value else { return "Type -" }
        return "Type \(value)"
    }

    private func angleText(_ value: Double) -> String {
        value.formatted(.number.sign(strategy: .always()).precision(.fractionLength(0))) + "°"
    }

    private func caseLabel(_ laminateCase: DDLaminateCase) -> String {
        switch laminateCase {
        case .case2:
            return "Case 2"
        case .case3:
            return "Case 3"
        case .case4:
            return "Case 4"
        }
    }

    private func clamp(_ value: Double) -> Double {
        min(max(value, 0), 1)
    }

    private func inputDouble(_ key: String) -> Double? {
        guard let value = insight.inputs[key] else { return nil }
        switch value {
        case .double(let double):
            return double
        case .string(let string):
            return Double(string)
        case .bool, .null:
            return nil
        }
    }

    private func inputString(_ key: String) -> String? {
        guard let value = insight.inputs[key] else { return nil }
        switch value {
        case .string(let string):
            return string
        case .double(let double):
            return double.metricText(digits: 0)
        case .bool(let bool):
            return bool ? "true" : "false"
        case .null:
            return nil
        }
    }

    private func localText(en: String, ko: String) -> String {
        let languageCode = UserDefaults.standard.string(forKey: "kyulai.ddLaminate.languageCode")
            ?? (Locale.current.language.languageCode?.identifier == "ko" ? "ko" : "en")
        return languageCode == "ko" ? ko : en
    }
}

struct PredictionUncertaintyCard: View {
    let uncertainty: PredictionUncertainty

    private func localText(en: String, ko: String) -> String {
        let languageCode = UserDefaults.standard.string(forKey: "kyulai.ddLaminate.languageCode")
            ?? (Locale.current.language.languageCode?.identifier == "ko" ? "ko" : "en")
        return languageCode == "ko" ? ko : en
    }

    private var badgeText: String {
        switch uncertainty.confidenceLabel {
        case "high": return localText(en: "High confidence", ko: "높은 신뢰")
        case "medium": return localText(en: "Medium confidence", ko: "중간 신뢰")
        default: return localText(en: "Use caution", ko: "주의 필요")
        }
    }

    private var coverageText: String {
        switch uncertainty.interpolationLabel {
        case "interpolation": return localText(en: "Interpolation", ko: "보간 영역")
        case "near-edge": return localText(en: "Near edge", ko: "경계 근처")
        default: return localText(en: "Extrapolation", ko: "외삽 주의")
        }
    }

    var body: some View {
        ResultDetailCard {
            VStack(alignment: .leading, spacing: 12) {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 3) {
                        Text(localText(en: "Confidence", ko: "신뢰도"))
                            .font(.caption.weight(.black))
                            .foregroundStyle(ResultDetailTheme.primary)
                            .textCase(.uppercase)
                        Text(localText(en: "Prediction reliability", ko: "예측 안정성"))
                            .font(.headline.weight(.black))
                            .foregroundStyle(ResultDetailTheme.ink)
                    }
                    Spacer()
                    Text(badgeText)
                        .font(.caption.weight(.black))
                        .foregroundStyle(badgeColor)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 7)
                        .background(badgeColor.opacity(0.14), in: Capsule())
                }

                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                    uncertaintyMetric(localText(en: "Reliability", ko: "종합 신뢰도"), Optional(uncertainty.reliabilityScore).percentText)
                    uncertaintyMetric(localText(en: "Pt range", ko: "Pt 예상 범위"), ptRangeText)
                    uncertaintyMetric(localText(en: "Coverage", ko: "커버리지"), coverageText)
                    uncertaintyMetric(localText(en: "Type agreement", ko: "Type 일치도"), uncertainty.typeConsistency.percentText)
                }

                ForEach(uncertainty.notes.prefix(2), id: \.self) { note in
                    Text(localizedNote(note))
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(ResultDetailTheme.muted)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
    }

    private var badgeColor: Color {
        switch uncertainty.confidenceLabel {
        case "high": return ResultDetailTheme.success
        case "medium": return ResultDetailTheme.warning
        default: return ResultDetailTheme.danger
        }
    }

    private var ptRangeText: String {
        guard let low = uncertainty.ptIntervalLow, let high = uncertainty.ptIntervalHigh else { return "-" }
        return "\(low.metricText(digits: 0)) - \(high.metricText(digits: 0))"
    }

    private func uncertaintyMetric(_ title: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(title)
                .font(.caption.weight(.black))
                .foregroundStyle(ResultDetailTheme.muted)
            Text(value)
                .font(.subheadline.monospacedDigit().weight(.black))
                .foregroundStyle(ResultDetailTheme.ink)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(11)
        .background(ResultDetailTheme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(ResultDetailTheme.line, lineWidth: 1)
        )
    }

    private func localizedNote(_ note: String) -> String {
        let map = [
            "Reliability combines model confidence, distance to nearby curated simulations, and local Type agreement.":
                localText(en: note, ko: "종합 신뢰도는 모델 확률, 가까운 curated 해석 데이터와의 거리, 주변 Type 일치도를 함께 반영합니다."),
            "Pt interval is a screening band from nearby Pt scatter, not a formal statistical confidence interval.":
                localText(en: note, ko: "Pt 범위는 주변 Pt 산포 기반의 screening band이며, 엄밀한 통계적 신뢰구간은 아닙니다."),
            "This theta/case input is within a well-covered region of the observed design space.":
                localText(en: note, ko: "현재 θ/Case 입력은 관측된 설계 공간 안에서 비교적 잘 커버된 영역에 있습니다."),
            "This theta/case input is close to the edge of the observed design space.":
                localText(en: note, ko: "현재 θ/Case 입력은 관측된 설계 공간의 경계에 가까운 편입니다."),
            "This theta/case input is far from nearby curated simulations; validate before treating the recommendation as stable.":
                localText(en: note, ko: "현재 θ/Case 입력은 가까운 curated 해석 데이터에서 멀어, 안정적인 추천으로 보기 전에 검증이 필요합니다."),
        ]
        return map[note] ?? note
    }
}

public struct TeacherStudentAgreementCard: View {
    public let agreement: TeacherStudentAgreement

    public init(agreement: TeacherStudentAgreement) {
        self.agreement = agreement
    }

    private func localText(en: String, ko: String) -> String {
        let languageCode = UserDefaults.standard.string(forKey: "kyulai.ddLaminate.languageCode")
            ?? (Locale.current.language.languageCode?.identifier == "ko" ? "ko" : "en")
        return languageCode == "ko" ? ko : en
    }

    private var badgeText: String {
        switch agreement.confidenceLabel {
        case "high": return localText(en: "High agreement", ko: "높은 일치")
        case "medium": return localText(en: "Medium agreement", ko: "중간 일치")
        default: return localText(en: "Low agreement", ko: "낮은 일치")
        }
    }

    private var badgeColor: Color {
        switch agreement.confidenceLabel {
        case "high": return ResultDetailTheme.success
        case "medium": return ResultDetailTheme.warning
        default: return ResultDetailTheme.danger
        }
    }

    private var typeText: String {
        if agreement.typeAgreement {
            return "\(localText(en: "Match", ko: "일치")) · Type \(agreement.teacher.predictedType)"
        }
        return "\(localText(en: "Mismatch", ko: "불일치")) · T\(agreement.teacher.predictedType) / S\(agreement.student.predictedType)"
    }

    public var body: some View {
        ResultDetailCard {
            VStack(alignment: .leading, spacing: 12) {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 3) {
                        Text(localText(en: "Agreement", ko: "모델 일치도"))
                            .font(.caption.weight(.black))
                            .foregroundStyle(ResultDetailTheme.primary)
                            .textCase(.uppercase)
                        Text(localText(en: "Tree vs Student agreement", ko: "Tree vs Student 일치도"))
                            .font(.headline.weight(.black))
                            .foregroundStyle(ResultDetailTheme.ink)
                    }
                    Spacer()
                    Text(badgeText)
                        .font(.caption.weight(.black))
                        .foregroundStyle(badgeColor)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 7)
                        .background(badgeColor.opacity(0.14), in: Capsule())
                }

                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                    agreementMetric(localText(en: "Agreement", ko: "종합 일치도"), Optional(agreement.agreementScore).percentText)
                    agreementMetric(localText(en: "Type comparison", ko: "Type 비교"), typeText)
                    agreementMetric(localText(en: "Pt delta", ko: "Pt 차이"), "\(agreement.ptDelta.metricText(digits: 0)) (\(Optional(agreement.ptDeltaPercent).percentText))")
                    agreementMetric(localText(en: "Curve delta", ko: "곡선 차이"), agreement.curveNormRmse.map { "\(($0 * 100).metricText(digits: 2))%" } ?? "-")
                }

                Text("\(localText(en: "Student", ko: "Student")): Type \(agreement.student.predictedType), Pt \(agreement.student.predictedPt.metricText(digits: 0))")
                    .font(.caption.weight(.black))
                    .foregroundStyle(ResultDetailTheme.ink)

                ForEach(agreement.notes.prefix(2), id: \.self) { note in
                    Text(localizedNote(note))
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(ResultDetailTheme.muted)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
    }

    private func agreementMetric(_ title: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(title)
                .font(.caption.weight(.black))
                .foregroundStyle(ResultDetailTheme.muted)
            Text(value)
                .font(.subheadline.monospacedDigit().weight(.black))
                .foregroundStyle(ResultDetailTheme.ink)
                .lineLimit(2)
                .minimumScaleFactor(0.72)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(11)
        .background(ResultDetailTheme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(ResultDetailTheme.line, lineWidth: 1)
        )
    }

    private func localizedNote(_ note: String) -> String {
        let map = [
            "Teacher is the deployment Tree model; Student is the distilled Hybrid neural model.":
                localText(en: note, ko: "Teacher는 배포 기본 Tree 모델이고, Student는 distillation 기반 Hybrid 신경망 모델입니다."),
            "Agreement compares Type, Pt, max force, and response-curve shape for the same theta/case input.":
                localText(en: note, ko: "같은 θ/Case 입력에 대해 Type, Pt, 최대 하중, 응답 곡선 형태가 얼마나 일치하는지 비교합니다."),
            "Tree and Student disagree on Type, so validate this candidate before treating the classification as stable.":
                localText(en: note, ko: "Tree와 Student의 Type 예측이 달라서, 안정적인 분류로 보기 전에 추가 검증이 필요합니다."),
            "Type agrees, but Pt differs by more than 8%; treat the Pt estimate as a screening value.":
                localText(en: note, ko: "Type은 일치하지만 Pt 차이가 8%를 넘어, Pt 값은 screening 용도로 해석하는 것이 좋습니다."),
            "Tree and Student are locally consistent, which supports using this result as an early screening candidate.":
                localText(en: note, ko: "Tree와 Student가 일관된 결과를 보여, 초기 screening 후보로 활용하기에 비교적 안정적입니다."),
            "Teacher/Student agreement is included as a deployment consistency check, not as a replacement for simulation validation.":
                localText(en: note, ko: "Teacher/Student 일치도는 배포용 일관성 체크이며, 최종 해석 검증을 대체하지는 않습니다."),
        ]
        return map[note] ?? note
    }
}

struct XAIExplanationCard: View {
    let xai: XAIExplanation
    @State private var isShowingAllFeatures = false

    private let visibleFeatureLimit = 5

    private var visibleFeatures: [XAIFeature] {
        isShowingAllFeatures ? xai.topFeatures : Array(xai.topFeatures.prefix(visibleFeatureLimit))
    }

    private var hiddenFeatureCount: Int {
        max(xai.topFeatures.count - visibleFeatureLimit, 0)
    }

    var body: some View {
        ResultDetailCard {
            VStack(alignment: .leading, spacing: 14) {
                Label(localText(en: "Why this prediction?", ko: "왜 이런 예측이 나왔나요?"), systemImage: "sparkle.magnifyingglass")
                    .font(.headline)
                    .foregroundStyle(ResultDetailTheme.ink)
                Text(localizedXAI(xai.summary))
                    .font(.callout)
                    .foregroundStyle(ResultDetailTheme.muted)
                    .fixedSize(horizontal: false, vertical: true)
                Text("\(localText(en: "Method", ko: "방법")): \(localizedXAI(xai.method)) · \(localText(en: "Feature set", ko: "특징 세트")): \(localizedXAIFeatureSet(xai.featureSet))")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(ResultDetailTheme.primary)
                VStack(spacing: 0) {
                    ForEach(Array(visibleFeatures.enumerated()), id: \.element.id) { index, feature in
                        featureImpactRow(feature)
                        if index < visibleFeatures.count - 1 {
                            Divider()
                        }
                    }
                }
                .background(ResultDetailTheme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))

                if hiddenFeatureCount > 0 {
                    Button {
                        withAnimation(.easeInOut(duration: 0.22)) {
                            isShowingAllFeatures.toggle()
                        }
                    } label: {
                        Label(
                            featureToggleTitle,
                            systemImage: isShowingAllFeatures ? "chevron.up" : "chevron.down"
                        )
                        .font(.caption.weight(.bold))
                        .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(ResultDetailSecondaryButtonStyle())
                }
            }
        }
    }

    private var featureToggleTitle: String {
        if isShowingAllFeatures {
            return localText(en: "Show top 5 only", ko: "상위 5개만 보기")
        }
        return localText(en: "Show \(hiddenFeatureCount) more features", ko: "나머지 \(hiddenFeatureCount)개 feature 보기")
    }

    private func featureImpactRow(_ feature: XAIFeature) -> some View {
        HStack(alignment: .center, spacing: 10) {
            VStack(alignment: .leading, spacing: 3) {
                HStack(spacing: 6) {
                    Text(localizedXAI(feature.label))
                        .font(.caption.weight(.bold))
                        .foregroundStyle(ResultDetailTheme.ink)
                        .lineLimit(1)
                    Text(localizedXAICategory(feature.category))
                        .font(.caption2.weight(.black))
                        .foregroundStyle(ResultDetailTheme.primary)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(ResultDetailTheme.primary.opacity(0.10), in: Capsule())
                }
                Text(localizedXAI(feature.explanation))
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(ResultDetailTheme.muted)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 6)
            VStack(alignment: .trailing, spacing: 4) {
                Text(Optional(feature.importance).percentText)
                    .font(.caption2.weight(.black))
                    .foregroundStyle(ResultDetailTheme.primary)
                    .monospacedDigit()
                ProgressView(value: min(max(feature.importance, 0), 1))
                    .tint(ResultDetailTheme.primary)
                    .frame(width: 82)
            }
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 7)
    }

    private func localizedXAIFeatureSet(_ featureSet: String) -> String {
        let languageCode = UserDefaults.standard.string(forKey: "kyulai.ddLaminate.languageCode")
            ?? (Locale.current.language.languageCode?.identifier == "ko" ? "ko" : "en")
        guard languageCode == "ko" else { return featureSet }
        let map = [
            "theta + case": "θ + Case",
            "theta + CLT physics": "θ + CLT 물리 feature",
        ]
        return map[featureSet] ?? featureSet
    }

    private func localText(en: String, ko: String) -> String {
        let languageCode = UserDefaults.standard.string(forKey: "kyulai.ddLaminate.languageCode")
            ?? (Locale.current.language.languageCode?.identifier == "ko" ? "ko" : "en")
        return languageCode == "ko" ? ko : en
    }

    private func localizedXAICategory(_ category: String) -> String {
        let languageCode = UserDefaults.standard.string(forKey: "kyulai.ddLaminate.languageCode")
            ?? (Locale.current.language.languageCode?.identifier == "ko" ? "ko" : "en")
        guard languageCode == "ko" else { return category.capitalized }
        let map = [
            "angle": "각도",
            "stiffness": "강성",
            "coupling": "커플링",
            "case": "Case",
            "curve": "곡선",
            "other": "기타",
        ]
        return map[category] ?? category
    }

    private func localizedXAI(_ text: String) -> String {
        let languageCode = UserDefaults.standard.string(forKey: "kyulai.ddLaminate.languageCode")
            ?? (Locale.current.language.languageCode?.identifier == "ko" ? "ko" : "en")
        guard languageCode == "ko" else { return text }
        let map = [
            "This explanation uses the PPT-based physics-feature model. It combines θ₁, θ₂, Case, CLT ABD stiffness terms, membrane-bending coupling, and laminate anisotropy descriptors.":
                "PPT 기반 물리 feature 모델의 설명입니다. θ₁, θ₂, Case에 CLT ABD 강성, membrane-bending coupling, 적층 anisotropy descriptor를 함께 사용합니다.",
            "This explanation uses the Tree + Physics XAI model. It combines θ₁, θ₂, Case, CLT ABD stiffness terms, membrane-bending coupling, and laminate anisotropy descriptors.":
                "Tree + Physics XAI 모델의 설명입니다. θ₁, θ₂, Case에 CLT ABD 강성, membrane-bending coupling, 적층 anisotropy descriptor를 함께 사용합니다.",
            "This explanation uses the GointMLP + Physics XAI model. It masks one physics feature at a time and measures how much the neural Pt, max-value, and curve heads move.":
                "GointMLP + Physics XAI 모델의 설명입니다. 물리 feature를 하나씩 가리고 neural Pt, max value, curve head가 얼마나 움직이는지 측정합니다.",
            "This explanation uses the Laminate Forecast Tree + Physics XAI model. It combines θ₁, θ₂, Case, CLT ABD stiffness terms, membrane-bending coupling, and laminate anisotropy descriptors.":
                "Laminate Forecast Tree + Physics XAI 모델의 설명입니다. θ₁, θ₂, Case에 CLT ABD 강성, membrane-bending coupling, 적층 anisotropy descriptor를 함께 사용합니다.",
            "This explanation uses the Laminate Forecast GointMLP + Physics XAI model. It masks one physics feature at a time and measures how much the neural Type, Pt, max-value, and curve heads move.":
                "Laminate Forecast GointMLP + Physics XAI 모델의 설명입니다. 물리 feature를 하나씩 가리고 neural Type, Pt, max value, curve head가 얼마나 움직이는지 측정합니다.",
            "This explanation uses the Laminate Forecast Machine Learning model. It keeps the strongest θ, Case, CLT stiffness, coupling, anisotropy, and stack-shape features.":
                "Laminate Forecast Machine Learning 모델의 설명입니다. θ, Case, CLT 강성, coupling, anisotropy, 적층 형상 feature 중 영향이 큰 항목을 사용합니다.",
            "This explanation uses the Laminate Forecast Machine Learning model. It keeps the strongest θ, Case, normalized CLT stiffness, coupling, anisotropy, and stack-shape features.":
                "Laminate Forecast Machine Learning 모델의 설명입니다. θ, Case, 정규화된 CLT 강성, coupling, anisotropy, 적층 형상 feature 중 영향이 큰 항목을 사용합니다.",
            "This explanation uses the Laminate Forecast Deep Learning model. It keeps physics descriptors and selected basis terms that improved the neural multi-task surrogate.":
                "Laminate Forecast Deep Learning 모델의 설명입니다. neural multi-task surrogate에 도움이 된 물리 descriptor와 선택된 basis 항목을 사용합니다.",
            "This explanation uses the Laminate Forecast Deep Learning model. It masks one physics feature at a time for the current θ/Case input.":
                "Laminate Forecast Deep Learning 모델의 설명입니다. 현재 θ/Case 입력에서 물리 feature를 하나씩 가려 민감도를 확인합니다.",
            "This explanation uses the u3 Forecast Machine Learning model. It keeps θ periodicity, CLT stiffness, coupling, anisotropy, and stack-shape features.":
                "u3 Forecast Machine Learning 모델의 설명입니다. θ 주기성, CLT 강성, coupling, anisotropy, 적층 형상 feature를 사용합니다.",
            "This explanation uses the u3 Forecast Machine Learning model. It keeps θ periodicity, normalized CLT stiffness, coupling, anisotropy, and stack-shape features.":
                "u3 Forecast Machine Learning 모델의 설명입니다. θ 주기성, 정규화된 CLT 강성, coupling, anisotropy, 적층 형상 feature를 사용합니다.",
            "This explanation uses the u3 Forecast Deep Learning model. It masks one physics feature at a time and measures how much the neural Pt, max-value, and curve heads move for the current θ/Case input.":
                "u3 Forecast Deep Learning 모델의 설명입니다. 현재 θ/Case 입력에서 물리 feature를 하나씩 가리고 neural Pt, max value, curve head 변화량을 측정합니다.",
            "This explanation uses the GointMLP theta/case model. It masks one theta feature at a time and measures how much the neural Pt, max-value, and curve heads move.":
                "GointMLP θ/Case 모델의 설명입니다. θ feature를 하나씩 가리고 neural Pt, max value, curve head가 얼마나 움직이는지 측정합니다.",
            "This explanation uses the original theta/case model. It mainly shows angle periodicity and case effects, not full laminate physics.":
                "기존 θ/Case 모델의 설명입니다. 전체 적층 물리보다는 각도 주기성과 Case 효과를 주로 보여줍니다.",
            "This explanation uses the original Tree theta/case model. It mainly shows angle periodicity and case effects, not full laminate physics.":
                "기존 Tree θ/Case 모델의 설명입니다. 전체 적층 물리보다는 각도 주기성과 Case 효과를 주로 보여줍니다.",
            "Tree ensemble feature importance + local finite-difference sensitivity":
                "Tree ensemble feature importance + local finite-difference sensitivity",
            "GointMLP occlusion sensitivity + local finite-difference sensitivity":
                "GointMLP occlusion sensitivity + local finite-difference sensitivity",
            "Minimum |θ|": "최소 |θ|",
            "Mean |θ|": "평균 |θ|",
            "Maximum |θ|": "최대 |θ|",
            "|θ| spread": "|θ| 분산",
            "|θ₁|": "|θ₁|",
            "|θ₂|": "|θ₂|",
            "|θ₁ - θ₂|": "|θ₁ - θ₂|",
            "θ₁ × θ₂": "θ₁ × θ₂",
            "cos(2θ₁)": "cos(2θ₁)",
            "cos(2θ₂)": "cos(2θ₂)",
            "sin(4θ₁)": "sin(4θ₁)",
            "sin(4θ₂)": "sin(4θ₂)",
            "cos(4θ₁)": "cos(4θ₁)",
            "cos(4θ₂)": "cos(4θ₂)",
            "Angle spread": "각도 간격",
            "D11 bending stiffness": "D11 굽힘 강성",
            "D22 bending stiffness": "D22 굽힘 강성",
            "D12 bending coupling": "D12 굽힘 커플링",
            "D66 twisting stiffness": "D66 비틀림 강성",
            "A11 membrane stiffness": "A11 막 강성",
            "A22 membrane stiffness": "A22 막 강성",
            "A12 membrane coupling": "A12 막 커플링",
            "A66 shear stiffness": "A66 전단 강성",
            "A16 extension-shear coupling": "A16 인장-전단 커플링",
            "A26 extension-shear coupling": "A26 인장-전단 커플링",
            "A11/A22 ratio": "A11/A22 비율",
            "D11/D22 ratio": "D11/D22 비율",
            "A66 geometry ratio": "A66 기하 비율",
            "Membrane anisotropy": "막 이방성",
            "Bending anisotropy": "굽힘 이방성",
            "Stack balance cosine": "적층 balance cosine",
            "Stack balance sine": "적층 balance sine",
            "Stack symmetry mismatch": "적층 대칭 불일치",
            "DD angle center": "DD 각도 중심",
            "Mean signed angle": "평균 부호 각도",
            "B11 membrane-bending coupling": "B11 막-굽힘 커플링",
            "B22 membrane-bending coupling": "B22 막-굽힘 커플링",
            "B12 membrane-bending coupling": "B12 막-굽힘 커플링",
            "B66 shear-bending coupling": "B66 전단-굽힘 커플링",
            "B16 bend-twist coupling": "B16 굽힘-비틀림 커플링",
            "B26 bend-twist coupling": "B26 굽힘-비틀림 커플링",
            "B11/D11 coupling ratio": "B11/D11 커플링 비율",
            "B22/D22 coupling ratio": "B22/D22 커플링 비율",
            "A-matrix coupling norm": "A 행렬 커플링 크기",
            "B-matrix coupling norm": "B 행렬 커플링 크기",
            "D-matrix coupling norm": "D 행렬 커플링 크기",
            "D16 bend-twist coupling": "D16 굽힘-비틀림 커플링",
            "D26 bend-twist coupling": "D26 굽힘-비틀림 커플링",
            "Ply count": "플라이 수",
            "Total thickness": "전체 두께",
            "Panel aspect ratio": "패널 종횡비",
            "Length slenderness": "길이 slenderness",
            "Width slenderness": "폭 slenderness",
            "Case pattern II": "Case pattern II",
            "Case 2 flag": "Case 2 표시자",
            "Case 3 flag": "Case 3 표시자",
            "Case 4 flag": "Case 4 표시자",
            "Smallest absolute ply-family angle. The PPT shows high-performing regions away from 0°/90°, so this captures whether either family is too close to an axial baseline.":
                "가장 작은 절대 적층 각도입니다. 0°/90° 축 방향에 너무 가까운 각도 조합인지 판단하는 데 도움이 됩니다.",
            "Average absolute angle across the expanded laminate stack; helps identify the ±45°-type region emphasized in the PPT.":
                "확장된 적층 구조의 평균 절대각입니다. PPT에서 강조된 ±45° 계열 영역을 파악하는 데 도움이 됩니다.",
            "Largest absolute ply-family angle; helps separate ±45°-type candidates from near-90° dominated stacks.":
                "가장 큰 절대 적층 각도입니다. ±45° 계열 후보와 90°에 가까운 적층을 구분하는 데 도움이 됩니다.",
            "Spread of absolute angles in the expanded laminate stack. It captures how strongly the two Double-Double angle families differ.":
                "확장된 적층 구조에서 절대각의 퍼짐입니다. 두 Double-Double 각도군이 얼마나 다른지 나타냅니다.",
            "Absolute value of θ₁. This captures how far the first angle family is from the axial 0° direction.":
                "θ₁의 절대값입니다. 첫 번째 각도군이 0° 축 방향에서 얼마나 벗어났는지 나타냅니다.",
            "Absolute value of θ₂. This captures how far the second angle family is from the axial 0° direction.":
                "θ₂의 절대값입니다. 두 번째 각도군이 0° 축 방향에서 얼마나 벗어났는지 나타냅니다.",
            "Absolute separation between the two Double-Double angle families.":
                "두 Double-Double 각도군 사이의 절대 간격입니다.",
            "Interaction feature between θ₁ and θ₂. It helps the model distinguish angle pairs with opposite or same signs.":
                "θ₁과 θ₂의 상호작용 feature입니다. 두 각도가 같은 부호인지 반대 부호인지 구분하는 데 도움이 됩니다.",
            "Periodic angle descriptor for θ₁, commonly useful for laminate stiffness terms that repeat with 180° symmetry.":
                "θ₁의 주기적 각도 descriptor입니다. 180° 대칭으로 반복되는 적층 강성 항을 표현하는 데 유용합니다.",
            "Periodic angle descriptor for θ₂, commonly useful for laminate stiffness terms that repeat with 180° symmetry.":
                "θ₂의 주기적 각도 descriptor입니다. 180° 대칭으로 반복되는 적층 강성 항을 표현하는 데 유용합니다.",
            "Higher-order periodic descriptor for θ₁. It helps represent angle effects that appear in transformed laminate stiffness.":
                "θ₁의 고차 주기 descriptor입니다. 변환된 적층 강성에서 나타나는 각도 효과를 표현합니다.",
            "Higher-order periodic descriptor for θ₂. It helps represent angle effects that appear in transformed laminate stiffness.":
                "θ₂의 고차 주기 descriptor입니다. 변환된 적층 강성에서 나타나는 각도 효과를 표현합니다.",
            "Higher-order periodic descriptor for θ₁. It is strongly related to transformed orthotropic stiffness variation with angle.":
                "θ₁의 고차 주기 descriptor입니다. 각도에 따른 직교이방성 강성 변화와 관련이 큽니다.",
            "Higher-order periodic descriptor for θ₂. It is strongly related to transformed orthotropic stiffness variation with angle.":
                "θ₂의 고차 주기 descriptor입니다. 각도에 따른 직교이방성 강성 변화와 관련이 큽니다.",
            "Longitudinal bending stiffness term from the laminate D matrix. It is directly related to bending resistance under the panel loading setup.":
                "적층 D 행렬의 길이 방향 굽힘 강성 항입니다. 패널 하중 조건에서 굽힘 저항과 직접 관련됩니다.",
            "Transverse bending stiffness term from the laminate D matrix.":
                "적층 D 행렬의 횡방향 굽힘 강성 항입니다.",
            "Bending coupling term from the D matrix; useful for distinguishing how the post-transition response bends after the knee point.":
                "D 행렬의 굽힘 커플링 항입니다. Pt 이후 응답이 어떻게 휘어지는지 구분하는 데 유용합니다.",
            "Twisting/shear bending stiffness. It often matters for buckling-like mode transitions and post-transition curve shape.":
                "비틀림/전단 굽힘 강성입니다. 좌굴 유사 모드 전환과 Pt 이후 곡선 형상에 영향을 줄 수 있습니다.",
            "Longitudinal membrane stiffness from the laminate A matrix.":
                "적층 A 행렬의 길이 방향 막 강성 항입니다.",
            "Transverse membrane stiffness from the laminate A matrix.":
                "적층 A 행렬의 횡방향 막 강성 항입니다.",
            "In-plane membrane coupling term from the laminate A matrix.":
                "적층 A 행렬의 평면 내 막 커플링 항입니다.",
            "In-plane shear stiffness from the laminate A matrix.":
                "적층 A 행렬의 평면 내 전단 강성 항입니다.",
            "A-matrix coupling between axial extension and in-plane shear. It reflects unbalanced angle effects in the laminate.":
                "축방향 인장과 평면 내 전단 사이의 A 행렬 커플링입니다. 적층각 불균형 효과를 반영합니다.",
            "A-matrix coupling between transverse extension and in-plane shear. It can indicate directional imbalance in the stack.":
                "횡방향 인장과 평면 내 전단 사이의 A 행렬 커플링입니다. 적층의 방향성 불균형을 나타낼 수 있습니다.",
            "Membrane anisotropy ratio. This tells whether the laminate is biased toward the load direction or transverse direction.":
                "막 강성 이방성 비율입니다. 적층판이 하중 방향 또는 횡방향 중 어디에 더 치우쳤는지 보여줍니다.",
            "Shear stiffness ratio normalized by the laminate membrane stiffness scale; useful for comparing shear contribution across angle pairs.":
                "막 강성 스케일로 정규화한 전단 강성 비율입니다. 각도 조합별 전단 기여를 비교하는 데 유용합니다.",
            "Bending anisotropy ratio. It helps explain case/type differences driven by flexural stiffness balance.":
                "굽힘 이방성 비율입니다. 굽힘 강성 균형에 의해 발생하는 Case/Type 차이를 설명하는 데 도움이 됩니다.",
            "Normalized difference between D11 and D22; a compact descriptor for direction-dependent bending behavior.":
                "D11과 D22의 정규화된 차이입니다. 방향별 굽힘 거동을 간단히 나타냅니다.",
            "Normalized difference between A11 and A22; a compact descriptor for direction-dependent membrane behavior.":
                "A11과 A22의 정규화된 차이입니다. 방향별 막 거동을 간단히 나타냅니다.",
            "A trigonometric balance descriptor over all plies; helps the model recognize balanced ±θ families.":
                "전체 플라이에 대한 삼각함수 기반 balance descriptor입니다. 모델이 balanced ±θ 계열을 인식하는 데 도움이 됩니다.",
            "Sine-based balance descriptor over all plies. Values near zero indicate stronger ±θ cancellation in the expanded stack.":
                "전체 플라이에 대한 sine 기반 balance descriptor입니다. 0에 가까울수록 확장 적층에서 ±θ 상쇄가 강하다는 뜻입니다.",
            "Distance-like descriptor for top/bottom ply-angle mismatch. Larger values suggest more membrane-bending coupling potential.":
                "상/하부 플라이 각도 불일치를 나타내는 거리형 descriptor입니다. 값이 클수록 막-굽힘 커플링 가능성이 커질 수 있습니다.",
            "Average center of the two Double-Double angle families.":
                "두 Double-Double 각도군의 평균 중심값입니다.",
            "Average signed angle across the expanded stack. It helps detect directional bias not visible from absolute angles alone.":
                "확장된 적층 구조의 평균 부호 각도입니다. 절대각만으로 보이지 않는 방향성 편향을 감지하는 데 도움이 됩니다.",
            "Membrane-bending coupling term in the load direction. Nonzero B terms indicate asymmetric coupling effects in the laminate response.":
                "하중 방향의 막-굽힘 커플링 항입니다. B 항이 0이 아니면 적층 응답에 비대칭 커플링 효과가 있음을 의미합니다.",
            "Transverse membrane-bending coupling term from the laminate B matrix.":
                "적층 B 행렬의 횡방향 막-굽힘 커플링 항입니다.",
            "Cross membrane-bending coupling term from the laminate B matrix.":
                "적층 B 행렬의 교차 막-굽힘 커플링 항입니다.",
            "Shear-related membrane-bending coupling term from the laminate B matrix.":
                "적층 B 행렬의 전단 관련 막-굽힘 커플링 항입니다.",
            "B-matrix coupling between load-direction bending and twisting/shear response.":
                "하중 방향 굽힘과 비틀림/전단 응답 사이의 B 행렬 커플링입니다.",
            "B-matrix coupling between transverse bending and twisting/shear response.":
                "횡방향 굽힘과 비틀림/전단 응답 사이의 B 행렬 커플링입니다.",
            "Load-direction membrane-bending coupling normalized by bending stiffness.":
                "하중 방향 membrane-bending coupling을 굽힘 강성으로 정규화한 값입니다.",
            "Transverse membrane-bending coupling normalized by transverse bending stiffness.":
                "횡방향 membrane-bending coupling을 횡방향 굽힘 강성으로 정규화한 값입니다.",
            "Combined magnitude of A16 and A26 extension-shear coupling terms.":
                "A16과 A26 인장-전단 커플링 항의 결합 크기입니다.",
            "Combined magnitude of B16 and B26 membrane-bending coupling terms.":
                "B16과 B26 막-굽힘 커플링 항의 결합 크기입니다.",
            "Combined magnitude of D16 and D26 bend-twist coupling terms.":
                "D16과 D26 굽힘-비틀림 커플링 항의 결합 크기입니다.",
            "D-matrix coupling between load-direction bending and twisting response.":
                "하중 방향 굽힘과 비틀림 응답 사이의 D 행렬 커플링입니다.",
            "D-matrix coupling between transverse bending and twisting response.":
                "횡방향 굽힘과 비틀림 응답 사이의 D 행렬 커플링입니다.",
            "Number of plies in the expanded laminate stack.":
                "확장된 적층 구조의 플라이 개수입니다.",
            "Total laminate thickness in inches based on the PPT ply thickness.":
                "PPT의 플라이 두께를 기준으로 계산한 전체 적층 두께(in)입니다.",
            "Panel length-to-width ratio from the PPT mechanics setup.":
                "PPT mechanics setup의 패널 길이/폭 비율입니다.",
            "Panel length divided by total laminate thickness.":
                "패널 길이를 전체 적층 두께로 나눈 값입니다.",
            "Panel width divided by total laminate thickness.":
                "패널 폭을 전체 적층 두께로 나눈 값입니다.",
            "Binary descriptor for the Case3-style Double-Double stack pattern.":
                "Case3 방식 Double-Double 적층 패턴을 나타내는 이진 descriptor입니다.",
            "One-hot indicator that the selected laminate structure is Case 2.":
                "선택한 적층 구조가 Case 2인지 나타내는 one-hot 표시자입니다.",
            "One-hot indicator that the selected laminate structure is Case 3.":
                "선택한 적층 구조가 Case 3인지 나타내는 one-hot 표시자입니다.",
            "One-hot indicator that the selected laminate structure is Case 4.":
                "선택한 적층 구조가 Case 4인지 나타내는 one-hot 표시자입니다.",
        ]
        return map[text] ?? text
    }
}

struct InterpretationSummaryView: View {
    let result: ResponsePredictionResult
    var maxLines: Int?
    var showsHeader: Bool

    init(result: ResponsePredictionResult, maxLines: Int? = nil, showsHeader: Bool = true) {
        self.result = result
        self.maxLines = maxLines
        self.showsHeader = showsHeader
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if showsHeader {
                Label(L10n.t("interpretation"), systemImage: "text.magnifyingglass")
                    .font(.headline)
                    .foregroundStyle(ResultDetailTheme.ink)
            }
            ForEach(Array(result.interpretationLines.prefix(maxLines ?? Int.max)), id: \.self) { line in
                HStack(alignment: .firstTextBaseline, spacing: 8) {
                    Circle()
                        .fill(ResultDetailTheme.primary)
                        .frame(width: 5, height: 5)
                    Text(line)
                        .font(.callout)
                        .foregroundStyle(ResultDetailTheme.ink)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            Text(L10n.t("interpretation.disclaimer"))
                .font(.caption2)
                .foregroundStyle(ResultDetailTheme.muted)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}

extension ResponsePredictionResult {
    var interpretationLines: [String] {
        [
            confidenceInterpretation,
            ptInterpretation,
            curveInterpretation,
        ].compactMap { $0 }
    }

    var shareSummaryText: String {
        let modelLines = [
            "ImperialAX Laminate Forecast",
            "",
            "MODEL",
            "• Model: \(displayModelLabel)",
            "",
            "INPUTS",
        ]
        let inputLines = shareInputSummaryLines.map { "• \($0)" }
        let resultLines = [
            "",
            "RESULTS",
            "• Predicted type: Type \(predictedType)",
            "• Confidence: \(confidence.percentText)",
            "• Pt: \(predictedPt.metricText(digits: 2))",
            "• Max force: \(predictedMaxForce.metricText(digits: 2))",
            "• Pt displacement: \(predictedPtDisplacement?.metricText(digits: 5) ?? "-")",
            "",
            "INTERPRETATION",
        ]
        let interpretationSummaryLines = self.interpretationLines.map { "• \($0)" }
        let chartLines = [
            "",
            "CHART",
            "• Response curve: \(curve.count) points",
            "",
            "GRAPH",
            "• Pt marker: \(predictedPt.metricText(digits: 2))",
            "• x Axis: displacement",
            "• y Axis: force",
        ]
        let lines = modelLines + inputLines + resultLines + interpretationSummaryLines + chartLines
        return lines.joined(separator: "\n").trimmingCharacters(in: .newlines)
    }

    var shareInputSummaryPlainLines: [String] {
        [
            inputValue("case").map { "Case: \($0)" },
            theta1Line,
            theta2Line,
        ].compactMap { $0 }
    }

    private var shareInputSummaryLines: [String] {
        shareInputSummaryPlainLines
    }

    private var confidenceInterpretation: String {
        guard let confidence else {
            return L10n.f("interpretation.confidence.none", predictedType)
        }
        if confidence >= 0.75 {
            return L10n.f("interpretation.confidence.high", predictedType)
        }
        if confidence >= 0.60 {
            return L10n.f("interpretation.confidence.medium", predictedType)
        }
        return L10n.f("interpretation.confidence.low", predictedType)
    }

    private var ptInterpretation: String {
        guard predictedMaxForce > 0 else {
            return L10n.t("interpretation.pt.generic")
        }
        let ratio = max(0, min(predictedPt / predictedMaxForce, 1))
        let percent = Int((ratio * 100).rounded())
        if ratio < 0.45 {
            return L10n.f("interpretation.pt.early", percent)
        }
        if ratio > 0.75 {
            return L10n.f("interpretation.pt.late", percent)
        }
        return L10n.f("interpretation.pt.mid", percent)
    }

    private var curveInterpretation: String? {
        guard curve.count >= 3, let maxPoint = curve.max(by: { $0.force < $1.force }) else {
            return nil
        }
        let finalForce = curve.last?.force ?? maxPoint.force
        guard maxPoint.force > 0 else {
            return nil
        }
        let retained = finalForce / maxPoint.force
        if retained < 0.25 {
            return L10n.t("interpretation.curve.strong.softening")
        }
        if retained < 0.75 {
            return L10n.t("interpretation.curve.softening")
        }
        return L10n.t("interpretation.curve.stable")
    }

    private var theta1Line: String? {
        guard let theta1 = inputValue("theta1", digits: 0) else { return nil }
        return "Theta 1: \(theta1) deg"
    }

    private var theta2Line: String? {
        guard let theta2 = inputValue("theta2", digits: 0) else { return nil }
        return "Theta 2: \(theta2) deg"
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
        case .null:
            nil
        }
    }
}
