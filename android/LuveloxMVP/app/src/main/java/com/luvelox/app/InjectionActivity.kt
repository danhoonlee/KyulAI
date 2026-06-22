package com.luvelox.app

import android.app.Activity
import android.graphics.Color
import android.graphics.Typeface
import android.os.Bundle
import android.view.Gravity
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.LinearLayout
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
        val scroll = ScrollView(this).apply { setBackgroundColor(color(0xF7F8FB)) }
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(24), dp(20), dp(44))
        }
        scroll.addView(root)
        setContentView(scroll)

        root.addView(label("INJECTION MODULE", color(0x127C82), 12f, Typeface.BOLD))
        root.addView(label("Sprue Pressure Forecast", color(0x17202A), 32f, Typeface.BOLD))
        root.addView(paragraph("Run Moldex3D-style sprue pressure and filling pressure prediction directly inside C2ES."), margin(top = 8, bottom = 16))

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
            background = rounded(color(0x17202A), dp(8))
            setOnClickListener { predict() }
        }, margin(top = 16))
        root.addView(inputCard)

        resultContainer = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        root.addView(resultContainer, margin(top = 16))
    }

    private fun loadCatalog() {
        Thread {
            val loaded = runCatching { InjectionApiNative().catalog() }
            runOnUiThread {
                loaded.onSuccess { catalog ->
                    sprueModels = catalog.sprueModels.filter { it.available }.ifEmpty {
                        listOf(InjectionModelInfo(DEFAULT_SPRUE_MODEL, "ExtraTrees + PCA", true))
                    }
                    fillingModels = catalog.fillingModels.filter { it.available }.ifEmpty {
                        listOf(InjectionModelInfo(DEFAULT_FILLING_MODEL, "ExtraTrees histogram", true))
                    }
                    geometries = catalog.geometries.ifEmpty { listOf(fallbackGeometry()) }
                    processes = catalog.processes.ifEmpty { listOf(fallbackProcess()) }
                    bindSpinners()
                    statusText.text = "API ready"
                    statusText.setTextColor(color(0x127C82))
                    renderValues()
                }.onFailure {
                    sprueModels = listOf(InjectionModelInfo(DEFAULT_SPRUE_MODEL, "ExtraTrees + PCA", true))
                    fillingModels = listOf(InjectionModelInfo(DEFAULT_FILLING_MODEL, "ExtraTrees histogram", true))
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
        geometrySpinner.setOnItemSelectedListener(simpleSelectionListener { renderValues() })
        processSpinner.setOnItemSelectedListener(simpleSelectionListener { renderValues() })
    }

    private fun simpleSelectionListener(onSelected: () -> Unit) = object : android.widget.AdapterView.OnItemSelectedListener {
        override fun onItemSelected(parent: android.widget.AdapterView<*>?, view: android.view.View?, position: Int, id: Long) = onSelected()
        override fun onNothingSelected(parent: android.widget.AdapterView<*>?) = Unit
    }

    private fun renderValues() {
        valuesGrid.removeAllViews()
        val geometry = selectedGeometry()
        val process = selectedProcess()
        val values = listOf(
            "L" to "${geometry.double("L_mm").metricText(2)} mm",
            "W" to "${geometry.double("W_mm").metricText(2)} mm",
            "t" to "${geometry.double("t_mm").metricText(3)} mm",
            "D" to "${geometry.double("D_mm").metricText(2)} mm",
            "Melt" to "${process.double("melt_temp_C").metricText(1)} C",
            "Mold" to "${process.double("mold_temp_C").metricText(1)} C",
            "Injection" to "${process.double("injection_time_s").metricText(3)} s",
            "Packing" to "${process.double("packing_pressure_MPa").metricText(1)} MPa",
        )
        values.chunked(2).forEach { rowItems ->
            val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
            rowItems.forEach { (name, value) ->
                row.addView(metricBox(name, value), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply { marginEnd = dp(8) })
            }
            valuesGrid.addView(row, margin(top = 10))
        }
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
            addView(label(result.predictedMaxPressureMPa.metricText(2), color(0x17202A), 34f, Typeface.BOLD))
            addView(label("Max sprue pressure MPa", color(0x647084), 14f, Typeface.BOLD))
        }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        top.addView(label("${result.predictedMaxTimeS.metricText(3)} s", color(0x16845F), 18f, Typeface.BOLD))
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
            card.addView(label("Filling pressure", color(0x17202A), 18f, Typeface.BOLD), margin(top = 16))
            result.fillingBins.take(5).forEach { bin ->
                card.addView(label("Group ${bin.group}  ${bin.volumeRatioPct.metricText(1)}%", color(0x647084), 13f, Typeface.BOLD), margin(top = 6))
            }
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

    private fun selectedGeometry(): InjectionDoeOption = geometries.getOrNull(geometrySpinner.selectedItemPosition) ?: fallbackGeometry()
    private fun selectedProcess(): InjectionDoeOption = processes.getOrNull(processSpinner.selectedItemPosition) ?: fallbackProcess()

    private fun inputBlock(title: String, child: android.view.View): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        addView(label(title, color(0x647084), 12f, Typeface.BOLD))
        addView(child, margin(top = 6))
    }

    private fun metricBox(title: String, value: String): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(12), dp(10), dp(12), dp(10))
        background = rounded(color(0xF4F8FA), dp(8))
        addView(label(title, color(0x647084), 12f, Typeface.BOLD))
        addView(label(value, color(0x17202A), 15f, Typeface.BOLD))
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

    private fun strokedRounded(fill: Int, stroke: Int, radius: Int) = android.graphics.drawable.GradientDrawable().apply {
        setColor(fill)
        setStroke(dp(1), stroke)
        cornerRadius = radius.toFloat()
    }

    private fun color(rgb: Int): Int = Color.rgb(rgb shr 16 and 0xFF, rgb shr 8 and 0xFF, rgb and 0xFF)
    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}

