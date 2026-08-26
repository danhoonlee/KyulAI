package com.imperialax.app

import android.app.Activity
import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.DashPathEffect
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RectF
import android.graphics.Typeface
import android.os.Bundle
import android.util.TypedValue
import android.view.Gravity
import android.view.MotionEvent
import android.view.ScaleGestureDetector
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.HorizontalScrollView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL
import kotlin.math.abs
import kotlin.math.hypot

private const val LAMINATE_RAG_BASE_URL = "https://laminate.imperialax.com"

class LaminateResultActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        render()
    }

    private fun render() {
        val scroll = ScrollView(this).apply {
            setBackgroundColor(LaminateV2.background)
        }
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(22), dp(18), dp(44))
        }
        scroll.addView(root)
        setContentView(scroll)

        val result = readResult()
        if (result == null) {
            root.addView(label("FORECAST RESULT", LaminateV2.blue, 12f, Typeface.BOLD))
            root.addView(label("Result unavailable", LaminateV2.ink, 32f, Typeface.BOLD), margin(top = 8))
            root.addView(paragraph("The prediction result could not be opened. Run the forecast again from the input screen."), margin(top = 8))
            root.addView(backButton("Back to inputs"), margin(top = 18))
            return
        }

        val mode = readMode()
        root.addView(label("FORECAST RESULT", LaminateV2.blue, 12f, Typeface.BOLD))
        root.addView(label(if (mode == "u3") "u3 Forecast" else "Laminate Response", LaminateV2.ink, 34f, Typeface.BOLD).apply {
            includeFontPadding = false
        }, margin(top = 8))
        root.addView(paragraph(
            if (mode == "u3") {
                "Review u3 Type, Pt, response curve, and explanation features for this run."
            } else {
                "Review Type, Pt, response metrics, and explanation features for this run."
            }
        ), margin(top = 8))
        root.addView(inputSummary(), margin(top = 14))

        val designSpaceContainer = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        val designSpace = readDesignSpace()
        if (designSpace != null) {
            designSpaceContainer.addView(designSpaceCard(designSpace))
        } else if (readDesignSpaceError() != null) {
            designSpaceContainer.addView(designSpaceUnavailableCard(readDesignSpaceError().orEmpty()))
        } else {
            designSpaceContainer.addView(designSpaceLoadingCard())
            loadDesignSpace(designSpaceContainer)
        }

        val sections = listOf(
            resultCard(result),
            curveResultCard(result),
            plySequenceResultCard(),
            LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                addView(xaiResultCard(result))
                addView(assistantCard(result), margin(top = 12))
            },
            designSpaceContainer,
        )
        val tabTitles = listOf(
            localText("Summary", "요약"),
            localText("Curve", "곡선"),
            "Ply Sequence",
            "XAI",
            localText("Design Space", "디자인 스페이스"),
        )
        val tabRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        val tabButtons = mutableListOf<Button>()
        tabTitles.forEachIndexed { index, title ->
            val button = Button(this).apply {
                text = title
                isAllCaps = false
                textSize = 12f
                minHeight = dp(48)
                useAppFont(Typeface.BOLD)
                setOnClickListener {
                    sections.forEachIndexed { sectionIndex, section -> section.visibility = if (sectionIndex == index) View.VISIBLE else View.GONE }
                    tabButtons.forEachIndexed { buttonIndex, item ->
                        item.setTextColor(if (buttonIndex == index) Color.WHITE else LaminateV2.muted)
                        item.background = if (buttonIndex == index) rounded(LaminateV2.blue, dp(999)) else strokedRounded(Color.WHITE, LaminateV2.line, dp(999))
                    }
                }
            }
            tabButtons.add(button)
            tabRow.addView(button, LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, dp(48)).apply {
                if (index > 0) marginStart = dp(6)
            })
        }
        root.addView(HorizontalScrollView(this).apply {
            isHorizontalScrollBarEnabled = false
            addView(tabRow)
        }, margin(top = 14))
        val sectionHost = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            sections.forEach { section ->
                section.visibility = View.GONE
                addView(section, margin(top = 12))
            }
        }
        root.addView(sectionHost)
        tabButtons.first().performClick()
        root.addView(backButton("Run another forecast"), margin(top = 16))
    }

    @Suppress("DEPRECATION")
    private fun readResult(): LaminateResult? {
        return intent.getSerializableExtra(EXTRA_LAMINATE_RESULT) as? LaminateResult
    }

    @Suppress("DEPRECATION")
    private fun readDesignSpace(): LaminateDesignSpaceInsight? {
        return intent.getSerializableExtra(EXTRA_LAMINATE_DESIGN_SPACE) as? LaminateDesignSpaceInsight
    }

    private fun readDesignSpaceError(): String? {
        return intent.getStringExtra(EXTRA_LAMINATE_DESIGN_SPACE_ERROR)
    }

    private fun readMode(): String {
        return intent.getStringExtra(EXTRA_LAMINATE_MODE) ?: "response"
    }

    private fun inputSummary(): LinearLayout {
        val caseName = intent.getStringExtra(EXTRA_LAMINATE_CASE) ?: "-"
        val theta1 = intent.getIntExtra(EXTRA_LAMINATE_THETA1, 0)
        val theta2 = intent.getIntExtra(EXTRA_LAMINATE_THETA2, 0)
        val panelA = intent.getDoubleExtra(EXTRA_LAMINATE_PANEL_A, Double.NaN)
        val panelB = intent.getDoubleExtra(EXTRA_LAMINATE_PANEL_B, Double.NaN)
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(14), dp(12), dp(14), dp(12))
            background = fieldBackground()
            addView(label("INPUTS", LaminateV2.blue, 11f, Typeface.BOLD))
            val row = LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                addView(summaryPill(if (readMode() == "u3") "u3 Forecast" else "Response"))
                addView(summaryPill(caseName), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                    marginStart = dp(8)
                })
                addView(summaryPill("θ₁ $theta1°"), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                    marginStart = dp(8)
                })
                addView(summaryPill("θ₂ $theta2°"), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                    marginStart = dp(8)
                })
            }
            addView(row, margin(top = 10))
            if (readMode() != "u3" && panelA.isFinite() && panelB.isFinite()) {
                addView(summaryPill("Panel ${formatDimension(panelA)} × ${formatDimension(panelB)} in"), margin(top = 8))
            }
        }
    }

    private fun resultCard(result: LaminateResult): LinearLayout {
        val card = card()
        val top = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        top.addView(LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(label("LATEST RESULT", LaminateV2.blue, 11f, Typeface.BOLD))
            addView(label("Type ${result.predictedType}", LaminateV2.ink, 36f, Typeface.BOLD).apply {
                includeFontPadding = false
            })
            addView(label(result.displayModelLabel, LaminateV2.muted, 14f, Typeface.BOLD))
        }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        top.addView(label(formatPercent(result.confidence), LaminateV2.green, 18f, Typeface.BOLD).apply {
            setPadding(dp(10), dp(7), dp(10), dp(7))
            background = greenSoftBackground()
        })
        card.addView(top)

        listOf(
            "Pt" to formatMetric(result.predictedPt, 2),
            "Pt displacement" to formatMetric(result.predictedPtDisplacement, 5),
            "Max force" to formatMetric(result.predictedMaxForce, 2),
            "Curve points" to result.curve.size.toString(),
        ).chunked(2).forEach { rowItems ->
            val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
            rowItems.forEachIndexed { index, item ->
                row.addView(metricBox(item.first, item.second), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                    if (index == 0) marginEnd = dp(8)
                })
            }
            card.addView(row, margin(top = 10))
        }

        result.uncertainty?.let {
            card.addView(uncertaintySection(it), margin(top = 14))
        }
        result.teacherStudent?.let {
            card.addView(teacherStudentSection(it), margin(top = 14))
        }

        card.addView(label("Class probability", LaminateV2.ink, 18f, Typeface.BOLD), margin(top = 16))
        result.probabilities.toSortedMap().forEach { (label, value) ->
            card.addView(label("$label  ${formatPercent(value)}", LaminateV2.muted, 13f, Typeface.BOLD), margin(top = 6))
        }

        return card
    }

    private fun curveResultCard(result: LaminateResult): LinearLayout = card().apply {
        addView(label(localText("Response curve", "응답 곡선"), LaminateV2.ink, 20f, Typeface.BOLD))
        addView(paragraph(localText("Inspect the predicted response shape and Pt marker without the summary competing for space.", "요약 정보와 분리해 예측 응답 형상과 Pt 마커를 확인합니다.")), margin(top = 6))
        if (result.curve.size >= 2) addView(responseCurveSection(result), margin(top = 12))
        else addView(paragraph(localText("Curve coordinates are not available for this run.", "이 실행에서는 곡선 좌표를 사용할 수 없습니다.")), margin(top = 12))
    }

    private fun plySequenceResultCard(): LinearLayout = card().apply {
        val caseName = intent.getStringExtra(EXTRA_LAMINATE_CASE) ?: "Case2"
        val theta1 = intent.getIntExtra(EXTRA_LAMINATE_THETA1, 0)
        val theta2 = intent.getIntExtra(EXTRA_LAMINATE_THETA2, 0)
        addView(label("Ply Sequence", LaminateV2.ink, 20f, Typeface.BOLD))
        addView(paragraph(localText("The stack reflects the selected Case and ply angles. Only P1 and P16 identify the sequence endpoints.", "선택한 Case와 각도를 반영한 적층 구조입니다. P1과 P16으로 순서의 양 끝만 구분합니다.")), margin(top = 6))
        addView(PlyStackPreviewView(this@LaminateResultActivity).apply {
            updateStack(caseName, theta1, theta2)
        }, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(260)).apply { topMargin = dp(12) })
    }

    private fun xaiResultCard(result: LaminateResult): LinearLayout = card().apply {
        val xai = result.xai
        if (xai == null) {
            addView(paragraph(localText("XAI is not available for this model run.", "이 모델 실행에서는 XAI를 제공하지 않습니다.")))
            return@apply
        }
        addView(label(localText("Why this prediction?", "왜 이런 예측이 나왔나요?"), LaminateV2.ink, 20f, Typeface.BOLD))
        addView(paragraph(LaminateXaiText.text(this@LaminateResultActivity, xai.summary)), margin(top = 6))
        val methodLabel = localText("Method", "방법")
        val featureSetLabel = localText("Feature set", "특징 세트")
        addView(label("$methodLabel: ${LaminateXaiText.text(this@LaminateResultActivity, xai.method)} - $featureSetLabel: ${LaminateXaiText.featureSet(this@LaminateResultActivity, xai.featureSet)}", LaminateV2.blue, 12f, Typeface.BOLD), margin(top = 8))
        xai.topFeatures.take(5).forEach { feature -> addView(xaiFeatureRow(feature), margin(top = 8)) }
        val hiddenFeatures = xai.topFeatures.drop(5)
        if (hiddenFeatures.isNotEmpty()) {
            val hiddenList = LinearLayout(this@LaminateResultActivity).apply {
                orientation = LinearLayout.VERTICAL
                visibility = View.GONE
                hiddenFeatures.forEach { feature -> addView(xaiFeatureRow(feature), margin(top = 8)) }
            }
            val toggle = Button(this@LaminateResultActivity).apply {
                text = localText("Show ${hiddenFeatures.size} more features", "나머지 ${hiddenFeatures.size}개 Feature 보기")
                isAllCaps = false
                minHeight = dp(44)
                setTextColor(LaminateV2.blue)
                useAppFont(Typeface.BOLD)
                background = blueSoftBackground()
                setOnClickListener {
                    val expanded = hiddenList.visibility != View.VISIBLE
                    hiddenList.visibility = if (expanded) View.VISIBLE else View.GONE
                    text = if (expanded) localText("Hide additional features", "추가 Feature 숨기기") else localText("Show ${hiddenFeatures.size} more features", "나머지 ${hiddenFeatures.size}개 Feature 보기")
                }
            }
            addView(toggle, margin(top = 10))
            addView(hiddenList)
        }
    }

    private fun uncertaintySection(uncertainty: LaminateUncertainty): LinearLayout {
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(12), dp(12), dp(12), dp(12))
            background = strokedRounded(LaminateV2.field, LaminateV2.line, dp(8))
        }
        val labelText = when (uncertainty.confidenceLabel) {
            "high" -> "High confidence"
            "medium" -> "Medium confidence"
            else -> "Use caution"
        }
        box.addView(LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            addView(label("Prediction reliability", LaminateV2.ink, 18f, Typeface.BOLD), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            addView(label(labelText, uncertaintyBadgeColor(uncertainty.confidenceLabel), 12f, Typeface.BOLD).apply {
                setPadding(dp(10), dp(6), dp(10), dp(6))
                background = rounded(uncertaintyBadgeBackground(uncertainty.confidenceLabel), dp(999))
            })
        })
        val range = if (uncertainty.ptIntervalLow != null && uncertainty.ptIntervalHigh != null) {
            "${formatMetric(uncertainty.ptIntervalLow, 0)} - ${formatMetric(uncertainty.ptIntervalHigh, 0)}"
        } else {
            "-"
        }
        val coverage = when (uncertainty.interpolationLabel) {
            "interpolation" -> "Interpolation"
            "near-edge" -> "Near edge"
            else -> "Extrapolation"
        }
        listOf(
            "Reliability" to formatPercent(uncertainty.reliabilityScore),
            "Pt range" to range,
            "Coverage" to coverage,
            "Type agreement" to formatPercent(uncertainty.typeConsistency),
        ).chunked(2).forEach { rowItems ->
            val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
            rowItems.forEachIndexed { index, item ->
                row.addView(metricBox(item.first, item.second), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                    if (index == 0) marginEnd = dp(8)
                })
            }
            box.addView(row, margin(top = 10))
        }
        uncertainty.notes.take(2).forEach { note ->
            box.addView(paragraph(note), margin(top = 8))
        }
        return box
    }

    private fun teacherStudentSection(agreement: LaminateTeacherStudentAgreement): LinearLayout {
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(12), dp(12), dp(12), dp(12))
            background = strokedRounded(LaminateV2.field, LaminateV2.line, dp(8))
        }
        val labelText = when (agreement.confidenceLabel) {
            "high" -> localText("High agreement", "높은 일치")
            "medium" -> localText("Medium agreement", "중간 일치")
            else -> localText("Low agreement", "낮은 일치")
        }
        box.addView(LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            addView(label(localText("Tree vs Student agreement", "Tree vs Student 일치도"), LaminateV2.ink, 18f, Typeface.BOLD), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            addView(label(labelText, uncertaintyBadgeColor(agreement.confidenceLabel), 12f, Typeface.BOLD).apply {
                setPadding(dp(10), dp(6), dp(10), dp(6))
                background = rounded(uncertaintyBadgeBackground(agreement.confidenceLabel), dp(999))
            })
        })
        val typeText = if (agreement.typeAgreement) {
            "${localText("Match", "일치")} · Type ${agreement.teacher.predictedType}"
        } else {
            "${localText("Mismatch", "불일치")} · T${agreement.teacher.predictedType} / S${agreement.student.predictedType}"
        }
        val curveText = agreement.curveNormRmse?.let { formatMetric(it * 100.0, 2) + "%" } ?: "-"
        val studentText = "Type ${agreement.student.predictedType}, Pt ${formatMetric(agreement.student.predictedPt, 0)}"
        listOf(
            localText("Agreement", "종합 일치도") to formatPercent(agreement.agreementScore),
            localText("Type comparison", "Type 비교") to typeText,
            localText("Pt delta", "Pt 차이") to "${formatMetric(agreement.ptDelta, 0)} (${formatPercent(agreement.ptDeltaPercent)})",
            localText("Curve delta", "곡선 차이") to curveText,
            localText("Student prediction", "Student 예측") to studentText,
        ).chunked(2).forEach { rowItems ->
            val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
            rowItems.forEachIndexed { index, item ->
                row.addView(metricBox(item.first, item.second), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                    if (index == 0) marginEnd = dp(8)
                })
            }
            box.addView(row, margin(top = 10))
        }
        agreement.notes.take(2).forEach { note ->
            box.addView(paragraph(teacherStudentNote(note)), margin(top = 8))
        }
        return box
    }

    private fun teacherStudentNote(note: String): String {
        if (!LaminateXaiText.isKoreanUi(this)) return note
        return when (note) {
            "Teacher is the deployment Tree model; Student is the distilled Hybrid neural model." ->
                "Teacher는 배포 기본 Tree 모델이고, Student는 distillation 기반 Hybrid 신경망 모델입니다."
            "Agreement compares Type, Pt, max force, and response-curve shape for the same theta/case input." ->
                "같은 θ/Case 입력에 대해 Type, Pt, 최대 하중, 응답 곡선 형태가 얼마나 일치하는지 비교합니다."
            "Tree and Student disagree on Type, so validate this candidate before treating the classification as stable." ->
                "Tree와 Student의 Type 예측이 달라서, 안정적인 분류로 보기 전에 추가 검증이 필요합니다."
            "Type agrees, but Pt differs by more than 8%; treat the Pt estimate as a screening value." ->
                "Type은 일치하지만 Pt 차이가 8%를 넘어, Pt 값은 screening 용도로 해석하는 것이 좋습니다."
            "Tree and Student are locally consistent, which supports using this result as an early screening candidate." ->
                "Tree와 Student가 일관된 결과를 보여, 초기 screening 후보로 활용하기에 비교적 안정적입니다."
            "Teacher/Student agreement is included as a deployment consistency check, not as a replacement for simulation validation." ->
                "Teacher/Student 일치도는 배포용 일관성 체크이며, 최종 해석 검증을 대체하지는 않습니다."
            else -> note
        }
    }

    private fun uncertaintyBadgeColor(label: String): Int = when (label) {
        "high" -> LaminateV2.green
        "medium" -> LaminateV2.amber
        else -> LaminateV2.red
    }

    private fun uncertaintyBadgeBackground(label: String): Int = when (label) {
        "high" -> Color.rgb(220, 252, 231)
        "medium" -> Color.rgb(254, 243, 199)
        else -> Color.rgb(254, 226, 226)
    }

    private fun assistantCard(result: LaminateResult): LinearLayout {
        val card = card()
        card.addView(label("LAMINATE AI ASSISTANT", LaminateV2.blue, 11f, Typeface.BOLD))
        card.addView(label("Ask about this prediction", LaminateV2.ink, 20f, Typeface.BOLD), margin(top = 4))
        card.addView(paragraph("The assistant uses the app's laminate knowledge base plus this result's Type, Pt, curve metrics, and XAI features."), margin(top = 6))

        val questionInput = EditText(this).apply {
            hint = if (readMode() == "u3") {
                "Explain why this u3 Pt forecast was predicted."
            } else {
                "Explain this prediction using the XAI result."
            }
            minLines = 3
            setTextColor(LaminateV2.ink)
            setHintTextColor(LaminateV2.muted)
            textSize = 14f
            setPadding(dp(10), dp(8), dp(10), dp(8))
            background = fieldBackground()
        }
        val answerText = paragraph("Ask a question after prediction to explain XAI drivers and laminate response behavior.")

        card.addView(questionInput, margin(top = 12))
        card.addView(Button(this).apply {
            text = "Ask Assistant"
            isAllCaps = false
            setTextColor(Color.WHITE)
            useAppFont(Typeface.BOLD)
            background = commandButtonBackground()
            setOnClickListener {
                val fallback = questionInput.hint?.toString().orEmpty()
                val question = questionInput.text?.toString()?.trim().orEmpty().ifBlank { fallback }
                if (question.length < 2) {
                    answerText.text = "Enter a question."
                    return@setOnClickListener
                }
                answerText.text = "Asking..."
                Thread {
                    val response = runCatching { askLaminateAssistant(question, result) }
                    runOnUiThread {
                        answerText.text = response.getOrElse { "Assistant failed: ${it.message ?: "Unknown error"}" }
                    }
                }.start()
            }
        }, margin(top = 10))
        card.addView(answerText, margin(top = 10))
        return card
    }

    private fun askLaminateAssistant(question: String, result: LaminateResult): String {
        val xaiFeatures = JSONArray().apply {
            result.xai?.topFeatures?.take(8)?.forEach { feature ->
                put(JSONObject()
                    .put("label", feature.label)
                    .put("category", feature.category)
                    .put("importance", feature.importance)
                    .put("explanation", feature.explanation))
            }
        }
        val context = JSONObject()
            .put("mode", if (readMode() == "u3") "u3 Forecast" else "Laminate Response")
            .put("case", intent.getStringExtra(EXTRA_LAMINATE_CASE) ?: "")
            .put("theta1", intent.getIntExtra(EXTRA_LAMINATE_THETA1, 0))
            .put("theta2", intent.getIntExtra(EXTRA_LAMINATE_THETA2, 0))
            .put("panel_a_in", intent.getDoubleExtra(EXTRA_LAMINATE_PANEL_A, 6.0))
            .put("panel_b_in", intent.getDoubleExtra(EXTRA_LAMINATE_PANEL_B, 4.0))
            .put("model_label", result.displayModelLabel)
            .put("predicted_type", result.predictedType)
            .put("predicted_pt", result.predictedPt ?: JSONObject.NULL)
            .put("predicted_pt_displacement", result.predictedPtDisplacement ?: JSONObject.NULL)
            .put("predicted_max_force", result.predictedMaxForce ?: JSONObject.NULL)
            .put("curve_points", result.curve.size)
            .put("xai", JSONObject()
                .put("summary", result.xai?.summary ?: "")
                .put("method", result.xai?.method ?: "")
                .put("feature_set", result.xai?.featureSet ?: "")
                .put("top_features", xaiFeatures))
        val body = JSONObject()
            .put("query", question)
            .put("top_k", 3)
            .put("use_llm", true)
            .put("language", "auto")
            .put("prediction_context", context)
            .toString()
        val json = JSONObject(requestRag("POST", URL("$LAMINATE_RAG_BASE_URL/api/v1/rag/answer"), body))
        return json.optString("answer", "No answer returned.")
    }

    private fun requestRag(method: String, url: URL, body: String): String {
        val connection = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 8_000
            readTimeout = 25_000
            doOutput = true
            setRequestProperty("Content-Type", "application/json")
        }
        connection.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
        val stream = if (connection.responseCode in 200..299) connection.inputStream else connection.errorStream
        val text = BufferedReader(InputStreamReader(stream)).use { it.readText() }
        if (connection.responseCode !in 200..299) error("HTTP ${connection.responseCode}: $text")
        return text
    }

    private fun responseCurveSection(result: LaminateResult): LinearLayout {
        val chartView = ResponseCurveChartView(this).apply {
            setBackgroundColor(LaminateV2.field)
            configure(result.curve, result.predictedPt, result.curveFit)
        }
        val zoomLabel = label("100%", LaminateV2.muted, 11f, Typeface.BOLD).apply {
            gravity = Gravity.CENTER
            setPadding(dp(8), dp(6), dp(8), dp(6))
            background = fieldBackground()
        }
        chartView.onZoomChanged = { zoom ->
            zoomLabel.text = "${(zoom * 100).toInt()}%"
        }
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(12), dp(12), dp(12), dp(12))
            background = fieldBackground()
            addView(LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                addView(LinearLayout(context).apply {
                    orientation = LinearLayout.VERTICAL
                    addView(label("RESPONSE CURVE", LaminateV2.blue, 11f, Typeface.BOLD))
                    addView(label("Force-displacement view", LaminateV2.muted, 11f, Typeface.BOLD))
                }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
                addView(curveZoomButton("−") { chartView.zoomBy(0.75f) })
                addView(zoomLabel, LinearLayout.LayoutParams(dp(56), LinearLayout.LayoutParams.WRAP_CONTENT).apply {
                    marginStart = dp(6)
                })
                addView(curveZoomButton("+") { chartView.zoomBy(1.35f) }, LinearLayout.LayoutParams(dp(34), LinearLayout.LayoutParams.WRAP_CONTENT).apply {
                    marginStart = dp(6)
                })
                addView(curveZoomButton("↺") { chartView.resetZoom() }, LinearLayout.LayoutParams(dp(34), LinearLayout.LayoutParams.WRAP_CONTENT).apply {
                    marginStart = dp(6)
                })
            })
            addView(chartView, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(330)).apply {
                topMargin = dp(10)
            })
            addView(curveLegend(), margin(top = 8))
        }
    }

    private fun curveZoomButton(text: String, onClick: () -> Unit): Button = Button(this).apply {
        this.text = text
        isAllCaps = false
        textSize = 13f
        setTextColor(LaminateV2.blue)
        useAppFont(Typeface.BOLD)
        setPadding(0, 0, 0, 0)
        background = blueSoftBackground()
        setOnClickListener { onClick() }
        layoutParams = LinearLayout.LayoutParams(dp(34), LinearLayout.LayoutParams.WRAP_CONTENT)
    }

    private fun curveLegend(): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.HORIZONTAL
        addView(curveLegendPill("Curve", LaminateV2.blue), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        addView(curveLegendPill("Linear fit", LaminateV2.red), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
            marginStart = dp(6)
        })
        addView(curveLegendPill("Fit intersection", Color.rgb(126, 34, 206)), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
            marginStart = dp(6)
        })
        addView(curveLegendPill("Predicted Pt", LaminateV2.red), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
            marginStart = dp(6)
        })
    }

    private fun curveLegendPill(text: String, color: Int): TextView = label("■ $text", color, 10f, Typeface.BOLD).apply {
        gravity = Gravity.CENTER
        setPadding(dp(5), dp(5), dp(5), dp(5))
        background = rounded(Color.WHITE, dp(999))
        maxLines = 1
    }

    private fun loadDesignSpace(container: LinearLayout) {
        val caseName = intent.getStringExtra(EXTRA_LAMINATE_CASE) ?: "Case2"
        val theta1 = intent.getIntExtra(EXTRA_LAMINATE_THETA1, 0).toDouble()
        val theta2 = intent.getIntExtra(EXTRA_LAMINATE_THETA2, 0).toDouble()
        val scope = if (readMode() == "u3") "u3" else "response"
        Thread {
            val result = runCatching {
                LaminateApi().designSpace(
                    caseName = caseName,
                    theta1 = theta1,
                    theta2 = theta2,
                    scope = scope,
                )
            }
            runOnUiThread {
                container.removeAllViews()
                result.onSuccess {
                    container.addView(designSpaceCard(it))
                }.onFailure {
                    container.addView(designSpaceUnavailableCard(it.message ?: "Unknown design-space error"))
                }
            }
        }.start()
    }

    private fun designSpaceCard(insight: LaminateDesignSpaceInsight): LinearLayout {
        val card = card()
        card.addView(label("RESEARCH INSIGHT", LaminateV2.blue, 11f, Typeface.BOLD))
        card.addView(label("Design-space context", LaminateV2.ink, 22f, Typeface.BOLD), margin(top = 4))
        card.addView(paragraph("Simulation-backed comparison for the current theta and Case input."), margin(top = 6))

        val candidate = insight.recommendations.firstOrNull()
        if (insight.mapPoints.isNotEmpty()) {
            card.addView(designSpaceMap(insight, candidate), margin(top = 14))
        } else {
            card.addView(paragraph("Design-space map unavailable: no map points were returned."), margin(top = 12))
        }

        candidate?.let {
            card.addView(label("Top candidate", LaminateV2.ink, 17f, Typeface.BOLD), margin(top = 16))
            card.addView(candidateSummary(it), margin(top = 8))
            card.addView(scoreBreakdown(it), margin(top = 8))
            if (it.rationale.isNotBlank()) {
                card.addView(label(it.rationale, LaminateV2.muted, 11f, Typeface.NORMAL), margin(top = 6))
            }
        }

        if (insight.caseInsights.isNotEmpty()) {
            card.addView(label("Case behavior zones", LaminateV2.ink, 17f, Typeface.BOLD), margin(top = 18))
            insight.caseInsights.take(3).forEach { item ->
                card.addView(caseInsightRow(item), margin(top = 8))
            }
        }
        return card
    }

    private fun designSpaceLoadingCard(): LinearLayout {
        val card = card()
        card.addView(label("RESEARCH INSIGHT", LaminateV2.blue, 11f, Typeface.BOLD))
        card.addView(label("Loading design-space map", LaminateV2.ink, 20f, Typeface.BOLD), margin(top = 4))
        card.addView(paragraph("The result is ready. Nearby experiment points and Case behavior zones will appear here when the design-space request returns."), margin(top = 6))
        card.addView(label("Fetching map points...", LaminateV2.blue, 12f, Typeface.BOLD).apply {
            setPadding(dp(10), dp(8), dp(10), dp(8))
            background = blueSoftBackground()
        }, margin(top = 10))
        return card
    }

    private fun designSpaceUnavailableCard(message: String): LinearLayout {
        val card = card()
        val detail = message.ifBlank { "No error detail was returned from the server." }
        card.addView(label("RESEARCH INSIGHT", LaminateV2.blue, 11f, Typeface.BOLD))
        card.addView(label("Design-space map unavailable", LaminateV2.ink, 20f, Typeface.BOLD), margin(top = 4))
        card.addView(paragraph("The response prediction completed, but the design-space request failed."), margin(top = 6))
        card.addView(label(detail, LaminateV2.red, 11f, Typeface.BOLD).apply {
            setPadding(dp(10), dp(8), dp(10), dp(8))
            background = fieldBackground()
        }, margin(top = 10))
        return card
    }

    private fun designSpaceMap(
        insight: LaminateDesignSpaceInsight,
        candidate: LaminateDesignSpaceRecommendation?,
    ): LinearLayout {
        val caseName = intent.getStringExtra(EXTRA_LAMINATE_CASE) ?: candidate?.caseName ?: insight.mapPoints.firstOrNull()?.caseName.orEmpty()
        val theta1 = intent.getIntExtra(EXTRA_LAMINATE_THETA1, 0).toDouble()
        val theta2 = intent.getIntExtra(EXTRA_LAMINATE_THETA2, 0).toDouble()
        val selectedInfo = label("Tap a dot to inspect Case, theta values, Pt, Type, and Test ID.", LaminateV2.muted, 11f, Typeface.BOLD).apply {
            setPadding(dp(10), dp(8), dp(10), dp(8))
            background = fieldBackground()
        }
        val nearbyPoints = insight.mapPoints.sortedBy { it.distance }.take(5)
        val mapView = DesignSpaceMapView(this).apply {
            setBackgroundColor(LaminateV2.field)
            configure(
                points = insight.mapPoints,
                currentCase = caseName,
                currentTheta1 = theta1,
                currentTheta2 = theta2,
                topCandidate = candidate,
            ) { point ->
                selectedInfo.text = pointInfo(point)
            }
        }
        nearbyPoints.firstOrNull()?.let { point ->
            selectedInfo.text = pointInfo(point)
            mapView.selectPoint(point, notify = false)
        }
        val mapScroll = HorizontalScrollView(this).apply {
            isHorizontalScrollBarEnabled = true
            overScrollMode = View.OVER_SCROLL_IF_CONTENT_SCROLLS
            addView(mapView, FrameLayout.LayoutParams(dp(560), dp(260)))
        }
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                addView(label("Design-space map", LaminateV2.muted, 12f, Typeface.BOLD), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
                addView(label("Tap dots or rows · scroll map", LaminateV2.blue, 11f, Typeface.BOLD))
            })
            addView(label("${insight.mapPoints.size} map points loaded", LaminateV2.blue, 11f, Typeface.BOLD).apply {
                setPadding(dp(10), dp(6), dp(10), dp(6))
                background = blueSoftBackground()
            }, margin(top = 6))
            addView(mapScroll, margin(top = 6))
            addView(selectedInfo, margin(top = 8))
            if (nearbyPoints.isNotEmpty()) {
                addView(label("Nearest experiment points", LaminateV2.muted, 11f, Typeface.BOLD), margin(top = 8))
                nearbyPoints.forEach { point ->
                    addView(designSpacePointButton(point, mapView, selectedInfo), margin(top = 6))
                }
            }
            addView(mapLegend(), margin(top = 8))
        }
    }

    private fun pointInfo(point: LaminateDesignSpacePoint): String {
        return "${point.caseName} · ${point.testId}\n" +
            "θ₁ ${point.theta1.degText()} · θ₂ ${point.theta2.degText()} · Pt ${formatMetric(point.pt, 2)} · ${typeText(point.observedType)}\n" +
            "Distance ${formatMetric(point.distance, 2)}"
    }

    private fun designSpacePointButton(
        point: LaminateDesignSpacePoint,
        mapView: DesignSpaceMapView,
        selectedInfo: TextView,
    ): Button = Button(this).apply {
        isAllCaps = false
        text = "${point.caseName} · ${point.testId}\n" +
            "θ₁ ${point.theta1.degText()} · θ₂ ${point.theta2.degText()} · Pt ${formatMetric(point.pt, 2)}"
        gravity = Gravity.CENTER_VERTICAL
        setTextColor(LaminateV2.ink)
        textSize = 11f
        typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        setPadding(dp(10), dp(7), dp(10), dp(7))
        background = blueSoftBackground()
        setOnClickListener {
            selectedInfo.text = pointInfo(point)
            mapView.selectPoint(point)
        }
    }

    private fun mapLegend(): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        addView(legendRow(listOf(
            "● Type 1" to LaminateV2.green,
            "● Type 2" to LaminateV2.blue,
            "● Type 3" to LaminateV2.red,
        )))
        addView(legendRow(listOf(
            "● Current" to Color.rgb(126, 34, 206),
            "◆ Candidate" to LaminateV2.amber,
        )), margin(top = 6))
    }

    private fun legendRow(items: List<Pair<String, Int>>): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.HORIZONTAL
        items.forEachIndexed { index, item ->
            addView(legendPill(item.first, item.second), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                if (index > 0) marginStart = dp(6)
            })
        }
    }

    private fun legendPill(text: String, color: Int): TextView = label(text, color, 10f, Typeface.BOLD).apply {
        gravity = Gravity.CENTER
        setPadding(dp(6), dp(5), dp(6), dp(5))
        background = fieldBackground()
    }

    private fun candidateSummary(candidate: LaminateDesignSpaceRecommendation): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(12), dp(10), dp(12), dp(10))
        background = fieldBackground()
        addView(label("${candidate.caseName}  θ₁ ${candidate.theta1.degText()}  θ₂ ${candidate.theta2.degText()}", LaminateV2.ink, 14f, Typeface.BOLD))
        addView(label("Expected Pt ${formatMetric(candidate.expectedPt, 2)} · ${typeText(candidate.observedType)}", LaminateV2.muted, 12f, Typeface.BOLD), margin(top = 4))
    }

    private fun scoreBreakdown(candidate: LaminateDesignSpaceRecommendation): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        addView(label("Recommendation score", LaminateV2.muted, 12f, Typeface.BOLD))
        val row = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            addView(scorePill("Pt", candidate.scoreComponents.pt), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            addView(scorePill("Type", candidate.scoreComponents.type), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                marginStart = dp(6)
            })
            addView(scorePill("Distance", candidate.scoreComponents.proximity), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                marginStart = dp(6)
            })
            addView(scorePill("Total", candidate.score), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                marginStart = dp(6)
            })
        }
        addView(row, margin(top = 6))
    }

    private fun scorePill(title: String, value: Double): TextView = label("$title\n${formatPercent(value)}", LaminateV2.blue, 10f, Typeface.BOLD).apply {
        gravity = Gravity.CENTER
        setPadding(dp(6), dp(6), dp(6), dp(6))
        background = blueSoftBackground()
    }

    private fun caseInsightRow(item: LaminateDesignSpaceCaseInsight): LinearLayout = LinearLayout(this).apply {
        val tint = caseAccent(item.caseName)
        orientation = LinearLayout.VERTICAL
        setPadding(dp(12), dp(12), dp(12), dp(12))
        background = caseInsightBackground(tint)
        addView(LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            addView(label(caseDisplayLabel(item.caseName), Color.WHITE, 12f, Typeface.BOLD).apply {
                setPadding(dp(9), dp(5), dp(9), dp(5))
                background = rounded(tint, dp(999))
            })
            addView(label(focusKindText(item.focusKind), tint, 11f, Typeface.BOLD).apply {
                maxLines = 1
            }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                marginStart = dp(8)
            })
            addView(label(formatPercent(item.focusRate), tint, 12f, Typeface.BOLD))
        })

        addView(label("Theta range", LaminateV2.muted, 10f, Typeface.BOLD), margin(top = 10))
        addView(LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            addView(thetaRangeChip("θ₁", item.theta1Min, item.theta1Max, tint), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            addView(thetaRangeChip("θ₂", item.theta2Min, item.theta2Max, tint), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                marginStart = dp(8)
            })
        }, margin(top = 5))

        addView(LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            addView(LinearLayout(context).apply {
                orientation = LinearLayout.VERTICAL
                addView(label("Best Pt", LaminateV2.muted, 10f, Typeface.BOLD))
                addView(label(formatMetric(item.bestPt, 2), LaminateV2.ink, 12f, Typeface.BOLD))
            }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            addView(LinearLayout(context).apply {
                orientation = LinearLayout.VERTICAL
                gravity = Gravity.END
                addView(label(typeText(item.bestType), tint, 12f, Typeface.BOLD))
                addView(label("${item.focusCount}/${item.count}", LaminateV2.muted, 10f, Typeface.BOLD))
            })
        }, margin(top = 10))
    }

    private fun thetaRangeChip(labelText: String, min: Double?, max: Double?, tint: Int): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(10), dp(8), dp(10), dp(8))
        background = strokedRounded(Color.WHITE, withAlpha(tint, 56), dp(8))
        addView(label(labelText, tint, 10f, Typeface.BOLD))
        addView(label(rangeText(min, max), LaminateV2.ink, 12f, Typeface.BOLD).apply {
            maxLines = 1
        }, margin(top = 2))
    }

    private fun xaiFeatureRow(feature: LaminateXaiFeature): LinearLayout = LinearLayout(this).apply {
        val safeImportance = feature.importance.coerceIn(0.0, 1.0)
        orientation = LinearLayout.VERTICAL
        setPadding(0, dp(6), 0, dp(6))
        addView(LinearLayout(this@LaminateResultActivity).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            addView(label(LaminateXaiText.text(this@LaminateResultActivity, feature.label), LaminateV2.ink, 12f, Typeface.BOLD).apply {
                maxLines = 1
            }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            addView(label(LaminateXaiText.category(this@LaminateResultActivity, feature.category), LaminateV2.blue, 10f, Typeface.BOLD).apply {
                setPadding(dp(6), dp(2), dp(6), dp(2))
                background = blueSoftBackground()
            })
        })
        addView(LinearLayout(this@LaminateResultActivity).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            addView(FrameLayout(this@LaminateResultActivity).apply {
                background = rounded(LaminateV2.line, dp(999))
                addView(View(this@LaminateResultActivity).apply {
                    background = rounded(LaminateV2.blue, dp(999))
                    layoutParams = FrameLayout.LayoutParams(dp(6), FrameLayout.LayoutParams.MATCH_PARENT)
                })
                post {
                    val fill = getChildAt(0)
                    val params = fill.layoutParams as FrameLayout.LayoutParams
                    params.width = maxOf(dp(6), (width * safeImportance).toInt())
                    fill.layoutParams = params
                    fill.requestLayout()
                }
            }, LinearLayout.LayoutParams(0, dp(5), 1f))
            addView(label(formatPercent(safeImportance), LaminateV2.blue, 11f, Typeface.BOLD).apply {
                gravity = Gravity.END
            }, LinearLayout.LayoutParams(dp(56), LinearLayout.LayoutParams.WRAP_CONTENT))
        }, margin(top = 4))
        addView(label(LaminateXaiText.text(this@LaminateResultActivity, feature.explanation), LaminateV2.muted, 11f, Typeface.NORMAL), margin(top = 3))
    }

    private fun localText(en: String, ko: String): String =
        if (LaminateXaiText.isKoreanUi(this)) ko else en

    private fun summaryPill(text: String): TextView = label(text, LaminateV2.blue, 12f, Typeface.BOLD).apply {
        gravity = Gravity.CENTER
        setPadding(dp(8), dp(6), dp(8), dp(6))
        background = blueSoftBackground()
    }

    private fun metricBox(title: String, value: String): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(12), dp(10), dp(12), dp(10))
        background = fieldBackground()
        addView(label(title, LaminateV2.muted, 12f, Typeface.BOLD))
        addView(label(value, LaminateV2.ink, 16f, Typeface.BOLD))
    }

    private fun backButton(text: String): Button = Button(this).apply {
        this.text = text
        setTextColor(Color.WHITE)
        useAppFont(Typeface.BOLD)
        background = commandButtonBackground()
        setOnClickListener { finish() }
    }

    private fun formatMetric(value: Double?, digits: Int): String = value?.let { "%.${digits}f".format(it) } ?: "-"

    private fun formatPercent(value: Double?): String = value?.let { "%.1f%%".format(it * 100.0) } ?: "-"

    private fun formatDimension(value: Double): String {
        val rounded = kotlin.math.round(value * 1000.0) / 1000.0
        return if (rounded % 1.0 == 0.0) {
            rounded.toInt().toString()
        } else {
            "%.3f".format(rounded).trimEnd('0').trimEnd('.')
        }
    }

    private fun Double.degText(): String = "%+.0f°".format(this)

    private fun typeText(value: Int?): String = value?.let { "Type $it" } ?: "Type -"

    private fun focusKindText(value: String): String = when (value) {
        "type1" -> "Type 1 zone"
        "high_pt" -> "High Pt zone"
        else -> value
    }

    private fun rangeText(min: Double?, max: Double?): String {
        if (min == null || max == null) return "-"
        return "${min.degText()} ~ ${max.degText()}"
    }

    private fun caseDisplayLabel(caseName: String): String = when (caseName) {
        "Case2" -> "Case 2"
        "Case3" -> "Case 3"
        "Case4" -> "Case 4"
        else -> caseName
    }

    private fun caseAccent(caseName: String): Int = when (caseName) {
        "Case2" -> LaminateV2.blue
        "Case3" -> LaminateV2.cyan
        "Case4" -> LaminateV2.amber
        else -> LaminateV2.muted
    }

    private fun caseInsightBackground(tint: Int) = android.graphics.drawable.GradientDrawable(
        android.graphics.drawable.GradientDrawable.Orientation.TL_BR,
        intArrayOf(withAlpha(tint, 42), withAlpha(tint, 18)),
    ).apply {
        cornerRadius = dp(8).toFloat()
        setStroke(dp(1), withAlpha(tint, 86))
    }

    private fun withAlpha(color: Int, alpha: Int): Int {
        return Color.argb(alpha, Color.red(color), Color.green(color), Color.blue(color))
    }

    private fun card(): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(18), dp(18), dp(18), dp(18))
        background = strokedRounded(Color.WHITE, LaminateV2.line, dp(8))
        elevation = dp(1).toFloat()
    }

    private fun paragraph(text: String): TextView = label(text, LaminateV2.muted, 15f, Typeface.NORMAL).apply {
        setLineSpacing(dp(3).toFloat(), 1.0f)
    }

    private fun label(text: String, textColor: Int, size: Float, style: Int): TextView = TextView(this).apply {
        this.text = text
        textSize = size
        setTextColor(textColor)
        useAppFont(style)
    }

    private fun margin(top: Int = 0, bottom: Int = 0): LinearLayout.LayoutParams =
        LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
            topMargin = dp(top)
            bottomMargin = dp(bottom)
        }

    private fun rounded(fill: Int, radius: Int) = android.graphics.drawable.GradientDrawable().apply {
        setColor(fill)
        cornerRadius = radius.toFloat()
    }

    private fun fieldBackground() = android.graphics.drawable.GradientDrawable().apply {
        setColor(LaminateV2.field)
        cornerRadius = dp(8).toFloat()
        setStroke(dp(1), LaminateV2.line)
    }

    private fun commandButtonBackground() = android.graphics.drawable.GradientDrawable().apply {
        orientation = android.graphics.drawable.GradientDrawable.Orientation.LEFT_RIGHT
        colors = intArrayOf(LaminateV2.ink, LaminateV2.blue)
        cornerRadius = dp(8).toFloat()
    }

    private fun blueSoftBackground() = android.graphics.drawable.GradientDrawable().apply {
        setColor(LaminateV2.blueSoft)
        cornerRadius = dp(999).toFloat()
        setStroke(dp(1), LaminateV2.blueLine)
    }

    private fun greenSoftBackground() = android.graphics.drawable.GradientDrawable().apply {
        setColor(LaminateV2.greenSoft)
        cornerRadius = dp(999).toFloat()
        setStroke(dp(1), LaminateV2.greenLine)
    }

    private fun strokedRounded(fill: Int, stroke: Int, radius: Int) = android.graphics.drawable.GradientDrawable().apply {
        setColor(fill)
        setStroke(dp(1), stroke)
        cornerRadius = radius.toFloat()
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}

