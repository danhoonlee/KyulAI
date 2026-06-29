const SESSION_KEY = "luvelox.auth.session.v1";
const LOCALE = document.documentElement.lang.toLowerCase().startsWith("ko") ? "ko" : "en";

const TEXT = {
  en: {
    accessManaged: "Module access is managed by your Luvelox account.",
    accountWorkspace: "Account workspace",
    available: "Available",
    createAccount: "Create account",
    locked: "Locked",
    planned: "Planned",
    loginError: "Check your email and password.",
    loginMode: "Sign in",
    modules: "modules",
    newAccountHint: "New accounts include Laminate and Injection access.",
    on: "On",
    open: "Open",
    passwordHint: "Use at least 8 characters to create an account.",
    requestAccess: "Request access",
    requestFailed: "Request saved locally. We could not reach the Luvelox server right now.",
    requestMessage: "Requested from Luvelox web app.",
    requestSuccess: "Access request received.",
    requiresLicense: "This module requires a Luvelox license.",
    refresh: "Refresh",
    refreshLoading: "Refreshing...",
    refreshOffline: "Offline fallback shown",
    refreshReady: "Ready",
    refreshUpdated: "Updated",
    showPassword: "Show",
    hidePassword: "Hide",
    signIn: "Sign in",
    signupError: "Enter a name and a password with at least 8 characters.",
    signupMode: "Create account",
  },
  ko: {
    accessManaged: "모듈 접근 권한은 Luvelox 계정 기준으로 관리됩니다.",
    accountWorkspace: "계정 워크스페이스",
    available: "사용 가능",
    createAccount: "계정 만들기",
    locked: "잠김",
    planned: "준비 중",
    loginError: "이메일과 비밀번호를 확인하세요.",
    loginMode: "로그인",
    modules: "개 모듈",
    newAccountHint: "새 계정에는 Laminate와 Injection 접근 권한이 포함됩니다.",
    on: "사용 가능",
    open: "열기",
    passwordHint: "계정을 만들려면 비밀번호 8자 이상을 입력하세요.",
    requestAccess: "접근 권한 요청",
    requestFailed: "요청을 로컬에 저장했습니다. 현재 Luvelox 서버에 연결할 수 없습니다.",
    requestMessage: "Luvelox 웹 앱에서 접근 권한을 요청했습니다.",
    requestSuccess: "접근 권한 요청이 접수되었습니다.",
    requiresLicense: "이 모듈은 Luvelox 라이선스가 필요합니다.",
    refresh: "새로고침",
    refreshLoading: "업데이트 중...",
    refreshOffline: "오프라인 목록 표시 중",
    refreshReady: "준비됨",
    refreshUpdated: "업데이트됨",
    showPassword: "보기",
    hidePassword: "숨기기",
    signIn: "로그인",
    signupError: "이름과 8자 이상의 비밀번호를 입력하세요.",
    signupMode: "계정 만들기",
  },
};

const MODULE_COPY = {
  en: {
    laminate: {
      name: "Laminate",
      short_name: "Laminate",
      category: "Composite",
      summary: "Predict Type, Pt, and response curve.",
      tags: ["Double-Double", "Pt", "Force-displacement"],
      access_reason: "Available in the Luvelox MVP workspace.",
    },
    injection: {
      name: "Injection",
      short_name: "Injection",
      category: "Molding",
      summary: "Predict sprue and filling pressure.",
      tags: ["Moldex3D", "Sprue pressure", "Filling pressure"],
      access_reason: "Available in the Luvelox MVP workspace.",
    },
    optimization: {
      name: "Optimization",
      short_name: "Optimize",
      category: "Design",
      summary: "Search and rank laminate design candidates.",
      tags: ["DOE", "Ranking", "Design space"],
      access_reason: "Requires Optimization module access.",
    },
  },
  ko: {
    laminate: {
      name: "Laminate",
      short_name: "Laminate",
      category: "복합재",
      summary: "Type, Pt, 응답 곡선을 예측합니다.",
      tags: ["Double-Double", "Pt", "힘-변위"],
      access_reason: "현재 Luvelox MVP 워크스페이스에서 사용할 수 있습니다.",
    },
    injection: {
      name: "Injection",
      short_name: "Injection",
      category: "성형",
      summary: "Sprue와 충전 압력을 예측합니다.",
      tags: ["Moldex3D", "Sprue 압력", "충전 압력"],
      access_reason: "현재 Luvelox MVP 워크스페이스에서 사용할 수 있습니다.",
    },
    optimization: {
      name: "Optimization",
      short_name: "Optimization",
      category: "설계",
      summary: "Laminate 설계 후보를 탐색하고 랭킹합니다.",
      tags: ["DOE", "랭킹", "설계 공간"],
      access_reason: "Optimization 모듈 권한이 필요합니다.",
    },
  },
};

