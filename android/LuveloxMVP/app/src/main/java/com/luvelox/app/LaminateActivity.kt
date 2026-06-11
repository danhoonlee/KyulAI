package com.luvelox.app

import android.app.Activity
import android.graphics.Color
import android.graphics.Typeface
import android.os.Bundle
import android.text.InputType
import android.view.Gravity
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.Spinner
import android.widget.TextView
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL

private const val LAMINATE_BASE_URL = "https://laminate.luvelox.com"
private const val DEFAULT_RESPONSE_MODEL = "response_surrogate"

class LaminateActivity : Activity() {
    private lateinit var theta1Input: EditText
    private lateinit var theta2Input: EditText
    private lateinit var caseSpinner: Spinner
    private lateinit var modelSpinner: Spinner
    private lateinit var statusText: TextView
    private lateinit var resultContainer: LinearLayout
    private var models: List<LaminateModelInfo> = emptyList()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        render()
        loadModels()
    }

    private fun render() {
        val scroll = ScrollView(this).apply { setBackgroundColor(color(0xF7F8FB)) }
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(24), dp(20), dp(44))
        }
        scroll.addView(root)
        setContentView(scroll)

        root.addView(label("LAMINATE MODULE", color(0x127C82), 12f, Typeface.BOLD))
        root.addView(label("Double-Double Forecast", color(0x17202A), 32f, Typeface.BOLD))
        root.addView(paragraph("Run Type, Pt, and force-displacement response prediction directly inside Luvelox."), margin(top = 8, bottom = 16))

        val inputCard = card()
        val header = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        header.addView(label("Inputs", color(0x17202A), 18f, Typeface.BOLD), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        statusText = label("Checking", color(0x127C82), 12f, Typeface.BOLD).apply {
            setPadding(dp(10), dp(6), dp(10), dp(6))
            background = rounded(color(0xDFF4F3), dp(999))
        }
        header.addView(statusText)
        inputCard.addView(header)

        caseSpinner = Spinner(this).apply {
            adapter = ArrayAdapter(this@LaminateActivity, android.R.layout.simple_spinner_dropdown_item, listOf("Case2", "Case3", "Case4"))
        }
        inputCard.addView(caseSpinner, margin(top = 14))

        val thetaRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        theta1Input = numberInput("30")
        theta2Input = numberInput("-30")
        thetaRow.addView(inputBlock("Theta 1", theta1Input), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply { marginEnd = dp(8) })
        thetaRow.addView(inputBlock("Theta 2", theta2Input), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply { marginStart = dp(8) })
        inputCard.addView(thetaRow, margin(top = 14))

        modelSpinner = Spinner(this)
        inputCard.addView(inputBlock("Model", modelSpinner), margin(top = 14))

        inputCard.addView(Button(this).apply {
            text = "Predict response"
            setTextColor(Color.WHITE)
            setTypeface(typeface, Typeface.BOLD)
            background = rounded(color(0x17202A), dp(8))
            setOnClickListener { predict() }
        }, margin(top = 16))

        root.addView(inputCard)

        resultContainer = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        root.addView(resultContainer, margin(top = 16))
    }

    private fun loadModels() {
        Thread {
            val loaded = runCatching {
                LaminateApi().models().filter { it.available }
            }.getOrElse { emptyList() }
            runOnUiThread {
                models = loaded.ifEmpty {
                    listOf(LaminateModelInfo(DEFAULT_RESPONSE_MODEL, "ExtraTrees + PCA", "", true))
                }
                modelSpinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, models.map { it.displayLabel })
                statusText.text = if (loaded.isEmpty()) "Offline" else "API ready"
                statusText.setTextColor(if (loaded.isEmpty()) color(0xB42318) else color(0x127C82))
            }
        }.start()
    }

    private fun predict() {
        val theta1 = theta1Input.text.toString().toDoubleOrNull()
        val theta2 = theta2Input.text.toString().toDoubleOrNull()
        if (theta1 == null || theta2 == null) {
            showError("Enter numeric theta values.")
            return
        }
        val model = models.getOrNull(modelSpinner.selectedItemPosition)?.key ?: DEFAULT_RESPONSE_MODEL
        statusText.text = "Predicting"
        Thread {
            val result = runCatching {
                LaminateApi().predict(
                    caseName = caseSpinner.selectedItem.toString(),
                    theta1 = theta1,
                    theta2 = theta2,
                    modelKey = model,
                )
            }
            runOnUiThread {
                result.onSuccess {
                    statusText.text = "API ready"
                    renderResult(it)
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
            addView(label("Type ${result.predictedType}", color(0x17202A), 34f, Typeface.BOLD))
            addView(label(result.displayModelLabel, color(0x647084), 14f, Typeface.BOLD))
        }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        top.addView(label(result.confidence.percentText(), color(0x16845F), 18f, Typeface.BOLD))
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

        card.addView(label("Class probability", color(0x17202A), 18f, Typeface.BOLD), margin(top = 16))
        result.probabilities.toSortedMap().forEach { (label, value) ->
            card.addView(label("$label  ${value.percentText()}", color(0x647084), 13f, Typeface.BOLD), margin(top = 6))
        }
        resultContainer.addView(card)
    }

    private fun showError(message: String) {
        statusText.text = "Error"
        statusText.setTextColor(color(0xB42318))
        resultContainer.removeAllViews()
        resultContainer.addView(card().apply {
            addView(label(message, color(0xB42318), 15f, Typeface.BOLD))
        })
    }

    private fun inputBlock(title: String, child: android.view.View): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        addView(label(title, color(0x647084), 12f, Typeface.BOLD))
        addView(child, margin(top = 6))
    }

    private fun numberInput(initial: String): EditText = EditText(this).apply {
        setText(initial)
        inputType = InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_FLAG_DECIMAL or InputType.TYPE_NUMBER_FLAG_SIGNED
        textSize = 20f
        typeface = Typeface.MONOSPACE
        setPadding(dp(12), 0, dp(12), 0)
        background = rounded(color(0xF4F8FA), dp(8))
    }

    private fun metricBox(title: String, value: String): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(12), dp(10), dp(12), dp(10))
        background = rounded(color(0xF4F8FA), dp(8))
        addView(label(title, color(0x647084), 12f, Typeface.BOLD))
        addView(label(value, color(0x17202A), 16f, Typeface.BOLD))
    }

    private fun card(): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(18), dp(18), dp(18), dp(18))
        background = strokedRounded(Color.WHITE, color(0xD9E0EA), dp(8))
    }

    private fun paragraph(text: String): TextView = label(text, color(0x647084), 15f, Typeface.NORMAL).apply {
        setLineSpacing(dp(3).toFloat(), 1.0f)
    }

    private fun label(text: String, textColor: Int, size: Float, style: Int): TextView = TextView(this).apply {
        this.text = text
        textSize = size
        setTextColor(textColor)
        typeface = Typeface.create(Typeface.DEFAULT, style)
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

    private fun strokedRounded(fill: Int, stroke: Int, radius: Int) = android.graphics.drawable.GradientDrawable().apply {
        setColor(fill)
        setStroke(dp(1), stroke)
        cornerRadius = radius.toFloat()
    }

    private fun color(rgb: Int): Int = Color.rgb(rgb shr 16 and 0xFF, rgb shr 8 and 0xFF, rgb and 0xFF)

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}

private data class LaminateModelInfo(
    val key: String,
    val label: String,
    val description: String,
    val available: Boolean,
) {
    val displayLabel: String get() = label.cleanModelLabel()
}

private data class LaminateCurvePoint(val displacement: Double, val force: Double)

private data class LaminateResult(
    val predictedType: Int,
    val confidence: Double?,
    val predictedPt: Double?,
    val predictedMaxForce: Double?,
    val modelLabel: String,
    val probabilities: Map<String, Double>,
    val curve: List<LaminateCurvePoint>,
) {
    val displayModelLabel: String get() = modelLabel.cleanModelLabel()
    val predictedPtDisplacement: Double? get() = curve.displacementAtForce(predictedPt)
}

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

private fun String.cleanModelLabel(): String {
    return when (trim().lowercase()) {
        "laminate forecast - cases 2/3/4", "extra trees + pca", "extratrees + pca" -> "ExtraTrees + PCA"
        "laminate forecast - gointmlp nn + clt (legacy case3/4)", "gointmlp-style nn" -> "GointMLP NN"
        else -> trim()
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
private fun Double?.percentText(): String = this?.let { "%.1f%%".format(it * 100.0) } ?: "-"
private fun Double.percentText(): String = "%.1f%%".format(this * 100.0)