private class ResponseCurveChartView(context: Context) : View(context) {
    private var curve: List<LaminateCurvePoint> = emptyList()
    private var predictedPt: Double? = null
    private var curveFit: LaminateCurveFit? = null
    private var zoomScale = 1f
    private var panX = 0f
    private var panY = 0f
    private var lastX = 0f
    private var lastY = 0f
    private var downX = 0f
    private var downY = 0f
    private var gestureMoved = false
    private var isScrubbingCurve = false
    private var selectedCurvePoint: LaminateCurvePoint? = null
    var onZoomChanged: ((Float) -> Unit)? = null

    private val scaleDetector = ScaleGestureDetector(context, object : ScaleGestureDetector.SimpleOnScaleGestureListener() {
        private var startScale = 1f
        private var startPanX = 0f
        private var startPanY = 0f

        override fun onScaleBegin(detector: ScaleGestureDetector): Boolean {
            startScale = zoomScale
            startPanX = panX
            startPanY = panY
            parent?.requestDisallowInterceptTouchEvent(true)
            return true
        }

        override fun onScale(detector: ScaleGestureDetector): Boolean {
            applyCenteredZoom(
                nextScale = (startScale * detector.scaleFactor).coerceIn(1f, 5f),
                startScale = startScale,
                startPanX = startPanX,
                startPanY = startPanY,
            )
            onZoomChanged?.invoke(zoomScale)
            invalidate()
            return true
        }

        override fun onScaleEnd(detector: ScaleGestureDetector) {
            clampPan(chartPlot())
        }
    })

