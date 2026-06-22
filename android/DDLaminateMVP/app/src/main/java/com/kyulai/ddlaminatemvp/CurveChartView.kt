package com.kyulai.ddlaminatemvp

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

class CurveChartView(context: Context) : View(context) {
    var points: List<CurvePoint> = emptyList()
        set(value) {
            field = value
            invalidate()
        }
    var predictedPt: Double? = null
        set(value) {
            field = value
            invalidate()
        }

    private val axisPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(112, 136, 140)
        strokeWidth = 2f
        style = Paint.Style.STROKE
    }
    private val gridPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(230, 237, 243)
        strokeWidth = 1.5f
        style = Paint.Style.STROKE
    }
    private val curvePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(0, 133, 128)
        strokeWidth = 5f
        style = Paint.Style.STROKE
    }
    private val ptPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(220, 38, 38)
        strokeWidth = 3f
        style = Paint.Style.STROKE
        pathEffect = DashPathEffect(floatArrayOf(10f, 8f), 0f)
    }
    private val dotPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(220, 38, 38)
        style = Paint.Style.FILL
    }
    private val labelPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(220, 38, 38)
        textSize = 28f
        isFakeBoldText = true
    }
    private val tickPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(84, 103, 108)
        textSize = 24f
        textAlign = Paint.Align.CENTER
        isFakeBoldText = true
    }
    private val axisValuePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(100, 113, 132)
        textSize = 20f
        textAlign = Paint.Align.CENTER
        isFakeBoldText = true
    }
    private val selectionPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(88, 12, 19, 21)
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
        color = Color.argb(92, 0, 133, 128)
        strokeWidth = 2f
        style = Paint.Style.STROKE
    }

    private var selectedIndex: Int? = null
    private var touchStartIndex: Int? = null
    private var touchMoved = false
    private var touchStartX = 0f
    private var touchStartY = 0f

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val frame = computePlotFrame()
        val left = frame.left
        val top = frame.top
        val right = frame.right
        val bottom = frame.bottom
        if (points.size < 2) {
            drawBaseAxes(canvas, left, top, right, bottom)
            return
        }

        val minX = points.minOf { it.displacement }
        val maxX = max(points.maxOf { it.displacement }, minX + 0.000001)
        val minY = min(0.0, points.minOf { it.force })
        val bilinearFit = buildBilinearFit(points, predictedPt)
        val yValues = points.map { it.force }.toMutableList()
        predictedPt?.takeIf { it.isFinite() }?.let { yValues.add(it) }
        bilinearFit?.let { fit ->
            yValues.add(fit.firstLine.y(fit.firstStartX))
            yValues.add(fit.firstLine.y(fit.firstEndX))
            yValues.add(fit.secondLine.y(fit.secondStartX))
            yValues.add(fit.secondLine.y(fit.secondEndX))
            yValues.add(fit.kink.force)
        }
        val maxY = max((yValues.maxOrNull() ?: points.maxOf { it.force }) * 1.06, minY + 0.000001)

        fun x(value: Double) = left + (((value - minX) / (maxX - minX)) * (right - left)).toFloat()
        fun y(value: Double): Float {
            val ratio = (value - minY) / max(maxY - minY, 0.000001)
            return bottom - (ratio * (bottom - top)).toFloat()
        }

        drawAxisTicks(canvas, left, top, right, bottom, minX, maxX, minY, maxY, ::x, ::y)
        drawBaseAxes(canvas, left, top, right, bottom)

        bilinearFit?.let { drawBilinearFit(canvas, it, ::x, ::y, top, bottom) }

        val path = Path()
        points.forEachIndexed { index, point ->
            if (index == 0) path.moveTo(x(point.displacement), y(point.force))
            else path.lineTo(x(point.displacement), y(point.force))
        }
        canvas.drawPath(path, curvePaint)

        bilinearFit?.let { fit ->
            val marker = fit.predictedPoint ?: fit.kink
            val markerX = x(marker.displacement)
            val markerY = y(marker.force)
            canvas.drawCircle(markerX, markerY, 8f, dotPaint)
            canvas.drawCircle(markerX, markerY, 8f, Paint(Paint.ANTI_ALIAS_FLAG).apply {
                color = Color.WHITE
                strokeWidth = 3f
                style = Paint.Style.STROKE
            })
            canvas.drawText(context.getString(R.string.pt_marker_format, marker.force), min(markerX + 12f, right - 110f), max(top + 30f, markerY - 12f), labelPaint)
        }

        val selected = selectedIndex?.let { points.getOrNull(it) } ?: return
        val selectedX = x(selected.displacement)
        val selectedY = y(selected.force)
        canvas.drawLine(selectedX, top, selectedX, bottom, selectionPaint)
        canvas.drawLine(left, selectedY, right, selectedY, selectionPaint)
        canvas.drawCircle(selectedX, selectedY, 12f, selectionDotPaint)
        canvas.drawCircle(selectedX, selectedY, 12f, curvePaint)

        val firstLine = "x ${selected.displacement.axisText(4)}"
        val secondLine = "y ${selected.force.axisText(2)}"
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
            MotionEvent.ACTION_DOWN -> {
                touchStartIndex = selectedIndex
                touchMoved = false
                touchStartX = event.x
                touchStartY = event.y
                selectedIndex = nearestIndex(event.x)
                invalidate()
                parent?.requestDisallowInterceptTouchEvent(true)
                return true
            }
            MotionEvent.ACTION_MOVE -> {
                if (abs(event.x - touchStartX) > 12f || abs(event.y - touchStartY) > 12f) {
                    touchMoved = true
                }
                selectedIndex = nearestIndex(event.x)
                invalidate()
                parent?.requestDisallowInterceptTouchEvent(true)
                return true
            }
            MotionEvent.ACTION_UP -> {
                val nearest = nearestIndex(event.x)
                selectedIndex = if (!touchMoved && touchStartIndex != null) null else nearest
                touchStartIndex = null
                touchMoved = false
                invalidate()
                parent?.requestDisallowInterceptTouchEvent(false)
                return true
            }
            MotionEvent.ACTION_CANCEL -> {
                touchStartIndex = null
                touchMoved = false
                parent?.requestDisallowInterceptTouchEvent(false)
                return true
            }
        }
        return true
    }

    private fun nearestIndex(touchX: Float): Int {
        val frame = computePlotFrame()
        val left = frame.left
        val right = frame.right
        val minX = points.minOf { it.displacement }
        val maxX = max(points.maxOf { it.displacement }, minX + 0.000001)
        fun x(value: Double) = left + (((value - minX) / (maxX - minX)) * (right - left)).toFloat()
        return points.indices.minByOrNull { abs(x(points[it].displacement) - touchX) } ?: 0
    }

    private fun computePlotFrame(): PlotFrame {
        val outerLeft = 82f
        val outerTop = 52f
        val outerRight = width - 24f
        val outerBottom = height - 80f
        val availableWidth = max(1f, outerRight - outerLeft)
        val availableHeight = max(1f, outerBottom - outerTop)
        val targetRatio = 5f / 3f
        var plotWidth = availableWidth
        var plotHeight = plotWidth / targetRatio
        if (plotHeight > availableHeight) {
            plotHeight = availableHeight
            plotWidth = plotHeight * targetRatio
        }
        val left = outerLeft + (availableWidth - plotWidth) / 2f
        val top = outerTop + (availableHeight - plotHeight) / 2f
        return PlotFrame(left, top, left + plotWidth, top + plotHeight)
    }

    private fun drawBaseAxes(canvas: Canvas, left: Float, top: Float, right: Float, bottom: Float) {
        canvas.drawLine(left, bottom, right, bottom, axisPaint)
        canvas.drawLine(left, top, left, bottom, axisPaint)
        tickPaint.textAlign = Paint.Align.LEFT
        canvas.drawText(context.getString(R.string.axis_force), left, top - 16f, tickPaint)
        tickPaint.textAlign = Paint.Align.CENTER
        canvas.drawText(context.getString(R.string.axis_displacement), (left + right) / 2f, height - 14f, tickPaint)
    }

    private fun drawAxisTicks(
        canvas: Canvas,
        left: Float,
        top: Float,
        right: Float,
        bottom: Float,
        minX: Double,
        maxX: Double,
        minY: Double,
        maxY: Double,
        x: (Double) -> Float,
        y: (Double) -> Float,
    ) {
        val xTicks = axisTicks(minX, maxX, 6)
        val yTicks = axisTicks(minY, maxY, 6)
        xTicks.drop(1).dropLast(1).forEach { value ->
            val tickX = x(value)
            canvas.drawLine(tickX, top, tickX, bottom, gridPaint)
        }
        yTicks.drop(1).dropLast(1).forEach { value ->
            val tickY = y(value)
            canvas.drawLine(left, tickY, right, tickY, gridPaint)
        }

        axisValuePaint.textAlign = Paint.Align.RIGHT
        yTicks.forEach { value ->
            val tickY = y(value) + axisValuePaint.textSize * 0.34f
            canvas.drawText(value.axisTickText(2), left - 8f, tickY, axisValuePaint)
        }
        axisValuePaint.textAlign = Paint.Align.CENTER
        xTicks.forEach { value ->
            canvas.drawText(value.axisTickText(4), x(value), bottom + 28f, axisValuePaint)
        }
    }

    private fun axisTicks(min: Double, max: Double, count: Int): List<Double> {
        if (count <= 1) return listOf(min)
        val span = max - min
        return List(count) { index -> min + span * index / (count - 1).toDouble() }
    }

    private fun drawBilinearFit(
        canvas: Canvas,
        fit: BilinearFit,
        x: (Double) -> Float,
        y: (Double) -> Float,
        top: Float,
        bottom: Float,
    ) {
        val slopePath = Path().apply {
            moveTo(x(fit.firstStartX), y(fit.firstLine.y(fit.firstStartX)))
            lineTo(x(fit.firstEndX), y(fit.firstLine.y(fit.firstEndX)))
            moveTo(x(fit.secondStartX), y(fit.secondLine.y(fit.secondStartX)))
            lineTo(x(fit.secondEndX), y(fit.secondLine.y(fit.secondEndX)))
        }
        canvas.drawPath(slopePath, ptPaint)

        val kinkX = x(fit.kink.displacement)
        val guidePaint = Paint(ptPaint).apply {
            color = Color.rgb(124, 58, 237)
            strokeWidth = 2.5f
            pathEffect = DashPathEffect(floatArrayOf(14f, 8f), 0f)
        }
        canvas.drawLine(kinkX, top, kinkX, bottom, guidePaint)
    }
}

