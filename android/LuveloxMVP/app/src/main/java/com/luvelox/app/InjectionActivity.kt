package com.luvelox.app

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
import android.view.Gravity
import android.view.View
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.ScrollView
import android.widget.Spinner
import android.widget.TextView
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL

private const val INJECTION_BASE_URL = "https://injection.luvelox.com"
private const val DEFAULT_SPRUE_MODEL = "sprue_classical"
private const val DEFAULT_FILLING_MODEL = "filling_classical"
private const val INJECTION_HISTORY_PREFS = "injection_history"
private const val INJECTION_HISTORY_KEY = "recent_runs_v1"

class InjectionActivity : Activity() {
    private lateinit var statusText: TextView
    private lateinit var geometrySpinner: Spinner
    private lateinit var processSpinner: Spinner
    private lateinit var sprueModelSpinner: Spinner
    private lateinit var fillingModelSpinner: Spinner
    private lateinit var valuesGrid: LinearLayout
    private lateinit var resultContainer: LinearLayout

    private var sprueModels: List<InjectionModelInfo> = emptyList()
    private var fillingModels: List<InjectionModelInfo> = emptyList()
    private var geometries: List<InjectionDoeOption> = emptyList()
    private var processes: List<InjectionDoeOption> = emptyList()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        render()
        loadCatalog()
    }

    private fun render() {
        val scroll = ScrollView(this).apply { setBackgroundColor(color(0xF9FAFC)) }
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(24), dp(20), dp(44))
        }
        scroll.addView(root)
        setContentView(scroll)

        root.addView(label("INJECTION MODULE", color(0x0BA7C9), 12f, Typeface.BOLD))
        root.addView(label("Sprue Pressure Forecast", color(0x101215), 32f, Typeface.BOLD))
        root.addView(paragraph("Run Moldex3D-style sprue pressure and filling pressure prediction directly inside C2ES."), margin(top = 8, bottom = 16))

        val inputCard = card()
        val header = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        header.addView(label("Inputs", color(0x101215), 18f, Typeface.BOLD), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        statusText = label("Checking", color(0x0BA7C9), 12f, Typeface.BOLD).apply {
            setPadding(dp(10), dp(6), dp(10), dp(6))
            background = rounded(color(0xE2F7FB), dp(999))
        }
        header.addView(statusText)
        inputCard.addView(header)

        val selectionRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        geometrySpinner = Spinner(this)
        processSpinner = Spinner(this)
        selectionRow.addView(inputBlock("Geometry", geometrySpinner), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply { marginEnd = dp(8) })
        selectionRow.addView(inputBlock("Process", processSpinner), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply { marginStart = dp(8) })
        inputCard.addView(selectionRow, margin(top = 14))

        sprueModelSpinner = Spinner(this)
        fillingModelSpinner = Spinner(this)
        inputCard.addView(inputBlock("Sprue model", sprueModelSpinner), margin(top = 14))
        inputCard.addView(inputBlock("Filling model", fillingModelSpinner), margin(top = 14))

        valuesGrid = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        inputCard.addView(valuesGrid, margin(top = 14))

        inputCard.addView(Button(this).apply {
            text = "Predict pressure"
            setTextColor(Color.WHITE)
            useAppFont(Typeface.BOLD)
            background = commandButtonBackground()
            setOnClickListener { predict() }
        }, margin(top = 16))
        root.addView(inputCard)

        resultContainer = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        root.addView(resultContainer, margin(top = 16))
        renderHistoryPanel()
    }

    private fun loadCatalog() {
        Thread {
            val loaded = runCatching { InjectionApiNative().catalog() }
            runOnUiThread {
                loaded.onSuccess { catalog ->
                    sprueModels = catalog.sprueModels.filter { it.available }.ifEmpty {
                        listOf(InjectionModelInfo(DEFAULT_SPRUE_MODEL, "Machine Learning", true))
                    }
                    fillingModels = catalog.fillingModels.filter { it.available }.ifEmpty {
                        listOf(InjectionModelInfo(DEFAULT_FILLING_MODEL, "Machine Learning", true))
                    }
                    geometries = catalog.geometries.ifEmpty { listOf(fallbackGeometry()) }
                    processes = catalog.processes.ifEmpty { listOf(fallbackProcess()) }
                    bindSpinners()
                    statusText.text = "API ready"
                    statusText.setTextColor(color(0x0BA7C9))
                    renderValues()
                }.onFailure {
                    sprueModels = listOf(InjectionModelInfo(DEFAULT_SPRUE_MODEL, "Machine Learning", true))
                    fillingModels = listOf(InjectionModelInfo(DEFAULT_FILLING_MODEL, "Machine Learning", true))
                    geometries = listOf(fallbackGeometry())
                    processes = listOf(fallbackProcess())
                    bindSpinners()
                    statusText.text = "Offline"
                    statusText.setTextColor(color(0xB42318))
                    renderValues()
                }
            }
        }.start()
    }

    private fun bindSpinners() {
        geometrySpinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, geometries.map { it.id })
        processSpinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, processes.map { it.id })
        sprueModelSpinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, sprueModels.map { it.displayLabel })
        fillingModelSpinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, fillingModels.map { it.displayLabel })
        geometrySpinner.setSelection(defaultIndex(geometries, "G01"), false)
        processSpinner.setSelection(defaultIndex(processes, "P01"), false)
        geometrySpinner.setOnItemSelectedListener(simpleSelectionListener { renderValues() })
        processSpinner.setOnItemSelectedListener(simpleSelectionListener { renderValues() })
    }

    private fun defaultIndex(options: List<InjectionDoeOption>, preferredId: String): Int =
        options.indexOfFirst { it.id == preferredId }.takeIf { it >= 0 } ?: 0

    private fun simpleSelectionListener(onSelected: () -> Unit) = object : android.widget.AdapterView.OnItemSelectedListener {
        override fun onItemSelected(parent: android.widget.AdapterView<*>?, view: android.view.View?, position: Int, id: Long) = onSelected()
        override fun onNothingSelected(parent: android.widget.AdapterView<*>?) = Unit
    }

    private fun renderValues() {
        valuesGrid.removeAllViews()
        val geometry = selectedGeometry()
        val process = selectedProcess()
        val processValues = listOf(
            InjectionDetailValue("Melt temp", "${process.double("melt_temp_C").metricText(1)} C", percent(process.double("melt_temp_C"), 180.0, 320.0)),
            InjectionDetailValue("Mold temp", "${process.double("mold_temp_C").metricText(1)} C", percent(process.double("mold_temp_C"), 20.0, 130.0)),
            InjectionDetailValue("Packing pressure", "${process.double("packing_pressure_MPa").metricText(1)} MPa", percent(process.double("packing_pressure_MPa"), 10.0, 130.0)),
            InjectionDetailValue("Injection time", "${process.double("injection_time_s").metricText(3)} s", percent(process.double("injection_time_s"), 0.2, 4.0)),
            InjectionDetailValue("Packing time", "${process.double("packing_time_s").metricText(3)} s", percent(process.double("packing_time_s"), 0.2, 8.0)),
        )
        val geometryValues = listOf(
            InjectionDetailValue("L", "${geometry.double("L_mm").metricText(1)} mm", percent(geometry.double("L_mm"), 20.0, 140.0)),
            InjectionDetailValue("W", "${geometry.double("W_mm").metricText(1)} mm", percent(geometry.double("W_mm"), 20.0, 120.0)),
            InjectionDetailValue("Thickness", "${geometry.double("t_mm").metricText(2)} mm", percent(geometry.double("t_mm"), 0.5, 5.0)),
            InjectionDetailValue("Hole D", "${geometry.double("D_mm").metricText(1)} mm", percent(geometry.double("D_mm"), 0.0, 80.0)),
            InjectionDetailValue("Hole R", "${geometry.double("R_mm").metricText(1)} mm", percent(geometry.double("R_mm"), 0.0, 40.0)),
            InjectionDetailValue("Gate type", geometry.string("gate_type") ?: "-"),
            InjectionDetailValue("Gate width", "${geometry.double("gate_size_width_mm").metricText(1)} mm", percent(geometry.double("gate_size_width_mm"), 0.0, 30.0)),
            InjectionDetailValue("Gate height", "${geometry.double("gate_size_height_mm").metricText(2)} mm", percent(geometry.double("gate_size_height_mm"), 0.0, 5.0)),
        )
        valuesGrid.addView(shapePreviewSection(geometry))
        valuesGrid.addView(detailSection("Process details", processValues))
        valuesGrid.addView(detailSection("Geometry details", geometryValues), margin(top = 10))
    }

    private fun shapePreviewSection(geometry: InjectionDoeOption): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(8), dp(8), dp(8), dp(8))
        background = strokedRounded(Color.WHITE, color(0xDAE3EC), dp(8))
        val header = LinearLayout(this@InjectionActivity).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        header.addView(LinearLayout(this@InjectionActivity).apply {
            orientation = LinearLayout.VERTICAL
            addView(label("Shape Preview", color(0x0BA7C9), 12f, Typeface.BOLD))
            addView(label("DOE-driven geometry", color(0x101215), 18f, Typeface.BOLD))
        }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        header.addView(label("${geometry.id} / ${geometry.string("gate_type") ?: "-"}", color(0x0BA7C9), 12f, Typeface.BOLD).apply {
            setPadding(dp(9), dp(5), dp(9), dp(5))
            background = rounded(color(0xE2F7FB), dp(999))
        })
        addView(header)
        addView(InjectionShapePreviewView(this@InjectionActivity).apply {
            configure(
                lengthMm = geometry.double("L_mm") ?: 154.01,
                widthMm = geometry.double("W_mm") ?: 97.42,
                thicknessMm = geometry.double("t_mm") ?: 2.207,
                holeDiameterMm = geometry.double("D_mm") ?: 17.61,
                gateWidthMm = geometry.double("gate_size_width_mm") ?: 10.0,
                gateHeightMm = geometry.double("gate_size_height_mm") ?: 1.5,
            )
        }, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(210)).apply {
            topMargin = dp(10)
        })
    }

    private fun detailSection(title: String, values: List<InjectionDetailValue>): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(8), dp(8), dp(8), dp(8))
        background = strokedRounded(Color.WHITE, color(0xDAE3EC), dp(8))
        addView(label(title, color(0x637180), 12f, Typeface.BOLD))
        values.chunked(2).forEach { rowItems ->
            val row = LinearLayout(this@InjectionActivity).apply { orientation = LinearLayout.HORIZONTAL }
            rowItems.forEachIndexed { index, item ->
                val params = if (rowItems.size == 1) {
                    LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
                } else {
                    LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                        if (index == 0) marginEnd = dp(4) else marginStart = dp(4)
                    }
                }
                row.addView(detailBox(item), params)
            }
            addView(row, margin(top = 8))
        }
    }

    private fun detailBox(item: InjectionDetailValue): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.HORIZONTAL
        gravity = Gravity.CENTER_VERTICAL
        setPadding(dp(8), dp(7), dp(8), dp(7))
        background = strokedRounded(color(0xF6F9FB), color(0xDAE3EC), dp(8))

        val left = LinearLayout(this@InjectionActivity).apply {
            orientation = LinearLayout.VERTICAL
            addView(label(item.title, color(0x44556A), 12f, Typeface.BOLD).apply {
                maxLines = 1
                ellipsize = android.text.TextUtils.TruncateAt.END
            })
            addView(label(item.value, color(0x1451D8), 12f, Typeface.BOLD), margin(top = 2))
            if (item.percent != null) {
                addView(ProgressBar(this@InjectionActivity, null, android.R.attr.progressBarStyleHorizontal).apply {
                    max = 100
                    progress = item.percent
                    progressDrawable = rounded(color(0x1451D8), dp(999))
                    progressBackgroundTintList = android.content.res.ColorStateList.valueOf(color(0xE4ECF4))
                    minHeight = dp(5)
                    maxHeight = dp(5)
                }, margin(top = 4))
            } else {
                addView(View(this@InjectionActivity).apply {
                    background = rounded(color(0xE4ECF4), dp(999))
                }, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(5)).apply { topMargin = dp(4) })
            }
        }
        addView(left, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        addView(label(item.value, color(0x101215), 14f, Typeface.BOLD).apply {
            gravity = Gravity.CENTER
            maxLines = 1
            ellipsize = android.text.TextUtils.TruncateAt.END
            setPadding(dp(8), dp(7), dp(8), dp(7))
            background = strokedRounded(Color.WHITE, color(0xCAD8E4), dp(8))
        }, LinearLayout.LayoutParams(dp(88), LinearLayout.LayoutParams.WRAP_CONTENT).apply { marginStart = dp(8) })
    }

    private fun percent(value: Double?, min: Double, max: Double): Int {
        if (value == null || max <= min) return 0
        return (((value - min) / (max - min)) * 100.0).coerceIn(0.0, 100.0).toInt()
    }

    private fun predict() {
        val geometry = selectedGeometry()
        val process = selectedProcess()
        val sprueModel = sprueModels.getOrNull(sprueModelSpinner.selectedItemPosition)?.key ?: DEFAULT_SPRUE_MODEL
        val fillingModel = fillingModels.getOrNull(fillingModelSpinner.selectedItemPosition)?.key ?: DEFAULT_FILLING_MODEL
        val input = InjectionNativeInput(
            geometryId = geometry.id,
            processId = process.id,
            sprueModelKey = sprueModel,
            fillingModelKey = fillingModel,
            lMm = geometry.double("L_mm") ?: 154.01,
            wMm = geometry.double("W_mm") ?: 97.42,
            tMm = geometry.double("t_mm") ?: 2.207,
            dMm = geometry.double("D_mm") ?: 17.61,
            rMm = geometry.double("R_mm"),
            gateType = geometry.string("gate_type") ?: "edge_gate",
            gateWidthMm = geometry.double("gate_size_width_mm") ?: 10.0,
            gateHeightMm = geometry.double("gate_size_height_mm") ?: 1.5,
            meltTempC = process.double("melt_temp_C") ?: 226.1,
            moldTempC = process.double("mold_temp_C") ?: 61.7,
            injectionTimeS = process.double("injection_time_s") ?: 2.47,
            packingPressureMPa = process.double("packing_pressure_MPa") ?: 69.0,
            packingTimeS = process.double("packing_time_s") ?: 4.731,
        )
        statusText.text = "Predicting"
        Thread {
            val result = runCatching { InjectionApiNative().predict(input) }
            runOnUiThread {
                result.onSuccess {
                    statusText.text = "API ready"
                    saveRecentRun(input, it)
                    renderResult(it)
                }.onFailure {
                    showError("Prediction failed: ${it.message ?: "Unknown error"}")
                }
            }
        }.start()
    }

    private fun renderResult(result: InjectionNativeResult) {
        resultContainer.removeAllViews()
        val card = card()
        val top = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        top.addView(LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(label(result.predictedMaxPressureMPa.metricText(2), color(0x101215), 34f, Typeface.BOLD))
            addView(label("Max sprue pressure MPa", color(0x637180), 14f, Typeface.BOLD))
        }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        top.addView(label("${result.predictedMaxTimeS.metricText(3)} s", color(0x0A9F69), 18f, Typeface.BOLD))
        card.addView(top)

        listOf(
            "Sprue model" to result.displayModelLabel,
            "Filling model" to result.displayFillingModelLabel,
            "Curve points" to result.curveCount.toString(),
            "Fill bins" to result.fillingBins.size.toString(),
        ).chunked(2).forEach { rowItems ->
            val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
            rowItems.forEach { (name, value) ->
                row.addView(metricBox(name, value), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply { marginEnd = dp(8) })
            }
            card.addView(row, margin(top = 10))
        }

        if (result.fillingBins.isNotEmpty()) {
            card.addView(label("Filling pressure", color(0x101215), 18f, Typeface.BOLD), margin(top = 16))
            result.fillingBins.take(5).forEach { bin ->
                card.addView(label("Group ${bin.group}  ${bin.volumeRatioPct.metricText(1)}%", color(0x637180), 13f, Typeface.BOLD), margin(top = 6))
            }
        }
        if (result.xaiFeatures.isNotEmpty()) {
            card.addView(xaiSection(result.xaiFeatures), margin(top = 16))
        }
        card.addView(assistantSection(result), margin(top = 16))
        resultContainer.addView(card)
        renderHistoryPanel()
    }

    private fun xaiSection(features: List<InjectionXaiFeature>): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(12), dp(12), dp(12), dp(12))
        background = strokedRounded(color(0xF6F9FB), color(0xDAE3EC), dp(8))
        addView(label("Injection XAI", color(0x0BA7C9), 12f, Typeface.BOLD))
        addView(label(if (isKoreanUi()) "예측 영향 인자" else "Feature influence", color(0x101215), 18f, Typeface.BOLD), margin(top = 2))
        addView(paragraph(if (isKoreanUi()) "현재 입력에서 형상, 공정, 게이트 feature가 예측에 미친 영향을 보여줍니다." else "Top process, geometry, and gate descriptors used by the prediction."), margin(top = 4))

        features.take(5).forEach { feature ->
            addView(xaiFeatureRow(feature), margin(top = 10))
        }
    }

    private fun xaiFeatureRow(feature: InjectionXaiFeature): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(10), dp(10), dp(10), dp(10))
        background = strokedRounded(Color.WHITE, color(0xDAE3EC), dp(8))

        val header = LinearLayout(this@InjectionActivity).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        header.addView(label(localizedXaiLabel(feature), color(0x101215), 13f, Typeface.BOLD).apply {
            maxLines = 1
            ellipsize = android.text.TextUtils.TruncateAt.END
        }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        header.addView(label("${(feature.importance * 100.0).metricText(1)}%", color(0x0BA7C9), 13f, Typeface.BOLD))
        addView(header)

        val percent = (feature.importance.coerceIn(0.0, 1.0) * 100).toInt().coerceAtLeast(1)
        val bar = LinearLayout(this@InjectionActivity).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(0, 0, 0, 0)
            background = rounded(color(0xE4ECF4), dp(999))
            addView(View(this@InjectionActivity).apply {
                background = rounded(color(0x0BA7C9), dp(999))
            }, LinearLayout.LayoutParams(0, dp(7), percent.toFloat()))
            addView(View(this@InjectionActivity), LinearLayout.LayoutParams(0, dp(7), (100 - percent).toFloat()))
        }
        addView(bar, margin(top = 6))

        if (feature.explanation.isNotBlank()) {
            addView(paragraph(localizedXaiExplanation(feature)).apply {
                maxLines = 2
                ellipsize = android.text.TextUtils.TruncateAt.END
            }, margin(top = 6))
        }
    }

    private fun assistantSection(result: InjectionNativeResult): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(12), dp(12), dp(12), dp(12))
        background = strokedRounded(color(0xF6F9FB), color(0xDAE3EC), dp(8))
        addView(label("Injection AI Assistant", color(0x0BA7C9), 12f, Typeface.BOLD))
        addView(label(if (isKoreanUi()) "현재 예측에 대해 질문하기" else "Ask about this prediction", color(0x101215), 18f, Typeface.BOLD), margin(top = 2))

        val questionInput = EditText(this@InjectionActivity).apply {
            setText(if (isKoreanUi()) "수지 온도가 예측 Sprue Pressure에 왜 영향을 주나요?" else "Why is melt temperature influential in this prediction?")
            minLines = 3
            setTextColor(color(0x101215))
            textSize = 14f
            setPadding(dp(10), dp(8), dp(10), dp(8))
            background = strokedRounded(Color.WHITE, color(0xCAD8E4), dp(8))
        }
        addView(questionInput, margin(top = 10))

        val answerBlock = assistantAnswerBlock(if (isKoreanUi()) "예측 후 질문을 실행하면 XAI 영향 인자를 설명합니다." else "Run a question after prediction to explain XAI drivers.")
        addView(Button(this@InjectionActivity).apply {
            text = if (isKoreanUi()) "Injection AI에 질문" else "Ask Injection AI"
            setTextColor(Color.WHITE)
            useAppFont(Typeface.BOLD)
            background = commandButtonBackground()
            setOnClickListener {
                val question = questionInput.text?.toString()?.trim().orEmpty()
                if (question.length < 2) {
                    renderAssistantAnswer(answerBlock, if (isKoreanUi()) "질문을 입력해 주세요." else "Enter a question.")
                    return@setOnClickListener
                }
                renderAssistantAnswer(answerBlock, if (isKoreanUi()) "질문 중..." else "Asking...")
                Thread {
                    val answer = runCatching { InjectionApiNative().answer(question, result, if (isKoreanUi()) "ko" else "en") }
                    runOnUiThread {
                        renderAssistantAnswer(answerBlock, answer.getOrElse {
                            if (isKoreanUi()) "Assistant 응답에 실패했습니다: ${it.message ?: "Unknown error"}" else "Assistant failed: ${it.message ?: "Unknown error"}"
                        })
                    }
                }.start()
            }
        }, margin(top = 10))
        addView(answerBlock, margin(top = 10))
    }

    private fun renderHistoryPanel() {
        val runs = loadRecentRuns()
        val card = card()
        card.addView(LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            addView(LinearLayout(this@InjectionActivity).apply {
                orientation = LinearLayout.VERTICAL
                addView(label(if (isKoreanUi()) "예측 기록" else "Prediction history", color(0x101215), 18f, Typeface.BOLD))
                addView(paragraph(if (isKoreanUi()) "카드를 누르면 이전 DOE 설정을 다시 불러옵니다." else "Tap a card to reuse its DOE setup."), margin(top = 3))
            }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            addView(label(runs.size.toString(), color(0x0BA7C9), 12f, Typeface.BOLD).apply {
                setPadding(dp(10), dp(6), dp(10), dp(6))
                background = rounded(color(0xE2F7FB), dp(999))
            })
        })
        if (runs.isEmpty()) {
            card.addView(paragraph(if (isKoreanUi()) "Injection 예측을 실행하면 최근 예측 카드가 여기에 표시됩니다." else "Run an Injection forecast and recent prediction cards will appear here."), margin(top = 12))
        } else {
            runs.forEachIndexed { index, run ->
                card.addView(historyRunCard(run, index), margin(top = 10))
            }
            card.addView(Button(this).apply {
                text = if (isKoreanUi()) "기록 삭제" else "Clear history"
                setTextColor(color(0xB42318))
                useAppFont(Typeface.BOLD)
                background = rounded(color(0xFFF1F0), dp(8))
                setOnClickListener {
                    saveRecentRuns(emptyList())
                    resultContainer.removeView(card)
                    renderHistoryPanel()
                }
            }, margin(top = 10))
        }
        resultContainer.addView(card, margin(top = 16))
    }

    private fun historyRunCard(run: InjectionRecentRun, index: Int): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(12), dp(12), dp(12), dp(12))
        background = strokedRounded(Color.WHITE, if (index == 0) color(0x8FE3B1) else color(0xDAE3EC), dp(8))
        isClickable = true
        setOnClickListener { applyRecentRun(run) }
        addView(LinearLayout(this@InjectionActivity).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            val badge = if (index == 0) {
                if (isKoreanUi()) "최신" else "Latest"
            } else {
                "#${index + 1}"
            }
            addView(label(badge, if (index == 0) color(0x087A45) else color(0x0BA7C9), 11f, Typeface.BOLD).apply {
                setPadding(dp(8), dp(4), dp(8), dp(4))
                background = rounded(if (index == 0) color(0xE4F8EC) else color(0xE2F7FB), dp(999))
            })
            addView(label("${run.geometryId} / ${run.processId}", color(0x101215), 16f, Typeface.BOLD), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                marginStart = dp(8)
            })
        })
        addView(label("${run.meltTempC.metricText(1)} C · ${run.injectionTimeS.metricText(3)} s · ${run.packingPressureMPa.metricText(1)} MPa", color(0x637180), 12f, Typeface.BOLD), margin(top = 7))
        addView(label("${run.modelLabel} · ${run.fillingModelLabel} · ${run.pressureMPa.metricText(2)} MPa", color(0x0BA7C9), 12f, Typeface.BOLD), margin(top = 4))
    }

    private fun saveRecentRun(input: InjectionNativeInput, result: InjectionNativeResult) {
        val run = InjectionRecentRun(
            geometryId = input.geometryId,
            processId = input.processId,
            sprueModelKey = input.sprueModelKey,
            fillingModelKey = input.fillingModelKey,
            modelLabel = result.displayModelLabel,
            fillingModelLabel = result.displayFillingModelLabel,
            meltTempC = input.meltTempC,
            injectionTimeS = input.injectionTimeS,
            packingPressureMPa = input.packingPressureMPa,
            pressureMPa = result.predictedMaxPressureMPa,
        )
        val signature = run.signature
        saveRecentRuns((listOf(run) + loadRecentRuns().filter { it.signature != signature }).take(5))
    }

    private fun loadRecentRuns(): List<InjectionRecentRun> {
        val text = getSharedPreferences(INJECTION_HISTORY_PREFS, MODE_PRIVATE).getString(INJECTION_HISTORY_KEY, "[]") ?: "[]"
        return runCatching {
            val array = JSONArray(text)
            List(array.length()) { index -> InjectionRecentRun.fromJson(array.getJSONObject(index)) }
        }.getOrDefault(emptyList())
    }

    private fun saveRecentRuns(runs: List<InjectionRecentRun>) {
        val array = JSONArray()
        runs.take(5).forEach { array.put(it.toJson()) }
        getSharedPreferences(INJECTION_HISTORY_PREFS, MODE_PRIVATE)
            .edit()
            .putString(INJECTION_HISTORY_KEY, array.toString())
            .apply()
    }

    private fun applyRecentRun(run: InjectionRecentRun) {
        geometrySpinner.setSelection(defaultIndex(geometries, run.geometryId), false)
        processSpinner.setSelection(defaultIndex(processes, run.processId), false)
        sprueModelSpinner.setSelection(sprueModels.indexOfFirst { it.key == run.sprueModelKey }.takeIf { it >= 0 } ?: 0, false)
        fillingModelSpinner.setSelection(fillingModels.indexOfFirst { it.key == run.fillingModelKey }.takeIf { it >= 0 } ?: 0, false)
        renderValues()
    }

    private fun showError(message: String) {
        statusText.text = "Error"
        statusText.setTextColor(color(0xB42318))
        resultContainer.removeAllViews()
        resultContainer.addView(card().apply {
            addView(label(message, color(0xB42318), 15f, Typeface.BOLD))
        })
        renderHistoryPanel()
    }

    private fun isKoreanUi(): Boolean =
        java.util.Locale.getDefault().language.equals("ko", ignoreCase = true)

    private fun localizedXaiLabel(feature: InjectionXaiFeature): String {
        if (!isKoreanUi()) return feature.label.ifBlank { feature.name }
        if (feature.name.startsWith("gate_type__")) {
            return "게이트 타입: ${feature.name.removePrefix("gate_type__")}"
        }
        return injectionXaiCopy(feature.name)?.first ?: feature.label.ifBlank { feature.name }
    }

    private fun localizedXaiExplanation(feature: InjectionXaiFeature): String {
        if (!isKoreanUi()) return feature.explanation
        if (feature.name.startsWith("gate_type__")) {
            return "게이트 타입을 구분하기 위한 one-hot feature입니다. 입구 경계 조건 차이를 모델이 구분하는 데 사용됩니다."
        }
        return injectionXaiCopy(feature.name)?.second ?: feature.explanation
    }

    private fun injectionXaiCopy(name: String): Pair<String, String>? = mapOf(
        "L_mm" to ("길이" to "전체 제품 길이입니다. 유동 거리가 길어지면 필요한 압력이 커지고 압력 곡선의 시간 위치가 달라질 수 있습니다."),
        "W_mm" to ("폭" to "전체 제품 폭입니다. 투영 면적과 유동 가능한 영역을 바꿉니다."),
        "t_mm" to ("두께" to "제품 두께입니다. 두꺼운 캐비티는 대체로 유동 저항을 낮추고, 얇은 구간은 압력 민감도를 키울 수 있습니다."),
        "D_mm" to ("홀 직경" to "중앙 홀의 직경입니다. 순 유동 면적을 줄이고 홀 주변의 충전 경로를 바꿉니다."),
        "R_mm" to ("홀 반경" to "중앙 홀의 반경입니다. 홀 직경과 함께 사용되며 유효 단면에 영향을 줍니다."),
        "gate_size_width_mm" to ("게이트 폭" to "게이트 개구부의 폭입니다. 게이트 면적이 커지면 입구 부근의 국부 압력 손실이 줄어들 수 있습니다."),
        "gate_size_height_mm" to ("게이트 높이" to "게이트 개구부의 높이입니다. 게이트 면적과 제한 정도를 직접 바꿉니다."),
        "melt_temp_C" to ("수지 온도" to "수지 온도입니다. 온도가 높아지면 일반적으로 점도가 낮아져 필요한 압력이 줄어들 수 있습니다."),
        "mold_temp_C" to ("금형 온도" to "금형 온도입니다. 냉각 속도, 점도 증가, 벽면 근처 유동 저항에 영향을 줍니다."),
        "injection_time_s" to ("사출 시간" to "충전 시간 조건입니다. 빠른 사출은 peak pressure를 높일 수 있고, 느린 사출은 압력 곡선 형태를 바꿉니다."),
        "packing_pressure_MPa" to ("보압" to "보압 설정값입니다. 충전 후반부 압력 수준과 peak pressure 응답에 영향을 줄 수 있습니다."),
        "packing_time_s" to ("보압 시간" to "보압 유지 시간입니다. 주로 충전 이후 후반 압력 거동에 영향을 줍니다."),
        "gate_area_mm2" to ("게이트 면적" to "게이트 폭과 높이로 계산한 게이트 단면적입니다."),
        "flow_length_to_thickness" to ("유동 길이/두께 비율" to "유동 경로가 두께에 비해 얼마나 긴지 나타내는 지표입니다."),
        "process_total_time_s" to ("총 공정 시간" to "사출 시간과 보압 시간을 더한 값입니다."),
    )[name]

    private fun selectedGeometry(): InjectionDoeOption = geometries.getOrNull(geometrySpinner.selectedItemPosition) ?: fallbackGeometry()
    private fun selectedProcess(): InjectionDoeOption = processes.getOrNull(processSpinner.selectedItemPosition) ?: fallbackProcess()

    private fun inputBlock(title: String, child: android.view.View): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        addView(label(title, color(0x637180), 12f, Typeface.BOLD))
        addView(child, margin(top = 6))
    }

    private fun metricBox(title: String, value: String): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(12), dp(10), dp(12), dp(10))
        background = rounded(color(0xF6F9FB), dp(8))
        addView(label(title, color(0x637180), 12f, Typeface.BOLD))
        addView(label(value, color(0x101215), 15f, Typeface.BOLD))
    }

    private fun card(): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(18), dp(18), dp(18), dp(18))
        background = strokedRounded(Color.WHITE, color(0xDAE3EC), dp(8))
        elevation = dp(1).toFloat()
    }

    private fun paragraph(text: String): TextView = label(text, color(0x637180), 15f, Typeface.NORMAL).apply {
        setLineSpacing(dp(3).toFloat(), 1.0f)
    }

    private fun assistantAnswerBlock(text: String): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(12), dp(12), dp(12), dp(12))
        background = strokedRounded(color(0xF6F9FB), color(0xDAE3EC), dp(8))
        renderAssistantAnswer(this, text)
    }

    private fun renderAssistantAnswer(container: LinearLayout, text: String) {
        container.removeAllViews()
        val header = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            addView(label("Injection AI", color(0x101215), 14f, Typeface.BOLD), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            addView(label(if (isKoreanUi()) "답변" else "Answer", color(0x0BA7C9), 11f, Typeface.BOLD).apply {
                setPadding(dp(8), dp(4), dp(8), dp(4))
                background = rounded(color(0xE2F7FB), dp(999))
            })
        }
        container.addView(header)
        val paragraphs = text
            .replace("\r\n", "\n")
            .split(Regex("\\n{2,}"))
            .map { it.trim() }
            .filter { it.isNotEmpty() }
            .ifEmpty { listOf(text) }
        paragraphs.forEachIndexed { index, paragraph ->
            container.addView(LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(dp(10), dp(10), dp(10), dp(10))
                background = strokedRounded(if (index == 0) color(0xF0FCF6) else Color.WHITE, if (index == 0) color(0xBCEFD3) else color(0xDAE3EC), dp(8))
                val sectionTitle = if (index == 0) {
                    if (isKoreanUi()) "요약" else "Summary"
                } else {
                    "${if (isKoreanUi()) "해석" else "Reasoning"} $index"
                }
                addView(label(sectionTitle, if (index == 0) color(0x087A45) else color(0x0BA7C9), 11f, Typeface.BOLD).apply {
                    setPadding(dp(8), dp(4), dp(8), dp(4))
                    background = rounded(if (index == 0) color(0xE4F8EC) else color(0xE2F7FB), dp(999))
                })
                addView(label(paragraph, color(0x101215), 14f, if (index == 0) Typeface.BOLD else Typeface.NORMAL).apply {
                    setLineSpacing(dp(4).toFloat(), 1.0f)
                }, margin(top = 7))
            }, margin(top = 8))
        }
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

    private fun commandButtonBackground() = android.graphics.drawable.GradientDrawable().apply {
        orientation = android.graphics.drawable.GradientDrawable.Orientation.LEFT_RIGHT
        colors = intArrayOf(color(0x101215), color(0x0BA7C9))
        cornerRadius = dp(8).toFloat()
    }

    private fun strokedRounded(fill: Int, stroke: Int, radius: Int) = android.graphics.drawable.GradientDrawable().apply {
        setColor(fill)
        setStroke(dp(1), stroke)
        cornerRadius = radius.toFloat()
    }

    private fun color(rgb: Int): Int = Color.rgb(rgb shr 16 and 0xFF, rgb shr 8 and 0xFF, rgb and 0xFF)
    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}

