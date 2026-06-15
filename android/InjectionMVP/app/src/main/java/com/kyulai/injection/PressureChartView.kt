package com.kyulai.injection

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.DashPathEffect
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RectF
import android.view.MotionEvent
import android.view.View
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

class PressureChartView(context: Context) : View(context) {
    var points: List<PressurePoint> = emptyList()
        set(value) {
            field = value
            invalidate()
        }

    var maxPressure: Double? = null
        set(value) {
            field = value
            invalidate()
        }

    private val axisPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(125, 143, 166)
        strokeWidth = 2f
        style = Paint.Style.STROKE
    }
    private val curvePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(37, 85, 209)
        strokeWidth = 5f
        style = Paint.Style.STROKE
    }
    private val markerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(234, 76, 33)
        strokeWidth = 3f
        style = Paint.Style.STROKE
        pathEffect = DashPathEffect(floatArrayOf(10f, 8f), 0f)
    }
    private val dotPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(234, 76, 33)
        style = Paint.Style.FILL
    }
    private val labelPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(14, 19, 30)
        textSize = 28f
        isFakeBoldText = true
    }
    private val tickPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(91, 103, 122)
        textSize = 24f
        textAlign = Paint.Align.CENTER
    }
    private val yTickPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(91, 103, 122)
        textSize = 24f
        textAlign = Paint.Align.RIGHT
    }
    private val gridPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(64, 91, 103, 122)
        strokeWidth = 1.5f
        style = Paint.Style.STROKE
        pathEffect = DashPathEffect(floatArrayOf(6f, 8f), 0f)
    }
    private val selectionPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(92, 14, 19, 30)
        strokeWidth = 2f
        style = Paint.Style.STROKE
        pathEffect = DashPathEffect(floatArrayOf(8f, 8f), 0f)
    }
    private val selectionDotPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        style = Paint.Style.FILL
    }
    private val tooltipPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(238, 255, 255, 255)
        style = Paint.Style.FILL
    }
    private val tooltipStrokePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(92, 37, 85, 209)
        strokeWidth = 2f
        style = Paint.Style.STROKE
    }

    private var selectedIndex: Int? = null

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val left = 76f
        val top = 46f
        val right = width - 26f
        val bottom = height - 58f
        canvas.drawLine(left, bottom, right, bottom, axisPaint)
        canvas.drawLine(left, top, left, bottom, axisPaint)
        if (points.size < 2) return

        val maxTime = max(points.maxOf { it.timeS }, 0.000001)
        val minPressure = min(0.0, points.minOf { it.pressureMPa })
        val maxPressureValue = max(points.maxOf { it.pressureMPa }, max(maxPressure ?: 0.0, 0.000001))

        fun x(value: Double) = left + ((value / maxTime) * (right - left)).toFloat()
        fun y(value: Double): Float {
            val ratio = (value - minPressure) / max(maxPressureValue - minPressure, 0.000001)
            return bottom - (ratio * (bottom - top)).toFloat()
        }

        val xTicks = listOf(0.0, maxTime / 2.0, maxTime)
        val yTicks = listOf(0.0, maxPressureValue / 2.0, maxPressureValue)
        xTicks.forEach { tick ->
            val tickX = x(tick)
            canvas.drawLine(tickX, top, tickX, bottom, gridPaint)
            canvas.drawText(tick.axisText(if (tick == 0.0) 0 else 1), tickX, bottom + 30f, tickPaint)
        }
        yTicks.forEach { tick ->
            val tickY = y(tick)
            canvas.drawLine(left, tickY, right, tickY, gridPaint)
            canvas.drawText(tick.axisText(if (tick >= 10.0) 0 else 1), left - 10f, tickY + 8f, yTickPaint)
        }
        canvas.drawText(context.getString(R.string.axis_time), (left + right) / 2f, height - 12f, tickPaint)
        tickPaint.textAlign = Paint.Align.LEFT
        canvas.drawText(context.getString(R.string.axis_pressure), left, top - 14f, tickPaint)
        tickPaint.textAlign = Paint.Align.CENTER

        val path = Path()
        points.forEachIndexed { index, point ->
            if (index == 0) path.moveTo(x(point.timeS), y(point.pressureMPa))
            else path.lineTo(x(point.timeS), y(point.pressureMPa))
        }
        canvas.drawPath(path, curvePaint)

        val peak = maxPressure ?: return
        val marker = points.minByOrNull { kotlin.math.abs(it.pressureMPa - peak) } ?: return
        val markerX = x(marker.timeS)
        val markerY = y(marker.pressureMPa)
        canvas.drawLine(markerX, top, markerX, bottom, markerPaint)
        canvas.drawCircle(markerX, markerY, 9f, dotPaint)
        canvas.drawText(context.getString(R.string.peak_marker_format, peak), min(markerX + 12f, right - 210f), max(top + 30f, markerY - 14f), labelPaint)

        val selected = selectedIndex?.let { points.getOrNull(it) } ?: return
        val selectedX = x(selected.timeS)
        val selectedY = y(selected.pressureMPa)
        canvas.drawLine(selectedX, top, selectedX, bottom, selectionPaint)
        canvas.drawLine(left, selectedY, right, selectedY, selectionPaint)
        canvas.drawCircle(selectedX, selectedY, 12f, selectionDotPaint)
        canvas.drawCircle(selectedX, selectedY, 12f, curvePaint)

        val firstLine = "${selected.timeS.axisText(3)} s"
        val secondLine = "${selected.pressureMPa.axisText(2)} MPa"
        val boxWidth = max(labelPaint.measureText(firstLine), labelPaint.measureText(secondLine)) + 34f
        val boxHeight = 74f
        val boxLeft = min(max(selectedX + 16f, left + 8f), right - boxWidth - 8f)
        val boxTop = max(top + 8f, selectedY - boxHeight - 16f)
        val rect = RectF(boxLeft, boxTop, boxLeft + boxWidth, boxTop + boxHeight)
        canvas.drawRoundRect(rect, 16f, 16f, tooltipPaint)
        canvas.drawRoundRect(rect, 16f, 16f, tooltipStrokePaint)
        canvas.drawText(firstLine, boxLeft + 16f, boxTop + 30f, labelPaint)
        canvas.drawText(secondLine, boxLeft + 16f, boxTop + 60f, labelPaint)
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        if (points.size < 2) return false
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN, MotionEvent.ACTION_MOVE, MotionEvent.ACTION_UP -> {
                selectedIndex = nearestIndex(event.x)
                invalidate()
                parent?.requestDisallowInterceptTouchEvent(event.actionMasked != MotionEvent.ACTION_UP)
                return true
            }
        }
        return true
    }

    private fun nearestIndex(touchX: Float): Int {
        val left = 76f
        val right = width - 26f
        val maxTime = max(points.maxOf { it.timeS }, 0.000001)
        fun x(value: Double) = left + ((value / maxTime) * (right - left)).toFloat()
        return points.indices.minByOrNull { abs(x(points[it].timeS) - touchX) } ?: 0
    }
}

fun Double.axisText(digits: Int): String = "%.${digits}f".format(this).trimEnd('0').trimEnd('.')
