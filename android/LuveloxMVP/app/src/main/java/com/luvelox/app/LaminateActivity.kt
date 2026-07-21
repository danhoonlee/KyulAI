package com.luvelox.app

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.os.Build
import android.os.Bundle
import android.text.Editable
import android.text.InputType
import android.text.Layout
import android.text.TextWatcher
import android.view.Gravity
import android.view.View
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.SeekBar
import android.widget.Spinner
import android.widget.TextView
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.Serializable
import java.net.HttpURLConnection
import java.net.URL
import kotlin.math.roundToInt

private const val LAMINATE_BASE_URL = "https://laminate.luvelox.com"
private const val DEFAULT_RESPONSE_MODEL = "response_surrogate_physics_v2"
private const val DEEP_RESPONSE_MODEL = "response_goint_physics_nn_v2"
private const val DISTILLED_RESPONSE_MODEL = "response_distilled_grid_conf_v1"
private const val DEFAULT_U3_MODEL = "u3_forecast_physics_v2"
private const val DEEP_U3_MODEL = "u3_forecast_goint_physics_v2"
private const val LAMINATE_HISTORY_PREFS = "laminate_prediction_history"
private const val LAMINATE_HISTORY_KEY = "recent_runs_v1"
private const val LAMINATE_HISTORY_LIMIT = 5
const val EXTRA_LAMINATE_RESULT = "com.luvelox.app.EXTRA_LAMINATE_RESULT"
const val EXTRA_LAMINATE_DESIGN_SPACE = "com.luvelox.app.EXTRA_LAMINATE_DESIGN_SPACE"
const val EXTRA_LAMINATE_DESIGN_SPACE_ERROR = "com.luvelox.app.EXTRA_LAMINATE_DESIGN_SPACE_ERROR"
const val EXTRA_LAMINATE_MODE = "com.luvelox.app.EXTRA_LAMINATE_MODE"
const val EXTRA_LAMINATE_CASE = "com.luvelox.app.EXTRA_LAMINATE_CASE"
const val EXTRA_LAMINATE_THETA1 = "com.luvelox.app.EXTRA_LAMINATE_THETA1"
const val EXTRA_LAMINATE_THETA2 = "com.luvelox.app.EXTRA_LAMINATE_THETA2"
const val EXTRA_LAMINATE_PANEL_A = "com.luvelox.app.EXTRA_LAMINATE_PANEL_A"
const val EXTRA_LAMINATE_PANEL_B = "com.luvelox.app.EXTRA_LAMINATE_PANEL_B"

private enum class LaminateForecastMode(
    val key: String,
    val title: String,
    val actionTitle: String,
    val historyTitle: String,
) {
    RESPONSE("response", "Response Forecast", "Predict response", "Recent response forecasts"),
    U3("u3", "u3 Forecast", "Predict u3 Pt", "Recent u3 forecasts"),
}