private data class InjectionCatalog(
    val sprueModels: List<InjectionModelInfo>,
    val fillingModels: List<InjectionModelInfo>,
    val geometries: List<InjectionDoeOption>,
    val processes: List<InjectionDoeOption>,
)

private data class InjectionModelInfo(val key: String, val label: String, val available: Boolean) {
    val displayLabel: String get() = label.cleanInjectionModelLabel()
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
    val modelLabel: String,
    val fillingModelLabel: String,
    val curveCount: Int,
    val fillingBins: List<InjectionFillingBin>,
) {
    val displayModelLabel: String get() = modelLabel.cleanInjectionModelLabel()
    val displayFillingModelLabel: String get() = fillingModelLabel.cleanInjectionModelLabel()
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
            modelLabel = json.optString("model_label"),
            fillingModelLabel = json.optString("filling_model_label"),
            curveCount = json.optJSONArray("curve")?.length() ?: 0,
            fillingBins = filling?.optJSONArray("bins").toFillingBins(),
        )
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

private fun String.cleanInjectionModelLabel(): String {
    val trimmed = trim()
    val prefix = listOf("Sprue Pressure", "Filling Pressure").firstOrNull { trimmed.startsWith(it, ignoreCase = true) }
    val normalized = (prefix?.let { trimmed.drop(it.length) } ?: trimmed).trim(' ', '-', ':')
    return when (normalized.lowercase()) {
        "classical ml + pca" -> "ExtraTrees + PCA"
        "classical ml histogram" -> "ExtraTrees histogram"
        "gointmlp-style nn" -> "GointMLP NN"
        "deeponet operator nn" -> "DeepONet NN"
        "deeponet histogram nn" -> "DeepONet NN"
        else -> normalized
    }
}

private fun Double?.metricText(digits: Int): String = this?.let { "%.${digits}f".format(it) } ?: "-"
private fun Double.metricText(digits: Int): String = "%.${digits}f".format(this)
