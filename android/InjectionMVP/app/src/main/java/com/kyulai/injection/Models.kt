package com.kyulai.injection

data class ModelInfo(
    val key: String,
    val label: String,
    val description: String,
    val available: Boolean,
) {
    val displayLabel: String
        get() = label.cleanModelLabel()
}

data class ModelsResponse(
    val sprueModels: List<ModelInfo>,
    val fillingModels: List<ModelInfo>,
)

data class DoeOption(
    val id: String,
    val values: Map<String, Any?>,
) {
    fun double(key: String): Double? = when (val value = values[key]) {
        is Number -> value.toDouble()
        is String -> value.toDoubleOrNull()
        else -> null
    }

    fun string(key: String): String? = values[key]?.toString()
}

data class PressurePoint(
    val timeS: Double,
    val pressureMPa: Double,
)

data class FillingSummary(
    val stats: Map<String, Double>,
    val bins: List<FillingBin>,
    val note: String,
)

data class FillingBin(
    val group: Int,
    val fromMPa: Double,
    val toMPa: Double,
    val volumeRatioPct: Double,
)

data class SpruePressureResult(
    val predictedMaxTimeS: Double,
    val predictedMaxPressureMPa: Double,
    val modelLabel: String,
    val fillingModelLabel: String,
    val curve: List<PressurePoint>,
    val fillingSummary: FillingSummary?,
    val notes: List<String>,
) {
    val displayModelLabel: String
        get() = modelLabel.cleanModelLabel()

    val displayFillingModelLabel: String
        get() = fillingModelLabel.cleanModelLabel()
}

private fun String.cleanModelLabel(): String {
    val trimmed = trim()
    val prefixes = listOf("Sprue Pressure", "Filling Pressure")
    val prefix = prefixes.firstOrNull { trimmed.startsWith(it, ignoreCase = true) }
    val normalized = (prefix?.let { trimmed.drop(it.length) } ?: trimmed)
        .trim(' ', '-', ':')
    return when (normalized.lowercase()) {
        "classical ml + pca" -> "ExtraTrees + PCA"
        "classical ml histogram" -> "ExtraTrees histogram"
        "gointmlp-style nn" -> "GointMLP NN"
        "deeponet operator nn" -> "DeepONet NN"
        "deeponet histogram nn" -> "DeepONet NN"
        else -> normalized
    }
}

data class InjectionInput(
    val geometryId: String,
    val processId: String,
    val sprueModelKey: String,
    val fillingModelKey: String,
    val lMm: Double,
    val wMm: Double,
    val tMm: Double,
    val dMm: Double,
    val rMm: Double?,
    val gateType: String,
    val gateWidthMm: Double,
    val gateHeightMm: Double,
    val meltTempC: Double,
    val moldTempC: Double,
    val injectionTimeS: Double,
    val packingPressureMPa: Double,
    val packingTimeS: Double,
)

object Defaults {
    const val SPRUE_MODEL_KEY = "sprue_classical"
    const val FILLING_MODEL_KEY = "filling_classical"
    const val DEFAULT_BASE_URL = "https://injection.luvelox.com"
}
