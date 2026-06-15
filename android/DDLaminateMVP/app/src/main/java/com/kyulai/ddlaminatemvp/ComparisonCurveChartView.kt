package com.kyulai.ddlaminatemvp

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.DashPathEffect
import android.graphics.Paint
import android.graphics.Path
import android.view.View
import kotlin.math.max
import kotlin.math.min

class ComparisonCurveChartView(context: Context) : View(context) {
    var leftPoints: List<CurvePoint> = emptyList()
        set(value) {
            field = value
            invalidate()
        }
    var rightPoints: List<CurvePoint> = emptyList()
        set(value) {
            field = value
            invalidate()
        }
    var leftPt: Double? = null
        set(value) {
            field = value
            invalidate()
        }
    var rightPt: Double? = null
        set(value) {
            field = value
            invalidate()
        }

    private val axisPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(112, 136, 140)
        strokeWidth = 2f
        style = Paint.Style.STROKE
    }
    private val firstPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(0, 133, 128)
        strokeWidth = 5f
        style = Paint.Style.STROKE
    }
    private val secondPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(217, 119, 6)
        strokeWidth = 5f
        style = Paint.Style.STROKE
        pathEffect = DashPathEffect(floatArrayOf(18f, 14f), 0f)
    }
    private val labelPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(84, 103, 108)
        textSize = 24f
        isFakeBoldText = true
    }
    private val ptGuidePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        strokeWidth = 3f
        style = Paint.Style.STROKE
        pathEffect = DashPathEffect(floatArrayOf(10f, 8f), 0f)
    }
    private val ptDotPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val left = 64f
        val top = 46f
        val right = width - 24f
        val bottom = height - 58f
        canvas.drawLine(left, bottom, right, bottom, axisPaint)
        canvas.drawLine(left, top, left, bottom, axisPaint)
        canvas.drawText(context.getString(R.string.axis_force), left, top - 14f, labelPaint)
        labelPaint.textAlign = Paint.Align.CENTER
        canvas.drawText(context.getString(R.string.axis_displacement), (left + right) / 2f, height - 12f, labelPaint)
        labelPaint.textAlign = Paint.Align.LEFT

        val all = leftPoints + rightPoints
        if (leftPoints.size < 2 || rightPoints.size < 2 || all.size < 4) return

        val minX = all.minOf { it.displacement }
        val maxX = max(all.maxOf { it.displacement }, minX + 0.000001)
        val minY = min(0.0, all.minOf { it.force })
        val maxY = max(all.maxOf { it.force }, minY + 0.000001)

        fun x(value: Double) = left + (((value - minX) / (maxX - minX)) * (right - left)).toFloat()
        fun y(value: Double): Float {
            val ratio = (value - minY) / max(maxY - minY, 0.000001)
            return bottom - (ratio * (bottom - top)).toFloat()
        }

        fun path(points: List<CurvePoint>): Path {
            val path = Path()
            points.forEachIndexed { index, point ->
                if (index == 0) path.moveTo(x(point.displacement), y(point.force))
                else path.lineTo(x(point.displacement), y(point.force))
            }
            return path
        }

        canvas.drawPath(path(leftPoints), firstPaint)
        canvas.drawPath(path(rightPoints), secondPaint)
        drawPtMarker(canvas, leftPoints, leftPt, firstPaint.color, context.getString(R.string.compare_first), x = ::x, y = ::y, top = top, bottom = bottom, left = left, right = right)
        drawPtMarker(canvas, rightPoints, rightPt, secondPaint.color, context.getString(R.string.compare_second), x = ::x, y = ::y, top = top, bottom = bottom, left = left, right = right)
    }

    private fun drawPtMarker(
        canvas: Canvas,
        points: List<CurvePoint>,
        pt: Double?,
        color: Int,
        label: String,
        x: (Double) -> Float,
        y: (Double) -> Float,
        top: Float,
        bottom: Float,
        left: Float,
        right: Float,
    ) {
        if (pt == null || points.isEmpty()) return
        val marker = points.minByOrNull { kotlin.math.abs(it.force - pt) } ?: return
        val markerX = x(marker.displacement)
        val markerY = y(marker.force)
        ptGuidePaint.color = Color.argb(158, Color.red(color), Color.green(color), Color.blue(color))
        canvas.drawLine(markerX, top, markerX, bottom, ptGuidePaint)

        ptDotPaint.color = Color.WHITE
        canvas.drawCircle(markerX, markerY, 9f, ptDotPaint)
        ptDotPaint.color = color
        canvas.drawCircle(markerX, markerY, 5f, ptDotPaint)

        labelPaint.color = color
        labelPaint.textAlign = Paint.Align.LEFT
        val labelX = min(max(markerX + 12f, left + 8f), right - 132f)
        val labelY = max(top + 30f, markerY - 12f)
        canvas.drawText("$label Pt ${pt.compareAxisText(2)}", labelX, labelY, labelPaint)
        labelPaint.color = Color.rgb(84, 103, 108)
    }
}

private fun Double.compareAxisText(digits: Int): String = "%.${digits}f".format(this).trimEnd('0').trimEnd('.')
