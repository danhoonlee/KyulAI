package com.kyulai.injection

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.DashPathEffect
import android.graphics.Paint
import android.graphics.RectF
import android.view.View
import kotlin.math.max

class FillingHistogramView(context: Context) : View(context) {
    var bins: List<FillingBin> = emptyList()
        set(value) {
            field = value
            invalidate()
        }

    private val axisPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(148, 163, 184)
        strokeWidth = 2f
        style = Paint.Style.STROKE
    }
    private val gridPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(70, 100, 116, 139)
        strokeWidth = 1.5f
        style = Paint.Style.STROKE
        pathEffect = DashPathEffect(floatArrayOf(6f, 8f), 0f)
    }
    private val barPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(0, 148, 163)
        style = Paint.Style.FILL
    }
    private val tickPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(100, 116, 139)
        textSize = 24f
        textAlign = Paint.Align.CENTER
    }
    private val yTickPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(100, 116, 139)
        textSize = 24f
        textAlign = Paint.Align.RIGHT
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val left = 78f
        val top = 46f
        val right = width - 26f
        val bottom = height - 58f
        canvas.drawLine(left, bottom, right, bottom, axisPaint)
        canvas.drawLine(left, top, left, bottom, axisPaint)
        if (bins.isEmpty()) return

        val maxVolume = max(bins.maxOf { it.volumeRatioPct }, 0.000001)
        fun y(value: Double): Float = bottom - ((value / maxVolume) * (bottom - top)).toFloat()

        listOf(0.0, maxVolume / 2.0, maxVolume).forEach { tick ->
            val tickY = y(tick)
            canvas.drawLine(left, tickY, right, tickY, gridPaint)
            canvas.drawText(tick.axisText(if (tick >= 10.0) 0 else 1), left - 10f, tickY + 8f, yTickPaint)
        }

        val slot = (right - left) / bins.size.coerceAtLeast(1)
        val barWidth = max(8f, slot * 0.72f)
        bins.forEachIndexed { index, bin ->
            val x = left + index * slot + (slot - barWidth) / 2f
            val topY = y(bin.volumeRatioPct)
            canvas.drawRoundRect(RectF(x, topY, x + barWidth, bottom), 8f, 8f, barPaint)
        }

        val minPressure = bins.minOf { it.fromMPa }
        val maxPressure = bins.maxOf { it.toMPa }
        canvas.drawText(minPressure.axisText(1), left, bottom + 30f, tickPaint)
        canvas.drawText(maxPressure.axisText(1), right, bottom + 30f, tickPaint)
        canvas.drawText("Pressure bin (MPa)", (left + right) / 2f, height - 12f, tickPaint)
        tickPaint.textAlign = Paint.Align.LEFT
        canvas.drawText("Volume (%)", left, top - 14f, tickPaint)
        tickPaint.textAlign = Paint.Align.CENTER
    }
}
