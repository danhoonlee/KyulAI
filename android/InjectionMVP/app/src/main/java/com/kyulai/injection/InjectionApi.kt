package com.kyulai.injection

import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL

class InjectionApi {
    fun health(baseUrl: String) {
        request("GET", endpoint(baseUrl, "/health"))
    }

    fun models(baseUrl: String): ModelsResponse {
        val json = JSONObject(request("GET", endpoint(baseUrl, "/api/v1/simple-injection/models")))
        return ModelsResponse(
            sprueModels = json.optJSONArray("sprue_pressure_models").toModelInfos(),
            fillingModels = json.optJSONArray("filling_pressure_models").toModelInfos(),
        )
    }

    fun doe(baseUrl: String): Pair<List<DoeOption>, List<DoeOption>> {
        val json = JSONObject(request("GET", endpoint(baseUrl, "/api/v1/simple-injection/doe")))
        return json.optJSONArray("geometries").toDoeOptions() to json.optJSONArray("processes").toDoeOptions()
    }

    fun predictSpruePressure(baseUrl: String, input: InjectionInput): SpruePressureResult {
        val body = JSONObject()
            .put("geometry_id", input.geometryId)
            .put("process_id", input.processId)
            .put("model", input.sprueModelKey)
            .put("filling_model", input.fillingModelKey)
            .put("L_mm", input.lMm)
            .put("W_mm", input.wMm)
            .put("t_mm", input.tMm)
            .put("D_mm", input.dMm)
            .put("R_mm", input.rMm)
            .put("gate_type", input.gateType)
            .put("gate_size_width_mm", input.gateWidthMm)
            .put("gate_size_height_mm", input.gateHeightMm)
            .put("melt_temp_C", input.meltTempC)
            .put("mold_temp_C", input.moldTempC)
            .put("injection_time_s", input.injectionTimeS)
            .put("packing_pressure_MPa", input.packingPressureMPa)
            .put("packing_time_s", input.packingTimeS)
            .toString()
        val json = JSONObject(request("POST", endpoint(baseUrl, "/api/v1/simple-injection/predict/sprue-pressure"), body))
        val filling = json.optJSONObject("predicted_filling_pressure") ?: json.optJSONObject("filling_pressure")
        return SpruePressureResult(
            predictedMaxTimeS = json.optDouble("predicted_max_time_s"),
            predictedMaxPressureMPa = json.optDouble("predicted_max_pressure_MPa"),
            modelLabel = json.optString("model_label"),
            fillingModelLabel = json.optString("filling_model_label"),
            curve = json.optJSONArray("curve").toPressurePoints(),
            fillingSummary = filling?.toFillingSummary(),
            notes = json.optJSONArray("notes").toStringList(),
        )
    }

    private fun request(method: String, url: URL, body: String? = null): String {
        val connection = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 8_000
            readTimeout = 25_000
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

private fun JSONArray?.toModelInfos(): List<ModelInfo> {
    if (this == null) return emptyList()
    return (0 until length()).map { index ->
        val item = getJSONObject(index)
        item.toModelInfo()
    }
}

private fun JSONObject.toModelInfo(): ModelInfo {
    return ModelInfo(
        key = optString("key"),
        label = optString("label"),
        description = optString("description"),
        available = optBoolean("available"),
    )
}

private fun JSONArray?.toDoeOptions(): List<DoeOption> {
    if (this == null) return emptyList()
    return (0 until length()).map { index ->
        val item = getJSONObject(index)
        val values = item.keys().asSequence().associateWith { key ->
            when (val value = item.opt(key)) {
                JSONObject.NULL -> null
                else -> value
            }
        }
        DoeOption(id = item.optString("id"), values = values)
    }
}

private fun JSONArray?.toPressurePoints(): List<PressurePoint> {
    if (this == null) return emptyList()
    return (0 until length()).map { index ->
        val item = getJSONObject(index)
        PressurePoint(
            timeS = item.optDouble("time_s"),
            pressureMPa = item.optDouble("sprue_pressure_MPa"),
        )
    }
}

private fun JSONObject.toFillingSummary(): FillingSummary {
    return FillingSummary(
        stats = optJSONObject("stats").toDoubleMap(),
        bins = optJSONArray("bins").toFillingBins(),
        note = optString("note"),
    )
}

private fun JSONArray?.toFillingBins(): List<FillingBin> {
    if (this == null) return emptyList()
    return (0 until length()).map { index ->
        val item = getJSONObject(index)
        FillingBin(
            group = item.optInt("group"),
            fromMPa = item.optDouble("from_MPa"),
            toMPa = item.optDouble("to_MPa"),
            volumeRatioPct = item.optDouble("volume_ratio_pct"),
        )
    }
}

private fun JSONObject?.toDoubleMap(): Map<String, Double> {
    if (this == null) return emptyMap()
    return keys().asSequence().associateWith { key -> optDouble(key) }
}

private fun JSONArray?.toStringList(): List<String> {
    if (this == null) return emptyList()
    return (0 until length()).map { index -> optString(index) }
}
