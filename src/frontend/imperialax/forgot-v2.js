const SESSION_KEY = "imperialax.auth.session.v1";
const LOCALE = document.documentElement.lang.toLowerCase().startsWith("ko") ? "ko" : "en";

const TEXT = {
  en: {
    error: "Enter your name, email, and a new password with at least 8 characters.",
    failed: "We could not verify that name and email. Check the account details.",
    success: "Password reset. Opening the workspace...",
    workspaceUrl: "https://ai.imperialax.com/index.html",
  },
  ko: {
    error: "이름, 이메일, 8자 이상의 새 비밀번호를 입력하세요.",
    failed: "이름과 이메일을 확인할 수 없습니다. 계정 정보를 다시 확인하세요.",
    success: "비밀번호가 재설정되었습니다. 워크스페이스를 여는 중입니다...",
    workspaceUrl: "https://ai.imperialax.com/index.ko.html",
  },
};

const form = document.querySelector("#forgot-v2-form");
const message = document.querySelector("#forgot-message");
const submitButton = form.querySelector(".primary-button");
const fields = {
  name: document.querySelector("#forgot-name"),
  email: document.querySelector("#forgot-email"),
  password: document.querySelector("#forgot-password"),
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
  return value("name") && value("email") && fields.password.value.length >= 8;
}

async function resetPassword() {
  if (!isValid()) {
    setMessage(TEXT[LOCALE].error, "error");
    return;
  }
  setMessage("");
  setBusy(true);
  try {
    const response = await fetch("/api/v1/modules/auth/forgot-password", {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({
        name: value("name"),
        email: value("email").toLowerCase(),
        password: fields.password.value,
      }),
    });
    if (!response.ok) throw new Error(`Password reset failed: ${response.status}`);
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
  resetPassword();
});