private class InjectionShapePreviewView(context: Context) : View(context) {
    private var lengthMm = 154.01
    private var widthMm = 97.42
    private var thicknessMm = 2.207
    private var holeDiameterMm = 17.61
    private var gateWidthMm = 10.0
    private var gateHeightMm = 1.5

    private val fillPaint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val strokePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeWidth = 2.2f
        color = Color.argb(130, 255, 255, 255)
    }
    private val gridPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeWidth = 1.2f
        color = Color.argb(44, 255, 255, 255)
    }
    private val flowPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeWidth = 3f
        color = Color.rgb(235, 99, 28)
        pathEffect = DashPathEffect(floatArrayOf(12f, 8f), 0f)
    }
    private val labelPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(68, 85, 106)
        textSize = 24f
        typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        textAlign = Paint.Align.CENTER
    }

    fun configure(
        lengthMm: Double,
        widthMm: Double,
        thicknessMm: Double,
        holeDiameterMm: Double,
        gateWidthMm: Double,
        gateHeightMm: Double,
    ) {
        this.lengthMm = lengthMm
        this.widthMm = widthMm
        this.thicknessMm = thicknessMm
        this.holeDiameterMm = holeDiameterMm
        this.gateWidthMm = gateWidthMm
        this.gateHeightMm = gateHeightMm
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val canvasWidth = width.toFloat()
        val canvasHeight = height.toFloat()
        fillPaint.shader = android.graphics.LinearGradient(
            0f,
            0f,
            canvasWidth,
            canvasHeight,
            intArrayOf(Color.rgb(244, 250, 255), Color.rgb(224, 244, 249)),
            null,
            android.graphics.Shader.TileMode.CLAMP
        )
        canvas.drawRoundRect(RectF(0f, 0f, canvasWidth, canvasHeight), 18f, 18f, fillPaint)
        fillPaint.shader = null

        val gridStep = 42f
        var gridX = 0f
        while (gridX <= canvasWidth) {
            canvas.drawLine(gridX, 0f, gridX, canvasHeight, gridPaint)
            gridX += gridStep
        }
        var gridY = 0f
        while (gridY <= canvasHeight) {
            canvas.drawLine(0f, gridY, canvasWidth, gridY, gridPaint)
            gridY += gridStep
        }

        val margin = minOf(canvasWidth, canvasHeight) * 0.15f
        val scale = minOf(
            (canvasWidth - margin * 2f) / lengthMm.toFloat().coerceAtLeast(1f),
            (canvasHeight - margin * 2f) / widthMm.toFloat().coerceAtLeast(1f)
        )
        val plateWidth = lengthMm.toFloat() * scale
        val plateHeight = widthMm.toFloat() * scale
        val plate = RectF(
            (canvasWidth - plateWidth) / 2f,
            (canvasHeight - plateHeight) / 2f,
            (canvasWidth + plateWidth) / 2f,
            (canvasHeight + plateHeight) / 2f
        )

        fillPaint.shader = android.graphics.LinearGradient(
            plate.left,
            plate.top,
            plate.right,
            plate.bottom,
            Color.rgb(232, 242, 247),
            Color.rgb(184, 204, 216),
            android.graphics.Shader.TileMode.CLAMP
        )
        canvas.drawRoundRect(plate, 8f, 8f, fillPaint)
        fillPaint.shader = null
        canvas.drawRoundRect(plate, 8f, 8f, strokePaint)

        val holeRadius = (holeDiameterMm.toFloat() * scale / 2f).coerceAtLeast(5f)
        val holeCenterX = plate.centerX()
        val holeCenterY = plate.centerY()
        val hole = RectF(
            holeCenterX - holeRadius,
            holeCenterY - holeRadius,
            holeCenterX + holeRadius,
            holeCenterY + holeRadius
        )
        fillPaint.color = Color.rgb(21, 86, 142)
        canvas.drawOval(hole, fillPaint)
        canvas.drawOval(hole, strokePaint)

        val gateVisualHeight = (gateWidthMm.toFloat() * scale).coerceAtLeast(12f)
        val gateVisualWidth = (gateHeightMm.toFloat() * scale * 4f).coerceAtLeast(16f)
        val gate = RectF(
            plate.left - gateVisualWidth * 0.82f,
            plate.centerY() - gateVisualHeight / 2f,
            plate.left + gateVisualWidth * 0.18f,
            plate.centerY() + gateVisualHeight / 2f
        )
        fillPaint.color = Color.rgb(235, 99, 28)
        canvas.drawRoundRect(gate, 5f, 5f, fillPaint)

        val flow = Path().apply {
            moveTo(gate.right, gate.centerY())
            cubicTo(
                plate.left + plateWidth * 0.12f,
                plate.centerY() + plateHeight * 0.18f,
                plate.left + plateWidth * 0.25f,
                plate.centerY() - plateHeight * 0.12f,
                holeCenterX - holeRadius * 1.2f,
                holeCenterY
            )
        }
        canvas.drawPath(flow, flowPaint)

        canvas.drawText("L ${lengthMm.metricText(1)} mm", plate.centerX(), plate.bottom + 34f, labelPaint)
        canvas.save()
        canvas.rotate(-90f, plate.left - 46f, plate.centerY())
        canvas.drawText("W ${widthMm.metricText(1)} mm", plate.left - 46f, plate.centerY(), labelPaint)
        canvas.restore()
        canvas.drawText("D ${holeDiameterMm.metricText(1)} mm", holeCenterX, holeCenterY + holeRadius + 28f, labelPaint)
        canvas.drawText("Gate ${gateWidthMm.metricText(1)} mm", gate.centerX(), gate.top - 14f, labelPaint)
    }
}

