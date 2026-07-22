const TOKEN_KEY = "luvelox.admin.token.v1";
const IS_KO = document.documentElement.lang.toLowerCase().startsWith("ko");

const TEXT = {
  loadError: IS_KO ? "가입자 목록을 불러오지 못했습니다." : "Could not load users.",
  loaded: IS_KO ? "가입자 목록을 불러왔습니다." : "Users loaded.",
  missing: IS_KO ? "관리자 토큰을 입력하세요." : "Enter the admin token.",
  none: IS_KO ? "가입자가 없습니다." : "No users found.",
  resetButton: IS_KO ? "비밀번호 재설정" : "Reset password",
  resetPrompt: IS_KO
    ? "새 임시 비밀번호를 입력하세요. 최소 8자입니다."
    : "Enter a new temporary password. Minimum 8 characters.",
  resetShort: IS_KO ? "비밀번호는 최소 8자여야 합니다." : "Password must be at least 8 characters.",
  resetDone: IS_KO ? "비밀번호를 재설정했습니다." : "Password reset.",
  resetError: IS_KO ? "비밀번호를 재설정하지 못했습니다." : "Could not reset password.",
  entitlementDone: IS_KO ? "모듈 권한을 저장했습니다." : "Module access updated.",
  entitlementError: IS_KO ? "모듈 권한을 저장하지 못했습니다." : "Could not update module access.",
  createDone: IS_KO ? "계정을 생성했습니다." : "Account created.",
  createError: IS_KO ? "계정을 생성하지 못했습니다." : "Could not create account.",
  createLoadFirst: IS_KO ? "가입자 목록을 먼저 불러오면 권한을 선택할 수 있습니다." : "Load users first to choose module access.",
  editButton: IS_KO ? "정보 수정" : "Edit profile",
  editName: IS_KO ? "이름" : "Name",
  editCompany: IS_KO ? "회사" : "Company",
  editLocation: IS_KO ? "지역" : "Location",
  editMobile: IS_KO ? "휴대폰" : "Mobile",
  editDone: IS_KO ? "계정 정보를 저장했습니다." : "Account profile updated.",
  editError: IS_KO ? "계정 정보를 저장하지 못했습니다." : "Could not update account profile.",
};

const tokenInput = document.querySelector("#admin-token");
const loadButton = document.querySelector("#load-users");
const clearButton = document.querySelector("#clear-token");
const createForm = document.querySelector("#admin-create-form");
const createButton = document.querySelector("#create-user");
const createEntitlements = document.querySelector("#create-entitlements");
const statusText = document.querySelector("#admin-status");
const userCount = document.querySelector("#user-count");
const sessionCount = document.querySelector("#session-count");
const entitlementCount = document.querySelector("#entitlement-count");
const usersBody = document.querySelector("#admin-users");

const launchParams = new URLSearchParams(window.location.search);
const launchToken = launchParams.get("session_token") || launchParams.get("admin_token") || "";
tokenInput.value = launchToken || window.localStorage.getItem(TOKEN_KEY) || "";
let currentUsers = [];
let adminModules = [];

