package com.luvelox.app

import android.app.Activity
import android.graphics.Color
import android.graphics.Typeface
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

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

        root.addView(label("FORECAST RESULT", LaminateV2.blue, 12f, Typeface.BOLD))
        root.addView(label("Laminate Response", LaminateV2.ink, 34f, Typeface.BOLD).apply {
            includeFontPadding = false
        }, margin(top = 8))
        root.addView(paragraph("Review Type, Pt, response metrics, and explanation features for this run."), margin(top = 8))
        root.addView(inputSummary(), margin(top = 14))
        root.addView(resultCard(result), margin(top = 14))
        root.addView(backButton("Run another forecast"), margin(top = 16))
    }

    @Suppress("DEPRECATION")
    private fun readResult(): LaminateResult? {
        return intent.getSerializableExtra(EXTRA_LAMINATE_RESULT) as? LaminateResult
    }

    private fun inputSummary(): LinearLayout {
        val caseName = intent.getStringExtra(EXTRA_LAMINATE_CASE) ?: "-"
        val theta1 = intent.getIntExtra(EXTRA_LAMINATE_THETA1, 0)
        val theta2 = intent.getIntExtra(EXTRA_LAMINATE_THETA2, 0)
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(14), dp(12), dp(14), dp(12))
            background = fieldBackground()
            addView(label("INPUTS", LaminateV2.blue, 11f, Typeface.BOLD))
            val row = LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                addView(summaryPill(caseName))
                addView(summaryPill("theta1 $theta1 deg"), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                    marginStart = dp(8)
                })
                addView(summaryPill("theta2 $theta2 deg"), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                    marginStart = dp(8)
                })
            }
            addView(row, margin(top = 10))
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

        card.addView(label("Class probability", LaminateV2.ink, 18f, Typeface.BOLD), margin(top = 16))
        result.probabilities.toSortedMap().forEach { (label, value) ->
            card.addView(label("$label  ${formatPercent(value)}", LaminateV2.muted, 13f, Typeface.BOLD), margin(top = 6))
        }

        result.xai?.let { xai ->
            card.addView(label("Why this prediction?", LaminateV2.ink, 18f, Typeface.BOLD), margin(top = 18))
            card.addView(paragraph(xai.summary), margin(top = 6))
            card.addView(label("Method: ${xai.method} - ${xai.featureSet}", LaminateV2.blue, 12f, Typeface.BOLD), margin(top = 8))
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
        return card
    }

    private fun xaiFeatureRow(feature: LaminateXaiFeature): LinearLayout = LinearLayout(this).apply {
        val safeImportance = feature.importance.coerceIn(0.0, 1.0)
        orientation = LinearLayout.VERTICAL
        setPadding(0, dp(6), 0, dp(6))
        addView(LinearLayout(this@LaminateResultActivity).apply {
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
        addView(label(feature.explanation, LaminateV2.muted, 11f, Typeface.NORMAL), margin(top = 3))
    }

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

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}