private data class PlotFrame(
    val left: Float,
    val top: Float,
    val right: Float,
    val bottom: Float,
)

private fun Double.axisText(digits: Int): String = "%.${digits}f".format(this).trimEnd('0').trimEnd('.')

private fun Double.axisTickText(smallValueDigits: Int): String {
    if (!isFinite()) return "0"
    val absolute = abs(this)
    val digits = when {
        absolute >= 100.0 -> 0
        absolute >= 10.0 -> 1
        absolute >= 1.0 -> 2
        else -> smallValueDigits
    }
    val text = axisText(digits)
    return if (text == "-0") "0" else text
}

private fun buildBilinearFit(points: List<CurvePoint>, predictedPtValue: Double?): BilinearFit? {
    val predictedPt = predictedPtValue ?: return null
    if (!predictedPt.isFinite()) return null
    val ptOnCurve = pointAtForce(points, predictedPt) ?: return null
    val minX = points.minOfOrNull { it.displacement } ?: return null
    val maxX = points.maxOfOrNull { it.displacement } ?: return null
    val spanX = max(maxX - minX, 1e-9)

    val firstFitSamples = points.filter { point ->
        point.displacement > minX + spanX * 0.01 &&
            point.displacement <= max(ptOnCurve.displacement * 0.92, minX + spanX * 0.18) &&
            point.force <= predictedPt * 0.82
    }
    val firstFallbackEnd = max(8, (points.size * 0.28).toInt())
    val firstSamples = if (firstFitSamples.size >= 4) {
        firstFitSamples
    } else {
        points.drop(1).take(max(0, min(firstFallbackEnd - 1, points.size - 1)))
    }
    val firstFit = linearFit(firstSamples) ?: return null

    val tailStart = max(ptOnCurve.displacement + spanX * 0.08, minX + spanX * 0.58)
    val secondFitSamples = points.filter { it.displacement >= tailStart }
    val secondFallbackStart = max(0, (points.size * 0.72).toInt())
    val secondSamples = if (secondFitSamples.size >= 4) secondFitSamples else points.drop(secondFallbackStart)
    val secondFit = linearFit(secondSamples) ?: return null
    if (firstFit.slope <= 0 || secondFit.slope <= 0) return null

    val minKinkX = minX + spanX * 0.08
    val maxKinkX = minX + spanX * 0.78
    val rawIntersection = lineIntersection(firstFit, secondFit)
    val rawIsUsable = rawIntersection != null &&
        rawIntersection.displacement >= minKinkX &&
        rawIntersection.displacement <= maxKinkX &&
        rawIntersection.force > 0
    val fallbackKinkX = ptOnCurve.displacement.coerceIn(minKinkX, maxKinkX)
    var kinkX = if (rawIsUsable) rawIntersection!!.displacement else fallbackKinkX
    var kinkForce = if (rawIsUsable) rawIntersection!!.force else firstFit.y(fallbackKinkX)
    if (!kinkForce.isFinite() || kinkForce <= 0) kinkForce = predictedPt

    val leftEnvelopeSamples = points.filter {
        it.displacement < kinkX - spanX * 0.006 && it.force <= kinkForce
    }
    val rightEnvelopeSamples = points.filter {
        it.displacement > kinkX + spanX * 0.006 && it.force >= kinkForce * 0.96
    }
    val firstSlope = leftUpperEnvelopeSlope(leftEnvelopeSamples, kinkX, kinkForce, firstFit.slope)
    val secondSlope = rightUpperEnvelopeSlope(rightEnvelopeSamples, kinkX, kinkForce, secondFit.slope)
    val firstLine = FittedLine(firstSlope, kinkForce - firstSlope * kinkX)
    val secondLine = FittedLine(secondSlope, kinkForce - secondSlope * kinkX)
    val finalIntersection = lineIntersection(firstLine, secondLine)
    if (
        finalIntersection != null &&
        finalIntersection.displacement >= minKinkX &&
        finalIntersection.displacement <= maxKinkX &&
        finalIntersection.force > 0
    ) {
        kinkX = finalIntersection.displacement
        kinkForce = finalIntersection.force
    } else {
        kinkX = fallbackKinkX
        kinkForce = firstFit.y(fallbackKinkX)
        if (!kinkForce.isFinite() || kinkForce <= 0) kinkForce = predictedPt
    }
    val finalFirstLine = FittedLine(firstSlope, kinkForce - firstSlope * kinkX)
    val finalSecondLine = FittedLine(secondSlope, kinkForce - secondSlope * kinkX)

    return BilinearFit(
        kink = CurveCoordinate(kinkX, kinkForce),
        predictedPoint = CurveCoordinate(ptOnCurve.displacement, predictedPt),
        firstLine = finalFirstLine,
        secondLine = finalSecondLine,
        firstStartX = minX,
        firstEndX = min(maxX, kinkX + spanX * 0.045),
        secondStartX = max(minX, kinkX - spanX * 0.025),
        secondEndX = maxX,
    )
}

