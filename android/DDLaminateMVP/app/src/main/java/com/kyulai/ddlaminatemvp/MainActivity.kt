package com.kyulai.ddlaminatemvp

import android.app.Activity
import android.app.AlertDialog
import android.content.Context
import android.content.ContentValues
import android.content.Intent
import android.content.res.Configuration
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Rect
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.MediaStore
import android.text.Editable
import android.text.TextWatcher
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputMethodManager
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.PopupMenu
import android.widget.RadioButton
import android.widget.RadioGroup
import android.widget.ScrollView
import android.widget.SeekBar
import android.widget.Spinner
import android.widget.TextView
import org.json.JSONArray
import org.json.JSONObject
import java.util.Locale
import java.util.concurrent.Executors
import kotlin.math.roundToInt

class MainActivity : Activity() {
    private val api = DDLaminateApi()
    private val executor = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())

    private lateinit var baseUrlField: EditText
    private lateinit var statusText: TextView
    private lateinit var modelText: TextView
    private lateinit var responseModelSpinner: Spinner
    private lateinit var responseModelCard: LinearLayout
    private lateinit var responseModelTitle: TextView
    private lateinit var responseModelMeta: LinearLayout
    private lateinit var responseModelDescription: TextView
    private lateinit var theta1Field: EditText
    private lateinit var theta2Field: EditText
    private lateinit var panelAField: EditText
    private lateinit var panelBField: EditText
    private lateinit var theta1Readout: TextView
    private lateinit var theta2Readout: TextView
    private lateinit var theta1SeekBar: SeekBar
    private lateinit var theta2SeekBar: SeekBar
    private lateinit var caseGroup: RadioGroup
    private lateinit var plyPreview: PlyStackPreviewView
    private lateinit var plyCountText: TextView
    private lateinit var stackFormulaText: TextView
    private lateinit var recentButton: Button
    private lateinit var predictButton: Button
    private lateinit var resultSection: LinearLayout
    private lateinit var chartView: CurveChartView

    private var responseModels: List<ModelInfo> = emptyList()
    private var selectedResponseModelKey = Defaults.RESPONSE_MODEL_KEY
    private var responseModel: ModelInfo? = null
    private var isBusy = false
    private var isSyncingTheta = false

    override fun attachBaseContext(newBase: Context) {
        super.attachBaseContext(localizedContext(newBase))
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(buildContent())
        autoCheckApi()
    }

    override fun dispatchTouchEvent(event: MotionEvent): Boolean {
        if (event.action == MotionEvent.ACTION_DOWN) {
            val focusedView = currentFocus
            if (focusedView is EditText && event.isOutside(focusedView)) {
                focusedView.clearFocus()
                hideKeyboard(focusedView)
            }
        }
        return super.dispatchTouchEvent(event)
    }

    private fun buildContent(): ScrollView {
        val prefs = getSharedPreferences("settings", MODE_PRIVATE)
        val root = vertical(spacing = 16).apply {
            setPadding(dp(20), dp(18), dp(20), dp(28))
            setBackgroundColor(Ui.background)
        }

        root.addView(title(getString(R.string.app_title), 30))
        root.addView(body(getString(R.string.app_subtitle)))
        root.addView(languageSwitcher())

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
                gravity = Gravity.CENTER_VERTICAL
                addView(headline(getString(R.string.forecast_inputs)), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
                recentButton = Button(context).apply {
                    text = getString(R.string.recent_inputs)
                    setOnClickListener { showRecentMenu() }
                }
                addView(recentButton)
            })
            caseGroup = RadioGroup(context).apply {
                orientation = RadioGroup.HORIZONTAL
                listOf("Case2", "Case3", "Case4").forEachIndexed { index, label ->
                    addView(RadioButton(context).apply {
                        text = label
                        id = 100 + index
                        setTextColor(Ui.ink)
                    })
                }
                check(100)
                setOnCheckedChangeListener { _, _ -> updatePlyPreview() }
            }
            addView(caseGroup)
            addView(label(getString(R.string.response_model)))
            responseModelSpinner = Spinner(context).apply {
                visibility = View.GONE
                background = fieldBackground()
                onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
                    override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                        val item = parent?.getItemAtPosition(position) as? ModelPickerItem ?: return
                        selectedResponseModelKey = item.key
                        responseModel = responseModels.firstOrNull { it.key == item.key }
                        resultSection.visibility = LinearLayout.GONE
                        modelText.text = responseModel?.let { "${it.displayLabel}\n${it.description}" } ?: getString(R.string.response_missing)
                        setStatus(if (responseModel?.available == true) null else getString(R.string.model_unavailable))
                        updateResponseModelCard()
                    }

                    override fun onNothingSelected(parent: AdapterView<*>?) = Unit
                }
            }
            addView(responseModelSpinner)
            responseModelCard = modelSelectionCard()
            addView(responseModelCard)
            theta1Field = input("30")
            theta2Field = input("-30")
            theta1Readout = angleReadout(30)
            theta2Readout = angleReadout(-30)
            theta1SeekBar = angleSeekBar(30)
            theta2SeekBar = angleSeekBar(-30)
            addView(angleControl(getString(R.string.theta_1), theta1Field, theta1Readout, theta1SeekBar))
            addView(angleControl(getString(R.string.theta_2), theta2Field, theta2Readout, theta2SeekBar))
            panelAField = input("6")
            panelBField = input("4")
            addView(twoColumnRow(
                inputBlock("Panel length a (in)", panelAField),
                inputBlock("Panel width b (in)", panelBField),
            ))
            addView(plyPreviewCard())
            predictButton = Button(context).apply {
                text = getString(R.string.predict_forecast)
                setTextColor(Color.WHITE)
                background = primaryButtonBackground()
                setOnClickListener { predict() }
            }
            addView(predictButton)
            bindThetaControls()
            updatePlyPreview()
            updateRecentButton()
        })

        resultSection = vertical(spacing = 14).apply {
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
                api.models(baseUrl)
            }.onSuccess { models ->
                responseModels = models.responseModels
                main.post {
                    isBusy = false
                    populateResponseModelSpinner()
                    setStatus(if (responseModel?.available == true) null else getString(R.string.model_unavailable))
                    modelText.text = responseModel?.let { "${it.displayLabel}\n${it.description}" } ?: getString(R.string.response_missing)
                    updateResponseModelCard()
                    showApiSettings(false)
                    predictButton.isEnabled = true
                }
            }.onFailure { error ->
                responseModels = emptyList()
                responseModel = null
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

    private fun predict() {
        val theta1 = parseThetaDegrees(theta1Field.text.toString())
        val theta2 = parseThetaDegrees(theta2Field.text.toString())
        if (theta1 == null || theta2 == null) {
            modelText.text = getString(R.string.friendly_input)
            return
        }
        val panelA = parsePositiveDimension(panelAField.text.toString())
        val panelB = parsePositiveDimension(panelBField.text.toString())
        if (panelA == null || panelB == null) {
            modelText.text = "Enter positive panel length and width values."
            return
        }
        theta1Field.setText(theta1.toString())
        theta2Field.setText(theta2.toString())
        panelAField.setText(formatDimension(panelA))
        panelBField.setText(formatDimension(panelB))
        updatePlyPreview()

        isBusy = true
        renderBusy(getString(R.string.predicting))
        saveBaseUrl()
        val baseUrl = baseUrlField.text.toString()
        val caseName = selectedCase()

        executor.execute {
            runCatching {
                api.health(baseUrl)
                val models = api.models(baseUrl)
                responseModels = models.responseModels
                main.post { populateResponseModelSpinner() }
                val model = selectedResponseModel()
                check(model?.available == true) { getString(R.string.response_unavailable) }
                api.predictResponse(baseUrl, caseName, theta1.toDouble(), theta2.toDouble(), selectedResponseModelKey, panelA, panelB)
            }.onSuccess { result ->
                main.post {
                    isBusy = false
                    predictButton.isEnabled = true
                    setStatus(null)
                    showApiSettings(false)
                    saveRecentRun(caseName, selectedResponseModelKey, theta1.toString(), theta2.toString(), panelA, panelB, result)
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

    private fun populateResponseModelSpinner() {
        val visibleModels = responseModelOptions()
        val selectedKey = visibleModels.firstOrNull { it.key == selectedResponseModelKey }?.key
            ?: visibleModels.firstOrNull { it.key == Defaults.RESPONSE_MODEL_KEY && it.available }?.key
            ?: visibleModels.firstOrNull { it.available }?.key
            ?: visibleModels.firstOrNull()?.key
            ?: selectedResponseModelKey
        selectedResponseModelKey = selectedKey
        responseModel = responseModels.firstOrNull { it.key == selectedKey }

        val items = if (visibleModels.isEmpty()) {
            listOf(ModelPickerItem(selectedResponseModelKey, selectedResponseModelKey, false))
        } else {
            visibleModels.map { ModelPickerItem(it.key, it.displayLabel, it.available) }
        }
        responseModelSpinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, items)
        val selectedIndex = items.indexOfFirst { it.key == selectedResponseModelKey }.coerceAtLeast(0)
        responseModelSpinner.setSelection(selectedIndex)
        updateResponseModelCard()
    }

    private fun responseModelOptions(): List<ModelInfo> {
        val byKey = responseModels.associateBy { it.key }
        val selected = listOfNotNull(
            listOf(Defaults.RESPONSE_MODEL_KEY, "response_surrogate_physics").firstNotNullOfOrNull { byKey[it] },
            listOf(Defaults.RESPONSE_DEEP_MODEL_KEY, "response_goint_physics").firstNotNullOfOrNull { byKey[it] },
        )
        return selected.ifEmpty { responseModels.filter { it.available }.take(2).ifEmpty { responseModels.take(2) } }
    }

    private fun modelSelectionCard(): LinearLayout {
        return LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(12), dp(12), dp(12), dp(12))
            background = modelCardBackground(Ui.primary, selected = false)
            isClickable = true
            isFocusable = true
            setOnClickListener { showResponseModelDialog() }

            addView(modelIconView("ML", Ui.primary))
            addView(LinearLayout(context).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(dp(12), 0, dp(8), 0)
                responseModelTitle = headline(getString(R.string.model_loading)).apply {
                    textSize = 16f
                    maxLines = 1
                }
                responseModelMeta = LinearLayout(context).apply {
                    orientation = LinearLayout.HORIZONTAL
                    showDividers = LinearLayout.SHOW_DIVIDER_MIDDLE
                    dividerDrawable = SpaceDrawable(dp(6))
                }
                responseModelDescription = body(getString(R.string.model_loading)).apply {
                    textSize = 13f
                    maxLines = 2
                }
                addView(responseModelTitle)
                addView(responseModelMeta)
                addView(responseModelDescription)
            }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            addView(TextView(context).apply {
                text = "v"
                textSize = 20f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(Ui.primary)
                gravity = Gravity.CENTER
            }, LinearLayout.LayoutParams(dp(28), dp(28)))
        }
    }

    private fun updateResponseModelCard() {
        if (!::responseModelTitle.isInitialized) return
        val model = responseModel ?: responseModels.firstOrNull { it.key == selectedResponseModelKey }
        responseModelTitle.text = model?.displayLabel ?: selectedResponseModelKey
        responseModelMeta.removeAllViews()
        val badges = listOfNotNull(
            if (model?.key == Defaults.RESPONSE_MODEL_KEY) getString(R.string.model_recommended) to Ui.success else null,
            model?.let { modelTag(it) to Ui.primary },
            if (model?.available == false) getString(R.string.model_missing) to Ui.danger else null,
        )
        if (badges.isEmpty()) {
            responseModelMeta.addView(modelBadgeView(getString(R.string.model_loading), Ui.muted))
        } else {
            badges.forEach { (text, color) ->
                responseModelMeta.addView(modelBadgeView(text, color))
            }
        }
        responseModelDescription.text = modelDescription(model)
        responseModelCard.background = modelCardBackground(
            if (model?.available == false) Ui.danger else Ui.primary,
            selected = model?.available != false
        )
        responseModelCard.alpha = if (model?.available == false) 0.58f else 1f
    }

    private fun showResponseModelDialog() {
        val visibleModels = responseModelOptions()
        if (visibleModels.isEmpty()) {
            AlertDialog.Builder(this)
                .setTitle(getString(R.string.choose_model))
                .setMessage(getString(R.string.model_loading))
                .setPositiveButton(android.R.string.ok, null)
                .show()
            return
        }
        val content = vertical(spacing = 10).apply {
            setPadding(dp(16), dp(14), dp(16), dp(8))
            addView(body(getString(R.string.model_selection_hint)).apply {
                setTextColor(Ui.muted)
            })
        }
        var dialog: AlertDialog? = null
        visibleModels.forEach { model ->
            content.addView(modelOptionCard(model) {
                if (!model.available) {
                    setStatus(getString(R.string.model_unavailable))
                    return@modelOptionCard
                }
                selectedResponseModelKey = model.key
                responseModel = model
                populateResponseModelSpinner()
                resultSection.visibility = LinearLayout.GONE
                modelText.text = "${model.displayLabel}\n${modelDescription(model)}"
                dialog?.dismiss()
            })
        }
        dialog = AlertDialog.Builder(this)
            .setTitle(getString(R.string.choose_model))
            .setView(ScrollView(this).apply { addView(content) })
            .setNegativeButton(android.R.string.cancel, null)
            .create()
        dialog?.show()
    }

    private fun modelTag(model: ModelInfo): String {
        val label = model.displayLabel.lowercase()
        return when {
            model.key == Defaults.RESPONSE_DEEP_MODEL_KEY || model.key.contains("goint") || label.contains("deep learning") || label.contains("nn") -> getString(R.string.model_tag_deep)
            model.key == Defaults.RESPONSE_MODEL_KEY || label.contains("machine learning") || label.contains("extratrees") -> getString(R.string.model_tag_fast)
            else -> getString(R.string.model_tag_experimental)
        }
    }

    private fun modelDescription(model: ModelInfo?): String {
        val label = model?.displayLabel?.lowercase().orEmpty()
        return when {
            model == null -> getString(R.string.model_loading)
            model.key == Defaults.RESPONSE_MODEL_KEY || label.contains("machine learning") || label.contains("extratrees") -> getString(R.string.model_description_extratrees)
            model.key == Defaults.RESPONSE_DEEP_MODEL_KEY || model.key.contains("goint") || label.contains("deep learning") || label.contains("goint") -> getString(R.string.model_description_goint)
            model.description.isNotBlank() -> model.description
            else -> getString(R.string.model_description_generic)
        }
    }

    private fun selectedResponseModel(): ModelInfo? {
        val visibleModels = responseModelOptions()
        val selected = visibleModels.firstOrNull { it.key == selectedResponseModelKey && it.available }
            ?: visibleModels.firstOrNull { it.key == Defaults.RESPONSE_MODEL_KEY && it.available }
            ?: visibleModels.firstOrNull { it.available }
            ?: visibleModels.firstOrNull { it.key == selectedResponseModelKey }
            ?: responseModel
        if (selected != null) {
            selectedResponseModelKey = selected.key
            responseModel = selected
        }
        return selected
    }

    private fun angleControl(title: String, field: EditText, readout: TextView, seekBar: SeekBar): LinearLayout {
        return vertical(spacing = 8).apply {
            setPadding(dp(12), dp(12), dp(12), dp(12))
            background = fieldBackground()
            addView(LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                addView(caption(title), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
                addView(readout)
            })
            addView(field)
            addView(seekBar)
        }
    }

    private fun angleReadout(value: Int): TextView {
        return TextView(this).apply {
            text = value.thetaReadout()
            textSize = 13f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Ui.primary)
            setPadding(dp(8), dp(4), dp(8), dp(4))
            background = tintedBackground(Ui.primary, alpha = 22)
        }
    }

    private fun angleSeekBar(value: Int): SeekBar {
        return SeekBar(this).apply {
            max = 180
            progress = value.coerceIn(-90, 90) + 90
        }
    }

    private fun bindThetaControls() {
        bindThetaControl(theta1Field, theta1SeekBar, theta1Readout)
        bindThetaControl(theta2Field, theta2SeekBar, theta2Readout)
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

    private fun plyPreviewCard(): LinearLayout {
        return vertical(spacing = 9).apply {
            setPadding(dp(12), dp(12), dp(12), dp(12))
            background = fieldBackground()
            addView(LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.TOP
                addView(vertical(spacing = 2).apply {
                    addView(caption(getString(R.string.live_laminate_preview)).apply {
                        setTextColor(Ui.primary)
                    })
                    addView(headline(getString(R.string.angle_aware_ply_stack)).apply {
                        textSize = 16f
                    })
                }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
                plyCountText = modelBadgeView(getString(R.string.ply_count_format, 16), Ui.primary)
                addView(plyCountText)
            })
            plyPreview = PlyStackPreviewView(this@MainActivity).apply {
                layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(220))
                background = strokedPreviewBackground()
            }
            addView(plyPreview)
            addView(LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                showDividers = LinearLayout.SHOW_DIVIDER_MIDDLE
                dividerDrawable = SpaceDrawable(dp(6))
                addView(legendBadge("theta1", Color.rgb(101, 122, 212)))
                addView(legendBadge("theta2", Color.rgb(188, 143, 112)))
                addView(legendBadge("+", Ui.success))
                addView(legendBadge("-", Ui.danger))
            })
            addView(LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                addView(caption(getString(R.string.stack_formula_label)), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
                stackFormulaText = caption(caseFormula("Case2")).apply {
                    gravity = Gravity.END
                    setTextColor(Ui.ink)
                    maxLines = 2
                }
                addView(stackFormulaText)
            })
            addView(caption(getString(R.string.stack_compact_physics_note)).apply {
                textSize = 11f
            })
        }
    }

    private fun updatePlyPreview() {
        if (!::plyPreview.isInitialized) return
        val caseName = selectedCase()
        val theta1 = parseThetaDegrees(theta1Field.text.toString()) ?: 0
        val theta2 = parseThetaDegrees(theta2Field.text.toString()) ?: 0
        plyPreview.updateStack(caseName, theta1, theta2)
        plyCountText.text = getString(R.string.ply_count_format, plyPreview.plyCount)
        stackFormulaText.text = caseFormula(caseName)
    }

    private fun caseFormula(caseName: String): String {
        return when (caseName) {
            "Case3" -> "[[+/-theta1]/[+/-theta2]/[-/+theta1]/[-/+theta2]] x 2"
            "Case4" -> "([+/-theta1]/[+/-theta2]) x 2 + ([-/+theta1]/[-/+theta2]) x 2"
            else -> "[[+/-theta1]/[+/-theta2]] x 4"
        }
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

    private fun languageSwitcher(): LinearLayout {
        val current = languageCode()
        return LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            addView(caption(getString(R.string.language)), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            addView(languageButton("한국어", "ko", current))
            addView(languageButton("English", "en", current), LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
                leftMargin = dp(8)
            })
        }
    }

    private fun languageButton(label: String, code: String, current: String): Button {
        return Button(this).apply {
            text = label
            textSize = 12f
            setTextColor(if (code == current) Color.WHITE else Ui.primary)
            background = if (code == current) primaryButtonBackground() else fieldBackground()
            setOnClickListener {
                if (languageCode() != code) {
                    getSharedPreferences("settings", MODE_PRIVATE).edit().putString(LANGUAGE_KEY, code).apply()
                    recreate()
                }
            }
        }
    }

    private fun friendlyErrorMessage(error: Throwable, defaultMessage: String = getString(R.string.friendly_offline)): String {
        val message = error.localizedMessage.orEmpty().lowercase()
        return when {
            "timed out" in message || "timeout" in message -> getString(R.string.friendly_timeout)
            "http" in message -> getString(R.string.friendly_server)
            "unavailable" in message || "model" in message || "response_surrogate" in message -> getString(R.string.friendly_model)
            "theta" in message || "numeric" in message || "valid" in message -> getString(R.string.friendly_input)
            "failed to connect" in message || "unable to resolve host" in message || "network is unreachable" in message || "connection refused" in message -> getString(R.string.friendly_offline)
            else -> defaultMessage
        }
    }

    private fun renderResult(result: ForecastResult) {
        resultSection.removeAllViews()
        resultSection.visibility = LinearLayout.VISIBLE
        resultSection.addView(resultHeroCard(result))
        resultSection.addView(resultMetricsGrid(result))
        resultSection.addView(interpretationSection(result))
        resultSection.addView(curveResultCard(result))
        resultSection.addView(actionRow(result))
        resultSection.addView(probabilityCard(result))
        result.xai?.let { xai ->
            resultSection.addView(xaiCard(xai))
        }
    }

    private fun resultHeroCard(result: ForecastResult): LinearLayout {
        return card().apply {
            addView(LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.TOP
                addView(vertical(spacing = 4).apply {
                    addView(caption(getString(R.string.predicted_type)))
                    addView(title(getString(R.string.type_format, result.predictedType), 46).apply {
                        includeFontPadding = false
                    })
                }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
                addView(vertical(spacing = 2).apply {
                    gravity = Gravity.END
                    addView(TextView(context).apply {
                        text = result.confidence.percentText()
                        textSize = 22f
                        typeface = Typeface.DEFAULT_BOLD
                        setTextColor(Ui.primary)
                        gravity = Gravity.END
                    })
                    addView(caption(getString(R.string.confidence_label)).apply {
                        gravity = Gravity.END
                    })
                })
            })
            addView(View(context).apply {
                setBackgroundColor(Ui.border)
            }, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(1)).apply {
                topMargin = dp(4)
                bottomMargin = dp(4)
            })
            addView(TextView(context).apply {
                text = result.displayModelLabel
                textSize = 15f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(Ui.ink)
            })
            addView(caption(result.inputMode.uppercase()).apply {
                setTextColor(Ui.primary)
            })
        }
    }

    private fun resultMetricsGrid(result: ForecastResult): LinearLayout {
        return vertical(spacing = 10).apply {
            addView(LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                addView(metricCard(getString(R.string.predicted_pt), result.predictedPt.numberText(2), "force"), weightedReportParams(0))
                addView(metricCard(getString(R.string.max_force_label), result.predictedMaxForce.numberText(2), "force"), weightedReportParams(10))
            })
            addView(LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                addView(metricCard(getString(R.string.pt_displacement_label), result.predictedPtDisplacement.numberText(5), "disp."), weightedReportParams(0))
                addView(metricCard(getString(R.string.curve_points), result.curve.size.toString(), "samples"), weightedReportParams(10))
            })
        }
    }

    private fun metricCard(label: String, value: String, unit: String): LinearLayout {
        return vertical(spacing = 5).apply {
            setPadding(dp(14), dp(13), dp(14), dp(13))
            background = fieldBackground()
            addView(caption(label))
            addView(TextView(context).apply {
                text = value
                textSize = 18f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(Ui.ink)
                maxLines = 1
            })
            addView(caption(unit).apply {
                textSize = 11f
            })
        }
    }

    private fun curveResultCard(result: ForecastResult): LinearLayout {
        return card().apply {
            addView(LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                addView(headline(getString(R.string.response_curve)), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
                addView(modelBadgeView(getString(R.string.pt_marker), Ui.danger))
            })
            chartView = CurveChartView(this@MainActivity).apply {
                points = result.curve
                predictedPt = result.predictedPt
                layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(260)).apply {
                    topMargin = dp(12)
                }
            }
            addView(chartView)
        }
    }

    private fun actionRow(result: ForecastResult): LinearLayout {
        return LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            addView(actionButton(getString(R.string.share_result)) {
                shareText(laminateShareText(result))
            }, weightedReportParams(0))
            addView(actionButton(getString(R.string.share_image_result)) {
                shareResultImage(result)
            }, weightedReportParams(10))
        }
    }

    private fun probabilityCard(result: ForecastResult): LinearLayout {
        return card().apply {
            addView(headline(getString(R.string.class_probabilities)))
            val entries = probabilityEntries(result)
            if (entries.isEmpty()) {
                addView(body(getString(R.string.no_probabilities)).apply {
                    setTextColor(Ui.muted)
                })
            } else {
                entries.forEach { (label, value) ->
                    addView(probabilityRow(label, value, label == "type${result.predictedType}"))
                }
            }
        }
    }

    private fun probabilityEntries(result: ForecastResult): List<Pair<String, Double>> {
        return result.probabilities.entries
            .sortedBy { it.key }
            .map { it.key to it.value.coerceIn(0.0, 1.0) }
    }

    private fun xaiCard(xai: ForecastXai): LinearLayout {
        return card().apply {
            addView(headline(getString(R.string.xai_title)))
            addView(body(xai.summary).apply {
                setTextColor(Ui.muted)
            })
            addView(caption(getString(R.string.xai_method_format, xai.method, xai.featureSet)).apply {
                setTextColor(Ui.primary)
                typeface = Typeface.DEFAULT_BOLD
            })
            xai.topFeatures.take(5).forEach { feature ->
                addView(xaiFeatureRow(feature))
            }
            val hiddenFeatures = xai.topFeatures.drop(5)
            if (hiddenFeatures.isNotEmpty()) {
                val hiddenList = vertical(spacing = 0).apply {
                    visibility = View.GONE
                    hiddenFeatures.forEach { feature ->
                        addView(xaiFeatureRow(feature))
                    }
                }
                val toggle = Button(context).apply {
                    text = getString(R.string.xai_show_more, hiddenFeatures.size)
                    textSize = 13f
                    setTextColor(Ui.primary)
                    typeface = Typeface.DEFAULT_BOLD
                    background = secondaryButtonBackground()
                    setOnClickListener {
                        val shouldExpand = hiddenList.visibility != View.VISIBLE
                        hiddenList.visibility = if (shouldExpand) View.VISIBLE else View.GONE
                        text = if (shouldExpand) {
                            getString(R.string.xai_hide_more)
                        } else {
                            getString(R.string.xai_show_more, hiddenFeatures.size)
                        }
                    }
                }
                addView(toggle)
                addView(hiddenList)
            }
        }
    }

    private fun xaiFeatureRow(feature: ForecastXaiFeature): LinearLayout {
        val safeImportance = feature.importance.coerceIn(0.0, 1.0)
        return vertical(spacing = 4).apply {
            setPadding(0, dp(7), 0, dp(7))
            addView(LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                addView(TextView(context).apply {
                    text = feature.label.ifBlank { feature.name }
                    textSize = 12f
                    typeface = Typeface.DEFAULT_BOLD
                    setTextColor(Ui.ink)
                    maxLines = 1
                }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
                addView(TextView(context).apply {
                    text = feature.category.replaceFirstChar { it.uppercase() }
                    textSize = 10f
                    typeface = Typeface.DEFAULT_BOLD
                    setTextColor(Ui.primary)
                    setPadding(dp(6), dp(2), dp(6), dp(2))
                    background = capsuleBackground(Color.rgb(220, 244, 240))
                })
            })
            addView(LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                addView(FrameLayout(context).apply {
                    background = capsuleBackground(Ui.field)
                    addView(View(context).apply {
                        background = capsuleBackground(Ui.primary)
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
                addView(TextView(context).apply {
                    text = safeImportance.percentText()
                    textSize = 11f
                    typeface = Typeface.DEFAULT_BOLD
                    setTextColor(Ui.primary)
                    gravity = Gravity.END
                }, LinearLayout.LayoutParams(dp(52), LinearLayout.LayoutParams.WRAP_CONTENT))
            })
            addView(caption(feature.explanation).apply {
                setTextColor(Ui.muted)
                textSize = 11f
            })
        }
    }

    private fun probabilityRow(label: String, value: Double, selected: Boolean): LinearLayout {
        return vertical(spacing = 7).apply {
            addView(LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                addView(TextView(context).apply {
                    text = label.replaceFirstChar { it.uppercase() }
                    textSize = 15f
                    typeface = Typeface.DEFAULT_BOLD
                    setTextColor(Ui.ink)
                }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
                addView(TextView(context).apply {
                    text = value.percentText()
                    textSize = 15f
                    typeface = Typeface.DEFAULT_BOLD
                    setTextColor(Ui.muted)
                })
            })
            addView(FrameLayout(context).apply {
                background = capsuleBackground(Ui.field)
                addView(View(context).apply {
                    background = capsuleBackground(if (selected) Ui.primary else Ui.probabilityMuted)
                    layoutParams = FrameLayout.LayoutParams(dp(6), FrameLayout.LayoutParams.MATCH_PARENT)
                })
                post {
                    val availableWidth = width
                    val fill = getChildAt(0)
                    val params = fill.layoutParams as FrameLayout.LayoutParams
                    params.width = maxOf(dp(6), (availableWidth * value).toInt())
                    fill.layoutParams = params
                    fill.requestLayout()
                }
            }, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(8)))
        }
    }

    private fun actionButton(text: String, onClick: () -> Unit): Button {
        return Button(this).apply {
            this.text = text
            textSize = 13f
            setTextColor(Ui.primary)
            typeface = Typeface.DEFAULT_BOLD
            background = secondaryButtonBackground()
            setOnClickListener { onClick() }
        }
    }

    private fun laminateShareText(result: ForecastResult): String {
        val inputLines = listOf(
            "• Case: ${selectedCase()}",
            "• Theta 1: ${displayThetaDegrees(theta1Field.text.toString())} deg",
            "• Theta 2: ${displayThetaDegrees(theta2Field.text.toString())} deg",
        )

        return (
            listOf(
                "ImperialAX Laminate Forecast",
                "",
                "MODEL",
                "• Model: ${result.displayModelLabel}",
                "",
                "INPUTS",
            ) + inputLines + listOf(
                "",
                "RESULTS",
                "• Predicted type: Type ${result.predictedType}",
                "• Confidence: ${result.confidence.percentText()}",
                "• Pt: ${result.predictedPt.numberText(2)}",
                "• Max force: ${result.predictedMaxForce.numberText(2)}",
                "• Pt displacement: ${result.predictedPtDisplacement.numberText(5)}",
                "",
                "INTERPRETATION",
            ) + interpretationLines(result).map { "• $it" } + listOf(
                "",
                "CHART",
                "• Response curve: ${result.curve.size} points",
                "",
                "GRAPH",
                "• Pt marker: ${result.predictedPt.numberText(2)}",
                "• x Axis: displacement",
                "• y Axis: force",
            )
        ).joinToString("\n").trimEnd()
    }

    private fun shareResultImage(result: ForecastResult) {
        val reportView = buildLaminateShareReport(result)
        val bitmap = renderReportBitmap(reportView)
        val uri = saveBitmapToPictures(bitmap, "ImperialAX_Laminate_Forecast_${System.currentTimeMillis()}.png") ?: return
        shareImage(uri)
    }

    private fun buildLaminateShareReport(result: ForecastResult): LinearLayout {
        return vertical(spacing = 14).apply {
            setPadding(dp(24), dp(24), dp(24), dp(24))
            setBackgroundColor(Ui.reportBackground)

            addView(LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                addView(TextView(context).apply {
                    text = "ImperialAX"
                    textSize = 20f
                    typeface = Typeface.DEFAULT_BOLD
                    gravity = Gravity.CENTER
                    setTextColor(Color.WHITE)
                    background = GradientDrawable().apply {
                        setColor(Ui.accent)
                        cornerRadius = dp(8).toFloat()
                    }
                }, LinearLayout.LayoutParams(dp(76), dp(76)))
                addView(vertical(spacing = 4).apply {
                    addView(title("ImperialAX Laminate Forecast", 24))
                    addView(caption("Generated result summary"))
                }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                    leftMargin = dp(14)
                })
            })

            addView(LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                addView(reportMetric("TYPE", "Type ${result.predictedType}", Ui.primary), weightedReportParams(0))
                addView(reportMetric("CONFIDENCE", result.confidence.percentText(), Ui.success), weightedReportParams(8))
                addView(reportMetric("PT", result.predictedPt.numberText(2), Ui.warning), weightedReportParams(8))
            })

            addView(LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                addView(reportSection("MODEL", listOf(
                    "Model: ${result.displayModelLabel}",
                )), weightedReportParams(0))
                addView(reportSection("INPUTS", listOf(
                    "Case: ${selectedCase()}",
                    "Theta 1: ${displayThetaDegrees(theta1Field.text.toString())} deg",
                    "Theta 2: ${displayThetaDegrees(theta2Field.text.toString())} deg",
                )), weightedReportParams(8))
            })

            addView(LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                addView(reportSection("RESULTS", listOf(
                    "Max force: ${result.predictedMaxForce.numberText(2)}",
                    "Pt displacement: ${result.predictedPtDisplacement.numberText(5)}",
                    "Curve points: ${result.curve.size}",
                )), weightedReportParams(0))
                addView(reportSection("GRAPH", listOf(
                    "x Axis: displacement",
                    "y Axis: force",
                    "Pt marker: ${result.predictedPt.numberText(2)}",
                )), weightedReportParams(8))
            })

            addView(reportSection("INTERPRETATION", interpretationLines(result)))

            addView(CurveChartView(this@MainActivity).apply {
                points = result.curve
                predictedPt = result.predictedPt
                layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(270)).apply {
                    topMargin = dp(8)
                }
            })
        }
    }

    private fun interpretationSection(result: ForecastResult): LinearLayout {
        return vertical(spacing = 8).apply {
            setPadding(dp(14), dp(14), dp(14), dp(14))
            background = reportBoxBackground(Ui.primary)
            addView(headline(getString(R.string.interpretation)).apply {
                textSize = 17f
            })
            interpretationLines(result).forEach { line ->
                addView(body("• $line").apply {
                    setTextColor(Ui.ink)
                })
            }
            addView(caption(getString(R.string.interpretation_disclaimer)).apply {
                textSize = 11f
            })
        }
    }

    private fun interpretationLines(result: ForecastResult): List<String> {
        return listOfNotNull(
            confidenceInterpretation(result),
            ptInterpretation(result),
            curveInterpretation(result),
        )
    }

    private fun confidenceInterpretation(result: ForecastResult): String {
        val confidence = result.confidence
        return when {
            confidence == null -> getString(R.string.interpretation_confidence_none, result.predictedType)
            confidence >= 0.75 -> getString(R.string.interpretation_confidence_high, result.predictedType)
            confidence >= 0.60 -> getString(R.string.interpretation_confidence_medium, result.predictedType)
            else -> getString(R.string.interpretation_confidence_low, result.predictedType)
        }
    }

    private fun ptInterpretation(result: ForecastResult): String {
        val pt = result.predictedPt
        val maxForce = result.predictedMaxForce
        if (pt == null || maxForce == null || maxForce <= 0.0) {
            return getString(R.string.interpretation_pt_generic)
        }
        val ratio = (pt / maxForce).coerceIn(0.0, 1.0)
        val percent = kotlin.math.round(ratio * 100.0).toInt()
        return when {
            ratio < 0.45 -> getString(R.string.interpretation_pt_early, percent)
            ratio > 0.75 -> getString(R.string.interpretation_pt_late, percent)
            else -> getString(R.string.interpretation_pt_mid, percent)
        }
    }

    private fun curveInterpretation(result: ForecastResult): String? {
        if (result.curve.size < 3) return null
        val maxPoint = result.curve.maxByOrNull { it.force } ?: return null
        if (maxPoint.force <= 0.0) return null
        val retained = (result.curve.lastOrNull()?.force ?: maxPoint.force) / maxPoint.force
        return when {
            retained < 0.25 -> getString(R.string.interpretation_curve_strong_softening)
            retained < 0.75 -> getString(R.string.interpretation_curve_softening)
            else -> getString(R.string.interpretation_curve_stable)
        }
    }

    private fun reportMetric(header: String, value: String, accent: Int): LinearLayout {
        return vertical(spacing = 6).apply {
            setPadding(dp(14), dp(14), dp(14), dp(14))
            background = reportBoxBackground(accent)
            addView(caption(header))
            addView(title(value, 24).apply {
                setTextColor(accent)
            })
        }
    }

    private fun reportSection(header: String, lines: List<String>): LinearLayout {
        return vertical(spacing = 8).apply {
            setPadding(dp(14), dp(14), dp(14), dp(14))
            background = reportBoxBackground(Ui.primary)
            addView(caption(header).apply {
                setTextColor(Ui.primary)
            })
            lines.forEach { item ->
                addView(body("• $item").apply {
                    textSize = 14f
                    setTextColor(Ui.ink)
                })
            }
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
                put(MediaStore.Images.Media.RELATIVE_PATH, "Pictures/ImperialAX")
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

    private fun saveBaseUrl() {
        getSharedPreferences("settings", MODE_PRIVATE)
            .edit()
            .putString("base_url", baseUrlField.text.toString())
            .apply()
    }

    private fun languageCode(): String {
        return getSharedPreferences("settings", MODE_PRIVATE).stringLanguageCode()
    }

    private fun selectedCase(): String {
        return when (caseGroup.checkedRadioButtonId) {
            101 -> "Case3"
            102 -> "Case4"
            else -> "Case2"
        }
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

    private fun displayThetaDegrees(rawValue: String): String {
        return rawValue.trim().toDoubleOrNull()
            ?.roundToInt()
            ?.coerceIn(-90, 90)
            ?.toString()
            ?: rawValue.trim()
    }

    private fun showRecentMenu() {
        val runs = loadRecentRuns()
        if (runs.length() == 0) return
        PopupMenu(this, recentButton).apply {
            for (index in 0 until runs.length()) {
                val item = runs.getJSONObject(index)
                val model = item.optString("model", Defaults.RESPONSE_MODEL_KEY).cleanModelKeyLabel()
                val prefix = if (index == 0) "${index + 1}. ${getString(R.string.recent_latest)}" else "${index + 1}."
                val summary = item.optIntOrNull("predicted_type")?.let {
                    " · Type $it · Pt ${item.optDoubleOrNull("predicted_pt").numberText(2)} · ${item.optDoubleOrNull("confidence").percentText()}"
                }.orEmpty()
                val title = "$prefix ${item.optString("case")} · $model$summary"
                menu.add(0, index, index, title)
            }
            if (runs.length() >= 2) {
                menu.add(1, 1001, runs.length(), getString(R.string.compare_latest_two))
            }
            menu.add(1, 1000, runs.length() + 1, getString(R.string.recent_clear))
            setOnMenuItemClickListener { menuItem ->
                if (menuItem.itemId == 1000) {
                    showDeleteRecentDialog()
                } else if (menuItem.itemId == 1001) {
                    showComparisonDialog(runs.getJSONObject(0), runs.getJSONObject(1))
                } else {
                    showRecentRunDetail(runs.getJSONObject(menuItem.itemId), menuItem.itemId)
                }
                true
            }
            show()
        }
    }

    private fun applyRecentRun(item: JSONObject) {
        when (item.optString("case")) {
            "Case3" -> caseGroup.check(101)
            "Case4" -> caseGroup.check(102)
            else -> caseGroup.check(100)
        }
        theta1Field.setText(displayThetaDegrees(item.optString("theta1", theta1Field.text.toString())))
        theta2Field.setText(displayThetaDegrees(item.optString("theta2", theta2Field.text.toString())))
        item.optDoubleOrNull("panel_a_in")?.let { panelAField.setText(formatDimension(it)) }
        item.optDoubleOrNull("panel_b_in")?.let { panelBField.setText(formatDimension(it)) }
        selectedResponseModelKey = item.optString("model", Defaults.RESPONSE_MODEL_KEY)
        populateResponseModelSpinner()
        updatePlyPreview()
        resultSection.visibility = LinearLayout.GONE
    }

    private fun showRecentRunDetail(item: JSONObject, index: Int) {
        val model = item.optString("model", Defaults.RESPONSE_MODEL_KEY).cleanModelKeyLabel()
        val type = item.optIntOrNull("predicted_type")?.let { "Type $it" } ?: getString(R.string.recent_no_result)
        val message = listOf(
            "${index + 1}. ${if (index == 0) getString(R.string.recent_latest) else getString(R.string.recent_result)}",
            "",
            "MODEL",
            "• Model: $model",
            "",
            "INPUTS",
            "• Case: ${item.optString("case")}",
            "• Theta 1: ${displayThetaDegrees(item.optString("theta1"))} deg",
            "• Theta 2: ${displayThetaDegrees(item.optString("theta2"))} deg",
            "• Panel: ${formatDimension(item.optDoubleOrNull("panel_a_in") ?: 6.0)} × ${formatDimension(item.optDoubleOrNull("panel_b_in") ?: 4.0)} in",
            "",
            "RESULTS",
            "• Predicted type: $type",
            "• Confidence: ${item.optDoubleOrNull("confidence").percentText()}",
            "• Pt: ${item.optDoubleOrNull("predicted_pt").numberText(2)}",
            "• Max force: ${item.optDoubleOrNull("predicted_max_force").numberText(2)}",
            "• Pt displacement: ${recentPtDisplacement(item).numberText(5)}",
        ).joinToString("\n")

        AlertDialog.Builder(this)
            .setTitle(getString(R.string.recent_result_detail))
            .setMessage(message)
            .setPositiveButton(getString(R.string.recent_use_inputs)) { _, _ -> applyRecentRun(item) }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun saveRecentRun(caseName: String, modelKey: String, theta1: String, theta2: String, panelA: Double, panelB: Double, result: ForecastResult) {
        val run = JSONObject()
            .put("case", caseName)
            .put("model", modelKey)
            .put("theta1", theta1)
            .put("theta2", theta2)
            .put("panel_a_in", panelA)
            .put("panel_b_in", panelB)
            .put("predicted_type", result.predictedType)
            .put("confidence", result.confidence)
            .put("predicted_pt", result.predictedPt)
            .put("predicted_max_force", result.predictedMaxForce)
            .put("predicted_max_displacement", result.predictedMaxDisplacement)
            .put("model_label", result.displayModelLabel)
            .put("curve", curveToJson(result.curve))
        val signature = recentSignature(run)
        val existing = loadRecentRuns()
        val next = JSONArray().put(run)
        for (index in 0 until existing.length()) {
            val item = existing.getJSONObject(index)
            if (recentSignature(item) != signature && next.length() < 5) {
                next.put(item)
            }
        }
        recentPrefs().edit().putString("laminate_recent_runs", next.toString()).apply()
        updateRecentButton()
    }

    private fun clearRecentRuns() {
        recentPrefs().edit().remove("laminate_recent_runs").apply()
        updateRecentButton()
    }

    private fun showDeleteRecentDialog() {
        val runs = loadRecentRuns()
        if (runs.length() == 0) return
        val checked = BooleanArray(runs.length())
        val labels = Array(runs.length()) { index ->
            val item = runs.getJSONObject(index)
            val model = item.optString("model", Defaults.RESPONSE_MODEL_KEY).cleanModelKeyLabel()
            val prefix = if (index == 0) "${index + 1}. ${getString(R.string.recent_latest)}" else "${index + 1}."
            "$prefix ${item.optString("case")} · $model · Theta ${displayThetaDegrees(item.optString("theta1"))}/${displayThetaDegrees(item.optString("theta2"))} · Panel ${formatDimension(item.optDoubleOrNull("panel_a_in") ?: 6.0)}×${formatDimension(item.optDoubleOrNull("panel_b_in") ?: 4.0)} · Pt ${item.optDoubleOrNull("predicted_pt").numberText(2)}"
        }
        AlertDialog.Builder(this)
            .setTitle(getString(R.string.recent_delete_title))
            .setMultiChoiceItems(labels, checked) { _, which, isChecked ->
                checked[which] = isChecked
            }
            .setPositiveButton(getString(R.string.recent_delete_selected)) { _, _ ->
                deleteRecentRuns(checked)
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun deleteRecentRuns(checked: BooleanArray) {
        val existing = loadRecentRuns()
        val next = JSONArray()
        for (index in 0 until existing.length()) {
            if (checked.getOrNull(index) != true) {
                next.put(existing.getJSONObject(index))
            }
        }
        if (next.length() == existing.length()) return
        if (next.length() == 0) {
            recentPrefs().edit().remove("laminate_recent_runs").apply()
        } else {
            recentPrefs().edit().putString("laminate_recent_runs", next.toString()).apply()
        }
        updateRecentButton()
    }

    private fun loadRecentRuns(): JSONArray {
        return runCatching {
            JSONArray(recentPrefs().getString("laminate_recent_runs", "[]"))
        }.getOrDefault(JSONArray())
    }

    private fun recentSignature(item: JSONObject): String {
        return "${item.optString("case")}|${item.optString("model", Defaults.RESPONSE_MODEL_KEY)}|${item.optString("theta1")}|${item.optString("theta2")}|${item.optDoubleOrNull("panel_a_in") ?: "-"}|${item.optDoubleOrNull("panel_b_in") ?: "-"}"
    }

    private fun updateRecentButton() {
        val hasRecent = loadRecentRuns().length() > 0
        recentButton.isEnabled = hasRecent
        recentButton.alpha = if (hasRecent) 1f else 0.45f
    }

    private fun showComparisonDialog(first: JSONObject, second: JSONObject) {
        val firstCurve = curveFromJson(first.optJSONArray("curve"))
        val secondCurve = curveFromJson(second.optJSONArray("curve"))
        val content = vertical(spacing = 12).apply {
            setPadding(dp(18), dp(16), dp(18), dp(8))
            addView(caption(getString(R.string.compare_summary)))
            addView(compareMetric("Pt", first.optDoubleOrNull("predicted_pt"), second.optDoubleOrNull("predicted_pt"), 2))
            addView(compareMetric(getString(R.string.max_force_label), first.optDoubleOrNull("predicted_max_force"), second.optDoubleOrNull("predicted_max_force"), 2))
            addView(compareMetric(getString(R.string.pt_displacement_label), recentPtDisplacement(first), recentPtDisplacement(second), 5))
            addView(compareMetric(getString(R.string.confidence_label), first.optDoubleOrNull("confidence"), second.optDoubleOrNull("confidence"), 3, isPercent = true))
            if (firstCurve.isNotEmpty() && secondCurve.isNotEmpty()) {
                addView(caption(getString(R.string.compare_curves)))
                addView(ComparisonCurveChartView(this@MainActivity).apply {
                    leftPoints = firstCurve
                    rightPoints = secondCurve
                    leftPt = first.optDoubleOrNull("predicted_pt")
                    rightPt = second.optDoubleOrNull("predicted_pt")
                    layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(250))
                })
                addView(body("${getString(R.string.compare_first)}: ${first.optString("case")} · ${displayThetaDegrees(first.optString("theta1"))}/${displayThetaDegrees(first.optString("theta2"))} · Pt ${first.optDoubleOrNull("predicted_pt").numberText(2)}"))
                addView(body("${getString(R.string.compare_second)}: ${second.optString("case")} · ${displayThetaDegrees(second.optString("theta1"))}/${displayThetaDegrees(second.optString("theta2"))} · Pt ${second.optDoubleOrNull("predicted_pt").numberText(2)}"))
            } else {
                addView(body(getString(R.string.compare_curve_missing)))
            }
            addView(caption(getString(R.string.interpretation)))
            comparisonInterpretation(first, second).forEach { line ->
                addView(body("• $line"))
            }
        }
        AlertDialog.Builder(this)
            .setTitle(getString(R.string.compare_results))
            .setView(ScrollView(this).apply { addView(content) })
            .setPositiveButton(android.R.string.ok, null)
            .show()
    }

    private fun compareMetric(title: String, first: Double?, second: Double?, digits: Int, isPercent: Boolean = false): TextView {
        val delta = if (first != null && second != null) second - first else null
        val line = "$title\n" +
            "${getString(R.string.compare_first)} ${formatCompareValue(first, digits, isPercent)}   " +
            "${getString(R.string.compare_second)} ${formatCompareValue(second, digits, isPercent)}   " +
            "Δ ${formatSignedDelta(delta, digits, isPercent)}"
        return body(line).apply {
            background = fieldBackground()
            setPadding(dp(12), dp(10), dp(12), dp(10))
        }
    }

    private fun comparisonInterpretation(first: JSONObject, second: JSONObject): List<String> {
        return listOfNotNull(
            deltaSentence("pt", first.optDoubleOrNull("predicted_pt"), second.optDoubleOrNull("predicted_pt"), 2),
            deltaSentence("force", first.optDoubleOrNull("predicted_max_force"), second.optDoubleOrNull("predicted_max_force"), 2),
            confidenceCompareSentence(first.optDoubleOrNull("confidence"), second.optDoubleOrNull("confidence")),
        )
    }

    private fun deltaSentence(kind: String, first: Double?, second: Double?, digits: Int): String? {
        if (first == null || second == null) return null
        val delta = second - first
        val value = kotlin.math.abs(delta).numberText(digits)
        if (kotlin.math.abs(delta) < 0.000001) {
            return when (kind) {
                "pt" -> getString(R.string.compare_interpretation_pt_same, second.numberText(digits))
                else -> getString(R.string.compare_interpretation_force_same, second.numberText(digits))
            }
        }
        return when {
            kind == "pt" && delta > 0 -> getString(R.string.compare_interpretation_pt_higher, value)
            kind == "pt" -> getString(R.string.compare_interpretation_pt_lower, value)
            delta > 0 -> getString(R.string.compare_interpretation_force_higher, value)
            else -> getString(R.string.compare_interpretation_force_lower, value)
        }
    }

    private fun confidenceCompareSentence(first: Double?, second: Double?): String? {
        if (first == null || second == null) return null
        val delta = second - first
        return when {
            kotlin.math.abs(delta) < 0.02 -> getString(R.string.compare_interpretation_confidence_similar)
            delta > 0 -> getString(R.string.compare_interpretation_confidence_higher)
            else -> getString(R.string.compare_interpretation_confidence_lower)
        }
    }

    private fun formatCompareValue(value: Double?, digits: Int, isPercent: Boolean): String {
        if (value == null) return "-"
        return if (isPercent) value.percentText() else value.numberText(digits)
    }

    private fun formatSignedDelta(value: Double?, digits: Int, isPercent: Boolean): String {
        if (value == null) return "-"
        val sign = if (value > 0) "+" else ""
        return if (isPercent) "$sign${(value * 100.0).numberText(1)}%" else "$sign${value.numberText(digits)}"
    }

    private fun curveToJson(points: List<CurvePoint>): JSONArray {
        val array = JSONArray()
        points.forEach { point ->
            array.put(JSONObject().put("displacement", point.displacement).put("force", point.force))
        }
        return array
    }

    private fun curveFromJson(array: JSONArray?): List<CurvePoint> {
        if (array == null) return emptyList()
        return (0 until array.length()).mapNotNull { index ->
            val item = array.optJSONObject(index) ?: return@mapNotNull null
            CurvePoint(item.optDouble("displacement"), item.optDouble("force"))
        }
    }

    private fun recentPtDisplacement(item: JSONObject): Double? {
        return curveFromJson(item.optJSONArray("curve")).displacementAtForce(item.optDoubleOrNull("predicted_pt"))
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
        intArrayOf(Ui.accent, Ui.primary)
    ).apply {
        cornerRadius = dp(8).toFloat()
    }

    private fun secondaryButtonBackground(): GradientDrawable = GradientDrawable().apply {
        setColor(Color.argb(24, Color.red(Ui.primary), Color.green(Ui.primary), Color.blue(Ui.primary)))
        cornerRadius = dp(8).toFloat()
        setStroke(1, Color.argb(80, Color.red(Ui.primary), Color.green(Ui.primary), Color.blue(Ui.primary)))
    }

    private fun fieldBackground(): GradientDrawable = GradientDrawable().apply {
        setColor(Ui.field)
        cornerRadius = dp(8).toFloat()
        setStroke(1, Ui.fieldBorder)
    }

    private fun strokedPreviewBackground(): GradientDrawable = GradientDrawable().apply {
        setColor(Color.rgb(236, 243, 246))
        cornerRadius = dp(8).toFloat()
        setStroke(1, Ui.border)
    }

    private fun modelCardBackground(accent: Int, selected: Boolean): GradientDrawable = GradientDrawable().apply {
        setColor(if (selected) Color.argb(22, Color.red(accent), Color.green(accent), Color.blue(accent)) else Ui.field)
        cornerRadius = dp(8).toFloat()
        setStroke(if (selected) 2 else 1, Color.argb(if (selected) 170 else 48, Color.red(accent), Color.green(accent), Color.blue(accent)))
    }

    private fun tintedBackground(color: Int, alpha: Int): GradientDrawable = GradientDrawable().apply {
        setColor(Color.argb(alpha, Color.red(color), Color.green(color), Color.blue(color)))
        cornerRadius = dp(8).toFloat()
    }

    private fun capsuleBackground(color: Int): GradientDrawable = GradientDrawable().apply {
        setColor(color)
        cornerRadius = dp(999).toFloat()
    }

    private fun reportBoxBackground(accent: Int): GradientDrawable = GradientDrawable().apply {
        setColor(Color.WHITE)
        cornerRadius = dp(8).toFloat()
        setStroke(1, Color.argb(42, Color.red(accent), Color.green(accent), Color.blue(accent)))
    }

    private fun weightedReportParams(leftMargin: Int): LinearLayout.LayoutParams {
        return LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
            this.leftMargin = dp(leftMargin)
        }
    }

    private fun vertical(spacing: Int = 0): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        showDividers = LinearLayout.SHOW_DIVIDER_MIDDLE
        dividerDrawable = SpaceDrawable(dp(spacing))
    }

    private fun twoColumnRow(left: View, right: View): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.HORIZONTAL
        addView(left, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
            rightMargin = dp(6)
        })
        addView(right, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
            leftMargin = dp(6)
        })
    }

    private fun inputBlock(title: String, field: EditText): LinearLayout = vertical(spacing = 6).apply {
        addView(label(title))
        addView(field)
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

    private fun body(text: String): TextView = TextView(this).apply {
        this.text = text
        textSize = 14f
        setTextColor(Ui.body)
    }

    private fun caption(text: String): TextView = TextView(this).apply {
        this.text = text
        textSize = 12f
        typeface = Typeface.DEFAULT_BOLD
        setTextColor(Ui.muted)
    }

    private fun label(text: String): TextView = caption(text).apply {
        gravity = Gravity.START
    }

    private fun modelOptionCard(model: ModelInfo, onClick: () -> Unit): LinearLayout {
        val selected = model.key == selectedResponseModelKey
        val accent = when {
            !model.available -> Ui.danger
            selected -> Ui.success
            else -> Ui.primary
        }
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(14), dp(12), dp(14), dp(12))
            background = modelCardBackground(accent, selected)
            alpha = if (model.available) 1f else 0.55f
            isClickable = true
            isFocusable = true
            setOnClickListener { onClick() }

            addView(LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                addView(modelIconView(if (model.key.contains("goint")) "NN" else "ML", accent))
                addView(LinearLayout(context).apply {
                    orientation = LinearLayout.VERTICAL
                    setPadding(dp(12), 0, dp(8), 0)
                    addView(headline(model.displayLabel).apply {
                        textSize = 17f
                        maxLines = 1
                        setTextColor(if (model.available) Ui.ink else Ui.muted)
                    })
                    addView(LinearLayout(context).apply {
                        orientation = LinearLayout.HORIZONTAL
                        showDividers = LinearLayout.SHOW_DIVIDER_MIDDLE
                        dividerDrawable = SpaceDrawable(dp(6))
                        if (model.key == Defaults.RESPONSE_MODEL_KEY) {
                            addView(modelBadgeView(getString(R.string.model_recommended), Ui.success))
                        }
                        addView(modelBadgeView(modelTag(model), Ui.primary))
                        if (!model.available) {
                            addView(modelBadgeView(getString(R.string.model_missing), Ui.danger))
                        }
                    })
                }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
                addView(TextView(context).apply {
                    text = if (selected) "OK" else ">"
                    textSize = if (selected) 12f else 20f
                    typeface = Typeface.DEFAULT_BOLD
                    setTextColor(accent)
                    gravity = Gravity.CENTER
                }, LinearLayout.LayoutParams(dp(34), dp(34)))
            })
            addView(body(modelDescription(model)).apply {
                textSize = 13f
                setPadding(0, dp(10), 0, 0)
                setTextColor(Ui.muted)
            })
        }
    }

    private fun modelIconView(text: String, color: Int): TextView = TextView(this).apply {
        this.text = text
        textSize = 12f
        typeface = Typeface.DEFAULT_BOLD
        gravity = Gravity.CENTER
        setTextColor(color)
        background = tintedBackground(color, alpha = 24)
        layoutParams = LinearLayout.LayoutParams(dp(42), dp(42))
    }

    private fun modelBadgeView(text: String, color: Int): TextView = TextView(this).apply {
        this.text = text
        textSize = 10f
        typeface = Typeface.DEFAULT_BOLD
        setTextColor(color)
        setPadding(dp(7), dp(3), dp(7), dp(3))
        background = tintedBackground(color, alpha = 22)
    }

    private fun legendBadge(text: String, color: Int): TextView = TextView(this).apply {
        this.text = text
        textSize = 10f
        typeface = Typeface.DEFAULT_BOLD
        setTextColor(color)
        setPadding(dp(7), dp(4), dp(7), dp(4))
        background = GradientDrawable().apply {
            setColor(Color.WHITE)
            cornerRadius = dp(999).toFloat()
            setStroke(1, Ui.border)
        }
    }

    private fun input(value: String): EditText = EditText(this).apply {
        setText(value)
        setSingleLine(true)
        setTextColor(Ui.ink)
        setHintTextColor(Ui.muted)
        background = fieldBackground()
        setPadding(dp(14), dp(10), dp(14), dp(10))
        minHeight = dp(48)
        textSize = 18f
        imeOptions = EditorInfo.IME_ACTION_DONE
        setOnEditorActionListener { view, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_DONE) {
                view.clearFocus()
                hideKeyboard(view)
                true
            } else {
                false
            }
        }
        inputType = android.text.InputType.TYPE_CLASS_NUMBER or
            android.text.InputType.TYPE_NUMBER_FLAG_SIGNED
    }

    private fun MotionEvent.isOutside(view: View): Boolean {
        val bounds = Rect()
        view.getGlobalVisibleRect(bounds)
        return !bounds.contains(rawX.toInt(), rawY.toInt())
    }

    private fun hideKeyboard(view: View) {
        val inputManager = getSystemService(INPUT_METHOD_SERVICE) as InputMethodManager
        inputManager.hideSoftInputFromWindow(view.windowToken, 0)
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    companion object {
        private const val LANGUAGE_KEY = "language_code"

        private fun localizedContext(base: Context): Context {
            val languageCode = base.getSharedPreferences("settings", Context.MODE_PRIVATE).stringLanguageCode()
            val locale = Locale(languageCode)
            Locale.setDefault(locale)
            val config = Configuration(base.resources.configuration)
            config.setLocale(locale)
            return base.createConfigurationContext(config)
        }
    }
}

