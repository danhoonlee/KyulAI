package com.luvelox.app

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.LinearGradient
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RectF
import android.graphics.Shader
import android.util.AttributeSet
import android.view.View
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin

class PlyStackPreviewView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : View(context, attrs) {
    private var sequence: List<PreviewPly> = buildSequence("Case2", 30, -30)

    private val fillPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
    }
    private val strokePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeJoin = Paint.Join.ROUND
    }
    private val textPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(244, 255, 23)
        typeface = AppFonts.typeface(context, android.graphics.Typeface.BOLD)
    }

    val plyCount: Int
        get() = sequence.size

    fun updateStack(caseName: String, theta1: Int, theta2: Int) {
        sequence = buildSequence(caseName, theta1, theta2)
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        if (width == 0 || height == 0) return

        val scale = min(width / CANVAS_WIDTH, height / CANVAS_HEIGHT)
        val offsetX = (width - CANVAS_WIDTH * scale) / 2f
        val offsetY = (height - CANVAS_HEIGHT * scale) / 2f

        canvas.save()
        canvas.translate(offsetX, offsetY)
        canvas.scale(scale, scale)
        drawScene(canvas)
        sequence.forEachIndexed { index, ply ->
            drawPly(canvas, ply, index)
        }
        canvas.restore()
    }

    private fun drawScene(canvas: Canvas) {
        fillPaint.shader = LinearGradient(
            34f,
            34f,
            1126f,
            734f,
            intArrayOf(Color.rgb(28, 51, 78), Color.rgb(47, 73, 102), Color.rgb(137, 152, 168)),
            null,
            Shader.TileMode.CLAMP,
        )
        canvas.drawRoundRect(RectF(34f, 34f, 1126f, 734f), 8f, 8f, fillPaint)
        fillPaint.shader = null

        strokePaint.color = Color.argb(56, 237, 247, 255)
        strokePaint.strokeWidth = 1f
        listOf(
            118f to 42f to (992f to 524f),
            70f to 94f to (944f to 576f),
            22f to 146f to (896f to 628f),
            214f to 660f to (1088f to 178f),
            48f to 536f to (742f to 150f),
            122f to 578f to (816f to 192f),
            196f to 620f to (890f to 234f),
            270f to 662f to (964f to 276f),
        ).forEach { (start, end) ->
            canvas.drawLine(start.first, start.second, end.first, end.second, strokePaint)
        }

        fillPaint.color = Color.rgb(185, 151, 127)
        canvas.drawPath(pathOf(98f to 456f, 574f to 704f, 1018f to 458f, 542f to 210f), fillPaint)
        fillPaint.color = Color.rgb(200, 167, 142)
        canvas.drawPath(pathOf(98f to 456f, 574f to 704f, 574f to 728f, 98f to 480f), fillPaint)
        fillPaint.color = Color.rgb(152, 118, 95)
        canvas.drawPath(pathOf(574f to 704f, 1018f to 458f, 1018f to 482f, 574f to 728f), fillPaint)
    }

    private fun drawPly(canvas: Canvas, ply: PreviewPly, index: Int) {
        val originX = 555f - index * 30f
        val originY = 470f - index * 28f
        val palette = paletteFor(ply.family)

        canvas.save()
        canvas.translate(originX, originY)

        val top = pathOf(0f to 130f, 138f to 210f, 420f to 52f, 282f to -28f)
        fillPaint.color = palette.sideA
        canvas.drawPath(pathOf(0f to 130f, 138f to 210f, 138f to 230f, 0f to 150f), fillPaint)
        fillPaint.color = palette.sideB
        canvas.drawPath(pathOf(138f to 210f, 420f to 52f, 420f to 72f, 138f to 230f), fillPaint)
        fillPaint.shader = LinearGradient(0f, 130f, 420f, 52f, palette.topA, palette.topB, Shader.TileMode.CLAMP)
        canvas.drawPath(top, fillPaint)
        fillPaint.shader = null

        strokePaint.color = palette.edge
        strokePaint.strokeWidth = 1.4f
        canvas.drawPath(top, strokePaint)

        drawAngleHatch(canvas, top, ply.angle)

        strokePaint.color = Color.argb(235, 244, 255, 23)
        strokePaint.strokeWidth = 2.2f
        canvas.drawLine(400f, 61f, 426f, 51f, strokePaint)

        fillPaint.color = Color.argb(245, 16, 32, 51)
        val labelRect = RectF(426f, 36f, 552f, 70f)
        canvas.drawRoundRect(labelRect, 7f, 7f, fillPaint)
        strokePaint.color = Color.rgb(244, 255, 23)
        strokePaint.strokeWidth = 1.8f
        canvas.drawRoundRect(labelRect, 7f, 7f, strokePaint)

        textPaint.textSize = 22f
        canvas.drawText("Ply-${index + 1}", labelRect.left + 11f, labelRect.top + 24f, textPaint)
        canvas.restore()
    }

    private fun drawAngleHatch(canvas: Canvas, top: Path, angle: Int) {
        val radians = Math.toRadians((-angle).toDouble())
        val directionX = cos(radians).toFloat()
        val directionY = sin(radians).toFloat()
        val normalX = -directionY
        val normalY = directionX
        val centerX = 210f
        val centerY = 91f
        val lineLength = 560f

        canvas.save()
        canvas.clipPath(top)
        strokePaint.color = if (angle >= 0) Color.rgb(5, 150, 105) else Color.rgb(180, 35, 24)
        strokePaint.strokeWidth = 3f
        for (step in -18..18) {
            val distance = step * 24f
            val midpointX = centerX + normalX * distance
            val midpointY = centerY + normalY * distance
            canvas.drawLine(
                midpointX - directionX * lineLength / 2f,
                midpointY - directionY * lineLength / 2f,
                midpointX + directionX * lineLength / 2f,
                midpointY + directionY * lineLength / 2f,
                strokePaint,
            )
        }
        canvas.restore()
    }

    private fun pathOf(vararg points: Pair<Float, Float>): Path {
        val path = Path()
        points.firstOrNull()?.let { first ->
            path.moveTo(first.first, first.second)
            points.drop(1).forEach { path.lineTo(it.first, it.second) }
            path.close()
        }
        return path
    }

    private fun paletteFor(family: PreviewPly.Family): PlyPalette {
        return when (family) {
            PreviewPly.Family.THETA1 -> PlyPalette(
                topA = Color.rgb(154, 168, 237),
                topB = Color.rgb(101, 122, 212),
                sideA = Color.rgb(128, 143, 212),
                sideB = Color.rgb(94, 112, 186),
                edge = Color.rgb(78, 96, 170),
            )
            PreviewPly.Family.THETA2 -> PlyPalette(
                topA = Color.rgb(224, 189, 161),
                topB = Color.rgb(188, 143, 112),
                sideA = Color.rgb(202, 166, 139),
                sideB = Color.rgb(167, 126, 99),
                edge = Color.rgb(142, 104, 79),
            )
        }
    }

    companion object {
        private const val CANVAS_WIDTH = 1160f
        private const val CANVAS_HEIGHT = 760f

        private fun buildSequence(caseName: String, theta1: Int, theta2: Int): List<PreviewPly> {
            val theta1Pair = anglePair(theta1, PreviewPly.Family.THETA1)
            val theta2Pair = anglePair(theta2, PreviewPly.Family.THETA2)
            val theta1Inverse = inversePair(theta1, PreviewPly.Family.THETA1)
            val theta2Inverse = inversePair(theta2, PreviewPly.Family.THETA2)
            return when (caseName) {
                "Case3" -> repeated(theta1Pair + theta2Pair + theta1Inverse + theta2Inverse, 2)
                "Case4" -> repeated(theta1Pair + theta2Pair, 2) + repeated(theta1Inverse + theta2Inverse, 2)
                else -> repeated(theta1Pair + theta2Pair, 4)
            }
        }

        private fun anglePair(angle: Int, family: PreviewPly.Family): List<PreviewPly> {
            val value = angle.coerceIn(-90, 90)
            return listOf(PreviewPly(value, family), PreviewPly(-value, family))
        }

        private fun inversePair(angle: Int, family: PreviewPly.Family): List<PreviewPly> {
            val value = angle.coerceIn(-90, 90)
            return listOf(PreviewPly(-value, family), PreviewPly(value, family))
        }

        private fun repeated(pattern: List<PreviewPly>, count: Int): List<PreviewPly> {
            return List(count) { pattern }.flatten()
        }
    }
}

private data class PreviewPly(
    val angle: Int,
    val family: Family,
) {
    enum class Family {
        THETA1,
        THETA2,
    }
}

private data class PlyPalette(
    val topA: Int,
    val topB: Int,
    val sideA: Int,
    val sideB: Int,
    val edge: Int,
)

fun Int.thetaReadout(): String = "${if (this > 0) "+" else ""}${coerceIn(-90, 90)}\u00B0"