private fun pointAtForce(points: List<CurvePoint>, force: Double): CurveCoordinate? {
    val first = points.firstOrNull() ?: return null
    if (force <= first.force) return CurveCoordinate(first.displacement, first.force)
    for (index in 1 until points.size) {
        val previous = points[index - 1]
        val current = points[index]
        val low = min(previous.force, current.force)
        val high = max(previous.force, current.force)
        if (force < low || force > high) continue
        val delta = current.force - previous.force
        if (delta == 0.0) return CurveCoordinate(current.displacement, current.force)
        val ratio = (force - previous.force) / delta
        return CurveCoordinate(
            previous.displacement + ratio * (current.displacement - previous.displacement),
            force,
        )
    }
    val last = points.lastOrNull() ?: return null
    return CurveCoordinate(last.displacement, last.force)
}

private fun linearFit(samples: List<CurvePoint>): FittedLine? {
    val valid = samples.filter { it.displacement.isFinite() && it.force.isFinite() }
    if (valid.size < 2) return null
    val meanX = valid.sumOf { it.displacement } / valid.size
    val meanY = valid.sumOf { it.force } / valid.size
    val numerator = valid.sumOf { (it.displacement - meanX) * (it.force - meanY) }
    val denominator = valid.sumOf { (it.displacement - meanX) * (it.displacement - meanX) }
    if (abs(denominator) < 1e-12) return null
    val slope = numerator / denominator
    return FittedLine(slope, meanY - slope * meanX)
}