private data class InjectionCatalog(
    val sprueModels: List<InjectionModelInfo>,
    val fillingModels: List<InjectionModelInfo>,
    val geometries: List<InjectionDoeOption>,
    val processes: List<InjectionDoeOption>,
)

private data class InjectionModelInfo(val key: String, val label: String, val available: Boolean) {
    val displayLabel: String get() = injectionModelDisplayLabel(key, label)
}

private data class InjectionDoeOption(val id: String, val values: Map<String, Any?>) {
    fun double(key: String): Double? = when (val value = values[key]) {
        is Number -> value.toDouble()
        is String -> value.toDoubleOrNull()
        else -> null
    }

    fun string(key: String): String? = values[key]?.toString()
}

private data class InjectionNativeInput(
    val geometryId: String,
    val processId: String,
    val sprueModelKey: String,
    val fillingModelKey: String,
    val lMm: Double,
    val wMm: Double,
    val tMm: Double,
    val dMm: Double,
    val rMm: Double?,
    val gateType: String,
    val gateWidthMm: Double,
    val gateHeightMm: Double,
    val meltTempC: Double,
    val moldTempC: Double,
    val injectionTimeS: Double,
    val packingPressureMPa: Double,
    val packingTimeS: Double,
)

private data class InjectionFillingBin(val group: Int, val volumeRatioPct: Double)