    private val plotPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(242, 246, 249, 251)
        style = Paint.Style.FILL
    }
    private val gridPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(58, 99, 113, 128)
        strokeWidth = dp(1).toFloat()
        style = Paint.Style.STROKE
    }
    private val axisPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(118, 99, 113, 128)
        strokeWidth = dp(1).toFloat()
        style = Paint.Style.STROKE
    }
    private val curvePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = LaminateV2.blue
        strokeWidth = dp(3).toFloat()
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeJoin = Paint.Join.ROUND
    }
    private val fitPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = LaminateV2.red
        strokeWidth = dp(2).toFloat()
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        pathEffect = DashPathEffect(floatArrayOf(dp(7).toFloat(), dp(5).toFloat()), 0f)
    }
    private val kinkPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(126, 34, 206)
        strokeWidth = dp(2).toFloat()
        style = Paint.Style.STROKE
        pathEffect = DashPathEffect(floatArrayOf(dp(7).toFloat(), dp(4).toFloat()), 0f)
    }
    private val markerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
        color = Color.WHITE
    }
    private val markerStrokePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeWidth = dp(2).toFloat()
        color = Color.rgb(126, 34, 206)
    }
    private val predictedPtPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
        color = LaminateV2.red
    }
    private val predictedPtStrokePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeWidth = dp(2).toFloat()
        color = Color.WHITE
    }
    private val labelPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = LaminateV2.muted
        textSize = sp(10)
        typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
    }
    private val calloutPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(126, 34, 206)
        textSize = sp(11)
        typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
    }
    private val selectionPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(82, 16, 18, 21)
        strokeWidth = dp(1).toFloat()
        style = Paint.Style.STROKE
        pathEffect = DashPathEffect(floatArrayOf(dp(4).toFloat(), dp(4).toFloat()), 0f)
    }
    private val selectedPointPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        style = Paint.Style.FILL
    }
    private val selectedPointStrokePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = LaminateV2.blue
        strokeWidth = dp(3).toFloat()
        style = Paint.Style.STROKE
    }
    private val selectedTextPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = LaminateV2.ink
        textSize = sp(10)
        typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
    }

    init {
        isClickable = true
        isFocusable = true
        minimumHeight = dp(320)
    }

    fun configure(points: List<LaminateCurvePoint>, predictedPt: Double?, curveFit: LaminateCurveFit?) {
        curve = points.filter { it.displacement.isFinite() && it.force.isFinite() }.sortedBy { it.displacement }
        this.predictedPt = predictedPt?.takeIf { it.isFinite() }
        this.curveFit = curveFit
        zoomScale = 1f
        panX = 0f
        panY = 0f
        selectedCurvePoint = null
        onZoomChanged?.invoke(zoomScale)
        invalidate()
    }

    fun zoomBy(factor: Float) {
        applyCenteredZoom(
            nextScale = (zoomScale * factor).coerceIn(1f, 5f),
            startScale = zoomScale,
            startPanX = panX,
            startPanY = panY,
        )
        onZoomChanged?.invoke(zoomScale)
        invalidate()
    }

    fun resetZoom() {
        zoomScale = 1f
        panX = 0f
        panY = 0f
        onZoomChanged?.invoke(zoomScale)
        invalidate()
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val desiredHeight = maxOf(minimumHeight, dp(320))
        setMeasuredDimension(resolveSize(dp(320), widthMeasureSpec), resolveSize(desiredHeight, heightMeasureSpec))
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val plot = chartPlot()
        canvas.drawRoundRect(plot, dp(8).toFloat(), dp(8).toFloat(), plotPaint)
        val domain = visibleDomain(plot) ?: return

        drawGrid(canvas, plot, domain)
        val fit = activeFit()

        canvas.save()
        canvas.clipRect(plot)
        drawCurve(canvas, plot, domain)
        fit?.let {
            drawFit(canvas, plot, domain, it)
            drawKink(canvas, plot, domain, it)
        }
        drawPredictedPt(canvas, plot, domain)
        canvas.restore()

        selectedCurvePoint?.let {
            drawSelectedCurvePoint(canvas, plot, domain, it)
        }
        drawAxisLabels(canvas, plot)
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        scaleDetector.onTouchEvent(event)
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                downX = event.x
                downY = event.y
                lastX = event.x
                lastY = event.y
                gestureMoved = false
                isScrubbingCurve = startCurveScrub(event.x, event.y)
                parent?.requestDisallowInterceptTouchEvent(isScrubbingCurve || zoomScale > 1.01f)
            }
            MotionEvent.ACTION_POINTER_DOWN -> {
                gestureMoved = true
                isScrubbingCurve = false
                parent?.requestDisallowInterceptTouchEvent(true)
            }
            MotionEvent.ACTION_MOVE -> {
                if (hypot((event.x - downX).toDouble(), (event.y - downY).toDouble()) > dp(6)) {
                    gestureMoved = true
                }
                if (!scaleDetector.isInProgress && isScrubbingCurve) {
                    updateCurveScrub(event.x, event.y)
                    parent?.requestDisallowInterceptTouchEvent(true)
                    invalidate()
                    lastX = event.x
                    lastY = event.y
                    return true
                }
                if (!scaleDetector.isInProgress && zoomScale > 1.01f) {
                    val dx = event.x - lastX
                    val dy = event.y - lastY
                    panX += dx
                    panY += dy
                    clampPan(chartPlot())
                    selectedCurvePoint = null
                    parent?.requestDisallowInterceptTouchEvent(true)
                    invalidate()
                }
                lastX = event.x
                lastY = event.y
            }
            MotionEvent.ACTION_UP -> {
                if (!scaleDetector.isInProgress) {
                    if (isScrubbingCurve) {
                        updateCurveScrub(event.x, event.y)
                        invalidate()
                    } else if (!gestureMoved) {
                        updateCurveTap(event.x, event.y)
                    }
                }
                isScrubbingCurve = false
                parent?.requestDisallowInterceptTouchEvent(false)
                performClick()
            }
            MotionEvent.ACTION_CANCEL -> {
                isScrubbingCurve = false
                parent?.requestDisallowInterceptTouchEvent(false)
                performClick()
            }
        }
        return true
    }

    override fun performClick(): Boolean {
        super.performClick()
        return true
    }

    private fun chartPlot(): RectF {
        return RectF(dp(54).toFloat(), dp(30).toFloat(), width - dp(18).toFloat(), height - dp(54).toFloat())
    }

    private fun drawGrid(canvas: Canvas, plot: RectF, domain: CurveDomain) {
        tickValues(domain.minY, domain.maxY).forEach { value ->
            val y = y(value, plot, domain)
            canvas.drawLine(plot.left, y, plot.right, y, gridPaint)
            labelPaint.textAlign = Paint.Align.RIGHT
            canvas.drawText(value.axisText(2), plot.left - dp(6), y + dp(4), labelPaint)
        }
        tickValues(domain.minX, domain.maxX).forEach { value ->
            val x = x(value, plot, domain)
            canvas.drawLine(x, plot.top, x, plot.bottom, gridPaint)
            labelPaint.textAlign = Paint.Align.CENTER
            canvas.drawText(value.axisText(4), x, plot.bottom + dp(18), labelPaint)
        }
        canvas.drawRect(plot, axisPaint)
    }

    private fun drawCurve(canvas: Canvas, plot: RectF, domain: CurveDomain) {
        if (curve.size < 2) return
        val path = Path()
        curve.forEachIndexed { index, point ->
            val px = x(point.displacement, plot, domain)
            val py = y(point.force, plot, domain)
            if (index == 0) path.moveTo(px, py) else path.lineTo(px, py)
        }
        canvas.drawPath(path, curvePaint)
    }

    private fun drawFit(canvas: Canvas, plot: RectF, domain: CurveDomain, fit: ChartFit) {
        val path = Path()
        path.moveTo(x(fit.firstStartX, plot, domain), y(fit.firstLine.y(fit.firstStartX), plot, domain))
        path.lineTo(x(fit.firstEndX, plot, domain), y(fit.firstLine.y(fit.firstEndX), plot, domain))
        path.moveTo(x(fit.secondStartX, plot, domain), y(fit.secondLine.y(fit.secondStartX), plot, domain))
        path.lineTo(x(fit.secondEndX, plot, domain), y(fit.secondLine.y(fit.secondEndX), plot, domain))
        canvas.drawPath(path, fitPaint)
    }

    private fun drawKink(canvas: Canvas, plot: RectF, domain: CurveDomain, fit: ChartFit) {
        val kx = x(fit.kink.displacement, plot, domain)
        val ky = y(fit.kink.force, plot, domain)
        canvas.drawLine(kx, plot.top, kx, plot.bottom, kinkPaint)

        val radius = dp(7).toFloat()
        val diamond = Path().apply {
            moveTo(kx, ky - radius)
            lineTo(kx + radius, ky)
            lineTo(kx, ky + radius)
            lineTo(kx - radius, ky)
            close()
        }
        canvas.drawPath(diamond, markerPaint)
        canvas.drawPath(diamond, markerStrokePaint)

        val label = "Fit ${fit.kink.force.metricText(2)}"
        val labelWidth = calloutPaint.measureText(label) + dp(16)
        val labelLeft = (kx + dp(10)).coerceAtMost(plot.right - labelWidth).coerceAtLeast(plot.left + dp(4))
        val labelTop = (ky - dp(34)).coerceAtLeast(plot.top + dp(6))
        val rect = RectF(labelLeft, labelTop, labelLeft + labelWidth, labelTop + dp(26))
        val bubblePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.argb(232, 255, 255, 255)
            style = Paint.Style.FILL
        }
        val bubbleStroke = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.argb(118, 126, 34, 206)
            style = Paint.Style.STROKE
            strokeWidth = dp(1).toFloat()
        }
        canvas.drawRoundRect(rect, dp(8).toFloat(), dp(8).toFloat(), bubblePaint)
        canvas.drawRoundRect(rect, dp(8).toFloat(), dp(8).toFloat(), bubbleStroke)
        canvas.drawText(label, rect.left + dp(8), rect.bottom - dp(9), calloutPaint)
    }

    private fun drawPredictedPt(canvas: Canvas, plot: RectF, domain: CurveDomain) {
        val target = predictedPt ?: return
        val marker = pointAtForce(target) ?: return
        if (marker.displacement !in domain.minX..domain.maxX || marker.force !in domain.minY..domain.maxY) return
        val px = x(marker.displacement, plot, domain)
        val py = y(marker.force, plot, domain)
        val radius = dp(6).toFloat()
        canvas.drawCircle(px, py, radius, predictedPtPaint)
        canvas.drawCircle(px, py, radius, predictedPtStrokePaint)
    }

    private fun drawSelectedCurvePoint(canvas: Canvas, plot: RectF, domain: CurveDomain, point: LaminateCurvePoint) {
        if (point.displacement !in domain.minX..domain.maxX || point.force !in domain.minY..domain.maxY) return
        val px = x(point.displacement, plot, domain)
        val py = y(point.force, plot, domain)
        if (px !in plot.left..plot.right || py !in plot.top..plot.bottom) return

        canvas.drawLine(px, plot.top, px, plot.bottom, selectionPaint)
        canvas.drawLine(plot.left, py, plot.right, py, selectionPaint)
        canvas.drawCircle(px, py, dp(7).toFloat(), selectedPointPaint)
        canvas.drawCircle(px, py, dp(7).toFloat(), selectedPointStrokePaint)

        val firstLine = "x ${point.displacement.metricText(4)}"
        val secondLine = "y ${point.force.metricText(2)}"
        val labelWidth = maxOf(selectedTextPaint.measureText(firstLine), selectedTextPaint.measureText(secondLine)) + dp(18)
        val labelHeight = dp(38).toFloat()
        val labelLeft = (px + dp(12)).coerceAtMost(plot.right - labelWidth).coerceAtLeast(plot.left + dp(4))
        val labelTop = (py - dp(42)).coerceAtLeast(plot.top + dp(6))
        val rect = RectF(labelLeft, labelTop, labelLeft + labelWidth, labelTop + labelHeight)
        val bubblePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.argb(236, 255, 255, 255)
            style = Paint.Style.FILL
        }
        val bubbleStroke = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.argb(72, 37, 99, 235)
            style = Paint.Style.STROKE
            strokeWidth = dp(1).toFloat()
        }
        canvas.drawRoundRect(rect, dp(8).toFloat(), dp(8).toFloat(), bubblePaint)
        canvas.drawRoundRect(rect, dp(8).toFloat(), dp(8).toFloat(), bubbleStroke)
        canvas.drawText(firstLine, rect.left + dp(8), rect.top + dp(15), selectedTextPaint)
        canvas.drawText(secondLine, rect.left + dp(8), rect.top + dp(30), selectedTextPaint)
    }

    private fun drawAxisLabels(canvas: Canvas, plot: RectF) {
        labelPaint.textAlign = Paint.Align.CENTER
        canvas.drawText("Displacement", plot.centerX(), height - dp(12).toFloat(), labelPaint)
        labelPaint.textAlign = Paint.Align.LEFT
        canvas.drawText("Force", dp(12).toFloat(), plot.centerY(), labelPaint)
        labelPaint.textAlign = Paint.Align.CENTER
    }

    private fun visibleDomain(plot: RectF): CurveDomain? {
        val full = fullDomain() ?: return null
        val scale = zoomScale.toDouble().coerceAtLeast(1.0)
        val xSpan = (full.maxX - full.minX).coerceAtLeast(1e-12)
        val ySpan = (full.maxY - full.minY).coerceAtLeast(1e-12)
        val startX = (-panX / (plot.width() * zoomScale)).toDouble().coerceIn(0.0, 1.0 - 1.0 / scale)
        val startY = (panY / (plot.height() * zoomScale)).toDouble().coerceIn(0.0, 1.0 - 1.0 / scale)
        val minX = full.minX + xSpan * startX
        val minY = full.minY + ySpan * startY
        return CurveDomain(
            minX = minX,
            maxX = minX + xSpan / scale,
            minY = minY,
            maxY = minY + ySpan / scale,
        )
    }

    private fun fullDomain(): CurveDomain? {
        if (curve.size < 2) return null
        val minX = curve.minOf { it.displacement }
        val maxX = curve.maxOf { it.displacement }
        val yValues = curve.map { it.force }.toMutableList()
        predictedPt?.let { yValues.add(it) }
        activeFit()?.let { fit ->
            yValues.add(fit.firstLine.y(fit.firstStartX))
            yValues.add(fit.firstLine.y(fit.firstEndX))
            yValues.add(fit.secondLine.y(fit.secondStartX))
            yValues.add(fit.secondLine.y(fit.secondEndX))
            yValues.add(fit.kink.force)
        }
        val minY = minOf(0.0, yValues.minOrNull() ?: 0.0)
        val maxY = (yValues.maxOrNull() ?: 1.0).coerceAtLeast(1.0) * 1.06
        if (maxX <= minX || maxY <= minY) return null
        return CurveDomain(minX, maxX, minY, maxY)
    }

    private fun activeFit(): ChartFit? {
        backendFit()?.let { return it }
        return fallbackFit()
    }

    private fun backendFit(): ChartFit? {
        val fit = curveFit ?: return null
        val first = fit.firstLine ?: return null
        val second = fit.secondLine ?: return null
        val kink = fit.kink ?: return null
        val minX = curve.minOfOrNull { it.displacement } ?: return null
        val maxX = curve.maxOfOrNull { it.displacement } ?: return null
        return ChartFit(
            kink = CurveXY(kink.displacement, kink.force),
            firstLine = ChartLine(first.slope, first.intercept),
            secondLine = ChartLine(second.slope, second.intercept),
            firstStartX = fit.firstStartX ?: minX,
            firstEndX = fit.firstEndX ?: kink.displacement,
            secondStartX = fit.secondStartX ?: kink.displacement,
            secondEndX = fit.secondEndX ?: maxX,
        )
    }

    private fun fallbackFit(): ChartFit? {
        if (curve.size < 2) return null
        val first = curve.first()
        val last = curve.last()
        val kink = predictedPt?.let { pointAtForce(it) }
            ?: curve.getOrNull(curve.size / 2)?.let { CurveXY(it.displacement, it.force) }
            ?: return null
        val firstLine = ChartLine.from(first.displacement, first.force, kink.displacement, kink.force) ?: return null
        val secondLine = ChartLine.from(kink.displacement, kink.force, last.displacement, last.force) ?: return null
        return ChartFit(
            kink = kink,
            firstLine = firstLine,
            secondLine = secondLine,
            firstStartX = first.displacement,
            firstEndX = kink.displacement,
            secondStartX = kink.displacement,
            secondEndX = last.displacement,
        )
    }

    private fun pointAtForce(force: Double): CurveXY? {
        val first = curve.firstOrNull() ?: return null
        if (force <= first.force) return CurveXY(first.displacement, force)
        for (index in 1 until curve.size) {
            val previous = curve[index - 1]
            val current = curve[index]
            val low = minOf(previous.force, current.force)
            val high = maxOf(previous.force, current.force)
            if (force < low || force > high) continue
            val delta = current.force - previous.force
            if (abs(delta) < 1e-12) return CurveXY(current.displacement, current.force)
            val ratio = (force - previous.force) / delta
            return CurveXY(
                previous.displacement + ratio * (current.displacement - previous.displacement),
                force,
            )
        }
        return curve.lastOrNull()?.let { CurveXY(it.displacement, force) }
    }

    private fun startCurveScrub(touchX: Float, touchY: Float): Boolean {
        val plot = chartPlot()
        val domain = visibleDomain(plot) ?: return false
        if (!plot.contains(touchX, touchY)) return false
        val nearest = nearestCurvePoint(touchX, touchY, plot, domain) ?: return false
        if (zoomScale > 1.01f && screenDistance(nearest, touchX, touchY, plot, domain) > dp(44)) {
            return false
        }
        selectedCurvePoint = nearest
        invalidate()
        return true
    }

    private fun updateCurveTap(touchX: Float, touchY: Float) {
        val plot = chartPlot()
        val domain = visibleDomain(plot) ?: return
        selectedCurvePoint = nearestCurvePoint(touchX, touchY, plot, domain)
        invalidate()
    }

    private fun updateCurveScrub(touchX: Float, touchY: Float) {
        val plot = chartPlot()
        val domain = visibleDomain(plot) ?: return
        val clampedX = touchX.coerceIn(plot.left + 1f, plot.right - 1f)
        val clampedY = touchY.coerceIn(plot.top + 1f, plot.bottom - 1f)
        selectedCurvePoint = nearestCurvePoint(clampedX, clampedY, plot, domain)
    }

    private fun nearestCurvePoint(touchX: Float, touchY: Float, plot: RectF, domain: CurveDomain): LaminateCurvePoint? {
        if (!plot.contains(touchX, touchY)) return null
        return curve.minByOrNull { point ->
            abs(x(point.displacement, plot, domain) - touchX)
        }
    }

    private fun screenDistance(point: LaminateCurvePoint, touchX: Float, touchY: Float, plot: RectF, domain: CurveDomain): Double {
        val dx = x(point.displacement, plot, domain) - touchX
        val dy = y(point.force, plot, domain) - touchY
        return hypot(dx.toDouble(), dy.toDouble())
    }

    private fun applyCenteredZoom(nextScale: Float, startScale: Float, startPanX: Float, startPanY: Float) {
        val plot = chartPlot()
        if (nextScale <= 1.01f) {
            zoomScale = 1f
            panX = 0f
            panY = 0f
            return
        }
        val safeStartScale = startScale.coerceAtLeast(1f)
        val anchorX = plot.width() / 2f
        val anchorFromBottom = plot.height() / 2f
        val normalizedX = (anchorX - startPanX) / (plot.width() * safeStartScale).coerceAtLeast(1f)
        val normalizedY = (anchorFromBottom + startPanY) / (plot.height() * safeStartScale).coerceAtLeast(1f)
        zoomScale = nextScale
        panX = anchorX - normalizedX * plot.width() * nextScale
        panY = normalizedY * plot.height() * nextScale - anchorFromBottom
        clampPan(plot)
    }

    private fun clampPan(plot: RectF) {
        if (zoomScale <= 1.01f) {
            panX = 0f
            panY = 0f
            return
        }
        val minX = plot.width() * (1f - zoomScale)
        val maxY = plot.height() * (zoomScale - 1f)
        panX = panX.coerceIn(minX, 0f)
        panY = panY.coerceIn(0f, maxY)
    }

    private fun tickValues(min: Double, max: Double, count: Int = 5): List<Double> {
        if (count <= 1 || max <= min) return listOf(min)
        return (0 until count).map { index -> min + (max - min) * index / (count - 1) }
    }

    private fun x(value: Double, plot: RectF, domain: CurveDomain): Float {
        return (plot.left + ((value - domain.minX) / (domain.maxX - domain.minX)).toFloat() * plot.width())
    }

    private fun y(value: Double, plot: RectF, domain: CurveDomain): Float {
        return (plot.bottom - ((value - domain.minY) / (domain.maxY - domain.minY)).toFloat() * plot.height())
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    private fun sp(value: Int): Float {
        return TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_SP, value.toFloat(), resources.displayMetrics)
    }

    private fun Double.metricText(digits: Int): String = "%.${digits}f".format(this)

    private fun Double.axisText(smallValueDigits: Int): String {
        val absolute = abs(this)
        val digits = when {
            absolute >= 100 -> 0
            absolute >= 10 -> 1
            absolute >= 1 -> 2
            else -> smallValueDigits
        }
        return "%.${digits}f".format(this).trimEnd('0').trimEnd('.').let { if (it == "-0") "0" else it }
    }
}