private fun lineIntersection(firstLine: FittedLine, secondLine: FittedLine): CurveCoordinate? {
    val denominator = firstLine.slope - secondLine.slope
    if (!denominator.isFinite() || abs(denominator) < 1e-9) return null
    val displacement = (secondLine.intercept - firstLine.intercept) / denominator
    val force = firstLine.y(displacement)
    if (!displacement.isFinite() || !force.isFinite()) return null
    return CurveCoordinate(displacement, force)
}

private fun rightUpperEnvelopeSlope(
    points: List<CurvePoint>,
    kinkX: Double,
    kinkForce: Double,
    proposedSlope: Double,
): Double {
    var requiredSlope = proposedSlope
    points.forEach { point ->
        val deltaX = point.displacement - kinkX
        if (deltaX > 1e-9) {
            requiredSlope = max(requiredSlope, (point.force - kinkForce) / deltaX)
        }
    }
    return max(requiredSlope * 1.015, proposedSlope)
}

private fun leftUpperEnvelopeSlope(
    points: List<CurvePoint>,
    kinkX: Double,
    kinkForce: Double,
    proposedSlope: Double,
): Double {
    var cappedSlope = proposedSlope
    points.forEach { point ->
        val deltaX = kinkX - point.displacement
        if (deltaX > 1e-9) {
            val upperSlope = (kinkForce - point.force) / deltaX
            if (upperSlope.isFinite() && upperSlope > 0) {
                cappedSlope = min(cappedSlope, upperSlope * 0.985)
            }
        }
    }
    return max(cappedSlope, proposedSlope * 0.72)
}

private data class CurveCoordinate(
    val displacement: Double,
    val force: Double,
)

private data class FittedLine(
    val slope: Double,
    val intercept: Double,
) {
    fun y(x: Double): Double = slope * x + intercept
}

private data class BilinearFit(
    val kink: CurveCoordinate,
    val predictedPoint: CurveCoordinate?,
    val firstLine: FittedLine,
    val secondLine: FittedLine,
    val firstStartX: Double,
    val firstEndX: Double,
    val secondStartX: Double,
    val secondEndX: Double,
)