const CAPABILITY_COPY = {
  ko: {
    response_prediction: "응답 예측",
    curve_chart: "곡선 차트",
    history: "예측 기록",
    comparison: "비교",
    share_report: "리포트 공유",
    sprue_pressure: "Sprue 압력",
    filling_histogram: "충전 압력 분포",
    filling_animation: "충전 애니메이션",
    candidate_ranking: "후보 랭킹",
    batch_prediction: "배치 예측",
  },
};

const FALLBACK_MODULES = [
  {
    id: "laminate",
    name: "Laminate",
    short_name: "Laminate",
    category: "Composite",
    summary: "Predict Type, Pt, and response curve.",
    icon: "layers",
    status: "active",
    entitlement_key: "module.laminate",
    access: "granted",
    access_reason: "Available in the Luvelox MVP workspace.",
    tags: ["Double-Double", "Pt", "Force-displacement"],
    capabilities: ["response_prediction", "curve_chart", "history", "comparison"],
    route: { web_url: "https://laminate.luvelox.com", api_prefix: "/api/v1/dd-laminate" },
  },
  {
    id: "injection",
    name: "Injection",
    short_name: "Injection",
    category: "Molding",
    summary: "Predict sprue and filling pressure.",
    icon: "gauge",
    status: "active",
    entitlement_key: "module.injection",
    access: "granted",
    access_reason: "Available in the Luvelox MVP workspace.",
    tags: ["Moldex3D", "Sprue pressure", "Filling pressure"],
    capabilities: ["sprue_pressure", "filling_histogram", "animation", "history"],
    route: { web_url: "https://injection.luvelox.com", api_prefix: "/api/v1/simple-injection" },
  },
  {
    id: "optimization",
    name: "Optimization",
    short_name: "Optimize",
    category: "Design",
    summary: "Rank promising design candidates.",
    icon: "sparkles",
    status: "active",
    entitlement_key: "module.optimization",
    access: "locked",
    access_reason: "Requires Optimization module access.",
    tags: ["DOE", "Ranking", "Design space"],
    capabilities: ["candidate_ranking", "batch_prediction"],
    route: { web_url: "https://ai.luvelox.com/optimization.html", api_prefix: "/api/v1/optimization" },
  },
];

const LOCAL_SESSIONS = {
  "demo@luvelox.com": {
    access_token: "demo-token",
    token_type: "bearer",
    user: {
      id: "demo-user",
      email: "demo@luvelox.com",
      name: "Demo Account",
      company: "Luvelox MVP",
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
      company: "Luvelox",
    },
    entitlements: ["module.injection", "module.laminate", "module.optimization"],
  },
};

