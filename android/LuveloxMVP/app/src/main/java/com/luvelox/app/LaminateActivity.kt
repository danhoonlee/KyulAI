package com.luvelox.app

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.os.Bundle
import android.text.Editable
import android.text.InputType
import android.text.TextWatcher
import android.view.Gravity
import android.view.View
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.SeekBar
import android.widget.Spinner
import android.widget.TextView
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
const val EXTRA_LAMINATE_RESULT = "com.luvelox.app.EXTRA_LAMINATE_RESULT"
const val EXTRA_LAMINATE_CASE = "com.luvelox.app.EXTRA_LAMINATE_CASE"
const val EXTRA_LAMINATE_THETA1 = "com.luvelox.app.EXTRA_LAMINATE_THETA1"
const val EXTRA_LAMINATE_THETA2 = "com.luvelox.app.EXTRA_LAMINATE_THETA2"

class LaminateActivity : Activity() {
    private lateinit var theta1Input: EditText
    private lateinit var theta2Input: EditText
    private lateinit var theta1Readout: TextView
    private lateinit var theta2Readout: TextView
    private lateinit var theta1SeekBar: SeekBar
    private lateinit var theta2SeekBar: SeekBar
    private lateinit var caseSpinner: Spinner
    private lateinit var modelSpinner: Spinner
    private lateinit var statusText: TextView
    private lateinit var resultContainer: LinearLayout
    private lateinit var plyPreview: PlyStackPreviewView
    private lateinit var plyCountText: TextView
    private lateinit var stackFormulaText: TextView
    private var models: List<LaminateModelInfo> = emptyList()
    private var isSyncingTheta = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        render()
        loadModels()
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
        root.addView(label("C2ES\nLaminate Forecast", LaminateV2.ink, 34f, Typeface.BOLD).apply {
            includeFontPadding = false
        }, margin(top = 8))
        root.addView(paragraph("Forecast laminate Type, Pt, and response curve from case and theta inputs."), margin(top = 8, bottom = 14))
        root.addView(forecastStrip(), margin(bottom = 14))

        val inputCard = card()
        val header = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        header.addView(LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(label("FORECAST SETUP", LaminateV2.blue, 11f, Typeface.BOLD))
            addView(label("Response Forecast", LaminateV2.ink, 20f, Typeface.BOLD))
        }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        statusText = label("Checking", LaminateV2.blue, 12f, Typeface.BOLD).apply {
            setPadding(dp(10), dp(6), dp(10), dp(6))
            background = blueSoftBackground()
        }
        header.addView(statusText)
        inputCard.addView(header)

        caseSpinner = Spinner(this).apply {
            adapter = ArrayAdapter(this@LaminateActivity, android.R.layout.simple_spinner_dropdown_item, listOf("Case2", "Case3", "Case4"))
            onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
                override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                    updatePlyPreview()
                }

