package com.kyulai.injection

import android.app.Activity
import android.content.ContentValues
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.MediaStore
import android.view.inputmethod.EditorInfo
import android.view.View
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.PopupMenu
import android.widget.ScrollView
import android.widget.Spinner
import android.widget.TextView
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.Executors

class MainActivity : Activity() {
    private val api = InjectionApi()
    private val executor = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())

    private lateinit var baseUrlField: EditText
    private lateinit var statusText: TextView
    private lateinit var modelText: TextView
    private lateinit var sprueModelSpinner: Spinner
    private lateinit var fillingModelSpinner: Spinner
    private lateinit var geometrySpinner: Spinner
    private lateinit var processSpinner: Spinner
    private lateinit var lField: EditText
    private lateinit var wField: EditText
    private lateinit var tField: EditText
    private lateinit var dField: EditText
    private lateinit var meltField: EditText
    private lateinit var moldField: EditText
    private lateinit var injectionField: EditText
    private lateinit var packingPressureField: EditText
    private lateinit var recentButton: Button
    private lateinit var predictButton: Button
    private lateinit var resultSection: LinearLayout
    private lateinit var chartView: PressureChartView

    private var sprueModels: List<ModelInfo> = emptyList()
    private var fillingModels: List<ModelInfo> = emptyList()
    private var geometries: List<DoeOption> = emptyList()
    private var processes: List<DoeOption> = emptyList()
    private var isBusy = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(buildContent())
        autoCheckApi()
    }

    private fun buildContent(): ScrollView {
        val prefs = getSharedPreferences("settings", MODE_PRIVATE)
        val root = vertical(spacing = 16).apply {
            setPadding(dp(20), dp(18), dp(20), dp(28))
            setBackgroundColor(Ui.background)
        }

        root.addView(title(getString(R.string.app_title), 30))
        root.addView(body(getString(R.string.app_subtitle)))

        root.addView(card().apply {
            statusText = headline(getString(R.string.api_status_checking))
            modelText = caption(getString(R.string.host_checked_auto))
            baseUrlField = EditText(context).apply {
                setText(prefs.getString("base_url", Defaults.DEFAULT_BASE_URL))
                visibility = View.GONE
                setSingleLine(true)
                imeOptions = EditorInfo.IME_ACTION_DONE
                setTextColor(Ui.ink)
                setHintTextColor(Ui.muted)
                background = fieldBackground()
                setOnEditorActionListener { _, actionId, _ ->
                    if (actionId == EditorInfo.IME_ACTION_DONE) {
                        saveBaseUrl()
                        autoCheckApi()
                        true
                    } else {
                        false
                    }
                }
                setOnFocusChangeListener { _, hasFocus ->
                    if (!hasFocus) {
                        saveBaseUrl()
                        autoCheckApi()
                    }
                }
            }
            addView(statusText)
            addView(baseUrlField)
            addView(modelText)
        })

        root.addView(card().apply {
            addView(LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                addView(headline(getString(R.string.injection_inputs)), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
                recentButton = Button(context).apply {
                    text = getString(R.string.recent_inputs)
                    setOnClickListener { showRecentMenu() }
                }
                addView(recentButton)
            })
            sprueModelSpinner = Spinner(context)
            fillingModelSpinner = Spinner(context)
            geometrySpinner = Spinner(context)
            processSpinner = Spinner(context)
            addView(label(getString(R.string.sprue_model)))
            addView(sprueModelSpinner)
            addView(label(getString(R.string.filling_model)))
            addView(fillingModelSpinner)
            addView(label(getString(R.string.geometry)))
            addView(geometrySpinner)
            addView(label(getString(R.string.process)))
            addView(processSpinner)

            lField = input("154.01")
            wField = input("97.42")
            tField = input("2.207")
            dField = input("17.61")
            meltField = input("226.1")
            moldField = input("61.7")
            injectionField = input("2.47")
            packingPressureField = input("69.0")
            listOf(
                "L (mm)" to lField,
                "W (mm)" to wField,
                "t (mm)" to tField,
                "D (mm)" to dField,
                getString(R.string.melt_temp) to meltField,
                getString(R.string.mold_temp) to moldField,
                getString(R.string.injection_time) to injectionField,
                getString(R.string.packing_pressure) to packingPressureField,
            ).forEach { (label, field) ->
                addView(label(label))
                addView(field)
            }
            predictButton = Button(context).apply {
                text = getString(R.string.predict_pressure)
                setTextColor(Color.WHITE)
                background = primaryButtonBackground()
                setOnClickListener { predict() }
            }
            addView(predictButton)
            updateRecentButton()
        })

        resultSection = card().apply {
            visibility = LinearLayout.GONE
        }
        root.addView(resultSection)

        return ScrollView(this).apply { addView(root) }
    }

    private fun autoCheckApi() {
        if (isBusy) return
        isBusy = true
        renderBusy(getString(R.string.api_status_checking))
        showApiSettings(false)
        val baseUrl = baseUrlField.text.toString()
        executor.execute {
            runCatching {
                api.health(baseUrl)
                val models = api.models(baseUrl)
                val doe = api.doe(baseUrl)
                models to doe
            }.onSuccess { (models, doe) ->
                sprueModels = models.sprueModels
                fillingModels = models.fillingModels
                val geometryOptions = doe.first
                val processOptions = doe.second
                geometries = geometryOptions
                processes = processOptions
                main.post {
                    isBusy = false
                    populateSpinners()
                    renderModelStatus()
                    showApiSettings(false)
                    predictButton.isEnabled = true
                }
            }.onFailure { error ->
                sprueModels = emptyList()
                fillingModels = emptyList()
                main.post {
                    isBusy = false
                    setStatus(getString(R.string.connection_failed))
                    modelText.text = friendlyErrorMessage(error)
                    showApiSettings(true)
                    predictButton.isEnabled = true
                }
            }
        }
    }

    private fun populateSpinners() {
        populateModelSpinner(sprueModelSpinner, sprueModels, Defaults.SPRUE_MODEL_KEY)
        populateModelSpinner(fillingModelSpinner, fillingModels, Defaults.FILLING_MODEL_KEY)
        geometrySpinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, geometries.map { it.id }.ifEmpty { listOf("G01") })
        processSpinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, processes.map { it.id }.ifEmpty { listOf("P01") })
        val modelListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                renderModelStatus()
            }

            override fun onNothingSelected(parent: AdapterView<*>?) = Unit
        }
        sprueModelSpinner.onItemSelectedListener = modelListener
        fillingModelSpinner.onItemSelectedListener = modelListener
        geometrySpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                geometries.getOrNull(position)?.let { applyGeometry(it) }
            }

            override fun onNothingSelected(parent: AdapterView<*>?) = Unit
        }
        processSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                processes.getOrNull(position)?.let { applyProcess(it) }
            }

            override fun onNothingSelected(parent: AdapterView<*>?) = Unit
        }
        geometries.firstOrNull()?.let { applyGeometry(it) }
        processes.firstOrNull()?.let { applyProcess(it) }
    }

    private fun populateModelSpinner(spinner: Spinner, models: List<ModelInfo>, defaultKey: String) {
        val currentKey = (spinner.selectedItem as? ModelPickerItem)?.key ?: defaultKey
        val selectedKey = models.firstOrNull { it.key == currentKey }?.key
            ?: models.firstOrNull { it.key == defaultKey && it.available }?.key
            ?: models.firstOrNull { it.available }?.key
            ?: models.firstOrNull()?.key
            ?: defaultKey
        val items = models.map { ModelPickerItem(it.key, it.displayLabel, it.available) }
            .ifEmpty { listOf(ModelPickerItem(defaultKey, defaultKey, false)) }
        spinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, items)
        val selectedIndex = items.indexOfFirst { it.key == selectedKey }
        if (selectedIndex >= 0) spinner.setSelection(selectedIndex)
    }

    private fun predict() {
        val selectedSprue = selectedSprueModel()
        val selectedFilling = selectedFillingModel()
        if (selectedSprue?.available != true || selectedFilling?.available != true) {
            modelText.text = getString(R.string.friendly_model)
            return
        }
        val input = buildInput() ?: run {
            modelText.text = getString(R.string.friendly_input)
            return
        }
        isBusy = true
        renderBusy(getString(R.string.predicting))
        saveBaseUrl()
        val baseUrl = baseUrlField.text.toString()

        executor.execute {
            runCatching {
                api.health(baseUrl)
                api.predictSpruePressure(baseUrl, input)
            }.onSuccess { result ->
                main.post {
                    isBusy = false
                    predictButton.isEnabled = true
                    setStatus(null)
                    renderModelStatus()
                    showApiSettings(false)
                    saveRecentRun(input)
                    renderResult(result)
                }
            }.onFailure { error ->
                main.post {
                    isBusy = false
                    predictButton.isEnabled = true
                    setStatus(getString(R.string.prediction_failed))
                    modelText.text = friendlyErrorMessage(error, defaultMessage = getString(R.string.friendly_prediction))
                    showApiSettings(true)
                }
            }
        }
    }

    private fun buildInput(): InjectionInput? {
        val geometryId = geometrySpinner.selectedItem?.toString() ?: "G01"
        val processId = processSpinner.selectedItem?.toString() ?: "P01"
        val geometry = geometries.firstOrNull { it.id == geometryId }
        return InjectionInput(
            geometryId = geometryId,
            processId = processId,
            sprueModelKey = selectedSprueModel()?.key ?: Defaults.SPRUE_MODEL_KEY,
            fillingModelKey = selectedFillingModel()?.key ?: Defaults.FILLING_MODEL_KEY,
            lMm = lField.doubleValue() ?: return null,
            wMm = wField.doubleValue() ?: return null,
            tMm = tField.doubleValue() ?: return null,
            dMm = dField.doubleValue() ?: return null,
            rMm = geometry?.double("R_mm") ?: 8.805,
            gateType = geometry?.string("gate_type") ?: "edge_gate",
            gateWidthMm = geometry?.double("gate_size_width_mm") ?: 10.0,
            gateHeightMm = geometry?.double("gate_size_height_mm") ?: 1.5,
            meltTempC = meltField.doubleValue() ?: return null,
            moldTempC = moldField.doubleValue() ?: return null,
            injectionTimeS = injectionField.doubleValue() ?: return null,
            packingPressureMPa = packingPressureField.doubleValue() ?: return null,
            packingTimeS = processes.firstOrNull { it.id == processId }?.double("packing_time_s") ?: 4.731,
        )
    }

    private fun selectedSprueModel(): ModelInfo? {
        val key = (sprueModelSpinner.selectedItem as? ModelPickerItem)?.key ?: Defaults.SPRUE_MODEL_KEY
        return sprueModels.firstOrNull { it.key == key }
    }

    private fun selectedFillingModel(): ModelInfo? {
        val key = (fillingModelSpinner.selectedItem as? ModelPickerItem)?.key ?: Defaults.FILLING_MODEL_KEY
        return fillingModels.firstOrNull { it.key == key }
    }

    private fun renderModelStatus() {
        val sprue = selectedSprueModel()
        val filling = selectedFillingModel()
        val ready = sprue?.available == true && filling?.available == true
        setStatus(if (ready) null else getString(R.string.model_unavailable))
        modelText.text = listOfNotNull(
            sprue?.let { getString(R.string.sprue_status_format, it.displayLabel, it.description) },
            filling?.let { getString(R.string.filling_status_format, it.displayLabel, it.description) },
        ).ifEmpty {
            listOf(getString(R.string.model_list_missing))
        }.joinToString("\n")
    }

    private fun applyGeometry(geometry: DoeOption) {
        lField.setText(geometry.double("L_mm")?.numberText(3) ?: lField.text.toString())
        wField.setText(geometry.double("W_mm")?.numberText(3) ?: wField.text.toString())
        tField.setText(geometry.double("t_mm")?.numberText(3) ?: tField.text.toString())
        dField.setText(geometry.double("D_mm")?.numberText(3) ?: dField.text.toString())
    }

    private fun applyProcess(process: DoeOption) {
        meltField.setText(process.double("melt_temp_C")?.numberText(2) ?: meltField.text.toString())
        moldField.setText(process.double("mold_temp_C")?.numberText(2) ?: moldField.text.toString())
        injectionField.setText(process.double("injection_time_s")?.numberText(3) ?: injectionField.text.toString())
        packingPressureField.setText(process.double("packing_pressure_MPa")?.numberText(2) ?: packingPressureField.text.toString())
    }

    private fun renderBusy(message: String) {
        setStatus(message)
        predictButton.isEnabled = false
    }

    private fun setStatus(message: String?) {
        statusText.text = message.orEmpty()
        statusText.visibility = if (message.isNullOrBlank()) View.GONE else View.VISIBLE
    }

    private fun showApiSettings(visible: Boolean) {
        baseUrlField.visibility = if (visible) View.VISIBLE else View.GONE
    }

    private fun friendlyErrorMessage(error: Throwable, defaultMessage: String = getString(R.string.friendly_offline)): String {
        val message = error.localizedMessage.orEmpty().lowercase()
        return when {
            "timed out" in message || "timeout" in message -> getString(R.string.friendly_timeout)
            "http" in message -> getString(R.string.friendly_server)
            "unavailable" in message || "model" in message -> getString(R.string.friendly_model)
            "numeric" in message || "valid" in message -> getString(R.string.friendly_input)
            "failed to connect" in message || "unable to resolve host" in message || "network is unreachable" in message || "connection refused" in message -> getString(R.string.friendly_offline)
            else -> defaultMessage
        }
    }

    private fun renderResult(result: SpruePressureResult) {
        resultSection.removeAllViews()
        resultSection.visibility = LinearLayout.VISIBLE
        resultSection.addView(caption(getString(R.string.latest_result)))
        resultSection.addView(title("${result.predictedMaxPressureMPa.numberText(2)} MPa", 34))
        resultSection.addView(body(getString(R.string.peak_time_format, result.predictedMaxTimeS.numberText(3))))
        resultSection.addView(body(getString(R.string.sprue_model_format, result.displayModelLabel)))
        resultSection.addView(body(getString(R.string.filling_model_format, result.displayFillingModelLabel)))
        chartView = PressureChartView(this).apply {
            points = result.curve
            maxPressure = result.predictedMaxPressureMPa
            layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(260)).apply {
                topMargin = dp(12)
            }
        }
        resultSection.addView(chartView)
        resultSection.addView(Button(this).apply {
            text = getString(R.string.share_result)
            setOnClickListener { shareText(injectionShareText(result)) }
        })
        resultSection.addView(Button(this).apply {
            text = getString(R.string.share_image_result)
            setOnClickListener { shareResultImage(result) }
        })
        result.fillingSummary?.let { filling ->
            resultSection.addView(body(getString(R.string.filling_max_format, filling.stats["max_MPa"]?.numberText(2) ?: "-")))
            if (filling.bins.isNotEmpty()) {
                resultSection.addView(FillingAnimationView(this).apply {
                    summary = filling
                    lengthMm = lField.doubleValue() ?: 154.01
                    widthMm = wField.doubleValue() ?: 97.42
                    diameterMm = dField.doubleValue() ?: 17.61
                    gateWidthMm = currentGeometry()?.double("gate_size_width_mm") ?: 10.0
                    layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
                        topMargin = dp(10)
                    }
                })
                resultSection.addView(FillingHistogramView(this).apply {
                    bins = filling.bins
                    layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(240)).apply {
                        topMargin = dp(10)
                    }
                })
            }
            if (filling.note.isNotBlank()) resultSection.addView(caption(filling.note))
        }
        result.notes.forEach { note -> resultSection.addView(caption(note)) }
    }

    private fun injectionShareText(result: SpruePressureResult): String {
        val input = buildInput()
        val inputLines = input?.let {
            listOf(
                "• Geometry: ${it.geometryId}",
                "• Process: ${it.processId}",
                "• Size (L x W x t): ${it.lMm.numberText(4)} x ${it.wMm.numberText(4)} x ${it.tMm.numberText(4)} mm",
                "• Diameter / radius: ${it.dMm.numberText(4)} / ${it.rMm?.numberText(4) ?: "-"} mm",
                "• Gate: ${it.gateType}, ${it.gateWidthMm.numberText(4)} x ${it.gateHeightMm.numberText(4)} mm",
                "• Temperatures (melt / mold): ${it.meltTempC.numberText(2)} / ${it.moldTempC.numberText(2)} C",
                "• Injection time: ${it.injectionTimeS.numberText(3)} s",
                "• Packing: ${it.packingPressureMPa.numberText(2)} MPa for ${it.packingTimeS.numberText(3)} s",
            )
        } ?: listOf(
            "• Geometry: ${geometrySpinner.selectedItem?.toString() ?: "-"}",
            "• Process: ${processSpinner.selectedItem?.toString() ?: "-"}",
        )

        return (
            listOfNotNull(
                "C2ES Injection Forecast",
                "",
                "MODEL",
                "• Sprue: ${result.displayModelLabel}",
                "• Filling: ${result.displayFillingModelLabel}",
                "",
                "INPUTS",
            ) + inputLines + listOfNotNull(
                "",
                "RESULTS",
                "• Peak sprue pressure: ${result.predictedMaxPressureMPa.numberText(2)} MPa",
                "• Peak time: ${result.predictedMaxTimeS.numberText(3)} s",
                result.fillingSummary?.stats?.get("max_MPa")?.let { "• Filling pressure max: ${it.numberText(2)} MPa" },
                "",
                "CHART",
                "• Pressure curve: ${result.curve.size} points",
                "",
                "GRAPH",
                "• Peak marker: ${result.predictedMaxTimeS.numberText(3)} s / ${result.predictedMaxPressureMPa.numberText(2)} MPa",
                result.fillingSummary?.bins?.takeIf { it.isNotEmpty() }?.let { "• Filling histogram: ${it.size} bins" },
            )
        ).joinToString("\n").trimEnd()
    }

    private fun shareResultImage(result: SpruePressureResult) {
        val reportView = buildInjectionShareReport(result)
        val bitmap = renderReportBitmap(reportView)
        val uri = saveBitmapToPictures(bitmap, "C2ES_Injection_Forecast_${System.currentTimeMillis()}.png") ?: return
        shareImage(uri)
    }

    private fun buildInjectionShareReport(result: SpruePressureResult): LinearLayout {
        val input = buildInput()
        return vertical(spacing = 12).apply {
            setPadding(dp(22), dp(22), dp(22), dp(22))
            setBackgroundColor(Color.WHITE)
            addView(title("C2ES Injection Forecast", 26))
            addView(title("${result.predictedMaxPressureMPa.numberText(2)} MPa", 32).apply {
                setTextColor(Ui.primary)
            })

            addReportSection("MODEL", listOf(
                "Sprue: ${result.displayModelLabel}",
                "Filling: ${result.displayFillingModelLabel}",
            ))

            addReportSection("INPUTS", input?.let {
                listOf(
                    "Geometry: ${it.geometryId}",
                    "Process: ${it.processId}",
                    "Size (L x W x t): ${it.lMm.numberText(4)} x ${it.wMm.numberText(4)} x ${it.tMm.numberText(4)} mm",
                    "Diameter / radius: ${it.dMm.numberText(4)} / ${it.rMm?.numberText(4) ?: "-"} mm",
                    "Gate: ${it.gateType}, ${it.gateWidthMm.numberText(4)} x ${it.gateHeightMm.numberText(4)} mm",
                    "Temperatures: ${it.meltTempC.numberText(2)} / ${it.moldTempC.numberText(2)} C",
                    "Injection time: ${it.injectionTimeS.numberText(3)} s",
                    "Packing: ${it.packingPressureMPa.numberText(2)} MPa for ${it.packingTimeS.numberText(3)} s",
                )
            } ?: listOf(
                "Geometry: ${geometrySpinner.selectedItem?.toString() ?: "-"}",
                "Process: ${processSpinner.selectedItem?.toString() ?: "-"}",
            ))

            addReportSection("RESULTS", listOfNotNull(
                "Peak sprue pressure: ${result.predictedMaxPressureMPa.numberText(2)} MPa",
                "Peak time: ${result.predictedMaxTimeS.numberText(3)} s",
                result.fillingSummary?.stats?.get("max_MPa")?.let { "Filling pressure max: ${it.numberText(2)} MPa" },
            ))

            addReportSection("CHART", listOf(
                "Pressure curve: ${result.curve.size} points",
            ))

            addReportSection("GRAPH", listOfNotNull(
                "Peak marker: ${result.predictedMaxTimeS.numberText(3)} s / ${result.predictedMaxPressureMPa.numberText(2)} MPa",
                result.fillingSummary?.bins?.takeIf { it.isNotEmpty() }?.let { "Filling histogram: ${it.size} bins" },
            ))

            addView(PressureChartView(this@MainActivity).apply {
                points = result.curve
                maxPressure = result.predictedMaxPressureMPa
                layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(270)).apply {
                    topMargin = dp(8)
                }
            })
        }
    }

    private fun LinearLayout.addReportSection(header: String, lines: List<String>) {
        addView(caption(header).apply {
            setTextColor(Ui.primary)
            textSize = 13f
        })
        lines.forEach { item ->
            addView(body("• $item").apply {
                textSize = 14f
            })
        }
    }

    private fun renderReportBitmap(view: View): Bitmap {
        val width = minOf(maxOf(resources.displayMetrics.widthPixels, dp(360)), dp(520))
        view.measure(
            View.MeasureSpec.makeMeasureSpec(width, View.MeasureSpec.EXACTLY),
            View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED)
        )
        view.layout(0, 0, width, view.measuredHeight)
        val bitmap = Bitmap.createBitmap(width, view.measuredHeight, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        canvas.drawColor(Color.WHITE)
        view.draw(canvas)
        return bitmap
    }

    private fun saveBitmapToPictures(bitmap: Bitmap, displayName: String): Uri? {
        val values = ContentValues().apply {
            put(MediaStore.Images.Media.DISPLAY_NAME, displayName)
            put(MediaStore.Images.Media.MIME_TYPE, "image/png")
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                put(MediaStore.Images.Media.RELATIVE_PATH, "Pictures/C2ES")
                put(MediaStore.Images.Media.IS_PENDING, 1)
            }
        }
        val uri = contentResolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values) ?: return null
        contentResolver.openOutputStream(uri)?.use { output ->
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, output)
        } ?: return null
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            values.clear()
            values.put(MediaStore.Images.Media.IS_PENDING, 0)
            contentResolver.update(uri, values, null, null)
        }
        return uri
    }

    private fun shareImage(uri: Uri) {
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "image/png"
            putExtra(Intent.EXTRA_STREAM, uri)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        startActivity(Intent.createChooser(intent, getString(R.string.share_image_result)))
    }

    private fun shareText(text: String) {
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_TEXT, text)
        }
        startActivity(Intent.createChooser(intent, getString(R.string.share_result)))
    }

    private fun currentGeometry(): DoeOption? {
        val geometryId = geometrySpinner.selectedItem?.toString() ?: return null
        return geometries.firstOrNull { it.id == geometryId }
    }

    private fun saveBaseUrl() {
        getSharedPreferences("settings", MODE_PRIVATE)
            .edit()
            .putString("base_url", baseUrlField.text.toString())
            .apply()
    }

    private fun showRecentMenu() {
        val runs = loadRecentRuns()
        if (runs.length() == 0) return
        PopupMenu(this, recentButton).apply {
            for (index in 0 until runs.length()) {
                val item = runs.getJSONObject(index)
                val title = "${item.optString("geometryId")} / ${item.optString("processId")} · ${item.optString("meltTempC")}C, ${item.optString("injectionTimeS")}s"
                menu.add(0, index, index, title)
            }
            menu.add(1, 1000, runs.length() + 1, getString(R.string.recent_clear))
            setOnMenuItemClickListener { menuItem ->
                if (menuItem.itemId == 1000) {
                    clearRecentRuns()
                } else {
                    applyRecentRun(runs.getJSONObject(menuItem.itemId))
                }
                true
            }
            show()
        }
    }

    private fun applyRecentRun(item: JSONObject) {
        setModelSelection(sprueModelSpinner, item.optString("sprueModelKey"))
        setModelSelection(fillingModelSpinner, item.optString("fillingModelKey"))
        setStringSelection(geometrySpinner, item.optString("geometryId"))
        setStringSelection(processSpinner, item.optString("processId"))
        lField.setText(item.optString("lMm", lField.text.toString()))
        wField.setText(item.optString("wMm", wField.text.toString()))
        tField.setText(item.optString("tMm", tField.text.toString()))
        dField.setText(item.optString("dMm", dField.text.toString()))
        meltField.setText(item.optString("meltTempC", meltField.text.toString()))
        moldField.setText(item.optString("moldTempC", moldField.text.toString()))
        injectionField.setText(item.optString("injectionTimeS", injectionField.text.toString()))
        packingPressureField.setText(item.optString("packingPressureMPa", packingPressureField.text.toString()))
        resultSection.visibility = LinearLayout.GONE
        renderModelStatus()
    }

    private fun saveRecentRun(input: InjectionInput) {
        val run = JSONObject()
            .put("geometryId", input.geometryId)
            .put("processId", input.processId)
            .put("sprueModelKey", input.sprueModelKey)
            .put("fillingModelKey", input.fillingModelKey)
            .put("lMm", lField.text.toString())
            .put("wMm", wField.text.toString())
            .put("tMm", tField.text.toString())
            .put("dMm", dField.text.toString())
            .put("meltTempC", meltField.text.toString())
            .put("moldTempC", moldField.text.toString())
            .put("injectionTimeS", injectionField.text.toString())
            .put("packingPressureMPa", packingPressureField.text.toString())
        val signature = recentSignature(run)
        val existing = loadRecentRuns()
        val next = JSONArray().put(run)
        for (index in 0 until existing.length()) {
            val item = existing.getJSONObject(index)
            if (recentSignature(item) != signature && next.length() < 5) {
                next.put(item)
            }
        }
        recentPrefs().edit().putString("injection_recent_runs", next.toString()).apply()
        updateRecentButton()
    }

    private fun clearRecentRuns() {
        recentPrefs().edit().remove("injection_recent_runs").apply()
        updateRecentButton()
    }

    private fun loadRecentRuns(): JSONArray {
        return runCatching {
            JSONArray(recentPrefs().getString("injection_recent_runs", "[]"))
        }.getOrDefault(JSONArray())
    }

    private fun recentSignature(item: JSONObject): String {
        return listOf(
            "geometryId", "processId", "sprueModelKey", "fillingModelKey",
            "lMm", "wMm", "tMm", "dMm", "meltTempC", "moldTempC", "injectionTimeS", "packingPressureMPa"
        ).joinToString("|") { item.optString(it) }
    }

    private fun updateRecentButton() {
        val hasRecent = loadRecentRuns().length() > 0
        recentButton.isEnabled = hasRecent
        recentButton.alpha = if (hasRecent) 1f else 0.45f
    }

    private fun setStringSelection(spinner: Spinner, value: String) {
        for (index in 0 until spinner.adapter.count) {
            if (spinner.adapter.getItem(index).toString() == value) {
                spinner.setSelection(index)
                return
            }
        }
    }

    private fun setModelSelection(spinner: Spinner, key: String) {
        for (index in 0 until spinner.adapter.count) {
            val item = spinner.adapter.getItem(index) as? ModelPickerItem
            if (item?.key == key) {
                spinner.setSelection(index)
                return
            }
        }
    }

    private fun recentPrefs() = getSharedPreferences("recent", MODE_PRIVATE)

    private fun card(): LinearLayout = vertical(spacing = 10).apply {
        setPadding(dp(16), dp(16), dp(16), dp(16))
        background = GradientDrawable().apply {
            setColor(Ui.card)
            cornerRadius = dp(8).toFloat()
            setStroke(1, Ui.border)
        }
    }

    private fun primaryButtonBackground(): GradientDrawable = GradientDrawable(
        GradientDrawable.Orientation.LEFT_RIGHT,
        intArrayOf(Ui.primary, Ui.accent)
    ).apply {
        cornerRadius = dp(8).toFloat()
    }

    private fun fieldBackground(): GradientDrawable = GradientDrawable().apply {
        setColor(Ui.field)
        cornerRadius = dp(8).toFloat()
        setStroke(1, Ui.fieldBorder)
    }

    private fun vertical(spacing: Int = 0): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        showDividers = LinearLayout.SHOW_DIVIDER_MIDDLE
        dividerDrawable = SpaceDrawable(dp(spacing))
    }

    private fun title(text: String, size: Int): TextView = TextView(this).apply {
        this.text = text
        textSize = size.toFloat()
        typeface = Typeface.DEFAULT_BOLD
        setTextColor(Ui.ink)
    }

    private fun headline(text: String): TextView = TextView(this).apply {
        this.text = text
        textSize = 18f
        typeface = Typeface.DEFAULT_BOLD
        setTextColor(Ui.ink)
    }

    private fun caption(text: String): TextView = TextView(this).apply {
        this.text = text
        textSize = 13f
        setTextColor(Ui.muted)
    }

    private fun body(text: String): TextView = TextView(this).apply {
        this.text = text
        textSize = 15f
        setTextColor(Ui.body)
    }

    private fun label(text: String): TextView = TextView(this).apply {
        this.text = text
        textSize = 12f
        typeface = Typeface.DEFAULT_BOLD
        setTextColor(Ui.muted)
    }

    private fun input(text: String): EditText = EditText(this).apply {
        setText(text)
        setSingleLine(true)
        setTextColor(Ui.ink)
        setHintTextColor(Ui.muted)
        background = fieldBackground()
        inputType = android.text.InputType.TYPE_CLASS_NUMBER or
            android.text.InputType.TYPE_NUMBER_FLAG_DECIMAL or
            android.text.InputType.TYPE_NUMBER_FLAG_SIGNED
    }

    private fun EditText.doubleValue(): Double? = text.toString().toDoubleOrNull()
    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}

private data class ModelPickerItem(
    val key: String,
    val label: String,
    val available: Boolean,
) {
    override fun toString(): String {
        return if (available) label else "$label (unavailable)"
    }
}

private fun Double.numberText(digits: Int): String = "%.${digits}f".format(this).trimEnd('0').trimEnd('.')

private object Ui {
    val background: Int = Color.rgb(243, 246, 250)
    val card: Int = Color.WHITE
    val field: Int = Color.rgb(241, 245, 249)
    val fieldBorder: Int = Color.rgb(220, 230, 241)
    val border: Int = Color.rgb(214, 226, 241)
    val ink: Int = Color.rgb(14, 19, 30)
    val body: Int = Color.rgb(51, 65, 85)
    val muted: Int = Color.rgb(91, 103, 122)
    val primary: Int = Color.rgb(37, 85, 209)
    val accent: Int = Color.rgb(234, 76, 33)
}

private class SpaceDrawable(private val size: Int) : android.graphics.drawable.ColorDrawable(Color.TRANSPARENT) {
    override fun getIntrinsicHeight(): Int = size
    override fun getIntrinsicWidth(): Int = size
}