private data class InjectionNativeResult(
    val predictedMaxTimeS: Double,
    val predictedMaxPressureMPa: Double,
    val modelKey: String,
    val modelLabel: String,
    val fillingModelKey: String,
    val fillingModelLabel: String,
    val curveCount: Int,
    val fillingBins: List<InjectionFillingBin>,
    val inputs: JSONObject,
    val fillingMaxMPa: Double?,
    val xaiFeatures: List<InjectionXaiFeature>,
) {
    val displayModelLabel: String get() = injectionModelDisplayLabel(modelKey, modelLabel)
    val displayFillingModelLabel: String get() = injectionModelDisplayLabel(fillingModelKey, fillingModelLabel)
}

private data class InjectionXaiFeature(
    val name: String,
    val label: String,
    val category: String,
    val importance: Double,
    val localSensitivity: Double,
    val localValue: Double?,
    val perturbation: String,
    val explanation: String,
)

private data class InjectionDetailValue(
    val title: String,
    val value: String,
    val percent: Int? = null,
)

private data class InjectionRecentRun(
    val geometryId: String,
    val processId: String,
    val sprueModelKey: String,
    val fillingModelKey: String,
    val modelLabel: String,
    val fillingModelLabel: String,
    val meltTempC: Double,
    val injectionTimeS: Double,
    val packingPressureMPa: Double,
    val pressureMPa: Double,
) {
    val signature: String
        get() = listOf(geometryId, processId, sprueModelKey, fillingModelKey, meltTempC, injectionTimeS, packingPressureMPa).joinToString("|")

    fun toJson(): JSONObject = JSONObject()
        .put("geometry_id", geometryId)
        .put("process_id", processId)
        .put("sprue_model_key", sprueModelKey)
        .put("filling_model_key", fillingModelKey)
        .put("model_label", modelLabel)
        .put("filling_model_label", fillingModelLabel)
        .put("melt_temp_C", meltTempC)
        .put("injection_time_s", injectionTimeS)
        .put("packing_pressure_MPa", packingPressureMPa)
        .put("pressure_MPa", pressureMPa)

    companion object {
        fun fromJson(json: JSONObject): InjectionRecentRun = InjectionRecentRun(
            geometryId = json.optString("geometry_id", "G01"),
            processId = json.optString("process_id", "P01"),
            sprueModelKey = json.optString("sprue_model_key", DEFAULT_SPRUE_MODEL),
            fillingModelKey = json.optString("filling_model_key", DEFAULT_FILLING_MODEL),
            modelLabel = json.optString("model_label", "Machine Learning"),
            fillingModelLabel = json.optString("filling_model_label", "Machine Learning"),
            meltTempC = json.optDouble("melt_temp_C"),
            injectionTimeS = json.optDouble("injection_time_s"),
            packingPressureMPa = json.optDouble("packing_pressure_MPa"),
            pressureMPa = json.optDouble("pressure_MPa"),
        )
    }
}