const ICONS = {
  layers: `
    <svg viewBox="0 0 48 48" aria-hidden="true" focusable="false">
      <path d="M10 17.5 24 10l14 7.5-14 7.5-14-7.5Z" />
      <path d="M10 24.5 24 32l14-7.5" />
      <path d="M10 31.5 24 39l14-7.5" />
      <path d="M18 14.8 30 21.2" />
      <path d="M30 14.8 18 21.2" />
    </svg>
  `,
  gauge: `
    <svg viewBox="0 0 48 48" aria-hidden="true" focusable="false">
      <path d="M15 14h18" />
      <path d="M18 14v10.5c0 6 12 6 12 0V14" />
      <path d="M24 30.5v8" />
      <path d="M18.5 38.5h11" />
      <path d="M16 21.5h16" />
      <path d="M35 24c3.2 2.4 4.8 5 4.8 7.7a6.8 6.8 0 0 1-13.6 0c0-2.7 1.6-5.3 4.8-7.7" />
    </svg>
  `,
  sparkles: `
    <svg viewBox="0 0 48 48" aria-hidden="true" focusable="false">
      <circle cx="24" cy="24" r="11" />
      <circle cx="24" cy="24" r="3.5" />
      <path d="M24 7v6" />
      <path d="M24 35v6" />
      <path d="M7 24h6" />
      <path d="M35 24h6" />
      <path d="m33.5 14.5 4-4" />
      <path d="m10.5 37.5 4-4" />
      <path d="m14.5 14.5-4-4" />
      <path d="m37.5 37.5-4-4" />
    </svg>
  `,
};

const state = {
  session: loadSession(),
  modules: FALLBACK_MODULES,
  selectedModule: null,
};

const loginView = document.querySelector("#login-view");
const workspaceView = document.querySelector("#workspace-view");
const loginForm = document.querySelector("#login-form");
const authTitle = document.querySelector("#auth-title");
const authHint = document.querySelector("#auth-hint");
const emailInput = document.querySelector("#email-input");
const passwordInput = document.querySelector("#password-input");
const passwordToggle = document.querySelector("#password-toggle");
const loginError = document.querySelector("#login-error");
const signinButton = document.querySelector("#signin-button");
const demoButton = document.querySelector("#demo-button");
const grid = document.querySelector("#module-grid");
const template = document.querySelector("#module-card-template");
const refreshButton = document.querySelector("#refresh-button");
const refreshStatus = document.querySelector("#refresh-status");
const signoutButton = document.querySelector("#signout-button");
const accountButton = document.querySelector("#account-button");
const accountLabel = document.querySelector("#account-label");
const accessDialog = document.querySelector("#access-dialog");
const accountDialog = document.querySelector("#account-dialog");
const requestAccessButton = document.querySelector("#request-access-button");
const requestStatus = document.querySelector("#request-status");

function humanize(value) {
  return CAPABILITY_COPY[LOCALE]?.[value] || String(value).replaceAll("_", " ");
}

function badgeText(access, status) {
  if (access === "granted") return TEXT[LOCALE].available;
  if (status === "planned") return TEXT[LOCALE].planned;
  return TEXT[LOCALE].locked;
}

function formatModuleCount(count) {
  return LOCALE === "ko" ? `${count}${TEXT.ko.modules}` : `${count} ${TEXT.en.modules}`;
}

function localizeModule(module) {
  const copy = MODULE_COPY[LOCALE]?.[module.id];
  return copy ? { ...module, ...copy } : module;
}

function normalizeEmail(email) {
  return String(email || "").trim().toLowerCase();
}