function setStatus(text, isError = false) {
  statusText.textContent = text;
  statusText.classList.toggle("is-error", isError);
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(IS_KO ? "ko-KR" : "en-US", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function cell(text) {
  const element = document.createElement("td");
  element.textContent = text || "-";
  return element;
}

function inputValue(selector) {
  return document.querySelector(selector).value.trim();
}

function optionalInputValue(selector) {
  const value = inputValue(selector);
  return value || null;
}

function tokenHeaders(extra = {}) {
  return { ...extra, "X-ImperialAX-Admin-Token": tokenInput.value.trim() };
}

function selectedCreateEntitlements() {
  return Array.from(createEntitlements.querySelectorAll("input[type='checkbox']:checked")).map((input) => input.value);
}

function renderCreateEntitlements() {
  createEntitlements.replaceChildren();
  if (!adminModules.length) {
    const note = document.createElement("p");
    note.className = "admin-inline-note";
    note.textContent = TEXT.createLoadFirst;
    createEntitlements.append(note);
    return;
  }
  const defaultEnabled = new Set(["module.laminate", "module.injection"]);
  for (const module of adminModules) {
    const label = document.createElement("label");
    label.className = "admin-module-toggle";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = module.entitlement_key;
    checkbox.checked = defaultEnabled.has(module.entitlement_key);
    const name = document.createElement("span");
    name.textContent = module.short_name || module.name;
    const status = document.createElement("small");
    status.textContent = module.status;
    label.append(checkbox, name, status);
    createEntitlements.append(label);
  }
}

function moduleAccessCell(user) {
  const element = document.createElement("td");
  element.className = "admin-module-cell";
  const granted = new Set(user.entitlements || []);
  for (const module of adminModules) {
    const label = document.createElement("label");
    label.className = "admin-module-toggle";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = granted.has(module.entitlement_key);
    checkbox.addEventListener("change", () => updateEntitlements(user, element, checkbox));
    const name = document.createElement("span");
    name.textContent = module.short_name || module.name;
    const status = document.createElement("small");
    status.textContent = module.status;
    label.append(checkbox, name, status);
    element.append(label);
  }
  return element;
}

function actionCell(user) {
  const element = document.createElement("td");
  element.className = "admin-actions-cell";
  const editButton = document.createElement("button");
  editButton.className = "admin-action-button";
  editButton.type = "button";
  editButton.textContent = TEXT.editButton;
  editButton.addEventListener("click", () => editProfile(user, editButton));
  const resetButton = document.createElement("button");
  resetButton.className = "admin-action-button";
  resetButton.type = "button";
  resetButton.textContent = TEXT.resetButton;
  resetButton.addEventListener("click", () => resetPassword(user, resetButton));
  element.append(editButton, resetButton);
  return element;
}

function renderUsers(users) {
  currentUsers = users;
  usersBody.replaceChildren();
  if (!users.length) {
    const row = document.createElement("tr");
    const empty = document.createElement("td");
    empty.colSpan = 9;
    empty.textContent = TEXT.none;
    row.append(empty);
    usersBody.append(row);
    return;
  }

  for (const user of users) {
    const row = document.createElement("tr");
    row.append(
      cell(user.name),
      cell(user.email),
      cell(user.company),
      cell(user.location),
      cell(user.mobile),
      moduleAccessCell(user),
      cell(String(user.session_count ?? 0)),
      cell(formatDate(user.created_at)),
      actionCell(user),
    );
    usersBody.append(row);
  }
}

function renderSummary(users) {
  userCount.textContent = String(users.length);
  sessionCount.textContent = String(users.reduce((total, user) => total + (user.session_count || 0), 0));
  entitlementCount.textContent = String(users.reduce((total, user) => total + (user.entitlements || []).length, 0));
}

async function loadUsers() {
  const token = tokenInput.value.trim();
  if (!token) {
    setStatus(TEXT.missing, true);
    return;
  }
  loadButton.disabled = true;
  setStatus("");
  try {
    const response = await fetch("/api/v1/modules/admin/users", {
      headers: { "X-ImperialAX-Admin-Token": token },
    });
    if (!response.ok) throw new Error(`Admin users failed: ${response.status}`);
    const data = await response.json();
    window.localStorage.setItem(TOKEN_KEY, token);
    adminModules = data.modules || [];
    currentUsers = data.users || [];
    renderCreateEntitlements();
    renderSummary(currentUsers);
    renderUsers(currentUsers);
    setStatus(TEXT.loaded);
  } catch {
    setStatus(TEXT.loadError, true);
  } finally {
    loadButton.disabled = false;
  }
}

async function updateEntitlements(user, cellElement, changedInput) {
  const token = tokenInput.value.trim();
  if (!token) {
    changedInput.checked = !changedInput.checked;
    setStatus(TEXT.missing, true);
    return;
  }
  const inputs = Array.from(cellElement.querySelectorAll("input[type='checkbox']"));
  const entitlements = inputs
    .filter((input) => input.checked)
    .map((input, index) => adminModules[index]?.entitlement_key)
    .filter(Boolean);
  inputs.forEach((input) => {
    input.disabled = true;
  });
  setStatus("");
  try {
    const response = await fetch(`/api/v1/modules/admin/users/${encodeURIComponent(user.id)}/entitlements`, {
      method: "PUT",
      headers: {
        ...tokenHeaders({ "Content-Type": "application/json" }),
      },
      body: JSON.stringify({ entitlements }),
    });
    if (!response.ok) throw new Error(`Admin entitlements failed: ${response.status}`);
    const data = await response.json();
    user.entitlements = data.entitlements || [];
    renderSummary(currentUsers);
    setStatus(`${TEXT.entitlementDone} ${user.email}`);
  } catch {
    changedInput.checked = !changedInput.checked;
    setStatus(TEXT.entitlementError, true);
  } finally {
    inputs.forEach((input) => {
      input.disabled = false;
    });
  }
}

async function createUser(event) {
  event.preventDefault();
  const token = tokenInput.value.trim();
  if (!token) {
    setStatus(TEXT.missing, true);
    return;
  }
  createButton.disabled = true;
  setStatus("");
  try {
    const response = await fetch("/api/v1/modules/admin/users", {
      method: "POST",
      headers: tokenHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        name: inputValue("#create-name"),
        email: inputValue("#create-email"),
        password: inputValue("#create-password"),
        company: optionalInputValue("#create-company"),
        location: optionalInputValue("#create-location"),
        mobile: optionalInputValue("#create-mobile"),
        entitlements: selectedCreateEntitlements(),
      }),
    });
    if (!response.ok) throw new Error(`Admin account create failed: ${response.status}`);
    createForm.reset();
    renderCreateEntitlements();
    window.localStorage.setItem(TOKEN_KEY, token);
    setStatus(TEXT.createDone);
    await loadUsers();
  } catch {
    setStatus(TEXT.createError, true);
  } finally {
    createButton.disabled = false;
  }
}