private class InjectionApiNative {
    fun catalog(): InjectionCatalog {
        val models = JSONObject(request("GET", endpoint("/api/v1/simple-injection/models")))
        val doe = JSONObject(request("GET", endpoint("/api/v1/simple-injection/doe")))
        return InjectionCatalog(
            sprueModels = models.optJSONArray("sprue_pressure_models").toInjectionModels(),
            fillingModels = models.optJSONArray("filling_pressure_models").toInjectionModels(),
            geometries = doe.optJSONArray("geometries").toDoeOptions(),
            processes = doe.optJSONArray("processes").toDoeOptions(),
        )
    }

    fun predict(input: InjectionNativeInput): InjectionNativeResult {
        val body = JSONObject()
            .put("geometry_id", input.geometryId)
            .put("process_id", input.processId)
            .put("model", input.sprueModelKey)
            .put("filling_model", input.fillingModelKey)
            .put("L_mm", input.lMm)
            .put("W_mm", input.wMm)
            .put("t_mm", input.tMm)
            .put("D_mm", input.dMm)
            .put("R_mm", input.rMm)
            .put("gate_type", input.gateType)
            .put("gate_size_width_mm", input.gateWidthMm)
            .put("gate_size_height_mm", input.gateHeightMm)
            .put("melt_temp_C", input.meltTempC)
            .put("mold_temp_C", input.moldTempC)
            .put("injection_time_s", input.injectionTimeS)
            .put("packing_pressure_MPa", input.packingPressureMPa)
            .put("packing_time_s", input.packingTimeS)
            .toString()
        val json = JSONObject(request("POST", endpoint("/api/v1/simple-injection/predict/sprue-pressure"), body))
        val filling = json.optJSONObject("predicted_filling_pressure") ?: json.optJSONObject("filling_pressure")
        return InjectionNativeResult(
            predictedMaxTimeS = json.optDouble("predicted_max_time_s"),
            predictedMaxPressureMPa = json.optDouble("predicted_max_pressure_MPa"),
            modelKey = json.optString("model_key"),
            modelLabel = json.optString("model_label"),
            fillingModelKey = json.optString("filling_model_key"),
            fillingModelLabel = json.optString("filling_model_label"),
            curveCount = json.optJSONArray("curve")?.length() ?: 0,
            fillingBins = filling?.optJSONArray("bins").toFillingBins(),
            inputs = json.optJSONObject("inputs") ?: JSONObject(),
            fillingMaxMPa = filling?.optJSONObject("stats")?.optDoubleOrNull("max_MPa"),
            xaiFeatures = json.optJSONObject("xai")?.optJSONArray("top_features").toXaiFeatures(),
        )
    }