function loadSession() {
  try {
    const raw = window.localStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function saveSession(session) {
  state.session = session;
  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

function clearSession() {
  state.session = null;
  window.localStorage.removeItem(SESSION_KEY);
}

function authHeaders() {
  if (!state.session) return {};
  const tokenType = state.session.token_type || "bearer";
  return { Authorization: `${tokenType[0].toUpperCase()}${tokenType.slice(1)} ${state.session.access_token}` };
}

function setBusy(isBusy) {
  signinButton.disabled = isBusy;
  demoButton.disabled = isBusy;
  refreshButton.disabled = isBusy;
  requestAccessButton.disabled = isBusy;
}

function setRefreshState(stateName) {
  const text = TEXT[LOCALE];
  if (stateName === "loading") {
    refreshButton.textContent = text.refreshLoading;
    refreshStatus.textContent = text.refreshLoading;
    return;
  }
  refreshButton.textContent = text.refresh;
  refreshStatus.textContent =
    stateName === "offline" ? text.refreshOffline :
    stateName === "updated" ? text.refreshUpdated :
    text.refreshReady;
}

function renderShell() {
  const signedIn = Boolean(state.session);
  loginView.classList.toggle("is-hidden", signedIn);
  workspaceView.classList.toggle("is-hidden", !signedIn);
  if (!signedIn) return;

  const { user, entitlements = [] } = state.session;
  accountLabel.textContent = user?.name
    ? `${user.name} · ${formatModuleCount(entitlements.length)}`
    : TEXT[LOCALE].accountWorkspace;
}

function renderModules(modules) {
  grid.replaceChildren();
  for (const module of modules) {
    const displayModule = localizeModule(module);
    const card = template.content.firstElementChild.cloneNode(true);
    const locked = module.access && module.access !== "granted";
    card.classList.toggle("locked", locked);
    const icon = card.querySelector(".module-icon");
    icon.classList.add(`module-icon-${module.id}`);
    icon.innerHTML = ICONS[module.icon] || `<span>${escapeHtml(displayModule.name.slice(0, 1))}</span>`;
    card.querySelector(".module-category").textContent = displayModule.category;
    card.querySelector(".module-title").textContent = displayModule.name;
    card.querySelector(".access-badge").textContent = badgeText(module.access, module.status);
    card.querySelector(".module-summary").textContent = displayModule.summary;

    const tagRow = card.querySelector(".tag-row");
    for (const tag of displayModule.tags || []) {
      const item = document.createElement("span");
      item.className = "tag";
      item.textContent = tag;
      tagRow.append(item);
    }

    const capabilityList = card.querySelector(".capability-list");
    for (const capability of (module.capabilities || []).slice(0, 4)) {
      const item = document.createElement("div");
      item.className = "capability";
      item.textContent = humanize(capability);
      capabilityList.append(item);
    }

    const button = card.querySelector(".primary-link");
    button.textContent = locked
      ? TEXT[LOCALE].requestAccess
      : `${TEXT[LOCALE].open} ${displayModule.short_name || displayModule.name}`;
    button.addEventListener("click", () => {
      if (locked) {
        openAccessDialog(module);
      } else {
        window.location.assign(moduleUrl(module));
      }
    });
    grid.append(card);
  }
}

function moduleUrl(module) {
  if (module.id === "optimization" && LOCALE === "ko") {
    return "https://ai.luvelox.com/optimization.ko.html";
  }
  return module.route.web_url;
}

async function signIn(email, password) {
  const normalizedEmail = normalizeEmail(email) || "demo@luvelox.com";
  loginError.textContent = "";
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
    loginError.textContent = TEXT[LOCALE].loginError;
    setBusy(false);
    return;
  }
  renderShell();
  await loadModules();
  setBusy(false);
}

async function demoLogin() {
  const normalizedEmail = normalizeEmail(emailInput.value) || "demo@luvelox.com";
  loginError.textContent = "";
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
      loginError.textContent = TEXT[LOCALE].loginError;
      setBusy(false);
      return;
    }
    saveSession(localSession);
  }
  renderShell();
  await loadModules();
  setBusy(false);
}

async function loadModules() {
  if (!state.session) return;
  setBusy(true);
  setRefreshState("loading");
  let usedFallback = false;
  try {
    const response = await fetch("/api/v1/modules/me", {
      headers: { Accept: "application/json", ...authHeaders() },
    });
    if (!response.ok) throw new Error(`Module catalog failed: ${response.status}`);
    const payload = await response.json();
    state.modules = payload.modules;
    if (payload.user) {
      state.session = { ...state.session, user: payload.user };
      window.localStorage.setItem(SESSION_KEY, JSON.stringify(state.session));
    }
  } catch {
    usedFallback = true;
    state.modules = FALLBACK_MODULES.map((module) => ({
      ...module,
      access: isEntitled(module) ? "granted" : module.access,
    }));
  } finally {
    try {
      renderShell();
      renderModules(state.modules);
    } catch (error) {
      console.error("Could not render Luvelox modules", error);
    } finally {
      setRefreshState(usedFallback ? "offline" : "updated");
      setBusy(false);
    }
  }
}

