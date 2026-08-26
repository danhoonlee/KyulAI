(() => {
  const SESSION_KEY = "imperialax.auth.session.v1";
  const LAMINATE_ENTITLEMENT = "module.laminate";
  const isKo = document.documentElement.lang.toLowerCase().startsWith("ko");
  const isLocalStaticHost = ["localhost", "127.0.0.1"].includes(window.location.hostname)
    && !["8000", "80", "443"].includes(window.location.port);
  const modulesBase = isLocalStaticHost
    ? `http://${window.location.hostname || "localhost"}:8000/api/v1/modules`
    : `${window.location.origin}/api/v1/modules`;
  const laminateBase = isLocalStaticHost
    ? `http://${window.location.hostname || "localhost"}:8000/api/v1/dd-laminate`
    : `${window.location.origin}/api/v1/dd-laminate`;
  const nativeFetch = window.fetch.bind(window);

  const text = {
    lockedTitle: isKo ? "라이선스 로그인 필요" : "License sign-in required",
    lockedCopy: isKo
      ? "Laminate Forecast를 사용하려면 module.laminate 권한이 있는 계정으로 로그인해 주세요."
      : "Sign in with an account that has module.laminate access to use Laminate Forecast.",
    email: isKo ? "이메일" : "Email",
    password: isKo ? "비밀번호" : "Password",
    show: isKo ? "보기" : "Show",
    hide: isKo ? "숨기기" : "Hide",
    signIn: isKo ? "로그인" : "Sign in",
    signingIn: isKo ? "확인 중..." : "Checking...",
    signOut: isKo ? "로그아웃" : "Sign out",
    licenseReady: isKo ? "라이선스 확인됨" : "License verified",
    licenseDenied: isKo
      ? "이 계정에는 Laminate 사용 권한이 없습니다."
      : "This account does not include Laminate access.",
    loginFailed: isKo ? "로그인에 실패했습니다." : "Sign-in failed.",
    offline: isKo
      ? "라이선스 서버에 연결할 수 없습니다. 로컬 서버가 실행 중인지 확인해 주세요."
      : "Could not reach the license server. Check that the local server is running.",
    releaseHint: isKo
      ? "배포판에서는 관리자 계정에서 사용자 권한을 발급한 뒤 사용합니다."
      : "Release builds should use admin-issued accounts and module access.",
  };

  function readSession() {
    try {
      return JSON.parse(localStorage.getItem(SESSION_KEY) || "null");
    } catch {
      return null;
    }
  }

  function writeSession(session) {
    localStorage.setItem(SESSION_KEY, JSON.stringify({
      user: session?.user || null,
      entitlements: session?.entitlements || [],
    }));
  }

  function clearSession() {
    localStorage.removeItem(SESSION_KEY);
  }

  function buildGate() {
    const gate = document.createElement("section");
    gate.className = "license-gate hidden";
    gate.id = "license-gate";
    gate.innerHTML = `
      <div class="license-card" role="dialog" aria-modal="true" aria-labelledby="license-title">
        <p class="license-kicker">Laminate Forecast AI</p>
        <h2 id="license-title">${text.lockedTitle}</h2>
        <p class="license-copy">${text.lockedCopy}</p>
        <form class="license-form" id="license-form">
          <label>
            ${text.email}
            <input name="email" type="email" autocomplete="username" placeholder="user@example.com" required />
          </label>
          <label>
            ${text.password}
            <span class="license-password-row">
              <input name="password" type="password" autocomplete="current-password" required />
              <button type="button" class="license-ghost" id="license-password-toggle">${text.show}</button>
            </span>
          </label>
          <button class="primary" type="submit">${text.signIn}</button>
        </form>
        <p class="license-error hidden" id="license-error"></p>
        <p class="license-hint">${text.releaseHint}</p>
      </div>
    `;
    document.body.append(gate);
    return gate;
  }

  async function fetchMyModules() {
    const response = await nativeFetch(`${modulesBase}/me`, { credentials: "include" });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || `HTTP ${response.status}`);
    }
    return data;
  }

  async function serverRequiresAuth() {
    try {
      const response = await nativeFetch(`${laminateBase}/models`);
      return response.status === 401 || response.status === 403;
    } catch {
      return false;
    }
  }

  function hasLaminateAccess(data) {
    return Boolean(data?.user) && Array.isArray(data?.modules) && data.modules.some((module) => (
      module.entitlement_key === LAMINATE_ENTITLEMENT && module.access === "granted"
    ));
  }

  function setLocked(locked, sessionData = null) {
    document.body.classList.toggle("auth-locked", locked);
    const gate = document.querySelector("#license-gate") || buildGate();
    gate.classList.toggle("hidden", !locked);
    const userStatus = document.querySelector("#license-user-status") || document.createElement("button");
    userStatus.id = "license-user-status";
    userStatus.className = "language-link header-action header-action-account license-user-status";
    userStatus.type = "button";
    const accountDetail = sessionData?.user?.email
      ? `${text.licenseReady} · ${sessionData.user.email}`
      : text.licenseReady;
    userStatus.textContent = locked ? text.signIn : text.signOut;
    userStatus.title = locked ? text.lockedTitle : accountDetail;
    userStatus.setAttribute("aria-label", locked ? text.lockedTitle : `${accountDetail} · ${text.signOut}`);
    userStatus.onclick = async () => {
      try {
        await nativeFetch(`${modulesBase}/auth/logout`, { method: "POST", credentials: "include" });
      } catch {
        // Clear the local account hint even if sign-out cannot reach the server.
      }
      clearSession();
      window.location.reload();
    };
    if (!userStatus.isConnected) {
      const utilityGroup = document.querySelector(".top-action-group-secondary")
        || document.querySelector(".top-actions");
      utilityGroup?.classList.add("has-account");
      const status = utilityGroup?.querySelector("#api-status");
      if (status) {
        utilityGroup.insertBefore(userStatus, status);
      } else {
        utilityGroup?.append(userStatus);
      }
    }
  }

  async function verifySession() {
    const requiresAuth = await serverRequiresAuth();
    try {
      const data = await fetchMyModules();
      if (hasLaminateAccess(data)) {
        writeSession(data);
        setLocked(false, data);
        return true;
      }
      setLocked(requiresAuth);
      if (requiresAuth) {
        document.querySelector("#license-error")?.classList.remove("hidden");
        const error = document.querySelector("#license-error");
        if (error) error.textContent = text.licenseDenied;
      }
    } catch {
      clearSession();
      setLocked(requiresAuth);
    }
    return false;
  }

  function bindGate() {
    const gate = document.querySelector("#license-gate") || buildGate();
    const form = gate.querySelector("#license-form");
    const error = gate.querySelector("#license-error");
    const toggle = gate.querySelector("#license-password-toggle");
    const password = gate.querySelector('input[name="password"]');

    toggle?.addEventListener("click", () => {
      const visible = password.type === "text";
      password.type = visible ? "password" : "text";
      toggle.textContent = visible ? text.show : text.hide;
    });

    form?.addEventListener("submit", async (event) => {
      event.preventDefault();
      error?.classList.add("hidden");
      const submit = form.querySelector('button[type="submit"]');
      const original = submit.textContent;
      submit.disabled = true;
      submit.textContent = text.signingIn;
      try {
        const formData = new FormData(form);
        const response = await nativeFetch(`${modulesBase}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: String(formData.get("email") || ""),
            password: String(formData.get("password") || ""),
          }),
          credentials: "include",
        });
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || text.loginFailed);
        }
        writeSession(data);
        const verified = await verifySession();
        if (verified) {
          window.location.reload();
        }
      } catch (err) {
        if (error) {
          error.textContent = err?.message || text.offline;
          error.classList.remove("hidden");
        }
      } finally {
        submit.disabled = false;
        submit.textContent = original;
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    buildGate();
    bindGate();
    verifySession();
  });
})();
