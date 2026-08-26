package com.imperialax.app

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.net.Uri
import android.os.Bundle
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.text.InputType
import android.text.TextUtils
import android.text.method.PasswordTransformationMethod
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import android.util.Base64
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.security.KeyStore
import java.time.Instant
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

private const val CATALOG_URL = "https://laminate.imperialax.com/api/v1/modules/me"
private const val LOGIN_URL = "https://laminate.imperialax.com/api/v1/modules/auth/login"
private const val DEMO_LOGIN_URL = "https://laminate.imperialax.com/api/v1/modules/auth/demo-login"
private const val SIGNUP_URL = "https://laminate.imperialax.com/api/v1/modules/auth/signup"
private const val REQUEST_ACCESS_URL = "https://laminate.imperialax.com/api/v1/modules/request-access"
private const val LAUNCH_CODE_URL = "https://laminate.imperialax.com/api/v1/modules/auth/launch-code"
private const val SESSION_PREFS = "imperialax_auth"
private const val SECURE_SESSION_KEY = "secure_session"
private const val SESSION_KEY_ALIAS = "imperialax_session_key"
private const val SESSION_LIFETIME_MS = 24L * 60L * 60L * 1000L
const val EXTRA_AUTH_TOKEN = "com.imperialax.app.EXTRA_AUTH_TOKEN"

data class ModuleRoute(
    val webUrl: String,
    val apiPrefix: String,
)

data class ImperialAXModule(
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
    val expiresAt: String? = null,
    val savedAtMs: Long = System.currentTimeMillis(),
)

private class AuthenticationExpiredException : RuntimeException()