class LaminateActivity : Activity() {
    private lateinit var theta1Input: EditText
    private lateinit var theta2Input: EditText
    private lateinit var panelAInput: EditText
    private lateinit var panelBInput: EditText
    private lateinit var theta1Readout: TextView
    private lateinit var theta2Readout: TextView
    private lateinit var theta1SeekBar: SeekBar
    private lateinit var theta2SeekBar: SeekBar
    private lateinit var caseSpinner: Spinner
    private lateinit var caseFormulaReadout: TextView
    private lateinit var modelSpinner: Spinner
    private lateinit var statusText: TextView
    private lateinit var forecastTitleText: TextView
    private lateinit var responseModeButton: Button
    private lateinit var u3ModeButton: Button
    private lateinit var predictButton: Button
    private lateinit var resultContainer: LinearLayout
    private lateinit var plyPreview: PlyStackPreviewView
    private lateinit var plyCountText: TextView
    private lateinit var stackFormulaText: TextView
    private var responseModels: List<LaminateModelInfo> = emptyList()
    private var u3Models: List<LaminateModelInfo> = emptyList()
    private var models: List<LaminateModelInfo> = emptyList()
    private var selectedMode: LaminateForecastMode = LaminateForecastMode.RESPONSE
    private var isSyncingTheta = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        render()
        loadModels()
    }

    override fun onResume() {
        super.onResume()
        if (::resultContainer.isInitialized) {
            renderRecentHistory()
        }
    }

    private fun render() {
        val scroll = ScrollView(this).apply { setBackgroundColor(LaminateV2.background) }
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(22), dp(18), dp(44))
        }
        scroll.addView(root)
        setContentView(scroll)

        root.addView(label("COMPOSITE LAMINATE AI", LaminateV2.blue, 12f, Typeface.BOLD))
        root.addView(label("C2ES Laminate Forecast", LaminateV2.ink, 28f, Typeface.BOLD).apply {
            includeFontPadding = false
            maxLines = 1
        }, margin(top = 8))
        root.addView(paragraph("Forecast laminate Type, Pt, and response curve from case and theta inputs."), margin(top = 8, bottom = 14))
        root.addView(researchBriefCard(), margin(bottom = 14))
        root.addView(forecastStrip(), margin(bottom = 14))
        root.addView(modePicker(), margin(bottom = 14))

        val inputCard = card()
        val header = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        header.addView(LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(label("FORECAST SETUP", LaminateV2.blue, 11f, Typeface.BOLD))
            forecastTitleText = label(selectedMode.title, LaminateV2.ink, 20f, Typeface.BOLD)
            addView(forecastTitleText)
        }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        statusText = label("Checking", LaminateV2.blue, 12f, Typeface.BOLD).apply {
            setPadding(dp(10), dp(6), dp(10), dp(6))
            background = blueSoftBackground()
        }
        header.addView(statusText)
        inputCard.addView(header)

        caseSpinner = Spinner(this).apply {
            adapter = ArrayAdapter(this@LaminateActivity, android.R.layout.simple_spinner_dropdown_item, listOf("Case2", "Case3", "Case4"))
            background = fieldBackground()
            minimumHeight = dp(48)
            setPadding(dp(10), 0, dp(10), 0)
            onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
                override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                    if (::caseFormulaReadout.isInitialized) {
                        caseFormulaReadout.text = caseFormula(selectedItem.toString())
                    }
                    updatePlyPreview()
                }

                override fun onNothingSelected(parent: AdapterView<*>?) = Unit
            }
        }
        caseFormulaReadout = label(caseFormula("Case2"), LaminateV2.ink, 11f, Typeface.BOLD).apply {
            setPadding(dp(10), dp(8), dp(10), dp(8))
            background = fieldBackground()
        }
        inputCard.addView(setupSection(
            step = "01",
            title = "Case",
            subtitle = "Choose the Double-Double stack family",
            accent = LaminateV2.blue,
            content = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                addView(caseSpinner)
                addView(caseFormulaReadout, margin(top = 8))
            },
        ), margin(top = 16))

        theta1Input = numberInput("30")
        theta2Input = numberInput("-30")
        theta1Readout = angleReadout(30)
        theta2Readout = angleReadout(-30)
        theta1SeekBar = angleSeekBar(30)
        theta2SeekBar = angleSeekBar(-30)
        inputCard.addView(setupSection(
            step = "02",
            title = "Angles",
            subtitle = "Set θ₁ and θ₂ from -90° to +90°",
            accent = LaminateV2.cyan,
            content = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                addView(angleControl("θ₁", theta1Input, theta1Readout, theta1SeekBar))
                addView(angleControl("θ₂", theta2Input, theta2Readout, theta2SeekBar), margin(top = 10))
            },
        ), margin(top = 12))

        panelAInput = decimalInput("6")
        panelBInput = decimalInput("4")
        inputCard.addView(setupSection(
            step = "03",
            title = "Panel size",
            subtitle = "Geometry-aware forecast dimensions",
            accent = LaminateV2.amber,
            content = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                addView(inputBlock("Length a (in)", panelAInput), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
                addView(inputBlock("Width b (in)", panelBInput), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                    marginStart = dp(10)
                })
            },
        ), margin(top = 12))

        modelSpinner = Spinner(this)
        modelSpinner.background = fieldBackground()
        modelSpinner.minimumHeight = dp(48)
        modelSpinner.setPadding(dp(10), 0, dp(10), 0)
        inputCard.addView(setupSection(
            step = "04",
            title = "Model",
            subtitle = "Select Machine Learning or Deep Learning predictor",
            accent = LaminateV2.green,
            content = modelSpinner,
        ), margin(top = 12))
        inputCard.addView(plyPreviewCard(), margin(top = 14))

        predictButton = Button(this).apply {
            text = selectedMode.actionTitle
            setTextColor(Color.WHITE)
            useAppFont(Typeface.BOLD)
            background = commandButtonBackground()
            setOnClickListener { predict() }
        }
        inputCard.addView(predictButton, margin(top = 16))

        root.addView(inputCard)
        bindThetaControls()
        updatePlyPreview()

        resultContainer = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        root.addView(resultContainer, margin(top = 16))
        renderRecentHistory()
    }

    private fun loadModels() {
        Thread {
            val loaded = runCatching {
                LaminateApi().models()
            }.getOrElse { LaminateModelCatalog(emptyList(), emptyList()) }
            runOnUiThread {
                responseModels = optimalResponseModels(loaded.responseModels.filter { it.available }).ifEmpty {
                    listOf(LaminateModelInfo(DEFAULT_RESPONSE_MODEL, "Laminate Forecast - Machine Learning", "", false))
                }
                u3Models = optimalU3Models(loaded.u3Models.filter { it.available }).ifEmpty {
                    listOf(LaminateModelInfo(DEFAULT_U3_MODEL, "u3 Forecast - Machine Learning", "", false))
                }
                updateActiveModels()
                val offline = loaded.responseModels.isEmpty() && loaded.u3Models.isEmpty()
                statusText.text = if (offline) "Offline" else "API ready"
                statusText.setTextColor(if (offline) LaminateV2.red else LaminateV2.blue)
            }
        }.start()
    }

    private fun optimalResponseModels(allModels: List<LaminateModelInfo>): List<LaminateModelInfo> {
        val byKey = allModels.associateBy { it.key }
        val selected = listOfNotNull(
            listOf(DEFAULT_RESPONSE_MODEL, "response_surrogate_physics").firstNotNullOfOrNull { byKey[it] },
            listOf(DEEP_RESPONSE_MODEL, "response_goint_physics").firstNotNullOfOrNull { byKey[it] },
            byKey[DISTILLED_RESPONSE_MODEL],
        )
        return selected.ifEmpty { allModels.take(3) }
    }

    private fun optimalU3Models(allModels: List<LaminateModelInfo>): List<LaminateModelInfo> {
        val byKey = allModels.associateBy { it.key }
        val selected = listOfNotNull(
            listOf(DEFAULT_U3_MODEL, "u3_forecast_physics").firstNotNullOfOrNull { byKey[it] },
            listOf(DEEP_U3_MODEL, "u3_forecast_goint_physics").firstNotNullOfOrNull { byKey[it] },
        )
        return selected.ifEmpty { allModels.take(2) }
    }

    private fun updateActiveModels() {
        if (!::modelSpinner.isInitialized) return
        models = when (selectedMode) {
            LaminateForecastMode.RESPONSE -> responseModels
            LaminateForecastMode.U3 -> u3Models
        }
        modelSpinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, models.map { it.displayLabel })
    }

    private fun predict() {
        val theta1 = parseThetaDegrees(theta1Input.text.toString())
        val theta2 = parseThetaDegrees(theta2Input.text.toString())
        if (theta1 == null || theta2 == null) {
            showError("Enter numeric theta values.")
            return
        }
        val panelA = parsePositiveDimension(panelAInput.text.toString())
        val panelB = parsePositiveDimension(panelBInput.text.toString())
        if (selectedMode == LaminateForecastMode.RESPONSE && (panelA == null || panelB == null)) {
            showError("Enter positive panel length and width values.")
            return
        }
        theta1Input.setText(theta1.toString())
        theta2Input.setText(theta2.toString())
        panelA?.let { panelAInput.setText(it.dimensionReadout()) }
        panelB?.let { panelBInput.setText(it.dimensionReadout()) }
        updatePlyPreview()
        val mode = selectedMode
        val model = models.getOrNull(modelSpinner.selectedItemPosition)?.key ?: when (mode) {
            LaminateForecastMode.RESPONSE -> DEFAULT_RESPONSE_MODEL
            LaminateForecastMode.U3 -> DEFAULT_U3_MODEL
        }
        statusText.text = "Predicting"
        Thread {
            val api = LaminateApi()
            val result = runCatching {
                when (mode) {
                    LaminateForecastMode.RESPONSE -> api.predictResponse(
                        caseName = caseSpinner.selectedItem.toString(),
                        theta1 = theta1.toDouble(),
                        theta2 = theta2.toDouble(),
                        modelKey = model,
                        panelAIn = panelA ?: 6.0,
                        panelBIn = panelB ?: 4.0,
                    )
                    LaminateForecastMode.U3 -> api.predictU3Forecast(
                        caseName = caseSpinner.selectedItem.toString(),
                        theta1 = theta1.toDouble(),
                        theta2 = theta2.toDouble(),
                        modelKey = model,
                    )
                }
            }
            runOnUiThread {
                result.onSuccess {
                    statusText.text = "API ready"
                    saveRecentRun(it, mode, caseSpinner.selectedItem.toString(), theta1, theta2, model, panelA, panelB)
                    renderRecentHistory()
                    startActivity(Intent(this@LaminateActivity, LaminateResultActivity::class.java).apply {
                        putExtra(EXTRA_LAMINATE_RESULT, it)
                        putExtra(EXTRA_LAMINATE_MODE, mode.key)
                        putExtra(EXTRA_LAMINATE_CASE, caseSpinner.selectedItem.toString())
                        putExtra(EXTRA_LAMINATE_THETA1, theta1)
                        putExtra(EXTRA_LAMINATE_THETA2, theta2)
                        panelA?.let { value -> putExtra(EXTRA_LAMINATE_PANEL_A, value) }
                        panelB?.let { value -> putExtra(EXTRA_LAMINATE_PANEL_B, value) }
                    })
                }.onFailure {
                    showError("Prediction failed: ${it.message ?: "Unknown error"}")
                }
            }
        }.start()
    }

    private fun renderResult(result: LaminateResult) {
        resultContainer.removeAllViews()
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
        top.addView(label(result.confidence.percentText(), LaminateV2.green, 18f, Typeface.BOLD).apply {
            setPadding(dp(10), dp(7), dp(10), dp(7))
            background = greenSoftBackground()
        })
        card.addView(top)

        val metrics = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        listOf(
            "Pt" to result.predictedPt.metricText(2),
            "Pt displacement" to result.predictedPtDisplacement.metricText(5),
            "Max force" to result.predictedMaxForce.metricText(2),
            "Curve points" to result.curve.size.toString(),
        ).chunked(2).forEach { rowItems ->
            val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
            rowItems.forEach { (name, value) ->
                row.addView(metricBox(name, value), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply { marginEnd = dp(8) })
            }
            metrics.addView(row, margin(top = 10))
        }
        card.addView(metrics)

        card.addView(label("Class probability", LaminateV2.ink, 18f, Typeface.BOLD), margin(top = 16))
        result.probabilities.toSortedMap().forEach { (label, value) ->
            card.addView(label("$label  ${value.percentText()}", LaminateV2.muted, 13f, Typeface.BOLD), margin(top = 6))
        }
        result.xai?.let { xai ->
            card.addView(label(localText("Why this prediction?", "왜 이런 예측이 나왔나요?"), LaminateV2.ink, 18f, Typeface.BOLD), margin(top = 18))
            card.addView(paragraph(LaminateXaiText.text(this, xai.summary)), margin(top = 6))
            val methodLabel = localText("Method", "방법")
            val featureSetLabel = localText("Feature set", "특징 세트")
            card.addView(label("$methodLabel: ${LaminateXaiText.text(this, xai.method)} · $featureSetLabel: ${LaminateXaiText.featureSet(this, xai.featureSet)}", LaminateV2.blue, 12f, Typeface.BOLD), margin(top = 8))
            xai.topFeatures.take(5).forEach { feature ->
                card.addView(xaiFeatureRow(feature), margin(top = 6))
            }
            val hiddenFeatures = xai.topFeatures.drop(5)
            if (hiddenFeatures.isNotEmpty()) {
                val hiddenList = LinearLayout(this).apply {
                    orientation = LinearLayout.VERTICAL
                    visibility = View.GONE
                    hiddenFeatures.forEach { feature ->
                        addView(xaiFeatureRow(feature), margin(top = 6))
                    }
                }
                val toggle = Button(this).apply {
                    text = localText("Show ${hiddenFeatures.size} more features", "나머지 ${hiddenFeatures.size}개 feature 보기")
                    textSize = 13f
                    setTextColor(LaminateV2.blue)
                    useAppFont(Typeface.BOLD)
                    background = blueSoftBackground()
                    setOnClickListener {
                        val shouldExpand = hiddenList.visibility != View.VISIBLE
                        hiddenList.visibility = if (shouldExpand) View.VISIBLE else View.GONE
                        text = if (shouldExpand) {
                            localText("Hide extra features", "추가 feature 숨기기")
                        } else {
                            localText("Show ${hiddenFeatures.size} more features", "나머지 ${hiddenFeatures.size}개 feature 보기")
                        }
                    }
                }
                card.addView(toggle, margin(top = 8))
                card.addView(hiddenList)
            }
        }
        resultContainer.addView(card)
    }

    private fun renderRecentHistory() {
        if (!::resultContainer.isInitialized) return
        resultContainer.removeAllViews()
        val runs = loadRecentRuns()
        val card = card()
        card.addView(LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            addView(LinearLayout(this@LaminateActivity).apply {
                orientation = LinearLayout.VERTICAL
                addView(label("PREDICTION HISTORY", LaminateV2.blue, 11f, Typeface.BOLD))
                addView(label(selectedMode.historyTitle, LaminateV2.ink, 20f, Typeface.BOLD))
                addView(label("Tap a card to reuse its setup.", LaminateV2.muted, 12f, Typeface.BOLD), margin(top = 3))
            }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            addView(LinearLayout(this@LaminateActivity).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                addView(label(runs.size.toString(), LaminateV2.blue, 12f, Typeface.BOLD).apply {
                    setPadding(dp(10), dp(6), dp(10), dp(6))
                    background = blueSoftBackground()
                })
                if (runs.isNotEmpty()) {
                    addView(Button(this@LaminateActivity).apply {
                        text = "Manage"
                        textSize = 12f
                        setTextColor(LaminateV2.red)
                        useAppFont(Typeface.BOLD)
                        background = redSoftBackground()
                        setOnClickListener { showHistoryManager() }
                    }, LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, dp(38)).apply {
                        marginStart = dp(8)
                    })
                }
            })
        })
        if (runs.isEmpty()) {
            card.addView(paragraph("Run a forecast and recent prediction cards will appear here."), margin(top = 12))
        } else {
            runs.forEachIndexed { index, run ->
                card.addView(recentRunCard(run, index), margin(top = 10))
            }
        }
        resultContainer.addView(card)
    }

    private fun recentRunCard(run: LaminateRecentRun, index: Int): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(12), dp(12), dp(12), dp(12))
        background = strokedRounded(Color.WHITE, if (index == 0) LaminateV2.greenLine else LaminateV2.line, dp(8))
        isClickable = true
        setOnClickListener { applyRecentRun(run) }
        addView(LinearLayout(this@LaminateActivity).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            addView(label(if (index == 0) "Latest" else "#${index + 1}", if (index == 0) LaminateV2.green else LaminateV2.blue, 11f, Typeface.BOLD).apply {
                setPadding(dp(8), dp(4), dp(8), dp(4))
                background = if (index == 0) greenSoftBackground() else blueSoftBackground()
            })
            addView(label(run.caseName, LaminateV2.ink, 16f, Typeface.BOLD), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                marginStart = dp(8)
            })
        })
        addView(label(run.modelLabel, LaminateV2.blue, 12f, Typeface.BOLD).apply {
            maxLines = 1
        }, margin(top = 7))
        addView(wrapRow(
            listOf(
                "θ₁ ${run.theta1.thetaReadout()}",
                "θ₂ ${run.theta2.thetaReadout()}",
                run.panelLabel,
                run.predictedType?.let { "Type $it" } ?: "Type -",
                run.confidence.percentText(),
                "Pt ${run.predictedPt.metricText(2)}",
            ).filterNotNull()
        ), margin(top = 8))
    }

    private fun showHistoryManager() {
        val runs = loadRecentRuns()
        if (runs.isEmpty()) return

        val selected = BooleanArray(runs.size)
        val rowChecks = mutableListOf<CheckBox>()
        var deleteButton: Button? = null
        val selectedCountText = label("0 selected", LaminateV2.muted, 12f, Typeface.BOLD)

        fun selectedSignatures(): Set<String> = runs
            .filterIndexed { index, _ -> selected[index] }
            .map { it.signature }
            .toSet()

        fun refreshSelection() {
            val selectedCount = selected.count { it }
            selectedCountText.text = "$selectedCount selected"
            rowChecks.forEachIndexed { index, checkBox ->
                checkBox.isChecked = selected[index]
            }
            deleteButton?.isEnabled = selectedCount > 0
            deleteButton?.alpha = if (selectedCount > 0) 1f else 0.45f
        }

        val rows = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            runs.forEachIndexed { index, run ->
                val checkBox = CheckBox(this@LaminateActivity).apply {
                    text = listOfNotNull(
                        if (index == 0) "Latest" else "#${index + 1}",
                        run.caseName,
                        "θ₁ ${run.theta1.thetaReadout()}",
                        "θ₂ ${run.theta2.thetaReadout()}",
                        run.panelLabel,
                        "Pt ${run.predictedPt.metricText(2)}",
                    ).joinToString("  ·  ")
                    textSize = 12f
                    setTextColor(LaminateV2.ink)
                    useAppFont(Typeface.BOLD)
                    setPadding(0, dp(10), 0, dp(10))
                    setOnClickListener {
                        selected[index] = isChecked
                        refreshSelection()
                    }
                }
                rowChecks.add(checkBox)
                addView(checkBox)
            }
        }

        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(4), dp(8), dp(4), 0)
            addView(paragraph("Select prediction records to remove. Models and datasets are not affected."))
            addView(LinearLayout(this@LaminateActivity).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                addView(Button(this@LaminateActivity).apply {
                    text = "Select all"
                    textSize = 12f
                    setTextColor(LaminateV2.blue)
                    useAppFont(Typeface.BOLD)
                    background = blueSoftBackground()
                    setOnClickListener {
                        selected.fill(true)
                        refreshSelection()
                    }
                }, LinearLayout.LayoutParams(0, dp(40), 1f))
                addView(Button(this@LaminateActivity).apply {
                    text = "Clear"
                    textSize = 12f
                    setTextColor(LaminateV2.muted)
                    useAppFont(Typeface.BOLD)
                    background = fieldBackground()
                    setOnClickListener {
                        selected.fill(false)
                        refreshSelection()
                    }
                }, LinearLayout.LayoutParams(0, dp(40), 1f).apply {
                    marginStart = dp(8)
                })
            }, margin(top = 12))
            addView(selectedCountText, margin(top = 10))
            addView(ScrollView(this@LaminateActivity).apply {
                addView(rows)
            }, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(260)).apply {
                topMargin = dp(6)
            })
        }

        val dialog = AlertDialog.Builder(this)
            .setTitle("Manage history")
            .setView(content)
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Delete selected", null)
            .create()
        dialog.setOnShowListener {
            deleteButton = dialog.getButton(AlertDialog.BUTTON_POSITIVE)
            deleteButton?.setTextColor(LaminateV2.red)
            deleteButton?.setOnClickListener {
                val signatures = selectedSignatures()
                if (signatures.isNotEmpty()) {
                    deleteRecentRuns(signatures)
                    dialog.dismiss()
                }
            }
            refreshSelection()
        }
        dialog.show()
    }

    private fun wrapRow(items: List<String>): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        items.chunked(3).forEach { rowItems ->
            addView(LinearLayout(this@LaminateActivity).apply {
                orientation = LinearLayout.HORIZONTAL
                rowItems.forEachIndexed { index, text ->
                    addView(label(text, LaminateV2.ink, 11f, Typeface.BOLD).apply {
                        setPadding(dp(8), dp(5), dp(8), dp(5))
                        background = fieldBackground()
                    }, LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
                        if (index > 0) marginStart = dp(6)
                    })
                }
            }, margin(top = 4))
        }
    }

    private fun applyRecentRun(run: LaminateRecentRun) {
        val runMode = forecastModeFromKey(run.kind)
        if (selectedMode != runMode) {
            selectedMode = runMode
            refreshModeButtons()
            forecastTitleText.text = selectedMode.title
            predictButton.text = selectedMode.actionTitle
            updateActiveModels()
        }
        val caseIndex = listOf("Case2", "Case3", "Case4").indexOf(run.caseName).takeIf { it >= 0 } ?: 0
        caseSpinner.setSelection(caseIndex)
        theta1Input.setText(run.theta1.toString())
        theta2Input.setText(run.theta2.toString())
        theta1SeekBar.progress = run.theta1.coerceIn(-90, 90) + 90
        theta2SeekBar.progress = run.theta2.coerceIn(-90, 90) + 90
        theta1Readout.text = run.theta1.thetaReadout()
        theta2Readout.text = run.theta2.thetaReadout()
        run.panelAIn?.let { panelAInput.setText(it.dimensionReadout()) }
        run.panelBIn?.let { panelBInput.setText(it.dimensionReadout()) }
        val modelIndex = models.indexOfFirst { it.key == run.modelKey }
        if (modelIndex >= 0) {
            modelSpinner.setSelection(modelIndex)
        }
        updatePlyPreview()
    }

    private fun deleteRecentRuns(signatures: Set<String>) {
        if (signatures.isEmpty()) return
        writeRecentRuns(loadAllRecentRuns().filterNot { it.signature in signatures })
        renderRecentHistory()
    }

    private fun saveRecentRun(
        result: LaminateResult,
        mode: LaminateForecastMode,
        caseName: String,
        theta1: Int,
        theta2: Int,
        modelKey: String,
        panelAIn: Double?,
        panelBIn: Double?,
    ) {
        val run = LaminateRecentRun(
            kind = mode.key,
            caseName = caseName,
            theta1 = theta1,
            theta2 = theta2,
            panelAIn = if (mode == LaminateForecastMode.RESPONSE) panelAIn else null,
            panelBIn = if (mode == LaminateForecastMode.RESPONSE) panelBIn else null,
            modelKey = modelKey,
            modelLabel = result.displayModelLabel,
            predictedType = result.predictedType,
            confidence = result.confidence,
            predictedPt = result.predictedPt,
        )
        val allRuns = loadAllRecentRuns()
        val nextRuns = listOf(run) + allRuns.filter { it.signature != run.signature }
        val trimmedByKind = LaminateForecastMode.values().flatMap { itemMode ->
            nextRuns.filter { it.kind == itemMode.key }.take(LAMINATE_HISTORY_LIMIT)
        }
        writeRecentRuns(trimmedByKind)
    }

    private fun writeRecentRuns(runs: List<LaminateRecentRun>) {
        val array = JSONArray()
        runs.take(LAMINATE_HISTORY_LIMIT * LaminateForecastMode.values().size).forEach { array.put(it.toJson()) }
        getSharedPreferences(LAMINATE_HISTORY_PREFS, MODE_PRIVATE)
            .edit()
            .putString(LAMINATE_HISTORY_KEY, array.toString())
            .apply()
    }

    private fun loadRecentRuns(): List<LaminateRecentRun> {
        return loadAllRecentRuns().filter { it.kind == selectedMode.key }.take(LAMINATE_HISTORY_LIMIT)
    }

    private fun loadAllRecentRuns(): List<LaminateRecentRun> {
        val raw = getSharedPreferences(LAMINATE_HISTORY_PREFS, MODE_PRIVATE)
            .getString(LAMINATE_HISTORY_KEY, "[]")
        val array = runCatching { JSONArray(raw ?: "[]") }.getOrElse { JSONArray() }
        return List(array.length()) { index ->
            LaminateRecentRun.fromJson(array.optJSONObject(index))
        }.filterNotNull().take(LAMINATE_HISTORY_LIMIT * LaminateForecastMode.values().size)
    }

    private fun showError(message: String) {
        statusText.text = "Error"
        statusText.setTextColor(LaminateV2.red)
        resultContainer.removeAllViews()
        resultContainer.addView(card().apply {
            addView(label(message, LaminateV2.red, 15f, Typeface.BOLD))
        })
    }

    private fun parseThetaDegrees(rawValue: String): Int? {
        val value = rawValue.trim().toDoubleOrNull() ?: return null
        if (value !in -90.0..90.0) return null
        return value.roundToInt().coerceIn(-90, 90)
    }

    private fun parsePositiveDimension(rawValue: String): Double? {
        val value = rawValue.trim().toDoubleOrNull() ?: return null
        return value.takeIf { it > 0.0 }
    }

    private fun angleControl(title: String, field: EditText, readout: TextView, seekBar: SeekBar): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(12), dp(12), dp(12), dp(12))
        background = fieldBackground()
        addView(LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            addView(label(title, LaminateV2.muted, 12f, Typeface.BOLD), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            addView(readout)
        })
        addView(field, margin(top = 8))
        addView(seekBar, margin(top = 6))
    }

    private fun angleReadout(value: Int): TextView = label(value.thetaReadout(), LaminateV2.blue, 13f, Typeface.BOLD).apply {
        setPadding(dp(8), dp(4), dp(8), dp(4))
        background = blueSoftBackground()
    }

    private fun angleSeekBar(value: Int): SeekBar = SeekBar(this).apply {
        max = 180
        progress = value.coerceIn(-90, 90) + 90
    }

    private fun bindThetaControls() {
        bindThetaControl(theta1Input, theta1SeekBar, theta1Readout)
        bindThetaControl(theta2Input, theta2SeekBar, theta2Readout)
    }

    private fun bindThetaControl(field: EditText, seekBar: SeekBar, readout: TextView) {
        field.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) = Unit
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) = Unit

            override fun afterTextChanged(s: Editable?) {
                if (isSyncingTheta) return
                val value = parseThetaDegrees(s?.toString().orEmpty()) ?: return
                isSyncingTheta = true
                seekBar.progress = value + 90
                readout.text = value.thetaReadout()
                isSyncingTheta = false
                updatePlyPreview()
            }
        })
        seekBar.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(bar: SeekBar?, progress: Int, fromUser: Boolean) {
                if (!fromUser || isSyncingTheta) return
                val value = (progress - 90).coerceIn(-90, 90)
                isSyncingTheta = true
                field.setText(value.toString())
                field.setSelection(field.text.length)
                readout.text = value.thetaReadout()
                isSyncingTheta = false
                updatePlyPreview()
            }

            override fun onStartTrackingTouch(bar: SeekBar?) = Unit
            override fun onStopTrackingTouch(bar: SeekBar?) = Unit
        })
    }

    private fun plyPreviewCard(): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(12), dp(12), dp(12), dp(12))
        background = fieldBackground()
        addView(LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.TOP
            addView(LinearLayout(context).apply {
                orientation = LinearLayout.VERTICAL
                addView(label("LIVE LAMINATE PREVIEW", LaminateV2.blue, 11f, Typeface.BOLD))
                addView(label("Angle-aware ply stack", LaminateV2.ink, 16f, Typeface.BOLD))
            }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            plyCountText = label("16 plies", LaminateV2.blue, 12f, Typeface.BOLD).apply {
                setPadding(dp(8), dp(5), dp(8), dp(5))
                background = blueSoftBackground()
            }
            addView(plyCountText)
        })
        plyPreview = PlyStackPreviewView(this@LaminateActivity).apply {
            background = strokedRounded(LaminateV2.previewField, LaminateV2.line, dp(8))
        }
        addView(plyPreview, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(220)).apply {
            topMargin = dp(10)
        })
        addView(legendRow(), margin(top = 8))
        addView(LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            addView(label("Formula", LaminateV2.muted, 12f, Typeface.BOLD), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            stackFormulaText = label(caseFormula("Case2"), LaminateV2.ink, 11f, Typeface.BOLD).apply {
                gravity = Gravity.END
                maxLines = 2
            }
            addView(stackFormulaText)
        }, margin(top = 8))
        addView(label("Compact physics features are used by the model layer; this preview follows the current Case and theta inputs.", LaminateV2.muted, 11f, Typeface.NORMAL), margin(top = 6))
    }

    private fun legendRow(): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.HORIZONTAL
        addView(legendBadge("θ₁", color(0x657AD4)))
        addView(legendBadge("θ₂", color(0xBC8F70)), LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
            marginStart = dp(6)
        })
        addView(legendBadge("+", LaminateV2.green), LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
            marginStart = dp(6)
        })
        addView(legendBadge("-", LaminateV2.red), LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
            marginStart = dp(6)
        })
    }

    private fun legendBadge(text: String, swatchColor: Int): TextView = label("■ $text", swatchColor, 11f, Typeface.BOLD).apply {
        setPadding(dp(7), dp(4), dp(7), dp(4))
        background = rounded(Color.WHITE, dp(999))
    }

    private fun updatePlyPreview() {
        if (!::plyPreview.isInitialized) return
        val caseName = caseSpinner.selectedItem?.toString() ?: "Case2"
        val theta1 = parseThetaDegrees(theta1Input.text.toString()) ?: 0
        val theta2 = parseThetaDegrees(theta2Input.text.toString()) ?: 0
        plyPreview.updateStack(caseName, theta1, theta2)
        plyCountText.text = "${plyPreview.plyCount} plies"
        stackFormulaText.text = caseFormula(caseName)
    }

    private fun caseFormula(caseName: String): String {
        return when (caseName) {
            "Case3" -> "[[±θ₁]/[±θ₂]/[∓θ₁]/[∓θ₂]] × 2"
            "Case4" -> "([±θ₁]/[±θ₂]) × 2 + ([∓θ₁]/[∓θ₂]) × 2"
            else -> "[[±θ₁]/[±θ₂]] × 4"
        }
    }

    private fun modePicker(): LinearLayout {
        return LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(dp(4), dp(4), dp(4), dp(4))
            background = strokedRounded(LaminateV2.field, LaminateV2.line, dp(8))
            responseModeButton = modeButton(LaminateForecastMode.RESPONSE)
            u3ModeButton = modeButton(LaminateForecastMode.U3)
            addView(responseModeButton, LinearLayout.LayoutParams(0, dp(48), 1f))
            addView(u3ModeButton, LinearLayout.LayoutParams(0, dp(48), 1f).apply {
                marginStart = dp(6)
            })
            refreshModeButtons()
        }
    }

    private fun modeButton(mode: LaminateForecastMode): Button = Button(this).apply {
        text = mode.title
        isAllCaps = false
        textSize = 13f
        useAppFont(Typeface.BOLD)
        setOnClickListener { selectMode(mode) }
    }

    private fun selectMode(mode: LaminateForecastMode) {
        if (selectedMode == mode) return
        selectedMode = mode
        refreshModeButtons()
        if (::forecastTitleText.isInitialized) {
            forecastTitleText.text = selectedMode.title
        }
        if (::predictButton.isInitialized) {
            predictButton.text = selectedMode.actionTitle
        }
        updateActiveModels()
        renderRecentHistory()
    }

    private fun forecastModeFromKey(key: String?): LaminateForecastMode {
        return LaminateForecastMode.values().firstOrNull { it.key == key } ?: LaminateForecastMode.RESPONSE
    }

    private fun refreshModeButtons() {
        if (!::responseModeButton.isInitialized || !::u3ModeButton.isInitialized) return
        listOf(
            responseModeButton to LaminateForecastMode.RESPONSE,
            u3ModeButton to LaminateForecastMode.U3,
        ).forEach { (button, mode) ->
            val selected = selectedMode == mode
            button.setTextColor(if (selected) Color.WHITE else LaminateV2.ink)
            button.background = if (selected) rounded(LaminateV2.blue, dp(8)) else rounded(Color.TRANSPARENT, dp(8))
        }
    }

    private fun forecastStrip(): LinearLayout {
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(14), dp(12), dp(14), dp(12))
            background = strokedRounded(LaminateV2.field, LaminateV2.line, dp(8))
            listOf(
                Triple("01", "Set case", "Choose stack family"),
                Triple("02", "Pick model", "ML default or DL check"),
                Triple("03", "Review", "Pt, curve, XAI"),
            ).forEachIndexed { index, item ->
                addView(stepRow(item.first, item.second, item.third), margin(top = if (index == 0) 0 else 8))
            }
        }
    }

    private fun researchBriefCard(): LinearLayout = card().apply {
        addView(label("RESEARCH PURPOSE", LaminateV2.blue, 11f, Typeface.BOLD))
        addView(label("Why Double-Double laminate forecasting?", LaminateV2.ink, 20f, Typeface.BOLD), margin(top = 3))
        addView(paragraph(
            "Double-Double laminates are being explored as lightweight, angle-driven alternatives to quasi-isotropic layups for impact and post-impact compression performance. This screen helps screen Case and θ candidates before deeper analysis."
        ), margin(top = 8))
        addView(researchPoint(
            title = "Problem",
            body = "0/±45/90 stacks can add weight and limit design freedom.",
            accent = LaminateV2.blue,
        ), margin(top = 12))
        addView(researchPoint(
            title = "Target",
            body = "Find the transition knee where force and u3 curves reveal stability loss.",
            accent = LaminateV2.cyan,
        ), margin(top = 8))
        addView(researchPoint(
            title = "Signal",
            body = "Current best DD candidates improved Pt by 28.93% and u3 metric by 31.31% vs. quasi-isotropic baselines.",
            accent = LaminateV2.green,
        ), margin(top = 8))
        addView(label(
            "Type 1 has a clear bilinear knee. Type 2 and Type 3 curve more after the knee, so u3 displacement behavior supports Pt estimation.",
            LaminateV2.muted,
            12f,
            Typeface.BOLD,
        ), margin(top = 10))
    }

    private fun researchPoint(title: String, body: String, accent: Int): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.HORIZONTAL
        gravity = Gravity.TOP
        setPadding(dp(10), dp(9), dp(10), dp(9))
        background = fieldBackground()
        addView(label(title.uppercase(), accent, 10f, Typeface.BOLD), LinearLayout.LayoutParams(dp(68), LinearLayout.LayoutParams.WRAP_CONTENT))
        addView(label(body, LaminateV2.ink, 12f, Typeface.BOLD), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
    }

    private fun stepRow(number: String, title: String, subtitle: String): LinearLayout {
        return LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            addView(label(number, Color.WHITE, 11f, Typeface.BOLD).apply {
                gravity = Gravity.CENTER
                background = rounded(LaminateV2.ink, dp(999))
            }, LinearLayout.LayoutParams(dp(32), dp(32)))
            addView(LinearLayout(context).apply {
                orientation = LinearLayout.VERTICAL
                addView(label(title, LaminateV2.ink, 13f, Typeface.BOLD))
                addView(label(subtitle, LaminateV2.muted, 12f, Typeface.NORMAL))
            }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                marginStart = dp(10)
            })
        }
    }

    private fun setupSection(
        step: String,
        title: String,
        subtitle: String,
        accent: Int,
        content: android.view.View,
    ): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(12), dp(12), dp(12), dp(12))
        background = strokedRounded(LaminateV2.field, LaminateV2.line, dp(8))
        addView(LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            addView(label(step, Color.WHITE, 11f, Typeface.BOLD).apply {
                gravity = Gravity.CENTER
                background = rounded(accent, dp(999))
            }, LinearLayout.LayoutParams(dp(32), dp(32)))
            addView(LinearLayout(context).apply {
                orientation = LinearLayout.VERTICAL
                addView(label(title, LaminateV2.ink, 15f, Typeface.BOLD))
                addView(label(subtitle, LaminateV2.muted, 11f, Typeface.NORMAL))
            }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                marginStart = dp(10)
            })
        })
        addView(content, margin(top = 10))
    }

    private fun inputBlock(title: String, child: android.view.View): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        addView(label(title, LaminateV2.muted, 12f, Typeface.BOLD))
        addView(child, margin(top = 6))
    }

    private fun numberInput(initial: String): EditText = EditText(this).apply {
        setText(initial)
        inputType = InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_FLAG_SIGNED
        textSize = 20f
        typeface = Typeface.MONOSPACE
        setPadding(dp(12), 0, dp(12), 0)
        background = strokedRounded(Color.WHITE, LaminateV2.line, dp(8))
    }

    private fun decimalInput(initial: String): EditText = EditText(this).apply {
        setText(initial)
        inputType = InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_FLAG_DECIMAL
        textSize = 18f
        typeface = Typeface.MONOSPACE
        setPadding(dp(12), 0, dp(12), 0)
        background = strokedRounded(Color.WHITE, LaminateV2.line, dp(8))
    }

    private fun metricBox(title: String, value: String): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(12), dp(10), dp(12), dp(10))
        background = fieldBackground()
        addView(label(title, LaminateV2.muted, 12f, Typeface.BOLD))
        addView(label(value, LaminateV2.ink, 16f, Typeface.BOLD))
    }

    private fun xaiFeatureRow(feature: LaminateXaiFeature): LinearLayout = LinearLayout(this).apply {
        val safeImportance = feature.importance.coerceIn(0.0, 1.0)
        orientation = LinearLayout.VERTICAL
        setPadding(0, dp(6), 0, dp(6))
        addView(LinearLayout(this@LaminateActivity).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            addView(label(LaminateXaiText.text(this@LaminateActivity, feature.label), LaminateV2.ink, 12f, Typeface.BOLD).apply {
                maxLines = 1
            }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            addView(label(LaminateXaiText.category(this@LaminateActivity, feature.category), LaminateV2.blue, 10f, Typeface.BOLD).apply {
                setPadding(dp(6), dp(2), dp(6), dp(2))
                background = blueSoftBackground()
            })
        })
        addView(LinearLayout(this@LaminateActivity).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            addView(FrameLayout(this@LaminateActivity).apply {
                background = rounded(LaminateV2.line, dp(999))
                addView(View(this@LaminateActivity).apply {
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
            addView(label(safeImportance.percentText(), LaminateV2.blue, 11f, Typeface.BOLD).apply {
                gravity = Gravity.END
            }, LinearLayout.LayoutParams(dp(56), LinearLayout.LayoutParams.WRAP_CONTENT))
        }, margin(top = 4))
        addView(label(LaminateXaiText.text(this@LaminateActivity, feature.explanation), LaminateV2.muted, 11f, Typeface.NORMAL), margin(top = 3))
    }

    private fun localText(en: String, ko: String): String =
        if (LaminateXaiText.isKoreanUi(this)) ko else en

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
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            breakStrategy = Layout.BREAK_STRATEGY_HIGH_QUALITY
            hyphenationFrequency = Layout.HYPHENATION_FREQUENCY_NONE
        }
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

    private fun redSoftBackground() = android.graphics.drawable.GradientDrawable().apply {
        setColor(Color.rgb(255, 241, 243))
        cornerRadius = dp(999).toFloat()
        setStroke(dp(1), Color.rgb(254, 205, 211))
    }

    private fun strokedRounded(fill: Int, stroke: Int, radius: Int) = android.graphics.drawable.GradientDrawable().apply {
        setColor(fill)
        setStroke(dp(1), stroke)
        cornerRadius = radius.toFloat()
    }

    private fun color(rgb: Int): Int = Color.rgb(rgb shr 16 and 0xFF, rgb shr 8 and 0xFF, rgb and 0xFF)

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}

object LaminateV2 {
    val background: Int = Color.rgb(249, 250, 252)
    val field: Int = Color.rgb(246, 249, 251)
    val previewField: Int = Color.rgb(241, 246, 249)
    val line: Int = Color.rgb(218, 227, 236)
    val blue: Int = Color.rgb(22, 99, 255)
    val blueSoft: Int = Color.rgb(233, 240, 255)
    val blueLine: Int = Color.rgb(188, 211, 255)
    val cyan: Int = Color.rgb(11, 167, 201)
    val green: Int = Color.rgb(10, 159, 105)
    val greenSoft: Int = Color.rgb(226, 248, 240)
    val greenLine: Int = Color.rgb(162, 224, 199)
    val amber: Int = Color.rgb(183, 121, 31)
    val red: Int = Color.rgb(217, 45, 32)
    val ink: Int = Color.rgb(16, 18, 21)
    val muted: Int = Color.rgb(99, 113, 128)
}

data class LaminateModelInfo(
    val key: String,
    val label: String,
    val description: String,
    val available: Boolean,
) {
    val displayLabel: String get() = label.cleanModelLabel()
}

data class LaminateModelCatalog(
    val responseModels: List<LaminateModelInfo>,
    val u3Models: List<LaminateModelInfo>,
)

data class LaminateRecentRun(
    val kind: String,
    val caseName: String,
    val theta1: Int,
    val theta2: Int,
    val panelAIn: Double?,
    val panelBIn: Double?,
    val modelKey: String,
    val modelLabel: String,
    val predictedType: Int?,
    val confidence: Double?,
    val predictedPt: Double?,
) {
    val signature: String get() = "$kind|$caseName|$theta1|$theta2|${panelAIn ?: "-"}|${panelBIn ?: "-"}|$modelKey"
    val panelLabel: String? get() = if (kind == LaminateForecastMode.RESPONSE.key && panelAIn != null && panelBIn != null) {
        "Panel ${panelAIn.dimensionReadout()}×${panelBIn.dimensionReadout()} in"
    } else {
        null
    }

    fun toJson(): JSONObject = JSONObject()
        .put("kind", kind)
        .put("case", caseName)
        .put("theta1", theta1)
        .put("theta2", theta2)
        .put("panel_a_in", panelAIn)
        .put("panel_b_in", panelBIn)
        .put("model_key", modelKey)
        .put("model_label", modelLabel)
        .put("predicted_type", predictedType)
        .put("confidence", confidence)
        .put("predicted_pt", predictedPt)

    companion object {
        fun fromJson(json: JSONObject?): LaminateRecentRun? {
            if (json == null) return null
            return LaminateRecentRun(
                kind = json.optString("kind", LaminateForecastMode.RESPONSE.key),
                caseName = json.optString("case", "Case2"),
                theta1 = json.optInt("theta1", 0).coerceIn(-90, 90),
                theta2 = json.optInt("theta2", 0).coerceIn(-90, 90),
                panelAIn = json.optionalDouble("panel_a_in"),
                panelBIn = json.optionalDouble("panel_b_in"),
                modelKey = json.optString("model_key", DEFAULT_RESPONSE_MODEL),
                modelLabel = json.optString("model_label", "Laminate Forecast - Machine Learning").cleanModelLabel(),
                predictedType = json.optionalInt("predicted_type"),
                confidence = json.optionalDouble("confidence"),
                predictedPt = json.optionalDouble("predicted_pt"),
            )
        }
    }
}

data class LaminateCurvePoint(val displacement: Double, val force: Double) : Serializable

data class LaminateCurveLine(val slope: Double, val intercept: Double) : Serializable

data class LaminateCurveCoordinate(val displacement: Double, val force: Double) : Serializable

data class LaminateCurveFit(
    val firstLine: LaminateCurveLine?,
    val secondLine: LaminateCurveLine?,
    val kink: LaminateCurveCoordinate?,
    val detectedKink: LaminateCurveCoordinate?,
    val firstStartX: Double?,
    val firstEndX: Double?,
    val secondStartX: Double?,
    val secondEndX: Double?,
) : Serializable

data class LaminateResult(
    val predictedType: Int,
    val confidence: Double?,
    val predictedPt: Double?,
    val predictedMaxForce: Double?,
    val modelLabel: String,
    val probabilities: Map<String, Double>,
    val curve: List<LaminateCurvePoint>,
    val xai: LaminateXai?,
    val curveFit: LaminateCurveFit?,
    val uncertainty: LaminateUncertainty?,
) : Serializable {
    val displayModelLabel: String get() = modelLabel.cleanModelLabel()
    val predictedPtDisplacement: Double? get() = curve.displacementAtForce(predictedPt)
}

data class LaminateUncertainty(
    val reliabilityScore: Double?,
    val confidenceLabel: String,
    val interpolationLabel: String,
    val nearestDistance: Double?,
    val nearestCount: Int,
    val localPtStd: Double?,
    val ptIntervalLow: Double?,
    val ptIntervalHigh: Double?,
    val typeConsistency: Double?,
    val notes: List<String>,
) : Serializable

data class LaminateXai(
    val title: String,
    val summary: String,
    val method: String,
    val featureSet: String,
    val topFeatures: List<LaminateXaiFeature>,
) : Serializable

data class LaminateXaiFeature(
    val label: String,
    val importance: Double,
    val category: String,
    val explanation: String,
) : Serializable

data class LaminateDesignSpaceInsight(
    val recommendations: List<LaminateDesignSpaceRecommendation>,
    val caseInsights: List<LaminateDesignSpaceCaseInsight>,
    val mapPoints: List<LaminateDesignSpacePoint>,
    val notes: List<String>,
) : Serializable

data class LaminateDesignSpacePoint(
    val theta1: Double,
    val theta2: Double,
    val caseName: String,
    val testId: String,
    val pt: Double,
    val observedType: Int?,
    val distance: Double,
    val source: String,
) : Serializable

data class LaminateDesignSpaceRecommendation(
    val theta1: Double,
    val theta2: Double,
    val caseName: String,
    val expectedPt: Double,
    val observedType: Int?,
    val score: Double,
    val scoreComponents: LaminateDesignSpaceScore,
    val rationale: String,
) : Serializable

data class LaminateDesignSpaceScore(
    val pt: Double,
    val type: Double,
    val proximity: Double,
) : Serializable

data class LaminateDesignSpaceCaseInsight(
    val caseName: String,
    val focusKind: String,
    val focusCount: Int,
    val count: Int,
    val focusRate: Double,
    val theta1Min: Double?,
    val theta1Max: Double?,
    val theta2Min: Double?,
    val theta2Max: Double?,
    val bestTheta1: Double?,
    val bestTheta2: Double?,
    val bestPt: Double?,
    val bestType: Int?,
) : Serializable

class LaminateApi {
    fun models(): LaminateModelCatalog {
        val json = JSONObject(request("GET", endpoint("/api/v1/dd-laminate/models")))
        return LaminateModelCatalog(
            responseModels = json.optJSONArray("response_models").toModelInfoList(),
            u3Models = json.optJSONArray("u3_pt_models").toModelInfoList(),
        )
    }

    fun predictResponse(
        caseName: String,
        theta1: Double,
        theta2: Double,
        modelKey: String,
        panelAIn: Double = 6.0,
        panelBIn: Double = 4.0,
    ): LaminateResult {
        val body = JSONObject()
            .put("case", caseName)
            .put("theta1", theta1)
            .put("theta2", theta2)
            .put("model", modelKey)
            .put("panel_a_in", panelAIn)
            .put("panel_b_in", panelBIn)
            .toString()
        val json = JSONObject(request("POST", endpoint("/api/v1/dd-laminate/predict/response"), body))
        return json.toLaminateResult()
    }

    fun predictU3Forecast(caseName: String, theta1: Double, theta2: Double, modelKey: String): LaminateResult {
        val body = JSONObject()
            .put("case", caseName)
            .put("theta1", theta1)
            .put("theta2", theta2)
            .put("test_id", "Forecast")
            .put("model", modelKey)
            .toString()
        val json = JSONObject(request("POST", endpoint("/api/v1/dd-laminate/predict/u3-forecast"), body))
        return json.toLaminateResult()
    }

    fun designSpace(caseName: String, theta1: Double, theta2: Double, scope: String = "response"): LaminateDesignSpaceInsight {
        val body = JSONObject()
            .put("case", caseName)
            .put("theta1", theta1)
            .put("theta2", theta2)
            .put("scope", scope)
            .toString()
        val json = JSONObject(request("POST", endpoint("/api/v1/dd-laminate/design-space"), body))
        return json.toLaminateDesignSpaceInsight()
    }

    private fun org.json.JSONArray?.toModelInfoList(): List<LaminateModelInfo> {
        if (this == null) return emptyList()
        return List(length()) { index ->
            val item = getJSONObject(index)
            LaminateModelInfo(
                key = item.getString("key"),
                label = item.getString("label"),
                description = item.optString("description"),
                available = item.optBoolean("available"),
            )
        }
    }

    private fun request(method: String, url: URL, body: String? = null): String {
        val connection = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 8_000
            readTimeout = 20_000
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

    private fun endpoint(path: String): URL = URL("${LAMINATE_BASE_URL}/${path.trimStart('/')}")
}

private fun JSONObject?.toDoubleMap(): Map<String, Double> {
    if (this == null) return emptyMap()
    return keys().asSequence().associateWith { key -> optDouble(key) }
}

private fun JSONObject.toLaminateResult(): LaminateResult {
    return LaminateResult(
        predictedType = optInt("predicted_type"),
        confidence = optionalDouble("confidence"),
        predictedPt = optionalDouble("predicted_pt"),
        predictedMaxForce = optionalDouble("predicted_max_force"),
        modelLabel = optString("model_label"),
        probabilities = optJSONObject("probabilities").toDoubleMap(),
        curve = optJSONArray("curve").toCurvePoints(),
        xai = optJSONObject("xai").toLaminateXai(),
        curveFit = optJSONObject("curve_fit").toLaminateCurveFit(),
        uncertainty = optJSONObject("uncertainty").toLaminateUncertainty(),
    )
}

private fun org.json.JSONArray?.toCurvePoints(): List<LaminateCurvePoint> {
    if (this == null) return emptyList()
    return List(length()) { index ->
        val item = getJSONObject(index)
        LaminateCurvePoint(item.optDouble("displacement"), item.optDouble("force"))
    }
}

private fun JSONObject.optionalDouble(key: String): Double? = if (has(key) && !isNull(key)) optDouble(key) else null

private fun JSONObject?.toLaminateUncertainty(): LaminateUncertainty? {
    if (this == null) return null
    val notesArray = optJSONArray("notes")
    val notes = if (notesArray == null) {
        emptyList()
    } else {
        List(notesArray.length()) { index -> notesArray.optString(index) }
    }
    return LaminateUncertainty(
        reliabilityScore = optionalDouble("reliability_score"),
        confidenceLabel = optString("confidence_label", "low"),
        interpolationLabel = optString("interpolation_label", "extrapolation"),
        nearestDistance = optionalDouble("nearest_distance"),
        nearestCount = optInt("nearest_count", 0),
        localPtStd = optionalDouble("local_pt_std"),
        ptIntervalLow = optionalDouble("pt_interval_low"),
        ptIntervalHigh = optionalDouble("pt_interval_high"),
        typeConsistency = optionalDouble("type_consistency"),
        notes = notes,
    )
}

private fun JSONObject?.toLaminateCurveFit(): LaminateCurveFit? {
    if (this == null) return null
    return LaminateCurveFit(
        firstLine = optJSONObject("first_line").toLaminateCurveLine(),
        secondLine = optJSONObject("second_line").toLaminateCurveLine(),
        kink = optJSONObject("kink").toLaminateCurveCoordinate(),
        detectedKink = optJSONObject("detected_kink").toLaminateCurveCoordinate(),
        firstStartX = optionalDouble("first_start_x"),
        firstEndX = optionalDouble("first_end_x"),
        secondStartX = optionalDouble("second_start_x"),
        secondEndX = optionalDouble("second_end_x"),
    )
}

private fun JSONObject?.toLaminateCurveLine(): LaminateCurveLine? {
    if (this == null) return null
    return LaminateCurveLine(
        slope = optDouble("slope"),
        intercept = optDouble("intercept"),
    )
}

private fun JSONObject?.toLaminateCurveCoordinate(): LaminateCurveCoordinate? {
    if (this == null) return null
    return LaminateCurveCoordinate(
        displacement = optDouble("displacement"),
        force = optDouble("force"),
    )
}

private fun JSONObject?.toLaminateXai(): LaminateXai? {
    if (this == null) return null
    val featureArray = optJSONArray("top_features")
    val features = if (featureArray == null) {
        emptyList()
    } else {
        List(featureArray.length()) { index ->
            val item = featureArray.getJSONObject(index)
            LaminateXaiFeature(
                label = item.optString("label", item.optString("name")),
                importance = item.optDouble("importance"),
                category = item.optString("category"),
                explanation = item.optString("explanation"),
            )
        }
    }
    return LaminateXai(
        title = optString("title", "Why this prediction?"),
        summary = optString("summary"),
        method = optString("method"),
        featureSet = optString("feature_set"),
        topFeatures = features,
    )
}

private fun JSONObject.toLaminateDesignSpaceInsight(): LaminateDesignSpaceInsight {
    val recommendationArray = optJSONArray("recommendations")
    val recommendations = if (recommendationArray == null) {
        emptyList()
    } else {
        List(recommendationArray.length()) { index ->
            val item = recommendationArray.getJSONObject(index)
            val components = item.optJSONObject("score_components")
            LaminateDesignSpaceRecommendation(
                theta1 = item.optDouble("theta1"),
                theta2 = item.optDouble("theta2"),
                caseName = item.optString("case"),
                expectedPt = item.optDouble("expected_pt"),
                observedType = item.optionalInt("observed_type"),
                score = item.optDouble("score"),
                scoreComponents = LaminateDesignSpaceScore(
                    pt = components?.optDouble("pt") ?: 0.0,
                    type = components?.optDouble("type") ?: 0.0,
                    proximity = components?.optDouble("proximity") ?: 0.0,
                ),
                rationale = item.optString("rationale"),
            )
        }
    }

    val insightArray = optJSONArray("case_insights")
    val caseInsights = if (insightArray == null) {
        emptyList()
    } else {
        List(insightArray.length()) { index ->
            val item = insightArray.getJSONObject(index)
            LaminateDesignSpaceCaseInsight(
                caseName = item.optString("case"),
                focusKind = item.optString("focus_kind"),
                focusCount = item.optInt("focus_count"),
                count = item.optInt("count"),
                focusRate = item.optDouble("focus_rate"),
                theta1Min = item.optionalDouble("theta1_min"),
                theta1Max = item.optionalDouble("theta1_max"),
                theta2Min = item.optionalDouble("theta2_min"),
                theta2Max = item.optionalDouble("theta2_max"),
                bestTheta1 = item.optionalDouble("best_theta1"),
                bestTheta2 = item.optionalDouble("best_theta2"),
                bestPt = item.optionalDouble("best_pt"),
                bestType = item.optionalInt("best_type"),
            )
        }
    }

    val pointArray = optJSONArray("map_points")
    val mapPoints = if (pointArray == null) {
        emptyList()
    } else {
        List(pointArray.length()) { index ->
            val item = pointArray.getJSONObject(index)
            LaminateDesignSpacePoint(
                theta1 = item.optDouble("theta1"),
                theta2 = item.optDouble("theta2"),
                caseName = item.optString("case"),
                testId = item.optString("test_id"),
                pt = item.optDouble("pt"),
                observedType = item.optionalInt("type"),
                distance = item.optDouble("distance"),
                source = item.optString("source"),
            )
        }
    }

    return LaminateDesignSpaceInsight(
        recommendations = recommendations,
        caseInsights = caseInsights,
        mapPoints = mapPoints,
        notes = optJSONArray("notes").toStringList(),
    )
}

private fun org.json.JSONArray?.toStringList(): List<String> {
    if (this == null) return emptyList()
    return List(length()) { index -> optString(index) }
}

private fun JSONObject.optionalInt(key: String): Int? = if (has(key) && !isNull(key)) optInt(key) else null

private fun String.cleanModelLabel(): String {
    val cleaned = trim()
    val lower = cleaned.lowercase()
    return when {
        lower == "u3_forecast_physics_v2" || lower == "u3_forecast_physics" -> "u3 Forecast - Machine Learning"
        lower == "u3_forecast_goint_physics_v2" || lower == "u3_forecast_goint_physics" -> "u3 Forecast - Deep Learning"
        lower == "u3 forecast - physics xai" || lower == "u3 forecast - machine learning" -> "u3 Forecast - Machine Learning"
        lower == "u3 forecast - gointmlp nn" || lower == "u3 forecast - deep learning" -> "u3 Forecast - Deep Learning"
        lower == "response_surrogate_physics" || lower == "response_surrogate_physics_v2" -> "Laminate Forecast - Machine Learning"
        lower == "response_goint_physics" || lower == "response_goint_physics_nn_v2" -> "Laminate Forecast - Deep Learning"
        lower == "response_distilled_grid_conf_v1" || lower == "laminate forecast - distilled nn v3" -> "Laminate Forecast - Distilled NN v3"
        lower == "response_distilled_grid_v1" || lower == "laminate forecast - distilled nn v2" -> "Laminate Forecast - Distilled NN v2"
        lower == "response_distilled_v1" || lower == "laminate forecast - distilled nn" -> "Laminate Forecast - Distilled NN"
        lower.contains("machine learning") -> "Laminate Forecast - Machine Learning"
        lower.contains("deep learning") -> "Laminate Forecast - Deep Learning"
        lower.contains("tree + physics") || lower.contains("tree + compact physics") || lower.contains("physics xai") && lower.contains("tree") -> "Laminate Forecast - Machine Learning"
        lower.contains("gointmlp + physics") || lower.contains("gointmlp + compact physics") || lower.contains("nn-friendly physics") -> "Laminate Forecast - Deep Learning"
        else -> when (lower) {
            "laminate forecast - cases 2/3/4", "extra trees + pca", "extratrees + pca" -> "ExtraTrees + PCA"
            "laminate forecast - gointmlp nn + clt (legacy case3/4)", "gointmlp-style nn" -> "GointMLP NN"
            "laminate forecast - tree (theta)" -> "Laminate Forecast - Tree (Theta)"
            "laminate forecast - gointmlp (theta)" -> "Laminate Forecast - GointMLP (Theta)"
            "u3 forecast - extratrees + pca" -> "u3 Forecast - Tree (Theta)"
            else -> cleaned
        }
    }
}

private fun List<LaminateCurvePoint>.displacementAtForce(targetForce: Double?): Double? {
    val force = targetForce?.takeIf { it.isFinite() } ?: return null
    val first = firstOrNull() ?: return null
    if (force <= first.force) return first.displacement
    for (index in 1 until size) {
        val previous = this[index - 1]
        val current = this[index]
        val low = minOf(previous.force, current.force)
        val high = maxOf(previous.force, current.force)
        if (force < low || force > high) continue
        val delta = current.force - previous.force
        if (delta == 0.0) return current.displacement
        val ratio = (force - previous.force) / delta
        return previous.displacement + ratio * (current.displacement - previous.displacement)
    }
    return lastOrNull()?.displacement
}

private fun Double?.metricText(digits: Int): String = this?.let { "%.${digits}f".format(it) } ?: "-"
private fun Double.metricText(digits: Int): String = "%.${digits}f".format(this)
private fun Double.dimensionReadout(): String {
    val rounded = kotlin.math.round(this * 1000.0) / 1000.0
    return if (rounded % 1.0 == 0.0) {
        rounded.toInt().toString()
    } else {
        "%.3f".format(rounded).trimEnd('0').trimEnd('.')
    }
}
private fun Double?.percentText(): String = this?.let { "%.1f%%".format(it * 100.0) } ?: "-"
private fun Double.percentText(): String = "%.1f%%".format(this * 100.0)