    fun answer(question: String, result: InjectionNativeResult, language: String): String {
        val xaiFeatures = JSONArray().apply {
            result.xaiFeatures.forEach { feature ->
                put(JSONObject()
                    .put("name", feature.name)
                    .put("label", feature.label)
                    .put("category", feature.category)
                    .put("importance", feature.importance)
                    .put("local_sensitivity", feature.localSensitivity)
                    .put("local_value", feature.localValue ?: JSONObject.NULL)
                    .put("perturbation", feature.perturbation)
                    .put("explanation", feature.explanation))
            }
        }
        val context = JSONObject()
            .put("mode", "Injection Forecast")
            .put("inputs", result.inputs)
            .put("model_key", result.modelKey)
            .put("model_label", result.displayModelLabel)
            .put("filling_model_key", result.fillingModelKey)
            .put("filling_model_label", result.displayFillingModelLabel)
            .put("predicted_max_pressure_MPa", result.predictedMaxPressureMPa)
            .put("predicted_max_time_s", result.predictedMaxTimeS)
            .put("curve_points", result.curveCount)
            .put("predicted_filling_max_MPa", result.fillingMaxMPa ?: JSONObject.NULL)
            .put("xai", JSONObject()
                .put("method", "App prediction XAI")
                .put("feature_set", "geometry + process + gate + derived flow descriptors")
                .put("top_features", xaiFeatures))
        val body = JSONObject()
            .put("query", question)
            .put("top_k", 3)
            .put("use_llm", true)
            .put("language", language)
            .put("prediction_context", context)
            .toString()
        val json = JSONObject(request("POST", endpoint("/api/v1/rag/answer"), body))
        return json.optString("answer", "No answer returned.")
    }

