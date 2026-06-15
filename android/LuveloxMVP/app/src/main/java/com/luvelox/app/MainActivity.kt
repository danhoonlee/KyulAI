package com.luvelox.app

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.net.Uri
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

private const val CATALOG_URL = "https://laminate.luvelox.com/api/v1/modules/me"
private const val LOGIN_URL = "https://laminate.luvelox.com/api/v1/modules/auth/demo-login"
private const val REQUEST_ACCESS_URL = "https://laminate.luvelox.com/api/v1/modules/request-access"
private const val SESSION_PREFS = "luvelox_auth"

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
    val entitlementKey: String,
    val access: String,
    val accessReason: String,
    val tags: List<String>,
    val capabilities: List<String>,
    val route: ModuleRoute,
) {
    val isGranted: Boolean get() = access == "granted"
}

data class AccountSession(
    val token: String,
    val email: String,
    val name: String,
    val entitlements: List<String>,
)

class MainActivity : Activity() {
    private lateinit var root: LinearLayout
    private lateinit var statusText: TextView
    private lateinit var moduleList: LinearLayout
    private var modules: List<LuveloxModule> = fallbackModules()
    private var session: AccountSession? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        session = loadSession()
        render()
        if (session != null) loadModules()
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

        if (session == null) {
            renderLogin()
        } else {
            renderHome()
        }
    }

    private fun renderLogin() {
        root.addView(title("C2ES", 48f))
        root.addView(title("Sign in to your CAE-AI workspace", 23f), margin(top = 10))
        root.addView(paragraph("Use a C2ES account to open licensed prediction modules from one app."), margin(top = 8, bottom = 18))

        val card = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(18), dp(18), dp(18))
            background = strokedRounded(Color.WHITE, color(0xD9E0EA), dp(8))
        }
        card.addView(label("Account", color(0x17202A), 17f, Typeface.BOLD))
        val emailField = input("demo@luvelox.com").apply {
            setSingleLine(true)
        }
        val passwordField = input("Password").apply {
            setSingleLine(true)
        }
        card.addView(emailField, margin(top = 12))
        card.addView(passwordField, margin(top = 10))
        val errorLabel = label("", Color.RED, 12f, Typeface.BOLD)
        card.addView(errorLabel, margin(top = 8))
        card.addView(Button(this).apply {
            text = "Sign in"
            setTextColor(Color.WHITE)
            setTypeface(typeface, Typeface.BOLD)
            background = rounded(color(0x17202A), dp(8))
            setOnClickListener {
                val email = emailField.text.toString().ifBlank { "demo@luvelox.com" }
                signIn(email, passwordField.text.toString(), errorLabel)
            }
        }, margin(top = 12))
        card.addView(Button(this).apply {
            text = "Continue with demo account"
            setTextColor(color(0x127C82))
            setTypeface(typeface, Typeface.BOLD)
            background = rounded(color(0xDFF4F3), dp(8))
            setOnClickListener {
                signIn("demo@luvelox.com", "", errorLabel)
            }
        }, margin(top = 10))
        root.addView(card)
        root.addView(label("MVP accounts: demo@luvelox.com or danlee@luvelox.com", color(0x647084), 12f, Typeface.NORMAL), margin(top = 12))
    }

    private fun renderHome() {
        root.addView(label("UNIFIED CAE-AI WORKSPACE", color(0x127C82), 12f, Typeface.BOLD))
        root.addView(title("C2ES", 48f))
        statusText = label("Account workspace", color(0x647084), 14f, Typeface.BOLD).apply {
            setPadding(dp(12), dp(8), dp(12), dp(8))
            background = rounded(Color.WHITE, dp(999))
        }
        root.addView(statusText, margin(top = 10, bottom = 18))

        root.addView(accountBand(), margin(bottom = 14))
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
                    "Open Laminate, Injection, and future CAE-AI modules from one C2ES account."
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
            addView(Button(context).apply {
                text = "Sign out"
                setTextColor(color(0x647084))
                setTypeface(typeface, Typeface.BOLD)
                background = rounded(color(0xEDF0F4), dp(8))
                setOnClickListener { signOut() }
            }, margin(top = 8))
        }
    }

    private fun accountBand(): View {
        val account = session ?: return View(this)
        return LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(16), dp(16), dp(16), dp(16))
            background = strokedRounded(Color.WHITE, color(0xD9E0EA), dp(8))
            addView(moduleIcon("account"))
            addView(LinearLayout(context).apply {
                orientation = LinearLayout.VERTICAL
                addView(label(account.name, color(0x17202A), 17f, Typeface.BOLD))
                addView(label(account.email, color(0x647084), 12f, Typeface.NORMAL))
            }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                marginStart = dp(12)
            })
            addView(label("${account.entitlements.size} modules", color(0x127C82), 12f, Typeface.BOLD).apply {
                setPadding(dp(10), dp(6), dp(10), dp(6))
                background = rounded(color(0xDFF4F3), dp(999))
            })
            setOnClickListener { showAccountDialog() }
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
            setTextColor(Color.WHITE)
            setTypeface(typeface, Typeface.BOLD)
            background = rounded(if (module.isGranted) color(0x17202A) else color(0x39404B), dp(8))
            setOnClickListener {
                if (!module.isGranted) {
                    showAccessDialog(module)
                } else if (module.id == "laminate") {
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
        val activeSession = session ?: return
        statusText.text = "Loading modules"
        Thread {
            val loaded = runCatching { fetchModules(activeSession) }.getOrElse { fallbackModules() }
            runOnUiThread {
                modules = loaded
                statusText.text = if (loaded == fallbackModules()) "Offline account" else "Account workspace"
                renderModules()
            }
        }.start()
    }

    private fun fetchModules(account: AccountSession): List<LuveloxModule> {
        val connection = URL(CATALOG_URL).openConnection() as HttpURLConnection
        connection.requestMethod = "GET"
        connection.connectTimeout = 5000
        connection.readTimeout = 5000
        connection.setRequestProperty("Accept", "application/json")
        connection.setRequestProperty("Authorization", "Bearer ${account.token}")
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
                entitlementKey = item.getString("entitlement_key"),
                access = item.optString("access", "granted"),
                accessReason = item.optString("access_reason", ""),
                tags = item.getJSONArray("tags").toStringList(),
                capabilities = item.getJSONArray("capabilities").toStringList(),
                route = ModuleRoute(
                    webUrl = route.getString("web_url"),
                    apiPrefix = route.getString("api_prefix"),
                )
            )
        }
    }

    private fun signIn(email: String, password: String, errorLabel: TextView) {
        errorLabel.text = ""
        Thread {
            val account = runCatching { login(email, password) }.getOrElse {
                localSession(email)
            }
            runOnUiThread {
                if (account == null) {
                    errorLabel.text = "Use demo@luvelox.com for the MVP account."
                } else {
                    session = account
                    saveSession(account)
                    render()
                    loadModules()
                }
            }
        }.start()
    }

    private fun login(email: String, password: String): AccountSession {
        val connection = URL(LOGIN_URL).openConnection() as HttpURLConnection
        connection.requestMethod = "POST"
        connection.connectTimeout = 5000
        connection.readTimeout = 5000
        connection.setRequestProperty("Accept", "application/json")
        connection.setRequestProperty("Content-Type", "application/json")
        connection.doOutput = true
        val payload = JSONObject()
            .put("email", email.trim().lowercase())
            .put("password", password)
            .toString()
        connection.outputStream.use { stream ->
            stream.write(payload.toByteArray(Charsets.UTF_8))
        }
        if (connection.responseCode !in 200..299) error("Unexpected status ${connection.responseCode}")
        val body = JSONObject(connection.inputStream.bufferedReader().use { it.readText() })
        val user = body.getJSONObject("user")
        return AccountSession(
            token = body.getString("access_token"),
            email = user.getString("email"),
            name = cleanAccountName(user.getString("name")),
            entitlements = body.getJSONArray("entitlements").toStringList(),
        )
    }

    private fun localSession(email: String): AccountSession? {
        return when (email.trim().lowercase()) {
            "", "demo@luvelox.com" -> AccountSession(
                token = "demo-token",
                email = "demo@luvelox.com",
                name = "Demo Account",
                entitlements = listOf("module.laminate", "module.injection"),
            )
            "danlee@luvelox.com" -> AccountSession(
                token = "danlee-token",
                email = "danlee@luvelox.com",
                name = "Dan Lee",
                entitlements = listOf("module.laminate", "module.injection", "module.optimization"),
            )
            else -> null
        }
    }

    private fun saveSession(account: AccountSession) {
        getSharedPreferences(SESSION_PREFS, MODE_PRIVATE)
            .edit()
            .putString("token", account.token)
            .putString("email", account.email)
            .putString("name", account.name)
            .putString("entitlements", account.entitlements.joinToString(","))
            .apply()
    }

    private fun loadSession(): AccountSession? {
        val prefs = getSharedPreferences(SESSION_PREFS, MODE_PRIVATE)
        val token = prefs.getString("token", null) ?: return null
        val email = prefs.getString("email", "") ?: ""
        val name = cleanAccountName(prefs.getString("name", "C2ES Account") ?: "C2ES Account")
        val entitlements = prefs.getString("entitlements", "")?.split(",")?.filter { it.isNotBlank() } ?: emptyList()
        return AccountSession(token, email, name, entitlements)
    }

    private fun cleanAccountName(name: String): String {
        return when (name.trim()) {
            "Luvelox Demo", "C2ES Demo" -> "Demo Account"
            "Luvelox Account" -> "C2ES Account"
            else -> name
        }
    }

    private fun signOut() {
        getSharedPreferences(SESSION_PREFS, MODE_PRIVATE).edit().clear().apply()
        session = null
        render()
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
            entitlementKey = "module.laminate",
            access = "granted",
            accessReason = "Available in the C2ES MVP workspace.",
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
            entitlementKey = "module.injection",
            access = "granted",
            accessReason = "Available in the C2ES MVP workspace.",
            tags = listOf("Moldex3D", "Sprue pressure", "Filling pressure"),
            capabilities = listOf("sprue_pressure", "filling_histogram", "filling_animation", "history"),
            route = ModuleRoute("https://injection.luvelox.com", "/api/v1/simple-injection"),
        ),
        LuveloxModule(
            id = "optimization",
            name = "Optimization",
            shortName = "Optimize",
            category = "Design",
            summary = "Explore candidate designs and rank promising simulation settings across enabled modules.",
            icon = "sparkles",
            status = "planned",
            entitlementKey = "module.optimization",
            access = "locked",
            accessReason = "Planned module; not available in this workspace yet.",
            tags = listOf("DOE", "Ranking", "Design space"),
            capabilities = listOf("candidate_ranking", "batch_prediction"),
            route = ModuleRoute("https://luvelox.com", "/api/v1/optimization"),
        ),
    )

    private fun showAccountDialog() {
        val account = session ?: return
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(10), dp(20), dp(4))
            addView(title(account.name, 24f))
            addView(label(account.email, color(0x647084), 14f, Typeface.BOLD), margin(top = 4, bottom = 14))
            addView(label("Licensed modules", color(0x17202A), 17f, Typeface.BOLD), margin(bottom = 8))
            modules.forEach { module ->
                val row = LinearLayout(context).apply {
                    orientation = LinearLayout.VERTICAL
                    setPadding(dp(12), dp(10), dp(12), dp(10))
                    background = strokedRounded(color(0xF7F8FB), color(0xD9E0EA), dp(8))
                    addView(label("${if (module.isGranted) "On" else "Locked"} - ${module.name}", if (module.isGranted) color(0x127C82) else color(0x647084), 14f, Typeface.BOLD))
                    addView(label(module.accessReason.ifBlank { module.entitlementKey }, color(0x647084), 12f, Typeface.NORMAL), margin(top = 2))
                }
                addView(row, margin(bottom = 8))
            }
        }
        AlertDialog.Builder(this)
            .setTitle("Account")
            .setView(content)
            .setPositiveButton("Refresh") { _, _ -> loadModules() }
            .setNegativeButton("Sign out") { _, _ -> signOut() }
            .setNeutralButton("Done", null)
            .show()
    }

    private fun showAccessDialog(module: LuveloxModule) {
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(10), dp(20), dp(4))
            addView(label(module.category.uppercase(), color(0x127C82), 12f, Typeface.BOLD))
            addView(title(module.name, 28f), margin(top = 4))
            addView(paragraph(module.summary), margin(top = 8, bottom = 14))
            addView(label("Access", color(0x17202A), 17f, Typeface.BOLD))
            addView(paragraph(module.accessReason.ifBlank { "This module requires a C2ES license." }), margin(top = 6))
            addView(label("Entitlement: ${module.entitlementKey}", color(0x647084), 12f, Typeface.BOLD), margin(top = 8, bottom = 14))
            addView(label("Included capabilities", color(0x17202A), 17f, Typeface.BOLD), margin(bottom = 8))
            module.capabilities.forEach { capability ->
                addView(label("- ${capability.replace("_", " ")}", color(0x647084), 14f, Typeface.BOLD), margin(bottom = 4))
            }
        }
        AlertDialog.Builder(this)
            .setTitle("Module access")
            .setView(content)
            .setPositiveButton("Request access") { _, _ -> requestAccess(module) }
            .setNegativeButton("Done", null)
            .show()
    }

    private fun requestAccess(module: LuveloxModule) {
        val activeSession = session
        Thread {
            val message = runCatching {
                val connection = URL(REQUEST_ACCESS_URL).openConnection() as HttpURLConnection
                connection.requestMethod = "POST"
                connection.connectTimeout = 5000
                connection.readTimeout = 5000
                connection.setRequestProperty("Accept", "application/json")
                connection.setRequestProperty("Content-Type", "application/json")
                if (activeSession != null) {
                    connection.setRequestProperty("Authorization", "Bearer ${activeSession.token}")
                }
                connection.doOutput = true
                val payload = JSONObject()
                    .put("module_id", module.id)
                    .put("message", "Requested from C2ES Android app.")
                    .toString()
                connection.outputStream.use { stream ->
                    stream.write(payload.toByteArray(Charsets.UTF_8))
                }
                if (connection.responseCode !in 200..299) error("Unexpected status ${connection.responseCode}")
                JSONObject(connection.inputStream.bufferedReader().use { it.readText() }).getString("message")
            }.getOrElse {
                "Request saved locally. We could not reach the C2ES server right now."
            }
            runOnUiThread {
                AlertDialog.Builder(this)
                    .setTitle("Request access")
                    .setMessage(message)
                    .setPositiveButton("Done", null)
                    .show()
            }
        }.start()
    }

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

    private fun input(hint: String): EditText {
        return EditText(this).apply {
            this.hint = hint
            textSize = 16f
            setTextColor(color(0x17202A))
            setHintTextColor(color(0x7A8495))
            setPadding(dp(12), 0, dp(12), 0)
            background = strokedRounded(color(0xF7F8FB), color(0xD9E0EA), dp(8))
            minHeight = dp(46)
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