private fun android.content.SharedPreferences.stringLanguageCode(): String {
    val stored = getString("language_code", null)
    if (stored == "ko" || stored == "en") return stored
    return if (Locale.getDefault().language == "ko") "ko" else "en"
}

private class SpaceDrawable(private val height: Int) : android.graphics.drawable.ColorDrawable(Color.TRANSPARENT) {
    override fun getIntrinsicHeight(): Int = height
}

private fun Double?.percentText(): String = this?.let { "%.1f%%".format(it * 100.0) } ?: "-"

private fun Double?.numberText(digits: Int): String = this?.let { "%.${digits}f".format(it) } ?: "-"

private fun formatDimension(value: Double): String {
    val rounded = kotlin.math.round(value * 1000.0) / 1000.0
    return if (rounded % 1.0 == 0.0) {
        rounded.toInt().toString()
    } else {
        "%.3f".format(rounded).trimEnd('0').trimEnd('.')
    }
}

private fun JSONObject.optDoubleOrNull(key: String): Double? = if (has(key) && !isNull(key)) optDouble(key) else null

private fun JSONObject.optIntOrNull(key: String): Int? = if (has(key) && !isNull(key)) optInt(key) else null

private data class ModelPickerItem(
    val key: String,
    val label: String,
    val available: Boolean,
) {
    override fun toString(): String = if (available) label else "$label (unavailable)"
}

private object Ui {
    val background: Int = Color.rgb(242, 247, 247)
    val card: Int = Color.WHITE
    val field: Int = Color.rgb(237, 246, 244)
    val fieldBorder: Int = Color.rgb(209, 229, 226)
    val border: Int = Color.rgb(201, 224, 221)
    val ink: Int = Color.rgb(12, 19, 21)
    val body: Int = Color.rgb(51, 70, 74)
    val muted: Int = Color.rgb(84, 103, 108)
    val primary: Int = Color.rgb(0, 133, 128)
    val accent: Int = Color.rgb(13, 56, 66)
    val success: Int = Color.rgb(5, 150, 105)
    val warning: Int = Color.rgb(217, 119, 6)
    val danger: Int = Color.rgb(220, 38, 38)
    val probabilityMuted: Int = Color.rgb(182, 198, 204)
    val reportBackground: Int = Color.rgb(246, 251, 249)
}