function isEntitled(module) {
  return (state.session?.entitlements || []).includes(module.entitlement_key);
}

function openAccessDialog(module) {
  const displayModule = localizeModule(module);
  state.selectedModule = module;
  requestStatus.textContent = "";
  document.querySelector("#access-category").textContent = displayModule.category;
  document.querySelector("#access-title").textContent = displayModule.name;
  document.querySelector("#access-summary").textContent = displayModule.summary;
  document.querySelector("#access-reason").textContent =
    displayModule.access_reason || TEXT[LOCALE].requiresLicense;
  document.querySelector("#access-entitlement").textContent = TEXT[LOCALE].accessManaged;

  const capabilities = document.querySelector("#access-capabilities");
  capabilities.replaceChildren();
  for (const capability of module.capabilities || []) {
    const item = document.createElement("div");
    item.className = "capability";
    item.textContent = humanize(capability);
    capabilities.append(item);
  }
  accessDialog.showModal();
}

function openAccountDialog() {
  const user = state.session?.user || {};
  document.querySelector("#account-dialog-name").textContent = user.name || "Luvelox Account";
  document.querySelector("#account-dialog-email").textContent = user.email || "";
  const accessList = document.querySelector("#account-access-list");
  accessList.replaceChildren();
  for (const module of state.modules) {
    const row = document.createElement("div");
    row.className = "access-row";
    row.innerHTML = `
      <span class="${module.access === "granted" ? "granted" : ""}">${module.access === "granted" ? "On" : "Locked"}</span>
      <div>
        <strong>${escapeHtml(localizeModule(module).name)}</strong>
        <p>${escapeHtml(localizeModule(module).access_reason || TEXT[LOCALE].accessManaged)}</p>
      </div>
    `;
    row.querySelector("span").textContent = module.access === "granted" ? TEXT[LOCALE].on : TEXT[LOCALE].locked;
    accessList.append(row);
  }
  accountDialog.showModal();
}

async function requestAccess() {
  const module = state.selectedModule;
  if (!module) return;
  setBusy(true);
  requestStatus.textContent = "";
  try {
    const response = await fetch("/api/v1/modules/request-access", {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({
        module_id: module.id,
        message: TEXT[LOCALE].requestMessage,
      }),
    });
    if (!response.ok) throw new Error(`Request failed: ${response.status}`);
    const payload = await response.json();
    requestStatus.textContent = LOCALE === "ko" ? TEXT.ko.requestSuccess : payload.message || TEXT.en.requestSuccess;
  } catch {
    requestStatus.textContent = TEXT[LOCALE].requestFailed;
  } finally {
    setBusy(false);
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

loginForm.addEventListener("submit", (event) => {
  event.preventDefault();
  signIn(emailInput.value, passwordInput.value);
});

demoButton.addEventListener("click", () => {
  emailInput.value = "";
  passwordInput.value = "";
  demoLogin();
});

passwordToggle.addEventListener("click", () => {
  const isVisible = passwordInput.type === "text";
  passwordInput.type = isVisible ? "password" : "text";
  passwordToggle.textContent = isVisible ? TEXT[LOCALE].showPassword : TEXT[LOCALE].hidePassword;
  passwordToggle.setAttribute("aria-label", passwordToggle.textContent);
  passwordToggle.setAttribute("aria-pressed", String(!isVisible));
  passwordInput.focus();
});

refreshButton.addEventListener("click", loadModules);
requestAccessButton.addEventListener("click", requestAccess);
accountButton.addEventListener("click", openAccountDialog);
signoutButton.addEventListener("click", () => {
  clearSession();
  renderShell();
  renderModules([]);
});

renderShell();
if (state.session) {
  loadModules();
}