    private fun request(method: String, url: URL, body: String? = null): String {
        val connection = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 8_000
            readTimeout = 25_000
            if (body != null) {
                doOutput = true
                setRequestProperty("Content-Type", "application/json")
            }
        }
        if (body != null) {
            connection.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
        }
        val stream = if (connection.responseCode in 200..299) connection.inputStream else connection.errorStream
        val text = BufferedReader(InputStreamReader(stream)).use { it.readText() }
        if (connection.responseCode !in 200..299) error("HTTP ${connection.responseCode}: $text")
        return text
    }

    private fun endpoint(path: String): URL = URL("${INJECTION_BASE_URL}/${path.trimStart('/')}")
}

private fun JSONArray?.toInjectionModels(): List<InjectionModelInfo> {
    if (this == null) return emptyList()
    return List(length()) { index ->
        val item = getJSONObject(index)
        InjectionModelInfo(item.optString("key"), item.optString("label"), item.optBoolean("available"))
    }
}

private fun JSONArray?.toDoeOptions(): List<InjectionDoeOption> {
    if (this == null) return emptyList()
    return List(length()) { index ->
        val item = getJSONObject(index)
        val values = item.optJSONObject("values") ?: item
        InjectionDoeOption(
            id = item.optString("id"),
            values = values.keys().asSequence().associateWith { key ->
                when (val value = values.opt(key)) {
                    JSONObject.NULL -> null
                    else -> value
                }
            }
        )
    }
}