async function editProfile(user, button) {
  const token = tokenInput.value.trim();
  if (!token) {
    setStatus(TEXT.missing, true);
    return;
  }
  const name = window.prompt(`${TEXT.editName}\n\n${user.email}`, user.name || "");
  if (name === null) return;
  const company = window.prompt(TEXT.editCompany, user.company || "");
  if (company === null) return;
  const location = window.prompt(TEXT.editLocation, user.location || "");
  if (location === null) return;
  const mobile = window.prompt(TEXT.editMobile, user.mobile || "");
  if (mobile === null) return;
  button.disabled = true;
  setStatus("");
  try {
    const response = await fetch(`/api/v1/modules/admin/users/${encodeURIComponent(user.id)}/profile`, {
      method: "PUT",
      headers: tokenHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        name,
        company: company || null,
        location: location || null,
        mobile: mobile || null,
      }),
    });
    if (!response.ok) throw new Error(`Admin profile update failed: ${response.status}`);
    const data = await response.json();
    Object.assign(user, data.user || {});
    renderUsers(currentUsers);
    setStatus(`${TEXT.editDone} ${user.email}`);
  } catch {
    setStatus(TEXT.editError, true);
  } finally {
    button.disabled = false;
  }
}

async function resetPassword(user, button) {
  const token = tokenInput.value.trim();
  if (!token) {
    setStatus(TEXT.missing, true);
    return;
  }
  const password = window.prompt(`${TEXT.resetPrompt}\n\n${user.email}`);
  if (password === null) return;
  if (password.length < 8) {
    setStatus(TEXT.resetShort, true);
    return;
  }
  button.disabled = true;
  setStatus("");
  try {
    const response = await fetch(`/api/v1/modules/admin/users/${encodeURIComponent(user.id)}/password`, {
      method: "POST",
      headers: {
        ...tokenHeaders({ "Content-Type": "application/json" }),
      },
      body: JSON.stringify({ password }),
    });
    if (!response.ok) throw new Error(`Admin password reset failed: ${response.status}`);
    window.localStorage.setItem(TOKEN_KEY, token);
    setStatus(`${TEXT.resetDone} ${user.email}`);
    await loadUsers();
  } catch {
    setStatus(TEXT.resetError, true);
  } finally {
    button.disabled = false;
  }
}

renderCreateEntitlements();

createForm.addEventListener("submit", createUser);
loadButton.addEventListener("click", loadUsers);
tokenInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") loadUsers();
});
clearButton.addEventListener("click", () => {
  window.localStorage.removeItem(TOKEN_KEY);
  tokenInput.value = "";
  currentUsers = [];
  adminModules = [];
  renderCreateEntitlements();
  renderSummary([]);
  renderUsers([]);
  setStatus("");
});

if (launchToken) {
  loadUsers();
}