private data class CurveDomain(val minX: Double, val maxX: Double, val minY: Double, val maxY: Double)
private data class CurveXY(val displacement: Double, val force: Double)
private data class ChartLine(val slope: Double, val intercept: Double) {
    fun y(x: Double): Double = slope * x + intercept

    companion object {
        fun from(x1: Double, y1: Double, x2: Double, y2: Double): ChartLine? {
            val dx = x2 - x1
            if (abs(dx) < 1e-12) return null
            val slope = (y2 - y1) / dx
            return ChartLine(slope, y1 - slope * x1)
        }
    }
}
private data class ChartFit(
    val kink: CurveXY,
    val firstLine: ChartLine,
    val secondLine: ChartLine,
    val firstStartX: Double,
    val firstEndX: Double,
    val secondStartX: Double,
    val secondEndX: Double,
)

private class DesignSpaceMapView(context: Context) : View(context) {
    private var points: List<LaminateDesignSpacePoint> = emptyList()
    private var currentCase: String = ""
    private var currentTheta1: Double = 0.0
    private var currentTheta2: Double = 0.0
    private var topCandidate: LaminateDesignSpaceRecommendation? = null
    private var selectedPoint: LaminateDesignSpacePoint? = null
    private var onPointSelected: ((LaminateDesignSpacePoint) -> Unit)? = null
    private var downX = 0f
    private var downY = 0f