private fun JSONArray?.toFillingBins(): List<InjectionFillingBin> {
    if (this == null) return emptyList()
    return List(length()) { index ->
        val item = getJSONObject(index)
        InjectionFillingBin(item.optInt("group"), item.optDouble("volume_ratio_pct"))
    }
}

private fun JSONArray?.toXaiFeatures(): List<InjectionXaiFeature> {
    if (this == null) return emptyList()
    return List(length()) { index ->
        val item = getJSONObject(index)
        InjectionXaiFeature(
            name = item.optString("name"),
            label = item.optString("label"),
            category = item.optString("category"),
            importance = item.optDouble("importance"),
            localSensitivity = item.optDouble("local_sensitivity"),
            localValue = item.optDoubleOrNull("local_value"),
            perturbation = item.optString("perturbation"),
            explanation = item.optString("explanation"),
        )
    }
}

private fun JSONObject.optDoubleOrNull(key: String): Double? =
    if (has(key) && !isNull(key)) optDouble(key) else null

private fun fallbackGeometry() = InjectionDoeOption(
    id = "G01",
    values = mapOf(
        "L_mm" to 154.01,
        "W_mm" to 97.42,
        "t_mm" to 2.207,
        "D_mm" to 17.61,
        "R_mm" to 8.805,
        "gate_type" to "edge_gate",
        "gate_size_width_mm" to 10.0,
        "gate_size_height_mm" to 1.5,
    )
)

private fun fallbackProcess() = InjectionDoeOption(
    id = "P01",
    values = mapOf(
        "melt_temp_C" to 226.1,
        "mold_temp_C" to 61.7,
        "injection_time_s" to 2.47,
        "packing_pressure_MPa" to 69.0,
        "packing_time_s" to 4.731,
    )
)

private fun injectionModelDisplayLabel(key: String, fallbackLabel: String): String =
    when (key) {
        "sprue_classical", "filling_classical" -> "Machine Learning"
        "sprue_goint", "filling_goint" -> "Deep Learning"
        "sprue_deeponet", "filling_deeponet" -> "Operator Learning"
        else -> fallbackLabel.cleanInjectionModelLabel()
    }

private fun String.cleanInjectionModelLabel(): String {
    val trimmed = trim()
    val prefix = listOf("Sprue Pressure", "Filling Pressure").firstOrNull { trimmed.startsWith(it, ignoreCase = true) }
    val normalized = (prefix?.let { trimmed.drop(it.length) } ?: trimmed).trim(' ', '-', ':')
    return when (normalized.lowercase()) {
        "classical ml + pca",
        "classical ml histogram" -> "Machine Learning"
        "gointmlp-style nn" -> "Deep Learning"
        "deeponet operator nn",
        "deeponet histogram nn" -> "Operator Learning"
        else -> normalized
    }
}

private fun Double?.metricText(digits: Int): String = this?.let { "%.${digits}f".format(it) } ?: "-"
private fun Double.metricText(digits: Int): String = "%.${digits}f".format(this)
