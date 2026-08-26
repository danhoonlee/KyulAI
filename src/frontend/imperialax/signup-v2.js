const SESSION_KEY = "imperialax.auth.session.v1";
const LOCALE = document.documentElement.lang.toLowerCase().startsWith("ko") ? "ko" : "en";

const TEXT = {
  en: {
    error: "Enter every field and use a password with at least 8 characters.",
    failed: "Could not create this account. Try another email or password.",
    success: "Account created. Opening the workspace...",
    workspaceUrl: "https://ai.imperialax.com/index.html",
  },
  ko: {
    error: "모든 항목을 입력하고 비밀번호는 8자 이상으로 설정하세요.",
    failed: "계정을 만들 수 없습니다. 다른 이메일이나 비밀번호를 사용해보세요.",
    success: "계정이 생성되었습니다. 워크스페이스를 여는 중입니다...",
    workspaceUrl: "https://ai.imperialax.com/index.ko.html",
  },
};

const form = document.querySelector("#signup-v2-form");
const message = document.querySelector("#signup-message");
const submitButton = form.querySelector(".primary-button");
const fields = {
  name: document.querySelector("#signup-name"),
  company: document.querySelector("#signup-company"),
  location: document.querySelector("#signup-location"),
  mobile: document.querySelector("#signup-mobile"),
  email: document.querySelector("#signup-email"),
  password: document.querySelector("#signup-password"),
};

function value(key) {
  return fields[key].value.trim();
}

function setBusy(isBusy) {
  submitButton.disabled = isBusy;
}

function setMessage(text, type = "") {
  message.textContent = text;
  message.classList.toggle("is-error", type === "error");
  message.classList.toggle("is-success", type === "success");
}

function saveSession(session) {
  const metadata = { user: session.user, entitlements: session.entitlements || [] };
  window.localStorage.setItem(SESSION_KEY, JSON.stringify(metadata));
}

function isValid() {
  return (
    value("name") &&
    value("company") &&
    value("location") &&
    value("mobile") &&
    value("email") &&
    fields.password.value.length >= 8
  );
}

async function signUp() {
  if (!isValid()) {
    setMessage(TEXT[LOCALE].error, "error");
    return;
  }
  setMessage("");
  setBusy(true);
  try {
    const response = await fetch("/api/v1/modules/auth/signup", {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({
        name: value("name"),
        company: value("company"),
        location: value("location"),
        mobile: value("mobile"),
        email: value("email").toLowerCase(),
        password: fields.password.value,
      }),
    });
    if (!response.ok) throw new Error(`Signup failed: ${response.status}`);
    saveSession(await response.json());
  } catch {
    setMessage(TEXT[LOCALE].failed, "error");
    setBusy(false);
    return;
  }

  setMessage(TEXT[LOCALE].success, "success");
  window.setTimeout(() => {
    window.location.assign(TEXT[LOCALE].workspaceUrl);
  }, 520);
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  signUp();
});
