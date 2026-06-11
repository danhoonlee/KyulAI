package com.luvelox.app

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.net.Uri
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

private const val CATALOG_URL = "https://laminate.luvelox.com/api/v1/modules/me"

data class ModuleRoute(
    val webUrl: String,
    val apiPrefix: String,
)

data class LuveloxModule(
    val id: String,
    val name: String,
    val shortName: String,
    val category: String,
    val summary: String,
    val icon: String,
    val status: String,
    val access: String,
    val tags: List<String>,
    val capabilities: List<String>,
    val route: ModuleRoute,
) {
    val isGranted: Boolean get() = access == "granted"
}

class MainActivity : Activity() {
    private lateinit var root: LinearLayout
    private lateinit var statusText: TextView
    private lateinit var moduleList: LinearLayout
    private var modules: List<LuveloxModule> = fallbackModules()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        render()
        loadModules()
    }

    private fun render() {
        val scroll = ScrollView(this).apply {
            setBackgroundColor(color(0xF7F8FB))
        }
        root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(26), dp(20), dp(44))
        }
        scroll.addView(root)
        setContentView(scroll)

        root.addView(label("UNIFIED CAE-AI WORKSPACE", color(0x127C82), 12f, Typeface.BOLD))
        root.addView(title("Luvelox", 48f))
        statusText = label("MVP workspace", color(0x647084), 14f, Typeface.BOLD).apply {
            setPadding(dp(12), dp(8), dp(12), dp(8))
            background = rounded(Color.WHITE, dp(999))
        }
        root.addView(statusText, margin(top = 10, bottom = 18))

        root.addView(introBand())
        moduleList = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }
        root.addView(moduleList, margin(top = 16))
        renderModules()
    }

    private fun introBand(): View {
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(18), dp(18), dp(18))
            background = strokedRounded(Color.WHITE, color(0xD9E0EA), dp(8))
            addView(title("Prediction modules", 24f))
            addView(
                paragraph(
                    "Open Laminate, Injection, and future CAE-AI modules from one Luvelox account."
                ),
                margin(top = 6)
            )
            addView(Button(context).apply {
                text = "Refresh"
                setTextColor(Color.WHITE)
                setTypeface(typeface, Typeface.BOLD)
                background = rounded(color(0x17202A), dp(8))
                setOnClickListener { loadModules() }
            }, margin(top = 14))
        }
    }

    private fun renderModules() {
        moduleList.removeAllViews()
        modules.forEach { module ->
            moduleList.addView(moduleCard(module), margin(bottom = 14))
        }
    }

    private fun moduleCard(module: LuveloxModule): View {
        val card = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(18), dp(18), dp(18))
            background = strokedRounded(Color.WHITE, color(0xD9E0EA), dp(8))
        }

        val header = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        header.addView(moduleIcon(module.icon))
        header.addView(LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(label(module.category.uppercase(), color(0x127C82), 11f, Typeface.BOLD))
            addView(title(module.name, 22f))
        }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
            marginStart = dp(12)
        })
        header.addView(accessBadge(module))
        card.addView(header)

        card.addView(paragraph(module.summary), margin(top = 16))
        card.addView(tagRow(module.tags), margin(top = 12))
        card.addView(capabilityGrid(module.capabilities), margin(top = 12))

        val openButton = Button(this).apply {
            text = if (module.isGranted) "Open ${module.shortName}" else "Request access"
            isEnabled = module.isGranted
            setTextColor(Color.WHITE)
            setTypeface(typeface, Typeface.BOLD)
            background = rounded(if (module.isGranted) color(0x17202A) else color(0xA8AFBA), dp(8))
            setOnClickListener {
                if (module.id == "laminate") {
                    startActivity(Intent(this@MainActivity, LaminateActivity::class.java))
                } else if (module.id == "injection") {
                    startActivity(Intent(this@MainActivity, InjectionActivity::class.java))
                } else {
                    startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(module.route.webUrl)))
                }
            }
        }
        card.addView(openButton, margin(top = 16))
        card.addView(label(module.route.apiPrefix, color(0x647084), 12f, Typeface.NORMAL), margin(top = 8))
        return card
    }

    private fun moduleIcon(icon: String): TextView {
        val symbol = when (icon) {
            "layers" -> "L"
            "gauge" -> "P"
            else -> "+"
        }
        return TextView(this).apply {
            text = symbol
            textSize = 22f
            setTextColor(color(0x127C82))
            typeface = Typeface.DEFAULT_BOLD
            gravity = Gravity.CENTER
            background = rounded(color(0xDFF4F3), dp(8))
        }.also {
            it.layoutParams = LinearLayout.LayoutParams(dp(48), dp(48))
        }
    }

    private fun accessBadge(module: LuveloxModule): TextView {
        return label(if (module.isGranted) "Available" else "Locked", if (module.isGranted) color(0x127C82) else color(0x7A8495), 12f, Typeface.BOLD).apply {
            setPadding(dp(10), dp(6), dp(10), dp(6))
            background = rounded(if (module.isGranted) color(0xDFF4F3) else color(0xEDF0F4), dp(999))
        }
    }

    private fun tagRow(tags: List<String>): LinearLayout {
        return LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            tags.take(3).forEach { tag ->
                addView(label(tag, color(0xC6531F), 12f, Typeface.BOLD).apply {
                    setPadding(dp(9), dp(6), dp(9), dp(6))
                    background = rounded(color(0xFFF0E7), dp(999))
                }, LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
                    marginEnd = dp(8)
                })
            }
        }
    }

    private fun capabilityGrid(capabilities: List<String>): LinearLayout {
        val outer = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }
        capabilities.take(4).chunked(2).forEach { rowItems ->
            val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
            rowItems.forEach { capability ->
                row.addView(label(capability.replace("_", " "), color(0x647084), 12f, Typeface.BOLD).apply {
                    gravity = Gravity.CENTER
                    setPadding(dp(8), dp(8), dp(8), dp(8))
                    background = strokedRounded(color(0xF7F8FB), color(0xD9E0EA), dp(8))
                }, LinearLayout.LayoutParams(0, dp(36), 1f).apply {
                    marginEnd = dp(8)
                })
            }
            outer.addView(row, margin(top = 8))
        }
        return outer
    }

    private fun loadModules() {
        statusText.text = "Loading modules"
        Thread {
            val loaded = runCatching { fetchModules() }.getOrElse { fallbackModules() }
            runOnUiThread {
                modules = loaded
                statusText.text = if (loaded == fallbackModules()) "Offline catalog" else "MVP workspace"
                renderModules()
            }
        }.start()
    }

    private fun fetchModules(): List<LuveloxModule> {
        val connection = URL(CATALOG_URL).openConnection() as HttpURLConnection
        connection.requestMethod = "GET"
        connection.connectTimeout = 5000
        connection.readTimeout = 5000
        connection.setRequestProperty("Accept", "application/json")
        if (connection.responseCode !in 200..299) error("Unexpected status ${connection.responseCode}")
        val body = connection.inputStream.bufferedReader().use { it.readText() }
        val modulesJson = JSONObject(body).getJSONArray("modules")
        return List(modulesJson.length()) { index ->
            val item = modulesJson.getJSONObject(index)
            val route = item.getJSONObject("route")
            LuveloxModule(
                id = item.getString("id"),
                name = item.getString("name"),
                shortName = item.getString("short_name"),
                category = item.getString("category"),
                summary = item.getString("summary"),
                icon = item.getString("icon"),
                status = item.getString("status"),
                access = item.optString("access", "granted"),
                tags = item.getJSONArray("tags").toStringList(),
                capabilities = item.getJSONArray("capabilities").toStringList(),
                route = ModuleRoute(
                    webUrl = route.getString("web_url"),
                    apiPrefix = route.getString("api_prefix"),
                )
            )
        }
    }

    private fun fallbackModules(): List<LuveloxModule> = listOf(
        LuveloxModule(
            id = "laminate",
            name = "Laminate",
            shortName = "Laminate",
            category = "Composite",
            summary = "Predict Double-Double laminate response, Pt, type, and force-displacement curves.",
            icon = "layers",
            status = "active",
            access = "granted",
            tags = listOf("Double-Double", "Pt", "Force-displacement"),
            capabilities = listOf("response_prediction", "curve_chart", "history", "comparison"),
            route = ModuleRoute("https://laminate.luvelox.com", "/api/v1/dd-laminate"),
        ),
        LuveloxModule(
            id = "injection",
            name = "Injection",
            shortName = "Injection",
            category = "Molding",
            summary = "Predict sprue pressure curves and filling pressure distributions for Simple Injection DOE.",
            icon = "gauge",
            status = "active",
            access = "granted",
            tags = listOf("Moldex3D", "Sprue pressure", "Filling pressure"),
            capabilities = listOf("sprue_pressure", "filling_histogram", "filling_animation", "history"),
            route = ModuleRoute("https://injection.luvelox.com", "/api/v1/simple-injection"),
        ),
    )

    private fun org.json.JSONArray.toStringList(): List<String> = List(length()) { index -> getString(index) }

    private fun title(text: String, size: Float): TextView = label(text, color(0x17202A), size, Typeface.BOLD)

    private fun paragraph(text: String): TextView = label(text, color(0x647084), 15f, Typeface.NORMAL).apply {
        setLineSpacing(dp(3).toFloat(), 1.0f)
    }

    private fun label(text: String, textColor: Int, size: Float, style: Int): TextView {
        return TextView(this).apply {
            this.text = text
            textSize = size
            setTextColor(textColor)
            typeface = Typeface.create(Typeface.DEFAULT, style)
            includeFontPadding = true
        }
    }

    private fun margin(top: Int = 0, bottom: Int = 0): LinearLayout.LayoutParams =
        LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
            topMargin = dp(top)
            bottomMargin = dp(bottom)
        }

    private fun rounded(fill: Int, radius: Int) = android.graphics.drawable.GradientDrawable().apply {
        setColor(fill)
        cornerRadius = radius.toFloat()
    }

    private fun strokedRounded(fill: Int, stroke: Int, radius: Int) = android.graphics.drawable.GradientDrawable().apply {
        setColor(fill)
        setStroke(dp(1), stroke)
        cornerRadius = radius.toFloat()
    }

    private fun color(rgb: Int): Int = Color.rgb(rgb shr 16 and 0xFF, rgb shr 8 and 0xFF, rgb and 0xFF)

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}
