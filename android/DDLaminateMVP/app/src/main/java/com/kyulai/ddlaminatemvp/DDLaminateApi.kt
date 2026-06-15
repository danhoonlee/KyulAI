package com.kyulai.ddlaminatemvp

import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL

class DDLaminateApi {
    fun health(baseUrl: String) {
        request("GET", endpoint(baseUrl, "/health"))
    }

    fun models(baseUrl: String): ModelsResponse {
        val json = JSONObject(request("GET", endpoint(baseUrl, "/api/v1/dd-laminate/models")))
        return ModelsResponse(responseModels = json.optJSONArray("response_models").toModelInfos())
    }

    fun predictResponse(
        baseUrl: String,
        caseName: String,
        theta1: Double,
        theta2: Double,
        modelKey: String,
    ): ForecastResult {
        val body = JSONObject()
            .put("case", caseName)
            .put("theta1", theta1)
            .put("theta2", theta2)
            .put("model", modelKey)
            .toString()
        val json = JSONObject(request("POST", endpoint(baseUrl, "/api/v1/dd-laminate/predict/response"), body))
        return ForecastResult(
            predictedType = json.optInt("predicted_type"),
            confidence = json.optionalDouble("confidence"),
            predictedPt = json.optionalDouble("predicted_pt") ?: json.optionalDouble("predicted_Pt"),
            predictedMaxForce = json.optionalDouble("predicted_max_force"),
            predictedMaxDisplacement = json.optionalDouble("predicted_max_displacement"),
            modelLabel = json.optString("model_label"),
            inputMode = json.optString("input_mode"),
            probabilities = json.optJSONObject("probabilities").toDoubleMap(),
            curve = json.optJSONArray("curve").toCurvePoints(),
            xai = json.optJSONObject("xai").toForecastXai(),
            notes = json.optJSONArray("notes").toStringList(),
        )
    }

    private fun request(method: String, url: URL, body: String? = null): String {
        val connection = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 8_000
            readTimeout = 20_000
            if (body != null) {
                doOutput = true
                setRequestProperty("Content-Type", "application/json")
            }
        }
        if (body != null) {
            connection.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
        }
        val stream = if (connection.responseCode in 200..299) {
            connection.inputStream
        } else {
            connection.errorStream ?: connection.inputStream
        }
        val text = BufferedReader(InputStreamReader(stream)).use { it.readText() }
        if (connection.responseCode !in 200..299) {
            throw IllegalStateException("HTTP ${connection.responseCode}: $text")
        }
        return text
    }

    private fun endpoint(baseUrl: String, path: String): URL {
        val cleanBase = baseUrl.trim().trimEnd('/')
        val cleanPath = path.trimStart('/')
        return URL("$cleanBase/$cleanPath")
    }
}

private fun org.json.JSONArray?.toModelInfos(): List<ModelInfo> {
    if (this == null) return emptyList()
    return (0 until length()).map { index ->
        val item = getJSONObject(index)
        ModelInfo(
            key = item.optString("key"),
            label = item.optString("label"),
            description = item.optString("description"),
            available = item.optBoolean("available"),
        )
    }
}

private fun JSONObject?.toDoubleMap(): Map<String, Double> {
    if (this == null) return emptyMap()
    return keys().asSequence().associateWith { key -> optDouble(key) }
}

private fun org.json.JSONArray?.toCurvePoints(): List<CurvePoint> {
    if (this == null) return emptyList()
    return (0 until length()).map { index ->
        val item = getJSONObject(index)
        CurvePoint(
            displacement = item.optDouble("displacement"),
            force = item.optDouble("force"),
        )
    }
}

private fun org.json.JSONArray?.toStringList(): List<String> {
    if (this == null) return emptyList()
    return (0 until length()).map { index -> optString(index) }
}

private fun JSONObject?.toForecastXai(): ForecastXai? {
    if (this == null || length() == 0) return null
    return ForecastXai(
        featureSet = optString("feature_set"),
        method = optString("method"),
        summary = optString("summary"),
        topFeatures = optJSONArray("top_features").toForecastXaiFeatures(),
    )
}

private fun org.json.JSONArray?.toForecastXaiFeatures(): List<ForecastXaiFeature> {
    if (this == null) return emptyList()
    return (0 until length()).map { index ->
        val item = getJSONObject(index)
        ForecastXaiFeature(
            name = item.optString("name"),
            label = item.optString("label"),
            category = item.optString("category"),
            importance = item.optDouble("importance"),
            explanation = item.optString("explanation"),
        )
    }
}

private fun JSONObject.optionalDouble(key: String): Double? {
    return if (has(key) && !isNull(key)) optDouble(key) else null
}
