const FALLBACK_MODULES = [
  {
    id: "laminate",
    name: "Laminate",
    category: "Composite",
    summary: "Predict Double-Double laminate response, Pt, type, and force-displacement curves.",
    icon: "layers",
    access: "granted",
    tags: ["Double-Double", "Pt", "Force-displacement"],
    capabilities: ["response prediction", "curve chart", "history", "comparison"],
    route: { web_url: "https://laminate.luvelox.com", api_prefix: "/api/v1/dd-laminate" },
  },
  {
    id: "injection",
    name: "Injection",
    category: "Molding",
    summary: "Predict sprue pressure curves and filling pressure distributions for Simple Injection DOE.",
    icon: "gauge",
    access: "granted",
    tags: ["Moldex3D", "Sprue pressure", "Filling pressure"],
    capabilities: ["sprue pressure", "filling histogram", "animation", "history"],
    route: { web_url: "https://injection.luvelox.com", api_prefix: "/api/v1/simple-injection" },
  },
];

const ICONS = {
  layers: "L",
  gauge: "P",
  sparkles: "+",
};

const grid = document.querySelector("#module-grid");
const template = document.querySelector("#module-card-template");
const refreshButton = document.querySelector("#refresh-button");

function humanize(value) {
  return String(value).replaceAll("_", " ");
}

function badgeText(access, status) {
  if (access === "granted") return "Available";
  if (status === "planned") return "Planned";
  return "Locked";
}

function renderModules(modules) {
  grid.replaceChildren();
  for (const module of modules) {
    const card = template.content.firstElementChild.cloneNode(true);
    const locked = module.access && module.access !== "granted";
    card.classList.toggle("locked", locked);
    card.querySelector(".module-icon").textContent = ICONS[module.icon] || module.name.slice(0, 1);
    card.querySelector(".module-category").textContent = module.category;
    card.querySelector(".module-title").textContent = module.name;
    card.querySelector(".access-badge").textContent = badgeText(module.access, module.status);
    card.querySelector(".module-summary").textContent = module.summary;

    const tagRow = card.querySelector(".tag-row");
    for (const tag of module.tags || []) {
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

    const link = card.querySelector(".primary-link");
    link.href = module.route.web_url;
    link.textContent = locked ? "Request access" : "Open";
    card.querySelector(".route-text").textContent = module.route.api_prefix;
    grid.append(card);
  }
}

async function loadModules() {
  refreshButton.disabled = true;
  try {
    const response = await fetch("/api/v1/modules/me", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`Module catalog failed: ${response.status}`);
    const payload = await response.json();
    renderModules(payload.modules);
  } catch {
    renderModules(FALLBACK_MODULES);
  } finally {
    refreshButton.disabled = false;
  }
}

refreshButton.addEventListener("click", loadModules);
loadModules();
