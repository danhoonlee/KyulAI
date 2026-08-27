package com.imperialax.app

import android.content.Context
import android.graphics.Typeface
import android.widget.TextView

object AppFonts {
    fun typeface(context: Context, style: Int): Typeface {
        val base = when (style) {
            Typeface.BOLD -> context.resources.getFont(R.font.pretendard_bold)
            Typeface.ITALIC, Typeface.BOLD_ITALIC -> context.resources.getFont(R.font.pretendard_regular)
            else -> context.resources.getFont(R.font.pretendard_regular)
        }
        return Typeface.create(base, style)
    }

    fun semibold(context: Context): Typeface {
        return context.resources.getFont(R.font.pretendard_semibold)
    }
}

fun TextView.useAppFont(style: Int = Typeface.NORMAL) {
    typeface = AppFonts.typeface(context, style)
}
