package com.imperialax.app

import android.content.Context
import java.util.Locale

object LaminateXaiText {
    @Suppress("DEPRECATION")
    fun isKoreanUi(context: Context): Boolean =
        context.resources.configuration.locale.language.equals("ko", ignoreCase = true)
            || Locale.getDefault().language.equals("ko", ignoreCase = true)

    fun text(context: Context, value: String): String {
        if (!isKoreanUi(context)) return value
        return translations[value] ?: value
    }

    fun category(context: Context, value: String): String {
        if (!isKoreanUi(context)) return value.replaceFirstChar { it.titlecase(Locale.getDefault()) }
        return when (value.lowercase(Locale.getDefault())) {
            "angle" -> "각도"
            "stiffness" -> "강성"
            "coupling" -> "커플링"
            "case" -> "Case"
            "curve" -> "곡선"
            "other" -> "기타"
            else -> value
        }
    }

    fun featureSet(context: Context, value: String): String {
        if (!isKoreanUi(context)) return value
        return when (value) {
            "theta + case" -> "θ + Case"
            "theta + CLT physics" -> "θ + CLT 물리 feature"
            else -> value
        }
    }

    private val translations = mapOf(
        "This explanation uses the PPT-based physics-feature model. It combines θ₁, θ₂, Case, CLT ABD stiffness terms, membrane-bending coupling, and laminate anisotropy descriptors." to
            "PPT 기반 물리 feature 모델의 설명입니다. θ₁, θ₂, Case에 CLT ABD 강성, 막-굽힘 커플링, 적층 이방성 descriptor를 함께 사용합니다.",
        "This explanation uses the Tree + Physics XAI model. It combines θ₁, θ₂, Case, CLT ABD stiffness terms, membrane-bending coupling, and laminate anisotropy descriptors." to
            "Tree + Physics XAI 모델의 설명입니다. θ₁, θ₂, Case에 CLT ABD 강성, 막-굽힘 커플링, 적층 이방성 descriptor를 함께 사용합니다.",
        "This explanation uses the GointMLP + Physics XAI model. It masks one physics feature at a time and measures how much the neural Pt, max-value, and curve heads move." to
            "GointMLP + Physics XAI 모델의 설명입니다. 물리 feature를 하나씩 가리고 neural Pt, 최대값, 곡선 head가 얼마나 변하는지 측정합니다.",
        "This explanation uses the Laminate Forecast Machine Learning model. It keeps the strongest θ, Case, CLT stiffness, coupling, anisotropy, and stack-shape features." to
            "Laminate Forecast Machine Learning 모델의 설명입니다. θ, Case, CLT 강성, 커플링, 이방성, 적층 형상 feature 중 영향이 큰 항목을 사용합니다.",
        "This explanation uses the Laminate Forecast Deep Learning model. It keeps physics descriptors and selected basis terms that improved the neural multi-task surrogate." to
            "Laminate Forecast Deep Learning 모델의 설명입니다. neural multi-task surrogate에 도움이 된 물리 descriptor와 선택된 basis 항목을 사용합니다.",
        "This explanation uses the Laminate Forecast Deep Learning model. It masks one physics feature at a time for the current θ/Case input." to
            "Laminate Forecast Deep Learning 모델의 설명입니다. 현재 θ/Case 입력에서 물리 feature를 하나씩 가려 민감도를 확인합니다.",
        "This explanation uses the u3 Forecast Machine Learning model. It keeps θ periodicity, CLT stiffness, coupling, anisotropy, and stack-shape features." to
            "u3 Forecast Machine Learning 모델의 설명입니다. θ 주기성, CLT 강성, 커플링, 이방성, 적층 형상 feature를 사용합니다.",
        "This explanation uses the u3 Forecast Deep Learning model. It masks one physics feature at a time and measures how much the neural Pt, max-value, and curve heads move for the current θ/Case input." to
            "u3 Forecast Deep Learning 모델의 설명입니다. 현재 θ/Case 입력에서 물리 feature를 하나씩 가리고 neural Pt, 최대값, 곡선 head 변화량을 측정합니다.",
        "Tree ensemble feature importance + local finite-difference sensitivity" to
            "Tree ensemble feature importance + local finite-difference sensitivity",
        "GointMLP occlusion sensitivity + local finite-difference sensitivity" to
            "GointMLP occlusion sensitivity + local finite-difference sensitivity",
        "Minimum |θ|" to "최소 |θ|",
        "Mean |θ|" to "평균 |θ|",
        "Maximum |θ|" to "최대 |θ|",
        "|θ| spread" to "|θ| 분산",
        "|θ₁|" to "|θ₁|",
        "|θ₂|" to "|θ₂|",
        "|θ₁ - θ₂|" to "|θ₁ - θ₂|",
        "θ₁ × θ₂" to "θ₁ × θ₂",
        "Angle spread" to "각도 간격",
        "D11 bending stiffness" to "D11 굽힘 강성",
        "D22 bending stiffness" to "D22 굽힘 강성",
        "D12 bending coupling" to "D12 굽힘 커플링",
        "D66 twisting stiffness" to "D66 비틀림 강성",
        "D16 bend-twist coupling" to "D16 굽힘-비틀림 커플링",
        "D26 bend-twist coupling" to "D26 굽힘-비틀림 커플링",
        "A11 membrane stiffness" to "A11 막 강성",
        "A22 membrane stiffness" to "A22 막 강성",
        "A12 membrane coupling" to "A12 막 커플링",
        "A66 shear stiffness" to "A66 전단 강성",
        "A16 extension-shear coupling" to "A16 인장-전단 커플링",
        "A26 extension-shear coupling" to "A26 인장-전단 커플링",
        "A11/A22 ratio" to "A11/A22 비율",
        "D11/D22 ratio" to "D11/D22 비율",
        "A66 geometry ratio" to "A66 기하 비율",
        "Membrane anisotropy" to "막 이방성",
        "Bending anisotropy" to "굽힘 이방성",
        "Stack balance cosine" to "적층 balance cosine",
        "Stack balance sine" to "적층 balance sine",
        "Stack symmetry mismatch" to "적층 대칭 불일치",
        "DD angle center" to "DD 각도 중심",
        "Mean signed angle" to "평균 부호 각도",
        "B11 membrane-bending coupling" to "B11 막-굽힘 커플링",
        "B22 membrane-bending coupling" to "B22 막-굽힘 커플링",
        "B12 membrane-bending coupling" to "B12 막-굽힘 커플링",
        "B66 shear-bending coupling" to "B66 전단-굽힘 커플링",
        "B16 bend-twist coupling" to "B16 굽힘-비틀림 커플링",
        "B26 bend-twist coupling" to "B26 굽힘-비틀림 커플링",
        "B11/D11 coupling ratio" to "B11/D11 커플링 비율",
        "B22/D22 coupling ratio" to "B22/D22 커플링 비율",
        "A-matrix coupling norm" to "A 행렬 커플링 크기",
        "B-matrix coupling norm" to "B 행렬 커플링 크기",
        "D-matrix coupling norm" to "D 행렬 커플링 크기",
        "Ply count" to "플라이 수",
        "Total thickness" to "전체 두께",
        "Panel aspect ratio" to "패널 종횡비",
        "Length slenderness" to "길이 slenderness",
        "Width slenderness" to "폭 slenderness",
        "Case 2 flag" to "Case 2 표시자",
        "Case 3 flag" to "Case 3 표시자",
        "Case 4 flag" to "Case 4 표시자",
        "Smallest absolute ply-family angle. The PPT shows high-performing regions away from 0°/90°, so this captures whether either family is too close to an axial baseline." to
            "가장 작은 절대 적층 각도입니다. 0°/90° 축 방향에 너무 가까운 각도 조합인지 판단하는 데 도움이 됩니다.",
        "Longitudinal bending stiffness term from the laminate D matrix. It is directly related to bending resistance under the panel loading setup." to
            "적층 D 행렬의 길이 방향 굽힘 강성 항입니다. 패널 하중 조건에서 굽힘 저항과 직접 관련됩니다.",
        "Transverse bending stiffness term from the laminate D matrix." to
            "적층 D 행렬의 횡방향 굽힘 강성 항입니다.",
        "Bending coupling term from the D matrix; useful for distinguishing how the post-transition response bends after the knee point." to
            "D 행렬의 굽힘 커플링 항입니다. Pt 이후 응답이 어떻게 휘어지는지 구분하는 데 유용합니다.",
        "Twisting/shear bending stiffness. It often matters for buckling-like mode transitions and post-transition curve shape." to
            "비틀림/전단 굽힘 강성입니다. 좌굴 유사 모드 전환과 Pt 이후 곡선 형상에 영향을 줄 수 있습니다.",
        "Longitudinal membrane stiffness from the laminate A matrix." to
            "적층 A 행렬의 길이 방향 막 강성 항입니다.",
        "Transverse membrane stiffness from the laminate A matrix." to
            "적층 A 행렬의 횡방향 막 강성 항입니다.",
        "In-plane membrane coupling term from the laminate A matrix." to
            "적층 A 행렬의 평면 내 막 커플링 항입니다.",
        "In-plane shear stiffness from the laminate A matrix." to
            "적층 A 행렬의 평면 내 전단 강성 항입니다.",
        "Membrane anisotropy ratio. This tells whether the laminate is biased toward the load direction or transverse direction." to
            "막 강성 이방성 비율입니다. 적층판이 하중 방향 또는 횡방향 중 어디에 더 치우쳤는지 보여줍니다.",
        "Bending anisotropy ratio. It helps explain case/type differences driven by flexural stiffness balance." to
            "굽힘 이방성 비율입니다. 굽힘 강성 균형에 의해 발생하는 Case/Type 차이를 설명하는 데 도움이 됩니다.",
        "Number of plies in the expanded laminate stack." to
            "확장된 적층 구조의 플라이 개수입니다.",
        "Total laminate thickness in inches based on the PPT ply thickness." to
            "PPT의 플라이 두께를 기준으로 계산한 전체 적층 두께(in)입니다.",
    )
}
