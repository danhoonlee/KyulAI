import KyulAIDDLaminateCore
import SwiftUI

struct ResultDetailView: View {
    let result: ResponsePredictionResult

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                heroCard
                metricsGrid
                interpretationCard
                curveCard
                probabilityCard
                if let xai = result.xai {
                    XAIExplanationCard(xai: xai)
                }
                if !result.notes.isEmpty {
                    notesCard
                }
            }
            .padding(20)
        }
        .background(AppTheme.background.ignoresSafeArea())
        .navigationTitle(L10n.t("result"))
        .appInlineNavigationTitle()
        .toolbar {
            ShareLink(item: result.shareSummaryText) {
                Image(systemName: "square.and.arrow.up")
            }
            #if os(iOS)
            ShareImageButton(
                fileName: "c2es-laminate-forecast",
                report: LaminateShareImageReportView(result: result)
            ) {
                Image(systemName: "photo")
            }
            #endif
        }
    }

    private var heroCard: some View {
        AppCard {
            VStack(alignment: .leading, spacing: 14) {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 6) {
                        Text(L10n.t("predicted.type"))
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(AppTheme.muted)
                        Text(L10n.f("type.format", result.predictedType))
                            .font(.system(size: 48, weight: .black, design: .rounded))
                            .foregroundStyle(AppTheme.ink)
                    }
                    Spacer()
                    VStack(alignment: .trailing, spacing: 4) {
                        Text(result.confidence.percentText)
                            .font(.title2.monospacedDigit().weight(.bold))
                            .foregroundStyle(AppTheme.primary)
                        Text(L10n.t("confidence"))
                            .font(.caption2.weight(.semibold))
                            .foregroundStyle(AppTheme.muted)
                    }
                }
                Divider()
                VStack(alignment: .leading, spacing: 4) {
                    Text(result.displayModelLabel)
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(AppTheme.ink)
                    Text(result.inputMode.uppercased())
                        .font(.caption2.monospaced().weight(.bold))
                        .foregroundStyle(AppTheme.primary)
                }
            }
        }
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

    private func localText(en: String, ko: String) -> String {
        let languageCode = UserDefaults.standard.string(forKey: "kyulai.ddLaminate.languageCode")
            ?? (Locale.current.language.languageCode?.identifier == "ko" ? "ko" : "en")
        return languageCode == "ko" ? ko : en
    }

    private var curveCard: some View {
        AppCard {
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    Label(L10n.t("response.curve"), systemImage: "chart.xyaxis.line")
                        .font(.headline)
                        .foregroundStyle(AppTheme.ink)
                    Spacer()
                    Text(L10n.t("pt.marker"))
                        .font(.caption2.bold())
                        .foregroundStyle(AppTheme.danger)
                }
                CurveChartView(points: result.curve, predictedPt: result.predictedPt)
                    .frame(height: 280)
            }
        }
    }

    private var interpretationCard: some View {
        AppCard {
            InterpretationSummaryView(result: result)
        }
    }

    private var probabilityCard: some View {
        AppCard {
            VStack(alignment: .leading, spacing: 14) {
                Label(L10n.t("class.probabilities"), systemImage: "chart.bar.fill")
                    .font(.headline)
                    .foregroundStyle(AppTheme.ink)
                if result.sortedProbabilities.isEmpty {
                    Text(L10n.t("no.probabilities"))
                        .font(.callout)
                        .foregroundStyle(AppTheme.muted)
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
                    .foregroundStyle(AppTheme.ink)
                Spacer()
                Text(Optional(value).percentText)
                    .font(.subheadline.monospacedDigit().weight(.bold))
                    .foregroundStyle(AppTheme.muted)
            }
            GeometryReader { proxy in
                ZStack(alignment: .leading) {
                    Capsule()
                        .fill(AppTheme.field)
                    Capsule()
                        .fill(label == "type\(result.predictedType)" ? AppTheme.primary : AppTheme.accent.opacity(0.28))
                        .frame(width: max(6, proxy.size.width * min(max(value, 0), 1)))
                }
            }
            .frame(height: 8)
        }
    }

    private var notesCard: some View {
        AppCard {
            VStack(alignment: .leading, spacing: 12) {
                Label(L10n.t("notes"), systemImage: "exclamationmark.triangle.fill")
                    .font(.headline)
                    .foregroundStyle(AppTheme.warning)
                ForEach(result.notes, id: \.self) { note in
                    Text(note)
                        .font(.callout)
                        .foregroundStyle(AppTheme.ink)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
    }
}

struct U3PtResultDetailView: View {
    let result: U3PtPredictionResult

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                heroCard
                metricsGrid
                curveCard
                if let xai = result.xai {
                    XAIExplanationCard(xai: xai)
                }
                if !result.notes.isEmpty {
                    notesCard
                }
            }
            .padding(20)
        }
        .background(AppTheme.background.ignoresSafeArea())
        .navigationTitle(L10n.t("u3.result"))
        .appInlineNavigationTitle()
    }

    private var heroCard: some View {
        AppCard {
            VStack(alignment: .leading, spacing: 14) {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 6) {
                        Text(L10n.t("predicted.pt"))
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(AppTheme.muted)
                        Text(result.predictedPt.metricText(digits: 2))
                            .font(.system(size: 44, weight: .black, design: .rounded))
                            .foregroundStyle(AppTheme.ink)
                            .lineLimit(1)
                            .minimumScaleFactor(0.72)
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
                Divider()
                VStack(alignment: .leading, spacing: 4) {
                    Text(L10n.t("u3.forecast"))
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(AppTheme.ink)
                    Text(result.inputMode.uppercased())
                        .font(.caption2.monospaced().weight(.bold))
                        .foregroundStyle(AppTheme.primary)
                }
            }
        }
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

    private func localText(en: String, ko: String) -> String {
        let languageCode = UserDefaults.standard.string(forKey: "kyulai.ddLaminate.languageCode")
            ?? (Locale.current.language.languageCode?.identifier == "ko" ? "ko" : "en")
        return languageCode == "ko" ? ko : en
    }

    private var curveCard: some View {
        AppCard {
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    Label(L10n.t("u3.response.curve"), systemImage: "chart.xyaxis.line")
                        .font(.headline)
                        .foregroundStyle(AppTheme.ink)
                    Spacer()
                    Text(L10n.t("pt.marker"))
                        .font(.caption2.bold())
                        .foregroundStyle(AppTheme.danger)
                }
                CurveChartView(points: result.curve, predictedPt: result.predictedPt, fitMode: .u3)
                    .frame(height: 280)
            }
        }
    }

    private var notesCard: some View {
        AppCard {
            VStack(alignment: .leading, spacing: 12) {
                Label(L10n.t("notes"), systemImage: "exclamationmark.triangle.fill")
                    .font(.headline)
                    .foregroundStyle(AppTheme.warning)
                ForEach(result.notes, id: \.self) { note in
                    Text(note)
                        .font(.callout)
                        .foregroundStyle(AppTheme.ink)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
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
        AppCard {
            VStack(alignment: .leading, spacing: 14) {
                Label(localText(en: "Why this prediction?", ko: "왜 이런 예측이 나왔나요?"), systemImage: "sparkle.magnifyingglass")
                    .font(.headline)
                    .foregroundStyle(AppTheme.ink)
                Text(localizedXAI(xai.summary))
                    .font(.callout)
                    .foregroundStyle(AppTheme.muted)
                    .fixedSize(horizontal: false, vertical: true)
                Text("\(localText(en: "Method", ko: "방법")): \(localizedXAI(xai.method)) · \(localText(en: "Feature set", ko: "특징 세트")): \(localizedXAIFeatureSet(xai.featureSet))")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(AppTheme.primary)
                VStack(spacing: 0) {
                    ForEach(Array(visibleFeatures.enumerated()), id: \.element.id) { index, feature in
                        featureImpactRow(feature)
                        if index < visibleFeatures.count - 1 {
                            Divider()
                        }
                    }
                }
                .background(AppTheme.field, in: RoundedRectangle(cornerRadius: 8, style: .continuous))

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
                    .buttonStyle(SecondaryButtonStyle())
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
                        .foregroundStyle(AppTheme.ink)
                        .lineLimit(1)
                    Text(localizedXAICategory(feature.category))
                        .font(.caption2.weight(.black))
                        .foregroundStyle(AppTheme.primary)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(AppTheme.primary.opacity(0.10), in: Capsule())
                }
                Text(localizedXAI(feature.explanation))
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(AppTheme.muted)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 6)
            VStack(alignment: .trailing, spacing: 4) {
                Text(Optional(feature.importance).percentText)
                    .font(.caption2.weight(.black))
                    .foregroundStyle(AppTheme.primary)
                    .monospacedDigit()
                ProgressView(value: min(max(feature.importance, 0), 1))
                    .tint(AppTheme.primary)
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
            "This explanation uses the Laminate Forecast Deep Learning model. It keeps physics descriptors and selected basis terms that improved the neural multi-task surrogate.":
                "Laminate Forecast Deep Learning 모델의 설명입니다. neural multi-task surrogate에 도움이 된 물리 descriptor와 선택된 basis 항목을 사용합니다.",
            "This explanation uses the Laminate Forecast Deep Learning model. It masks one physics feature at a time for the current θ/Case input.":
                "Laminate Forecast Deep Learning 모델의 설명입니다. 현재 θ/Case 입력에서 물리 feature를 하나씩 가려 민감도를 확인합니다.",
            "This explanation uses the u3 Forecast Machine Learning model. It keeps θ periodicity, CLT stiffness, coupling, anisotropy, and stack-shape features.":
                "u3 Forecast Machine Learning 모델의 설명입니다. θ 주기성, CLT 강성, coupling, anisotropy, 적층 형상 feature를 사용합니다.",
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

    init(result: ResponsePredictionResult, maxLines: Int? = nil) {
        self.result = result
        self.maxLines = maxLines
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label(L10n.t("interpretation"), systemImage: "text.magnifyingglass")
                .font(.headline)
                .foregroundStyle(AppTheme.ink)
            ForEach(Array(result.interpretationLines.prefix(maxLines ?? Int.max)), id: \.self) { line in
                HStack(alignment: .firstTextBaseline, spacing: 8) {
                    Circle()
                        .fill(AppTheme.primary)
                        .frame(width: 5, height: 5)
                    Text(line)
                        .font(.callout)
                        .foregroundStyle(AppTheme.ink)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            Text(L10n.t("interpretation.disclaimer"))
                .font(.caption2)
                .foregroundStyle(AppTheme.muted)
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
            "C2ES Laminate Forecast",
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
