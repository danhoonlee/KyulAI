const SESSION_KEY = "luvelox.auth.session.v1";
const LOCALE = document.documentElement.lang.toLowerCase().startsWith("ko") ? "ko" : "en";

const TEXT = {
  en: {
    locked: "Locked",
    modules: "modules",
    on: "On",
    signIn: "Sign in",
    signInError: "Check your email and password.",
    signedIn: "Signed in. Opening the workspace...",
    signUp: "Create account",
    signUpHint: "New accounts include Laminate and Injection access.",
    signUpError: "Enter a name and a password with at least 8 characters.",
    passwordHint: "Use at least 8 characters to create an account.",
    showPassword: "Show",
    hidePassword: "Hide",
    workspaceUrl: "https://ai.imperialax.com/index.html",
  },
  ko: {
    locked: "잠김",
    modules: "개 모듈",
    on: "사용 가능",
    signIn: "로그인",
    signInError: "이메일과 비밀번호를 확인하세요.",
    signedIn: "로그인되었습니다. 워크스페이스를 여는 중입니다...",
    signUp: "계정 만들기",
    signUpHint: "새 계정에는 Laminate와 Injection 접근 권한이 포함됩니다.",
    signUpError: "이름과 8자 이상의 비밀번호를 입력하세요.",
    passwordHint: "계정을 만들려면 비밀번호 8자 이상을 입력하세요.",
    showPassword: "보기",
    hidePassword: "숨기기",
    workspaceUrl: "https://ai.imperialax.com/index.ko.html",
  },
};

const LOCAL_SESSIONS = {
  "demo@imperialax.com": {
    access_token: "demo-token",
    token_type: "bearer",
    user: {
      id: "demo-user",
      email: "demo@imperialax.com",
      name: "Demo Account",
      company: "ImperialAX Demo",
    },
    entitlements: ["module.injection", "module.laminate"],
  },
  "demo@luvelox.com": {
    access_token: "demo-token",
    token_type: "bearer",
    user: {
      id: "demo-user",
      email: "demo@luvelox.com",
      name: "Demo Account",
      company: "ImperialAX Demo",
    },
    entitlements: ["module.injection", "module.laminate"],
  },
  "danlee@luvelox.com": {
    access_token: "danlee-token",
    token_type: "bearer",
    user: {
      id: "danlee",
      email: "danlee@luvelox.com",
      name: "Dan Lee",
      company: "ImperialAX",
    },
    entitlements: ["module.injection", "module.laminate", "module.optimization"],
  },
};

const form = document.querySelector("#login-v2-form");
const emailInput = document.querySelector("#login-v2-email");
const passwordInput = document.querySelector("#login-v2-password");
const passwordToggle = document.querySelector("#login-v2-password-toggle");
const message = document.querySelector("#login-v2-message");
const demoButton = document.querySelector("#login-v2-demo");
const submitButton = form.querySelector(".primary-button");
const accountName = document.querySelector("#login-v2-account-name");
const accountEmail = document.querySelector("#login-v2-account-email");
const accessCount = document.querySelector("#login-v2-access-count");
const optimizationRow = document.querySelector("#optimization-row");
const optimizationStatus = document.querySelector("#optimization-status");

function normalizeEmail(email) {
  return String(email || "").trim().toLowerCase();
}

function setBusy(isBusy) {
  submitButton.disabled = isBusy;
  demoButton.disabled = isBusy;
}

function setMessage(text, type = "") {
  message.textContent = text;
  message.classList.toggle("is-error", type === "error");
  message.classList.toggle("is-success", type === "success");
}

function formatModuleCount(count) {
  return LOCALE === "ko" ? `${count}${TEXT.ko.modules}` : `${count} ${TEXT.en.modules}`;
}

function saveSession(session) {
  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

function previewAccount() {
  const email = normalizeEmail(emailInput.value) || "demo@imperialax.com";
  const session = LOCAL_SESSIONS[email] || LOCAL_SESSIONS["demo@imperialax.com"];
  const hasOptimization = session.entitlements.includes("module.optimization");

  accountName.textContent = session.user.name;
  accountEmail.textContent = session.user.email;
  accessCount.textContent = formatModuleCount(session.entitlements.length);
  optimizationRow.classList.toggle("is-on", hasOptimization);
  optimizationStatus.textContent = hasOptimization ? TEXT[LOCALE].on : TEXT[LOCALE].locked;
}

async function signIn(email, password) {
  const normalizedEmail = normalizeEmail(email) || "demo@imperialax.com";
  setMessage("");
  setBusy(true);

  try {
    const response = await fetch("/api/v1/modules/auth/login", {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ email: normalizedEmail, password }),
    });
    if (!response.ok) throw new Error(`Login failed: ${response.status}`);
    saveSession(await response.json());
  } catch {
    setMessage(TEXT[LOCALE].signInError, "error");
    setBusy(false);
    return;
  }

  setMessage(TEXT[LOCALE].signedIn, "success");
  window.setTimeout(() => {
    window.location.assign(TEXT[LOCALE].workspaceUrl);
  }, 520);
}

async function demoLogin() {
  const normalizedEmail = normalizeEmail(emailInput.value) || "demo@imperialax.com";
  setMessage("");
  setBusy(true);
  try {
    const response = await fetch("/api/v1/modules/auth/demo-login", {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ email: normalizedEmail, password: "" }),
    });
    if (!response.ok) throw new Error(`Demo login failed: ${response.status}`);
    saveSession(await response.json());
  } catch {
    const localSession = LOCAL_SESSIONS[normalizedEmail];
    if (!localSession) {
      setMessage(TEXT[LOCALE].signInError, "error");
      setBusy(false);
      return;
    }
    saveSession(localSession);
  }
  setMessage(TEXT[LOCALE].signedIn, "success");
  window.setTimeout(() => {
    window.location.assign(TEXT[LOCALE].workspaceUrl);
  }, 520);
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  signIn(emailInput.value, passwordInput.value);
});

demoButton.addEventListener("click", () => {
  emailInput.value = "";
  passwordInput.value = "";
  previewAccount();
  demoLogin();
});

emailInput.addEventListener("input", previewAccount);

passwordToggle.addEventListener("click", () => {
  const isVisible = passwordInput.type === "text";
  passwordInput.type = isVisible ? "password" : "text";
  passwordToggle.textContent = isVisible ? TEXT[LOCALE].showPassword : TEXT[LOCALE].hidePassword;
  passwordToggle.setAttribute("aria-label", passwordToggle.textContent);
  passwordToggle.setAttribute("aria-pressed", String(!isVisible));
  passwordInput.focus();
});

previewAccount();