                override fun onNothingSelected(parent: AdapterView<*>?) = Unit
            }
        }
        inputCard.addView(caseSpinner, margin(top = 14))

        theta1Input = numberInput("30")
        theta2Input = numberInput("-30")
        theta1Readout = angleReadout(30)
        theta2Readout = angleReadout(-30)
        theta1SeekBar = angleSeekBar(30)
        theta2SeekBar = angleSeekBar(-30)
        inputCard.addView(angleControl("Theta 1", theta1Input, theta1Readout, theta1SeekBar), margin(top = 14))
        inputCard.addView(angleControl("Theta 2", theta2Input, theta2Readout, theta2SeekBar), margin(top = 10))

        modelSpinner = Spinner(this)
        inputCard.addView(inputBlock("Model", modelSpinner), margin(top = 14))
        inputCard.addView(plyPreviewCard(), margin(top = 14))

        inputCard.addView(Button(this).apply {
            text = "Predict response"
            setTextColor(Color.WHITE)
            useAppFont(Typeface.BOLD)
            background = commandButtonBackground()
            setOnClickListener { predict() }
        }, margin(top = 16))

        root.addView(inputCard)
        bindThetaControls()
        updatePlyPreview()

        resultContainer = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        root.addView(resultContainer, margin(top = 16))
    }

    private fun loadModels() {
        Thread {
            val loaded = runCatching {
                LaminateApi().models().filter { it.available }
            }.getOrElse { emptyList() }
            runOnUiThread {
                models = optimalModels(loaded).ifEmpty {
                    listOf(LaminateModelInfo(DEFAULT_RESPONSE_MODEL, "Laminate Forecast - Machine Learning", "", false))
                }
                modelSpinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, models.map { it.displayLabel })
                statusText.text = if (loaded.isEmpty()) "Offline" else "API ready"
                statusText.setTextColor(if (loaded.isEmpty()) LaminateV2.red else LaminateV2.blue)
            }
        }.start()
    }

    private fun optimalModels(allModels: List<LaminateModelInfo>): List<LaminateModelInfo> {
        val byKey = allModels.associateBy { it.key }
        val selected = listOfNotNull(
            listOf(DEFAULT_RESPONSE_MODEL, "response_surrogate_physics").firstNotNullOfOrNull { byKey[it] },
            listOf(DEEP_RESPONSE_MODEL, "response_goint_physics").firstNotNullOfOrNull { byKey[it] },
        )
        return selected.ifEmpty { allModels.take(2) }
    }

    private fun predict() {
        val theta1 = parseThetaDegrees(theta1Input.text.toString())
        val theta2 = parseThetaDegrees(theta2Input.text.toString())
        if (theta1 == null || theta2 == null) {
            showError("Enter numeric theta values.")
            return
        }
        theta1Input.setText(theta1.toString())
        theta2Input.setText(theta2.toString())
        updatePlyPreview()
        val model = models.getOrNull(modelSpinner.selectedItemPosition)?.key ?: DEFAULT_RESPONSE_MODEL
        statusText.text = "Predicting"
        Thread {
            val result = runCatching {
                LaminateApi().predict(
                    caseName = caseSpinner.selectedItem.toString(),
                    theta1 = theta1.toDouble(),
                    theta2 = theta2.toDouble(),
                    modelKey = model,
                )
            }
            runOnUiThread {
                result.onSuccess {
                    statusText.text = "API ready"
                    startActivity(Intent(this@LaminateActivity, LaminateResultActivity::class.java).apply {
                        putExtra(EXTRA_LAMINATE_RESULT, it)
                        putExtra(EXTRA_LAMINATE_CASE, caseSpinner.selectedItem.toString())
                        putExtra(EXTRA_LAMINATE_THETA1, theta1)
                        putExtra(EXTRA_LAMINATE_THETA2, theta2)
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
            card.addView(label("Why this prediction?", LaminateV2.ink, 18f, Typeface.BOLD), margin(top = 18))
            card.addView(paragraph(xai.summary), margin(top = 6))
            card.addView(label("Method: ${xai.method} · ${xai.featureSet}", LaminateV2.blue, 12f, Typeface.BOLD), margin(top = 8))
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
                    text = "Show ${hiddenFeatures.size} more features"
                    textSize = 13f
                    setTextColor(LaminateV2.blue)
                    useAppFont(Typeface.BOLD)
                    background = blueSoftBackground()
                    setOnClickListener {
                        val shouldExpand = hiddenList.visibility != View.VISIBLE
                        hiddenList.visibility = if (shouldExpand) View.VISIBLE else View.GONE
                        text = if (shouldExpand) "Hide extra features" else "Show ${hiddenFeatures.size} more features"
                    }
                }
                card.addView(toggle, margin(top = 8))
                card.addView(hiddenList)
            }
        }
        resultContainer.addView(card)
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
        addView(legendBadge("theta1", color(0x657AD4)))
        addView(legendBadge("theta2", color(0xBC8F70)), LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
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
            "Case3" -> "[[+/-theta1]/[+/-theta2]/[-/+theta1]/[-/+theta2]] x 2"
            "Case4" -> "([+/-theta1]/[+/-theta2]) x 2 + ([-/+theta1]/[-/+theta2]) x 2"
            else -> "[[+/-theta1]/[+/-theta2]] x 4"
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
            addView(label(feature.label, LaminateV2.ink, 12f, Typeface.BOLD).apply {
                maxLines = 1
            }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            addView(label(feature.category, LaminateV2.blue, 10f, Typeface.BOLD).apply {
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
        addView(label(feature.explanation, LaminateV2.muted, 11f, Typeface.NORMAL), margin(top = 3))
    }

    private fun card(): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(18), dp(18), dp(18), dp(18))
        background = strokedRounded(Color.WHITE, LaminateV2.line, dp(8))
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
        setColor(LaminateV2.ink)
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

    private fun color(rgb: Int): Int = Color.rgb(rgb shr 16 and 0xFF, rgb shr 8 and 0xFF, rgb and 0xFF)

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}

object LaminateV2 {
    val background: Int = Color.rgb(246, 249, 252)
    val field: Int = Color.rgb(239, 246, 255)
    val previewField: Int = Color.rgb(236, 243, 246)
    val line: Int = Color.rgb(208, 220, 236)
    val blue: Int = Color.rgb(37, 99, 235)
    val blueSoft: Int = Color.rgb(219, 234, 254)
    val blueLine: Int = Color.rgb(147, 197, 253)
    val green: Int = Color.rgb(5, 150, 105)
    val greenSoft: Int = Color.rgb(220, 252, 231)
    val greenLine: Int = Color.rgb(134, 239, 172)
    val red: Int = Color.rgb(180, 35, 24)
    val ink: Int = Color.rgb(12, 19, 28)
    val muted: Int = Color.rgb(91, 107, 128)
}

private data class LaminateModelInfo(
    val key: String,
    val label: String,
    val description: String,
    val available: Boolean,
) {
    val displayLabel: String get() = label.cleanModelLabel()
}

data class LaminateCurvePoint(val displacement: Double, val force: Double) : Serializable

data class LaminateResult(
    val predictedType: Int,
    val confidence: Double?,
    val predictedPt: Double?,
    val predictedMaxForce: Double?,
    val modelLabel: String,
    val probabilities: Map<String, Double>,
    val curve: List<LaminateCurvePoint>,
    val xai: LaminateXai?,
) : Serializable {
    val displayModelLabel: String get() = modelLabel.cleanModelLabel()
    val predictedPtDisplacement: Double? get() = curve.displacementAtForce(predictedPt)
}

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

private class LaminateApi {
    fun models(): List<LaminateModelInfo> {
        val json = JSONObject(request("GET", endpoint("/api/v1/dd-laminate/models")))
        val array = json.getJSONArray("response_models")
        return List(array.length()) { index ->
            val item = array.getJSONObject(index)
            LaminateModelInfo(
                key = item.getString("key"),
                label = item.getString("label"),
                description = item.optString("description"),
                available = item.optBoolean("available"),
            )
        }
    }

    fun predict(caseName: String, theta1: Double, theta2: Double, modelKey: String): LaminateResult {
        val body = JSONObject()
            .put("case", caseName)
            .put("theta1", theta1)
            .put("theta2", theta2)
            .put("model", modelKey)
            .toString()
        val json = JSONObject(request("POST", endpoint("/api/v1/dd-laminate/predict/response"), body))
        return LaminateResult(
            predictedType = json.optInt("predicted_type"),
            confidence = json.optionalDouble("confidence"),
            predictedPt = json.optionalDouble("predicted_pt"),
            predictedMaxForce = json.optionalDouble("predicted_max_force"),
            modelLabel = json.optString("model_label"),
            probabilities = json.optJSONObject("probabilities").toDoubleMap(),
            curve = json.optJSONArray("curve").toCurvePoints(),
            xai = json.optJSONObject("xai").toLaminateXai(),
        )
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

private fun org.json.JSONArray?.toCurvePoints(): List<LaminateCurvePoint> {
    if (this == null) return emptyList()
    return List(length()) { index ->
        val item = getJSONObject(index)
        LaminateCurvePoint(item.optDouble("displacement"), item.optDouble("force"))
    }
}

private fun JSONObject.optionalDouble(key: String): Double? = if (has(key) && !isNull(key)) optDouble(key) else null

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

private fun String.cleanModelLabel(): String {
    val cleaned = trim()
    val lower = cleaned.lowercase()
    return when {
        lower == "response_surrogate_physics" || lower == "response_surrogate_physics_v2" -> "Laminate Forecast - Machine Learning"
        lower == "response_goint_physics" || lower == "response_goint_physics_nn_v2" -> "Laminate Forecast - Deep Learning"
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
            "u3 forecast - physics xai" -> "u3 Forecast - Machine Learning"
            "u3 forecast - gointmlp nn" -> "u3 Forecast - Deep Learning"
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
private fun Double?.percentText(): String = this?.let { "%.1f%%".format(it * 100.0) } ?: "-"
private fun Double.percentText(): String = "%.1f%%".format(this * 100.0)
