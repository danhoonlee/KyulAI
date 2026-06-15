package com.kyulai.ddlaminatemvp

data class CurvePoint(
    val displacement: Double,
    val force: Double,
)

data class ForecastResult(
    val predictedType: Int,
    val confidence: Double?,
    val predictedPt: Double?,
    val predictedMaxForce: Double?,
    val predictedMaxDisplacement: Double?,
    val modelLabel: String,
    val inputMode: String,
    val probabilities: Map<String, Double>,
    val curve: List<CurvePoint>,
    val xai: ForecastXai?,
    val notes: List<String>,
) {
    val displayModelLabel: String
        get() = modelLabel.cleanModelLabel()

    val predictedPtDisplacement: Double?
        get() = curve.displacementAtForce(predictedPt)
}

data class ForecastXai(
    val featureSet: String,
    val method: String,
    val summary: String,
    val topFeatures: List<ForecastXaiFeature>,
)

data class ForecastXaiFeature(
    val name: String,
    val label: String,
    val category: String,
    val importance: Double,
    val explanation: String,
)

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
    val responseModels: List<ModelInfo>,
)

object Defaults {
    const val RESPONSE_MODEL_KEY = "response_surrogate_physics"
    const val DEFAULT_BASE_URL = "https://laminate.luvelox.com"
}

fun String.cleanModelLabel(): String {
    val cleaned = trim()
    return when (cleaned.lowercase()) {
        "laminate forecast - cases 2/3/4" -> "ExtraTrees + PCA"
        "laminate forecast - gointmlp nn + clt (legacy case3/4)" -> "GointMLP NN"
        "estimated response - extratrees + pca + clt" -> "ExtraTrees + PCA"
        "estimated response - gointmlp nn + clt" -> "GointMLP NN"
        "theta + case - randomforest" -> "RandomForest"
        "theta + case - gointmlp-style nn" -> "GointMLP NN"
        "curve + metadata - extratrees" -> "ExtraTrees"
        "curve + metadata - goint sequence nn" -> "GRU + GointMLP NN"
        "extra trees + pca" -> "ExtraTrees + PCA"
        "extratrees + pca" -> "ExtraTrees + PCA"
        "gointmlp-style nn" -> "GointMLP NN"
        "laminate forecast - tree (theta)" -> "Laminate Forecast - Tree (Theta)"
        "laminate forecast - gointmlp (theta)" -> "Laminate Forecast - GointMLP (Theta)"
        "laminate forecast - tree + physics xai" -> "Laminate Forecast - Tree + Physics XAI"
        "laminate forecast - gointmlp + physics xai" -> "Laminate Forecast - GointMLP + Physics XAI"
        else -> cleaned
    }
}

fun String.cleanModelKeyLabel(): String {
    return when (this) {
        "response_surrogate" -> "ExtraTrees + PCA"
        "response_goint" -> "GointMLP NN"
        "response_surrogate_physics" -> "Laminate Forecast - Tree + Physics XAI"
        "response_goint_physics" -> "Laminate Forecast - GointMLP + Physics XAI"
        "theta_classical" -> "RandomForest"
        "theta_goint" -> "GointMLP NN"
        "curve_classical" -> "ExtraTrees"
        "curve_goint" -> "GRU + GointMLP NN"
        else -> cleanModelLabel()
    }
}

fun List<CurvePoint>.displacementAtForce(targetForce: Double?): Double? {
    val force = targetForce?.takeIf { it.isFinite() } ?: return null
    val first = firstOrNull() ?: return null
    if (force <= first.force) return first.displacement
    for (index in 1 until size) {
        val previous = this[index - 1]
        val current = this[index]
        val low = minOf(previous.force, current.force)
        val high = maxOf(previous.force, current.force)
        if (force < low || force > high) continue
        val forceDelta = current.force - previous.force
        if (forceDelta == 0.0) return current.displacement
        val ratio = (force - previous.force) / forceDelta
        return previous.displacement + ratio * (current.displacement - previous.displacement)
    }
    return lastOrNull()?.displacement
}