    private val gridPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(38, 91, 107, 128)
        strokeWidth = dp(1).toFloat()
        style = Paint.Style.STROKE
    }
    private val borderPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(92, 91, 107, 128)
        strokeWidth = dp(1).toFloat()
        style = Paint.Style.STROKE
    }
    private val plotPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(242, 246, 249, 251)
        style = Paint.Style.FILL
    }
    private val dotPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
    }
    private val markerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
    }
    private val markerStrokePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeWidth = dp(3).toFloat()
    }
    private val textPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = LaminateV2.muted
        textSize = sp(10)
        typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        textAlign = Paint.Align.CENTER
    }

    init {
        isClickable = true
        isFocusable = true
        minimumWidth = dp(560)
        minimumHeight = dp(260)
    }

    fun configure(
        points: List<LaminateDesignSpacePoint>,
        currentCase: String,
        currentTheta1: Double,
        currentTheta2: Double,
        topCandidate: LaminateDesignSpaceRecommendation?,
        onPointSelected: (LaminateDesignSpacePoint) -> Unit,
    ) {
        this.points = points
        this.currentCase = currentCase
        this.currentTheta1 = currentTheta1
        this.currentTheta2 = currentTheta2
        this.topCandidate = topCandidate
        this.onPointSelected = onPointSelected
        invalidate()
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val desiredWidth = maxOf(minimumWidth, dp(560))
        val desiredHeight = maxOf(minimumHeight, dp(260))
        setMeasuredDimension(
            resolveSize(desiredWidth, widthMeasureSpec),
            resolveSize(desiredHeight, heightMeasureSpec),
        )
    }

    fun selectPoint(point: LaminateDesignSpacePoint, notify: Boolean = true) {
        selectedPoint = point
        if (notify) {
            onPointSelected?.invoke(point)
        }
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val plot = RectF(dp(48).toFloat(), dp(22).toFloat(), width - dp(22).toFloat(), height - dp(42).toFloat())
        canvas.drawRoundRect(plot, dp(8).toFloat(), dp(8).toFloat(), plotPaint)

        listOf(-90, -45, 0, 45, 90).forEach { tick ->
            val tickValue = tick.toDouble()
            val tickX = x(tickValue, plot)
            val tickY = y(tickValue, plot)
            canvas.drawLine(tickX, plot.top, tickX, plot.bottom, gridPaint)
            canvas.drawLine(plot.left, tickY, plot.right, tickY, gridPaint)
            canvas.drawText(tick.toString(), tickX, plot.bottom + dp(16), textPaint)
            textPaint.textAlign = Paint.Align.RIGHT
            canvas.drawText(tick.toString(), plot.left - dp(8), tickY + dp(4), textPaint)
            textPaint.textAlign = Paint.Align.CENTER
        }
        canvas.drawRect(plot, borderPaint)

        val maxPt = points.maxOfOrNull { it.pt }?.coerceAtLeast(1.0) ?: 1.0
        points.forEach { point ->
            val sameCase = point.caseName == currentCase
            dotPaint.color = withAlpha(typeColor(point.observedType), if (sameCase) 188 else 62)
            val radius = dp(3).toFloat() + (dp(5).toFloat() * (point.pt / maxPt).coerceIn(0.0, 1.0).toFloat())
            canvas.drawCircle(x(point.theta1, plot), y(point.theta2, plot), radius, dotPaint)
        }

        selectedPoint?.let { point ->
            markerStrokePaint.color = Color.argb(164, 12, 19, 28)
            canvas.drawCircle(x(point.theta1, plot), y(point.theta2, plot), dp(12).toFloat(), markerStrokePaint)
        }

        topCandidate?.let { candidate ->
            drawCandidate(canvas, x(candidate.theta1, plot), y(candidate.theta2, plot))
        }
        drawCurrentInput(canvas, x(currentTheta1, plot), y(currentTheta2, plot))

        canvas.drawText("θ₁", plot.centerX(), height - dp(10).toFloat(), textPaint)
        textPaint.textAlign = Paint.Align.LEFT
        canvas.drawText("θ₂", dp(10).toFloat(), plot.centerY(), textPaint)
        textPaint.textAlign = Paint.Align.CENTER
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        return when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                downX = event.x
                downY = event.y
                parent?.requestDisallowInterceptTouchEvent(true)
                true
            }
            MotionEvent.ACTION_MOVE -> {
                val moved = hypot((event.x - downX).toDouble(), (event.y - downY).toDouble())
                if (moved > dp(20)) {
                    parent?.requestDisallowInterceptTouchEvent(false)
                }
                true
            }
            MotionEvent.ACTION_UP -> {
                val moved = hypot((event.x - downX).toDouble(), (event.y - downY).toDouble())
                if (moved <= dp(20)) {
                    nearestPoint(event.x, event.y)?.let { point ->
                        selectPoint(point)
                    }
                }
                parent?.requestDisallowInterceptTouchEvent(false)
                performClick()
                true
            }
            MotionEvent.ACTION_CANCEL -> {
                parent?.requestDisallowInterceptTouchEvent(false)
                true
            }
            else -> true
        }
    }

    override fun performClick(): Boolean {
        super.performClick()
        return true
    }

    private fun nearestPoint(touchX: Float, touchY: Float): LaminateDesignSpacePoint? {
        val plot = RectF(dp(48).toFloat(), dp(22).toFloat(), width - dp(22).toFloat(), height - dp(42).toFloat())
        return points
            .map { point ->
                val dx = x(point.theta1, plot) - touchX
                val dy = y(point.theta2, plot) - touchY
                point to hypot(dx.toDouble(), dy.toDouble())
            }
            .minByOrNull { it.second }
            ?.takeIf { it.second <= dp(48) }
            ?.first
    }

    private fun drawCurrentInput(canvas: Canvas, centerX: Float, centerY: Float) {
        markerPaint.color = Color.WHITE
        canvas.drawCircle(centerX, centerY, dp(10).toFloat(), markerPaint)
        markerStrokePaint.color = Color.argb(96, 126, 34, 206)
        markerStrokePaint.strokeWidth = dp(5).toFloat()
        canvas.drawCircle(centerX, centerY, dp(10).toFloat(), markerStrokePaint)
        markerPaint.color = Color.rgb(126, 34, 206)
        canvas.drawCircle(centerX, centerY, dp(5).toFloat(), markerPaint)
        markerStrokePaint.strokeWidth = dp(3).toFloat()
    }

    private fun drawCandidate(canvas: Canvas, centerX: Float, centerY: Float) {
        val radius = dp(8).toFloat()
        val diamond = Path().apply {
            moveTo(centerX, centerY - radius)
            lineTo(centerX + radius, centerY)
            lineTo(centerX, centerY + radius)
            lineTo(centerX - radius, centerY)
            close()
        }
        markerPaint.color = Color.WHITE
        canvas.drawPath(diamond, markerPaint)
        markerStrokePaint.color = Color.rgb(217, 119, 6)
        markerStrokePaint.strokeWidth = dp(2).toFloat()
        canvas.drawPath(diamond, markerStrokePaint)
        markerStrokePaint.strokeWidth = dp(3).toFloat()
    }

    private fun x(value: Double, plot: RectF): Float {
        return plot.left + (((value + 90.0) / 180.0).coerceIn(0.0, 1.0).toFloat() * plot.width())
    }

    private fun y(value: Double, plot: RectF): Float {
        return plot.bottom - (((value + 90.0) / 180.0).coerceIn(0.0, 1.0).toFloat() * plot.height())
    }

    private fun typeColor(type: Int?): Int = when (type) {
        1 -> LaminateV2.green
        2 -> LaminateV2.blue
        3 -> LaminateV2.red
        else -> LaminateV2.muted
    }

    private fun withAlpha(color: Int, alpha: Int): Int {
        return Color.argb(alpha, Color.red(color), Color.green(color), Color.blue(color))
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    private fun sp(value: Int): Float {
        return TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_SP, value.toFloat(), resources.displayMetrics)
    }
}