class MainActivity : Activity() {
    private lateinit var root: LinearLayout
    private lateinit var statusText: TextView
    private lateinit var refreshButton: Button
    private lateinit var moduleList: LinearLayout
    private var modules: List<ImperialAXModule> = fallbackModules()
    private var session: AccountSession? = null
    private var signupMode = false
    private var authNotice: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        session = loadSession()
        render()
        if (session != null) loadModules()
    }

    override fun onResume() {
        super.onResume()
        expireSessionIfNeeded()
    }

    private fun render() {
        val scroll = ScrollView(this).apply {
            setBackgroundColor(V2.background)
        }
        root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(22), dp(18), dp(44))
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
        root.addView(LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(18), dp(18), dp(18))
            background = v2PanelBackground()
            addView(label("ImperialAX AI Workspace", V2.blue, 12f, Typeface.BOLD))
            addView(title("ImperialAX\nForecast Workspace", 42f).apply {
                includeFontPadding = false
                setLineSpacing(0f, 0.96f)
            }, margin(top = 10))
            addView(
                paragraph("Sign in once, then open the prediction module built for each engineering analysis."),
                margin(top = 12)
            )
            addView(modulePreviewStrip(), margin(top = 14))
        }, margin(bottom = 14))

        val card = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(18), dp(18), dp(18))
            background = v2PanelBackground()
        }
        card.addView(label("Account", V2.blue, 12f, Typeface.BOLD))
        card.addView(title(if (signupMode) "Create account" else "Sign in", 26f), margin(top = 4))
        val nameField = input("Name").apply {
            setSingleLine(true)
            visibility = if (signupMode) View.VISIBLE else View.GONE
        }
        val companyField = input("Company (optional)").apply {
            setSingleLine(true)
            visibility = if (signupMode) View.VISIBLE else View.GONE
        }
        card.addView(nameField, margin(top = 12))
        card.addView(companyField, margin(top = 10))
        val emailField = input("Email").apply {
            setSingleLine(true)
        }
        val passwordField = input("Password").apply {
            setSingleLine(true)
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
            transformationMethod = PasswordTransformationMethod.getInstance()
            useAppFont(Typeface.NORMAL)
        }
        val passwordToggle = Button(this).apply {
            text = "Show"
            setTextColor(V2.blue)
            useAppFont(Typeface.BOLD)
            background = softBackground(V2.blueSoft, V2.blueLine, dp(8))
            minHeight = dp(54)
            minWidth = dp(78)
        }
        var passwordVisible = false
        passwordToggle.setOnClickListener {
            passwordVisible = !passwordVisible
            val cursor = passwordField.selectionStart.coerceAtLeast(0)
            passwordField.transformationMethod = if (passwordVisible) null else PasswordTransformationMethod.getInstance()
            passwordToggle.text = if (passwordVisible) "Hide" else "Show"
            passwordField.setSelection(cursor.coerceAtMost(passwordField.text.length))
        }
        card.addView(emailField, margin(top = 12))
        card.addView(LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            addView(passwordField, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            addView(passwordToggle, LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
                marginStart = dp(8)
            })
        }, margin(top = 10))
        val errorLabel = label("", Color.RED, 12f, Typeface.BOLD)
        errorLabel.text = authNotice.orEmpty()
        card.addView(errorLabel, margin(top = 8))
        card.addView(Button(this).apply {
            text = if (signupMode) "Create account" else "Sign in"
            setTextColor(Color.WHITE)
            useAppFont(Typeface.BOLD)
            background = commandButtonBackground()
            setOnClickListener {
                val email = emailField.text.toString().trim()
                if (signupMode) {
                    signUp(
                        email = email,
                        password = passwordField.text.toString(),
                        name = nameField.text.toString(),
                        company = companyField.text.toString(),
                        errorLabel = errorLabel,
                    )
                } else {
                    signIn(email, passwordField.text.toString(), errorLabel)
                }
            }
        }, margin(top = 12))
        card.addView(Button(this).apply {
            text = if (signupMode) "Use existing account" else "Create a new account"
            setTextColor(V2.blue)
            useAppFont(Typeface.BOLD)
            background = softBackground(V2.blueSoft, V2.blueLine, dp(8))
            setOnClickListener {
                signupMode = !signupMode
                render()
            }
        }, margin(top = 10))
        if (!signupMode) {
            card.addView(Button(this).apply {
                text = "Try demo workspace"
                setTextColor(V2.blue)
                useAppFont(Typeface.BOLD)
                minHeight = dp(48)
                background = softBackground(Color.WHITE, V2.blueLine, dp(8))
                setOnClickListener { signInDemo(errorLabel) }
            }, margin(top = 10))
        }
        card.addView(label(
            if (signupMode) "Use at least 8 characters to create an account." else "New accounts include Laminate and Injection access.",
            V2.muted,
            12f,
            Typeface.BOLD
        ), margin(top = 12))
        root.addView(card)
    }

    private fun renderHome() {
        statusText = label("Ready", V2.blue, 13f, Typeface.BOLD).apply {
            setPadding(dp(12), dp(8), dp(12), dp(8))
            background = blueSoftBackground()
        }
        root.addView(workspaceHero(), margin(bottom = 12))
        root.addView(workflowStrip(), margin(bottom = 12))

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
            background = commandButtonBackground()
            addView(label("Module workspace", V2.tealLight, 11f, Typeface.BOLD))
            addView(label("Prediction modules", Color.WHITE, 24f, Typeface.BOLD), margin(top = 4))
            addView(
                label("Open prediction modules from one account.", V2.darkMuted, 15f, Typeface.BOLD),
                margin(top = 6)
            )
            addView(statusText, margin(top = 12))
            refreshButton = Button(context).apply {
                text = "Refresh"
                setTextColor(V2.ink)
                useAppFont(Typeface.BOLD)
                background = rounded(Color.WHITE, dp(8))
                setOnClickListener { loadModules() }
            }
            addView(refreshButton, margin(top = 14))
        }
    }

    private fun modulePreviewStrip(): LinearLayout {
        return LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            background = strokedRounded(V2.surfaceStrong, V2.line, dp(8))
            addView(modulePreviewItem("L", "Laminate", "Type, Pt, curve", V2.blue, V2.blueSoft), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            addView(modulePreviewItem("I", "Injection", "Sprue, filling", V2.teal, V2.tealSoft), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            addView(modulePreviewItem("O", "Optimization", "Design search", V2.amber, V2.amberSoft), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        }
    }

    private fun modulePreviewItem(letter: String, title: String, subtitle: String, accent: Int, soft: Int): LinearLayout {
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(10), dp(10), dp(10), dp(10))
            addView(label(letter, accent, 18f, Typeface.BOLD).apply {
                gravity = Gravity.CENTER
                background = rounded(soft, dp(8))
            }, LinearLayout.LayoutParams(dp(32), dp(32)))
            addView(label(title, V2.ink, 11f, Typeface.BOLD).apply {
                setSingleLine(true)
                ellipsize = TextUtils.TruncateAt.END
            }, margin(top = 5))
            addView(label(subtitle, V2.muted, 10f, Typeface.BOLD).apply {
                setSingleLine(true)
                ellipsize = TextUtils.TruncateAt.END
            }, margin(top = 1))
        }
    }

    private fun workspaceHero(): View {
        val account = session
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(18), dp(18), dp(18))
            background = v2PanelBackground()
            addView(label("ImperialAX AI Workspace", V2.blue, 12f, Typeface.BOLD))
            addView(title("ImperialAX\nForecast Workspace", 42f).apply {
                includeFontPadding = false
                setLineSpacing(0f, 0.96f)
            }, margin(top = 10))
            addView(paragraph("Choose a module to open its prediction screen."), margin(top = 12))
            addView(LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                addView(label("● ${account?.name ?: "Account workspace"} · ${account?.entitlements?.size ?: 0} modules", V2.green, 12f, Typeface.BOLD).apply {
                    setSingleLine(true)
                    ellipsize = TextUtils.TruncateAt.END
                    setPadding(dp(12), dp(9), dp(12), dp(9))
                    background = softBackground(V2.greenSoft, V2.greenSoft)
                    setOnClickListener { showAccountDialog() }
                }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
                addView(label("Sign out", V2.muted, 12f, Typeface.BOLD).apply {
                    gravity = Gravity.CENTER
                    setPadding(dp(12), dp(9), dp(12), dp(9))
                    background = mutedButtonBackground()
                    setOnClickListener { signOut() }
                }, LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
                    marginStart = dp(8)
                })
            }, margin(top = 14))
        }
    }

    private fun accountBand(): View {
        val account = session ?: return View(this)
        return LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(16), dp(16), dp(16), dp(16))
            background = v2PanelBackground()
            addView(moduleIcon("account"))
            addView(LinearLayout(context).apply {
                orientation = LinearLayout.VERTICAL
                addView(label(account.name, V2.ink, 17f, Typeface.BOLD))
                addView(label(account.email, V2.muted, 12f, Typeface.NORMAL))
            }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                marginStart = dp(12)
            })
            addView(label("${account.entitlements.size} modules", V2.blue, 12f, Typeface.BOLD).apply {
                setPadding(dp(10), dp(6), dp(10), dp(6))
                background = blueSoftBackground()
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

    private fun moduleCard(module: ImperialAXModule): View {
        val accent = accentFor(module)
        val soft = softFor(module)
        val card = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(18), dp(18), dp(18))
            background = v2PanelBackground()
        }

        val header = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        header.addView(moduleIcon(module.icon, module.id, module.isGranted))
        header.addView(LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(label(module.category.uppercase(), accent, 11f, Typeface.BOLD))
            addView(title(module.name, 22f).apply {
                setSingleLine(true)
                ellipsize = TextUtils.TruncateAt.END
            })
        }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
            marginStart = dp(12)
        })
        header.addView(accessBadge(module))
        card.addView(header)

        card.addView(paragraph(module.summary).apply {
            maxLines = 2
            ellipsize = TextUtils.TruncateAt.END
            typeface = Typeface.DEFAULT_BOLD
        }, margin(top = 12))
        card.addView(tagRow(module.tags, accent, soft), margin(top = 12))
        card.addView(capabilityGrid(module.capabilities), margin(top = 12))

        val openButton = Button(this).apply {
            text = if (module.isGranted) "Open ${module.shortName}" else "Request access"
            setTextColor(Color.WHITE)
            useAppFont(Typeface.BOLD)
            background = if (module.isGranted) commandButtonBackground() else rounded(V2.mutedDark, dp(8))
            setOnClickListener {
                if (!module.isGranted) {
                    showAccessDialog(module)
                } else {
                    openModule(module)
                }
            }
        }
        card.addView(openButton, margin(top = 16))
        return card
    }

    private fun quickActionRail(): LinearLayout {
        return LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            addView(quickActionIcon("A", "Account") { showAccountDialog() })
        }
    }

    private fun quickActionIcon(symbol: String, description: String, onClick: () -> Unit): TextView {
        return TextView(this).apply {
            text = symbol
            textSize = 17f
            setTextColor(V2.blue)
            useAppFont(Typeface.BOLD)
            gravity = Gravity.CENTER
            contentDescription = description
            background = blueSoftBackground()
            setOnClickListener { onClick() }
        }.also {
            it.layoutParams = LinearLayout.LayoutParams(dp(44), dp(44))
        }
    }

    private fun openModule(module: ImperialAXModule) {
        if (expireSessionIfNeeded()) return
        when (module.id) {
            "laminate" -> startActivity(
                Intent(this@MainActivity, LaminateActivity::class.java)
                    .putExtra(EXTRA_AUTH_TOKEN, session?.token.orEmpty())
            )
            "injection" -> startActivity(
                Intent(this@MainActivity, InjectionActivity::class.java)
                    .putExtra(EXTRA_AUTH_TOKEN, session?.token.orEmpty())
            )
            "admin", "optimization" -> {
                val activeSession = session ?: return
                Thread {
                    val launchUrl = runCatching {
                        createLaunchUrl(module.id, activeSession.token)
                    }.getOrNull()
                    runOnUiThread {
                        if (launchUrl == null) {
                            Toast.makeText(
                                this@MainActivity,
                                "Could not open this page securely. Sign in and try again.",
                                Toast.LENGTH_LONG,
                            ).show()
                        } else {
                            startActivity(
                                Intent(this@MainActivity, AdminWebActivity::class.java)
                                    .putExtra("url", launchUrl)
                            )
                        }
                    }
                }.start()
            }
            else -> startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(module.route.webUrl)))
        }
    }

    private fun moduleIcon(icon: String, moduleId: String? = null, granted: Boolean = true): TextView {
        val symbol = when (icon) {
            "layers" -> "L"
            "gauge" -> "I"
            "sparkles" -> "O"
            "shield" -> "A"
            "account" -> "A"
            else -> "+"
        }
        return TextView(this).apply {
            text = symbol
            textSize = 22f
            setTextColor(accentFor(moduleId, granted))
            useAppFont(Typeface.BOLD)
            gravity = Gravity.CENTER
            background = softBackground(softFor(moduleId, granted), softFor(moduleId, granted), dp(8))
        }.also {
            it.layoutParams = LinearLayout.LayoutParams(dp(48), dp(48))
        }
    }

    private fun accessBadge(module: ImperialAXModule): TextView {
        return label(if (module.isGranted) "Available" else "Locked", if (module.isGranted) V2.green else V2.muted, 12f, Typeface.BOLD).apply {
            setPadding(dp(10), dp(6), dp(10), dp(6))
            background = if (module.isGranted) softBackground(V2.greenSoft, V2.greenSoft) else mutedButtonBackground()
        }
    }

    private fun tagRow(tags: List<String>, accent: Int, soft: Int): LinearLayout {
        return LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            tags.take(3).forEach { tag ->
                addView(label(tag, accent, 12f, Typeface.BOLD).apply {
                    setPadding(dp(9), dp(6), dp(9), dp(6))
                    background = softBackground(soft, soft)
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
                row.addView(label(capability.replace("_", " "), V2.muted, 12f, Typeface.BOLD).apply {
                    gravity = Gravity.CENTER
                    setPadding(dp(8), dp(8), dp(8), dp(8))
                    background = strokedRounded(V2.field, V2.line, dp(8))
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
        if (::statusText.isInitialized) {
            statusText.text = "Refreshing modules..."
        }
        if (::refreshButton.isInitialized) {
            refreshButton.isEnabled = false
            refreshButton.text = "Refreshing..."
        }
        Thread {
            val fetched = runCatching { fetchModules(activeSession) }
            val loaded = fetched.getOrElse { fallbackModules() }
            runOnUiThread {
                if (fetched.exceptionOrNull() is AuthenticationExpiredException) {
                    clearSavedSession()
                    session = null
                    authNotice = "Session expired. Please sign in again."
                    render()
                    return@runOnUiThread
                }
                modules = loaded
                statusText.text = if (fetched.isFailure) "Offline fallback shown" else "Modules refreshed"
                if (::refreshButton.isInitialized) {
                    refreshButton.isEnabled = true
                    refreshButton.text = "Refresh"
                }
                renderModules()
            }
        }.start()
    }

    private fun fetchModules(account: AccountSession): List<ImperialAXModule> {
        val connection = URL(CATALOG_URL).openConnection() as HttpURLConnection
        connection.requestMethod = "GET"
        connection.connectTimeout = 5000
        connection.readTimeout = 5000
        connection.setRequestProperty("Accept", "application/json")
        connection.setRequestProperty("Authorization", "Bearer ${account.token}")
        val status = connection.responseCode
        if (status == 401 || status == 403) throw AuthenticationExpiredException()
        if (status !in 200..299) error("Unexpected status $status")
        val body = connection.inputStream.bufferedReader().use { it.readText() }
        val modulesJson = JSONObject(body).getJSONArray("modules")
        return List(modulesJson.length()) { index ->
            val item = modulesJson.getJSONObject(index)
            val route = item.getJSONObject("route")
            ImperialAXModule(
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
        authNotice = null
        if (email.isBlank() || password.isBlank()) {
            errorLabel.text = "Enter your email and password."
            return
        }
        Thread {
            val account = runCatching { login(email, password) }.getOrNull()
            runOnUiThread {
                if (account == null) {
                    errorLabel.text = "Check your email and password."
                } else {
                    session = account
                    saveSession(account)
                    render()
                    loadModules()
                }
            }
        }.start()
    }

    private fun signInDemo(errorLabel: TextView) {
        errorLabel.text = ""
        authNotice = null
        Thread {
            val account = runCatching { demoLogin() }.getOrNull()
            runOnUiThread {
                if (account == null) {
                    errorLabel.text = "The demo workspace is temporarily unavailable."
                } else {
                    session = account
                    saveSession(account)
                    render()
                    loadModules()
                }
            }
        }.start()
    }

    private fun signUp(
        email: String,
        password: String,
        name: String,
        company: String,
        errorLabel: TextView,
    ) {
        errorLabel.text = ""
        authNotice = null
        if (email.isBlank() || name.isBlank() || password.length < 8) {
            errorLabel.text = "Enter a name and a password with at least 8 characters."
            return
        }
        Thread {
            val account = runCatching { signup(email, password, name, company) }.getOrNull()
            runOnUiThread {
                if (account == null) {
                    errorLabel.text = "Could not create this account. Try another email or password."
                } else {
                    session = account
                    saveSession(account)
                    signupMode = false
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
        return parseSession(JSONObject(connection.inputStream.bufferedReader().use { it.readText() }))
    }

    private fun demoLogin(): AccountSession {
        val connection = URL(DEMO_LOGIN_URL).openConnection() as HttpURLConnection
        connection.requestMethod = "POST"
        connection.connectTimeout = 5000
        connection.readTimeout = 5000
        connection.setRequestProperty("Accept", "application/json")
        connection.setRequestProperty("Content-Type", "application/json")
        connection.doOutput = true
        val payload = JSONObject()
            .put("email", "demo@imperialax.com")
            .put("password", "")
            .toString()
        connection.outputStream.use { stream ->
            stream.write(payload.toByteArray(Charsets.UTF_8))
        }
        if (connection.responseCode !in 200..299) error("Unexpected status ${connection.responseCode}")
        return parseSession(JSONObject(connection.inputStream.bufferedReader().use { it.readText() }))
    }

    private fun signup(email: String, password: String, name: String, company: String): AccountSession {
        val connection = URL(SIGNUP_URL).openConnection() as HttpURLConnection
        connection.requestMethod = "POST"
        connection.connectTimeout = 5000
        connection.readTimeout = 5000
        connection.setRequestProperty("Accept", "application/json")
        connection.setRequestProperty("Content-Type", "application/json")
        connection.doOutput = true
        val trimmedCompany = company.trim()
        val payload = JSONObject()
            .put("email", email.trim().lowercase())
            .put("password", password)
            .put("name", name.trim())
            .put("company", if (trimmedCompany.isBlank()) JSONObject.NULL else trimmedCompany)
            .toString()
        connection.outputStream.use { stream ->
            stream.write(payload.toByteArray(Charsets.UTF_8))
        }
        if (connection.responseCode !in 200..299) error("Unexpected status ${connection.responseCode}")
        return parseSession(JSONObject(connection.inputStream.bufferedReader().use { it.readText() }))
    }

    private fun parseSession(body: JSONObject): AccountSession {
        val user = body.getJSONObject("user")
        return AccountSession(
            token = body.getString("access_token"),
            email = user.getString("email"),
            name = cleanAccountName(user.getString("name")),
            entitlements = body.getJSONArray("entitlements").toStringList(),
            expiresAt = body.optString("expires_at").ifBlank { null },
        )
    }

    private fun createLaunchUrl(target: String, token: String): String {
        val connection = URL(LAUNCH_CODE_URL).openConnection() as HttpURLConnection
        connection.requestMethod = "POST"
        connection.connectTimeout = 5_000
        connection.readTimeout = 8_000
        connection.setRequestProperty("Accept", "application/json")
        connection.setRequestProperty("Content-Type", "application/json")
        connection.setRequestProperty("Authorization", "Bearer $token")
        connection.doOutput = true
        connection.outputStream.use { stream ->
            stream.write(JSONObject().put("target", target).toString().toByteArray(Charsets.UTF_8))
        }
        if (connection.responseCode !in 200..299) error("Unexpected status ${connection.responseCode}")
        val body = JSONObject(connection.inputStream.bufferedReader().use { it.readText() })
        return body.getString("launch_url")
    }

    private fun saveSession(account: AccountSession) {
        val payload = JSONObject()
            .put("token", account.token)
            .put("email", account.email)
            .put("name", account.name)
            .put("entitlements", account.entitlements.joinToString(","))
            .put("expires_at", account.expiresAt ?: "")
            .put("saved_at_ms", account.savedAtMs)
            .toString()
        val encrypted = encryptSession(payload)
        getSharedPreferences(SESSION_PREFS, MODE_PRIVATE).edit()
            .clear()
            .putString(SECURE_SESSION_KEY, encrypted)
            .apply()
    }

    private fun loadSession(): AccountSession? {
        val prefs = getSharedPreferences(SESSION_PREFS, MODE_PRIVATE)
        val encrypted = prefs.getString(SECURE_SESSION_KEY, null)
        val account = if (encrypted != null) {
            runCatching { accountFromStoredJson(JSONObject(decryptSession(encrypted))) }.getOrNull()
        } else {
            migrateLegacySession()
        } ?: return null
        if (isSessionExpired(account)) {
            clearSavedSession()
            authNotice = "Session expired. Please sign in again."
            return null
        }
        return account
    }

    private fun expireSessionIfNeeded(): Boolean {
        val activeSession = session ?: return false
        if (!isSessionExpired(activeSession)) return false
        clearSavedSession()
        session = null
        authNotice = "Session expired. Please sign in again."
        render()
        return true
    }

    private fun isSessionExpired(account: AccountSession): Boolean {
        val serverExpired = account.expiresAt?.let { value ->
            runCatching { Instant.parse(value).toEpochMilli() <= System.currentTimeMillis() }
                .getOrDefault(false)
        } ?: false
        return serverExpired || System.currentTimeMillis() - account.savedAtMs >= SESSION_LIFETIME_MS
    }

    private fun accountFromStoredJson(body: JSONObject): AccountSession = AccountSession(
        token = body.getString("token"),
        email = body.optString("email"),
        name = cleanAccountName(body.optString("name", "ImperialAX Account")),
        entitlements = body.optString("entitlements").split(",").filter { it.isNotBlank() },
        expiresAt = body.optString("expires_at").ifBlank { null },
        savedAtMs = body.optLong("saved_at_ms", System.currentTimeMillis()),
    )

    private fun migrateLegacySession(): AccountSession? {
        val prefs = getSharedPreferences(SESSION_PREFS, MODE_PRIVATE)
        val token = prefs.getString("token", null) ?: return null
        val account = AccountSession(
            token = token,
            email = prefs.getString("email", "") ?: "",
            name = cleanAccountName(prefs.getString("name", "ImperialAX Account") ?: "ImperialAX Account"),
            entitlements = prefs.getString("entitlements", "")
                ?.split(",")?.filter { it.isNotBlank() } ?: emptyList(),
            savedAtMs = prefs.getLong("saved_at_ms", System.currentTimeMillis()),
        )
        saveSession(account)
        return account
    }

    private fun sessionKey(): SecretKey {
        val keyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (keyStore.getKey(SESSION_KEY_ALIAS, null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").run {
            init(
                KeyGenParameterSpec.Builder(
                    SESSION_KEY_ALIAS,
                    KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
                )
                    .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                    .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                    .build()
            )
            generateKey()
        }
    }

    private fun encryptSession(value: String): String {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, sessionKey())
        return JSONObject()
            .put("iv", Base64.encodeToString(cipher.iv, Base64.NO_WRAP))
            .put("data", Base64.encodeToString(cipher.doFinal(value.toByteArray()), Base64.NO_WRAP))
            .toString()
    }

    private fun decryptSession(value: String): String {
        val envelope = JSONObject(value)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        val iv = Base64.decode(envelope.getString("iv"), Base64.NO_WRAP)
        cipher.init(Cipher.DECRYPT_MODE, sessionKey(), GCMParameterSpec(128, iv))
        return String(
            cipher.doFinal(Base64.decode(envelope.getString("data"), Base64.NO_WRAP)),
            Charsets.UTF_8,
        )
    }

    private fun clearSavedSession() {
        getSharedPreferences(SESSION_PREFS, MODE_PRIVATE).edit().clear().apply()
    }

    private fun cleanAccountName(name: String): String {
        val legacyBrand = "Lu" + "velox"
        return when (name.trim()) {
            "$legacyBrand Demo", "ImperialAX Demo" -> "Demo Account"
            "$legacyBrand Account", "ImperialAX Account" -> "ImperialAX Account"
            else -> name
        }
    }

    private fun signOut() {
        clearSavedSession()
        session = null
        authNotice = null
        render()
    }

    private fun fallbackModules(): List<ImperialAXModule> = listOf(
        ImperialAXModule(
            id = "laminate",
            name = "Laminate",
            shortName = "Laminate",
            category = "Composite",
            summary = "Predict Type, Pt, and response curve.",
            icon = "layers",
            status = "active",
            entitlementKey = "module.laminate",
            access = "granted",
            accessReason = "Available in the ImperialAX MVP workspace.",
            tags = listOf("Double-Double", "Pt", "Force-displacement"),
            capabilities = listOf("response_prediction", "curve_chart", "history", "comparison"),
            route = ModuleRoute("https://laminate.imperialax.com", "/api/v1/dd-laminate"),
        ),
        ImperialAXModule(
            id = "injection",
            name = "Injection",
            shortName = "Injection",
            category = "Molding",
            summary = "Predict sprue and filling pressure.",
            icon = "gauge",
            status = "active",
            entitlementKey = "module.injection",
            access = "granted",
            accessReason = "Available in the ImperialAX MVP workspace.",
            tags = listOf("Moldex3D", "Sprue pressure", "Filling pressure"),
            capabilities = listOf("sprue_pressure", "filling_histogram", "filling_animation", "history"),
            route = ModuleRoute("https://injection.imperialax.com", "/api/v1/simple-injection"),
        ),
        ImperialAXModule(
            id = "optimization",
            name = "Optimization",
            shortName = "Optimize",
            category = "Design",
            summary = "Rank promising design candidates.",
            icon = "sparkles",
            status = "active",
            entitlementKey = "module.optimization",
            access = "locked",
            accessReason = "Requires Optimization module access.",
            tags = listOf("DOE", "Ranking", "Design space"),
            capabilities = listOf("candidate_ranking", "batch_prediction"),
            route = ModuleRoute("https://ai.imperialax.com/optimization.html", "/api/v1/optimization"),
        ),
    )

    private fun showAccountDialog() {
        val account = session ?: return
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(10), dp(20), dp(4))
            addView(title(account.name, 24f))
            addView(label(account.email, V2.muted, 14f, Typeface.BOLD), margin(top = 4, bottom = 14))
            addView(label("Licensed modules", V2.ink, 17f, Typeface.BOLD), margin(bottom = 8))
            modules.forEach { module ->
                val row = LinearLayout(context).apply {
                    orientation = LinearLayout.VERTICAL
                    setPadding(dp(12), dp(10), dp(12), dp(10))
                    background = strokedRounded(V2.field, V2.line, dp(8))
                    addView(label("${if (module.isGranted) "On" else "Locked"} - ${module.name}", if (module.isGranted) V2.green else V2.muted, 14f, Typeface.BOLD))
                    addView(label(module.accessReason.ifBlank { module.entitlementKey }, V2.muted, 12f, Typeface.NORMAL), margin(top = 2))
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

    private fun showAccessDialog(module: ImperialAXModule) {
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(10), dp(20), dp(4))
            addView(label(module.category.uppercase(), accentFor(module), 12f, Typeface.BOLD))
            addView(title(module.name, 28f), margin(top = 4))
            addView(paragraph(module.summary), margin(top = 8, bottom = 14))
            addView(label("Access", V2.ink, 17f, Typeface.BOLD))
            addView(paragraph(module.accessReason.ifBlank { "This module requires an ImperialAX license." }), margin(top = 6))
            addView(label("Entitlement: ${module.entitlementKey}", V2.muted, 12f, Typeface.BOLD), margin(top = 8, bottom = 14))
            addView(label("Included capabilities", V2.ink, 17f, Typeface.BOLD), margin(bottom = 8))
            module.capabilities.forEach { capability ->
                addView(label("- ${capability.replace("_", " ")}", V2.muted, 14f, Typeface.BOLD), margin(bottom = 4))
            }
        }
        AlertDialog.Builder(this)
            .setTitle("Module access")
            .setView(content)
            .setPositiveButton("Request access") { _, _ -> requestAccess(module) }
            .setNegativeButton("Done", null)
            .show()
    }

    private fun requestAccess(module: ImperialAXModule) {
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
                    .put("message", "Requested from ImperialAX Android app.")
                    .toString()
                connection.outputStream.use { stream ->
                    stream.write(payload.toByteArray(Charsets.UTF_8))
                }
                if (connection.responseCode !in 200..299) error("Unexpected status ${connection.responseCode}")
                JSONObject(connection.inputStream.bufferedReader().use { it.readText() }).getString("message")
            }.getOrElse {
                "Request saved locally. We could not reach the ImperialAX server right now."
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

    private fun workflowStrip(): LinearLayout {
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(14), dp(12), dp(14), dp(12))
            background = strokedRounded(Color.WHITE, V2.line, dp(8))
            listOf(
                Triple("01", "Account", "Sign in once to open your modules."),
                Triple("02", "Choose module", "Laminate, Injection, Optimization"),
                Triple("03", "Forecast", "Open a focused model workspace."),
            ).forEachIndexed { index, item ->
                addView(stepRow(item.first, item.second, item.third), margin(top = if (index == 0) 0 else 8))
            }
        }
    }

    private fun stepRow(number: String, title: String, subtitle: String): LinearLayout {
        return LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            addView(label(number, Color.WHITE, 11f, Typeface.BOLD).apply {
                gravity = Gravity.CENTER
                background = rounded(V2.ink, dp(8))
            }, LinearLayout.LayoutParams(dp(38), dp(38)))
            addView(LinearLayout(context).apply {
                orientation = LinearLayout.VERTICAL
                addView(label(title, V2.ink, 13f, Typeface.BOLD))
                addView(label(subtitle, V2.muted, 12f, Typeface.NORMAL))
            }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                marginStart = dp(10)
            })
        }
    }

    private fun org.json.JSONArray.toStringList(): List<String> = List(length()) { index -> getString(index) }

    private fun title(text: String, size: Float): TextView = label(text, V2.ink, size, Typeface.BOLD)

    private fun paragraph(text: String): TextView = label(text, V2.muted, 15f, Typeface.NORMAL).apply {
        setLineSpacing(dp(3).toFloat(), 1.0f)
    }

    private fun label(text: String, textColor: Int, size: Float, style: Int): TextView {
        return TextView(this).apply {
            this.text = text
            textSize = size
            setTextColor(textColor)
            useAppFont(style)
            includeFontPadding = true
        }
    }

    private fun input(hint: String): EditText {
        return EditText(this).apply {
            this.hint = hint
            textSize = 16f
            setTextColor(V2.ink)
            setHintTextColor(V2.muted)
            setPadding(dp(14), dp(8), dp(14), dp(8))
            background = strokedRounded(V2.field, V2.line, dp(8))
            minHeight = dp(54)
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

    private fun v2PanelBackground() = android.graphics.drawable.GradientDrawable().apply {
        setColor(Color.WHITE)
        cornerRadius = dp(8).toFloat()
        setStroke(dp(1), V2.line)
    }

    private fun commandButtonBackground() = android.graphics.drawable.GradientDrawable().apply {
        orientation = android.graphics.drawable.GradientDrawable.Orientation.LEFT_RIGHT
        colors = intArrayOf(V2.ink, V2.blue)
        cornerRadius = dp(8).toFloat()
    }

    private fun blueSoftBackground() = android.graphics.drawable.GradientDrawable().apply {
        setColor(V2.blueSoft)
        cornerRadius = dp(999).toFloat()
        setStroke(dp(1), V2.blueLine)
    }

    private fun softBackground(fill: Int, stroke: Int) = softBackground(fill, stroke, dp(999))

    private fun softBackground(fill: Int, stroke: Int, radius: Int) = android.graphics.drawable.GradientDrawable().apply {
        setColor(fill)
        cornerRadius = radius.toFloat()
        setStroke(dp(1), stroke)
    }

    private fun mutedButtonBackground() = android.graphics.drawable.GradientDrawable().apply {
        setColor(V2.field)
        cornerRadius = dp(999).toFloat()
        setStroke(dp(1), V2.line)
    }

    private fun strokedRounded(fill: Int, stroke: Int, radius: Int) = android.graphics.drawable.GradientDrawable().apply {
        setColor(fill)
        setStroke(dp(1), stroke)
        cornerRadius = radius.toFloat()
    }

    private fun color(rgb: Int): Int = Color.rgb(rgb shr 16 and 0xFF, rgb shr 8 and 0xFF, rgb and 0xFF)

    private fun accentFor(module: ImperialAXModule): Int = accentFor(module.id, module.isGranted)

    private fun accentFor(moduleId: String?, granted: Boolean = true): Int {
        if (!granted) return V2.muted
        return when (moduleId) {
            "admin" -> V2.green
            "injection" -> V2.teal
            "optimization" -> V2.amber
            else -> V2.blue
        }
    }

    private fun softFor(module: ImperialAXModule): Int = softFor(module.id, module.isGranted)

    private fun softFor(moduleId: String?, granted: Boolean = true): Int {
        if (!granted) return V2.field
        return when (moduleId) {
            "admin" -> V2.greenSoft
            "injection" -> V2.tealSoft
            "optimization" -> V2.amberSoft
            else -> V2.blueSoft
        }
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}

private object V2 {
    val background: Int = Color.rgb(249, 250, 252)
    val field: Int = Color.rgb(246, 249, 251)
    val surfaceStrong: Int = Color.rgb(251, 252, 254)
    val line: Int = Color.rgb(218, 227, 236)
    val blue: Int = Color.rgb(22, 99, 255)
    val blueSoft: Int = Color.rgb(233, 240, 255)
    val blueLine: Int = Color.rgb(188, 211, 255)
    val teal: Int = Color.rgb(11, 167, 201)
    val tealSoft: Int = Color.rgb(226, 247, 251)
    val tealLight: Int = Color.rgb(174, 229, 239)
    val amber: Int = Color.rgb(183, 121, 31)
    val amberSoft: Int = Color.rgb(255, 244, 222)
    val green: Int = Color.rgb(10, 159, 105)
    val greenSoft: Int = Color.rgb(226, 248, 240)
    val ink: Int = Color.rgb(16, 18, 21)
    val muted: Int = Color.rgb(99, 113, 128)
    val darkMuted: Int = Color.rgb(159, 173, 190)
    val mutedDark: Int = Color.rgb(67, 77, 90)
}
