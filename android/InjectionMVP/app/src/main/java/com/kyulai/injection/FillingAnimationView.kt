package com.kyulai.injection

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.os.SystemClock
import android.view.View
import kotlin.math.abs
import kotlin.math.exp
import kotlin.math.max
import kotlin.math.min
import kotlin.math.pow

class FillingAnimationView(context: Context) : View(context) {
    var summary: FillingSummary? = null
        set(value) {
            field = value
            invalidate()
        }
    var lengthMm: Double = 154.01
    var widthMm: Double = 97.42
    var diameterMm: Double = 17.61
    var gateWidthMm: Double = 10.0

    private val durationMs = 2_800L
    private val frameDelayMs = 66L
    private val previewProgress = 0.65
    private var isPlaying = false
    private var playbackStartMs = 0L
    private val outlinePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(91, 109, 140)
        strokeWidth = 2f
        style = Paint.Style.STROKE
    }
    private val holePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(238, 255, 255, 255)
        style = Paint.Style.FILL
    }
    private val gatePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(220, 38, 38)
        style = Paint.Style.FILL
    }
    private val cellPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
    }
    private val labelPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(17, 24, 39)
        textSize = 24f
        isFakeBoldText = true
        textAlign = Paint.Align.RIGHT
    }
    private val controlPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(210, 17, 24, 39)
        style = Paint.Style.FILL
    }
    private val controlIconPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        style = Paint.Style.FILL
    }

    init {
        isClickable = true
        setOnClickListener {
            if (isPlaying) {
                isPlaying = false
                invalidate()
            } else {
                playOnce()
            }
        }
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val measuredWidth = MeasureSpec.getSize(widthMeasureSpec)
        val desiredHeight = (measuredWidth * 360f / 760f).toInt()
        setMeasuredDimension(measuredWidth, desiredHeight)
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val data = summary ?: return
        if (data.bins.isEmpty()) return

        canvas.save()
        canvas.scale(width / 760f, height / 360f)
        val progress = if (isPlaying) {
            min(1.0, (SystemClock.uptimeMillis() - playbackStartMs).toDouble() / durationMs)
        } else {
            previewProgress
        }
        val canvasWidth = 760f
        val canvasHeight = 360f
        val margin = 54f
        val maxPartW = canvasWidth - margin * 2f
        val maxPartH = canvasHeight - 92f
        val scale = min(maxPartW / max(lengthMm, 1.0).toFloat(), maxPartH / max(widthMm, 1.0).toFloat())
        val partW = lengthMm.toFloat() * scale
        val partH = widthMm.toFloat() * scale
        val x0 = (canvasWidth - partW) / 2f
        val y0 = (canvasHeight - partH) / 2f + 10f
        val holeR = max(diameterMm.toFloat() * scale / 2f, 3f)
        val holeX = x0 + partW / 2f
        val holeY = y0 + partH / 2f
        val front = min(1.06, progress * 1.18)
        val maxPressure = max(data.stats["max_MPa"] ?: 1.0, 0.000001)
        val step = 5f

        canvas.save()
        val partPath = Path().apply {
            fillType = Path.FillType.EVEN_ODD
            addRect(x0, y0, x0 + partW, y0 + partH, Path.Direction.CW)
            addCircle(holeX, holeY, holeR, Path.Direction.CW)
        }
        canvas.clipPath(partPath)
        var y = y0
        while (y < y0 + partH) {
            var x = x0
            while (x < x0 + partW) {
                val localX = ((x - x0) / max(partW, 1f)).toDouble()
                val localY = abs(((y - (y0 + partH / 2f)) / max(partH / 2f, 1f)).toDouble())
                if (localX <= front) {
                    val gateHotspot = exp(-((localX / 0.16).pow(2) + (localY / 0.46).pow(2)))
                    val wake = max(0.0, 1.0 - (front - localX) * 2.2) * 0.18
                    val fraction = min(1.0, max(0.0, localX.pow(1.45) - gateHotspot * 0.08 - wake))
                    val pressure = pressureFromDistribution(data, fraction)
                    cellPaint.color = fillingColor(min(1.0, max(0.0, pressure / maxPressure)))
                    canvas.drawRect(x, y, x + step + 1f, y + step + 1f, cellPaint)
                }
                x += step
            }
            y += step
        }
        canvas.restore()

        canvas.drawRect(x0, y0, x0 + partW, y0 + partH, outlinePaint)
        canvas.drawCircle(holeX, holeY, holeR, holePaint)
        canvas.drawCircle(holeX, holeY, holeR, outlinePaint)
        val gateH = max(gateWidthMm.toFloat() * scale, 12f)
        canvas.drawRect(x0 - 24f, y0 + partH / 2f - gateH / 2f, x0, y0 + partH / 2f + gateH / 2f, gatePaint)

        val pressureNow = (data.stats["max_MPa"] ?: 0.0) * min(progress * 1.1, 1.0)
        canvas.drawText("${pressureNow.numberText(1)} MPa", x0 + partW, canvasHeight - 18f, labelPaint)
        drawPlaybackControl(canvas, canvasWidth, canvasHeight)
        canvas.restore()

        if (isPlaying) {
            if (progress >= 1.0) {
                isPlaying = false
                invalidate()
            } else {
                postInvalidateDelayed(frameDelayMs)
            }
        }
    }

    private fun playOnce() {
        isPlaying = true
        playbackStartMs = SystemClock.uptimeMillis()
        invalidate()
    }

    private fun drawPlaybackControl(canvas: Canvas, canvasWidth: Float, canvasHeight: Float) {
        val cx = canvasWidth - 34f
        val cy = canvasHeight - 34f
        canvas.drawCircle(cx, cy, 18f, controlPaint)
        if (isPlaying) {
            canvas.drawRect(cx - 7f, cy - 8f, cx - 3f, cy + 8f, controlIconPaint)
            canvas.drawRect(cx + 3f, cy - 8f, cx + 7f, cy + 8f, controlIconPaint)
        } else {
            val icon = Path().apply {
                moveTo(cx - 5f, cy - 9f)
                lineTo(cx - 5f, cy + 9f)
                lineTo(cx + 9f, cy)
                close()
            }
            canvas.drawPath(icon, controlIconPaint)
        }
    }

    private fun pressureFromDistribution(summary: FillingSummary, fraction: Double): Double {
        val bins = summary.bins.sortedByDescending { (it.fromMPa + it.toMPa) / 2.0 }
        val total = max(bins.sumOf { it.volumeRatioPct }, 0.000001)
        val target = min(100.0, max(0.0, fraction * 100.0))
        var cumulative = 0.0
        bins.forEach { bin ->
            cumulative += bin.volumeRatioPct / total * 100.0
            if (target <= cumulative) return (bin.fromMPa + bin.toMPa) / 2.0
        }
        return bins.lastOrNull()?.let { (it.fromMPa + it.toMPa) / 2.0 } ?: 0.0
    }

    private fun fillingColor(value: Double): Int {
        val stops = listOf(
            0.0 to Triple(0x07, 0x4b, 0xd8),
            0.25 to Triple(0x00, 0x92, 0xff),
            0.42 to Triple(0x12, 0xdf, 0xe3),
            0.56 to Triple(0x00, 0xd4, 0x5b),
            0.70 to Triple(0xd8, 0xea, 0x00),
            0.84 to Triple(0xff, 0x8a, 0x00),
            1.0 to Triple(0xd4, 0x00, 0x00),
        )
        val clamped = min(1.0, max(0.0, value))
        for (index in 0 until stops.lastIndex) {
            val start = stops[index]
            val end = stops[index + 1]
            if (clamped >= start.first && clamped <= end.first) {
                val t = (clamped - start.first) / max(0.000001, end.first - start.first)
                return Color.rgb(
                    (start.second.first + (end.second.first - start.second.first) * t).toInt(),
                    (start.second.second + (end.second.second - start.second.second) * t).toInt(),
                    (start.second.third + (end.second.third - start.second.third) * t).toInt(),
                )
            }
        }
        return Color.rgb(0xd4, 0x00, 0x00)
    }
}

private fun Double.numberText(digits: Int): String = "%.${digits}f".format(this).trimEnd('0').trimEnd('.')
