const state = {
  caseName: "Case2",
  theta1: 30,
  theta2: -30,
  sequenceCollapsed: window.matchMedia("(max-width: 820px)").matches,
};

const formulas = {
  Case2: "[[+/-θ1]/[+/-θ2]] x 4",
  Case3: "[[+/-θ1]/[+/-θ2]/[-/+θ1]/[-/+θ2]] x 2",
  Case4: "([+/-θ1]/[+/-θ2]) x 2 + ([-/+θ1]/[-/+θ2]) x 2",
};

const presets = {
  balanced: { caseName: "Case2", theta1: 30, theta2: -30 },
  asymmetric: { caseName: "Case3", theta1: 22, theta2: 64 },
  cross: { caseName: "Case4", theta1: 0, theta2: 90 },
  sparse: { caseName: "Case2", theta1: 8, theta2: 82 },
};

const colors = {
  theta1: {
    topA: "#9aa9ed",
    topB: "#657bd4",
    sideA: "#7f90d4",
    sideB: "#5e70ba",
    edge: "#4e60aa",
  },
  theta2: {
    topA: "#e0bda0",
    topB: "#bc8f70",
    sideA: "#caa68b",
    sideB: "#a77e63",
    edge: "#8e684f",
  },
};

const controls = {
  stackVisual: document.querySelector("#stack-visual"),
  sequenceList: document.querySelector("#sequence-list"),
  formula: document.querySelector("#case-formula"),
  plyCount: document.querySelector("#ply-count"),
  positiveCount: document.querySelector("#positive-count"),
  negativeCount: document.querySelector("#negative-count"),
  familyCount: document.querySelector("#family-count"),
  theta1Range: document.querySelector("#theta1-range"),
  theta1Number: document.querySelector("#theta1-number"),
  theta1Readout: document.querySelector("#theta1-readout"),
  theta2Range: document.querySelector("#theta2-range"),
  theta2Number: document.querySelector("#theta2-number"),
  theta2Readout: document.querySelector("#theta2-readout"),
  caseButtons: Array.from(document.querySelectorAll("[data-case]")),
  presetButtons: Array.from(document.querySelectorAll("[data-preset]")),
  inspectorPanel: document.querySelector(".inspector-panel"),
  sequenceToggle: document.querySelector("#sequence-toggle"),
  sequenceToggleText: document.querySelector("#sequence-toggle-text"),
};

const mobileInspectorQuery = window.matchMedia("(max-width: 820px)");
let sequenceToggleTouched = false;

function clampAngle(value) {
  const parsed = Number.parseFloat(value);
  if (!Number.isFinite(parsed)) {
    return 0;
  }
  return Math.max(-90, Math.min(90, Math.round(parsed)));
}

function formatAngle(value) {
  const rounded = Math.round(value);
  return `${rounded > 0 ? "+" : ""}${rounded} deg`;
}

function anglePair(angle, family) {
  return [
    { angle, family },
    { angle: -angle, family },
  ];
}

function inversePair(angle, family) {
  return [
    { angle: -angle, family },
    { angle, family },
  ];
}

function repeat(pattern, count) {
  return Array.from({ length: count }).flatMap(() => pattern.map((ply) => ({ ...ply })));
}

function buildSequence({ caseName, theta1, theta2 }) {
  const theta1Pair = anglePair(theta1, "theta1");
  const theta2Pair = anglePair(theta2, "theta2");
  const theta1Inverse = inversePair(theta1, "theta1");
  const theta2Inverse = inversePair(theta2, "theta2");

  if (caseName === "Case3") {
    return repeat([...theta1Pair, ...theta2Pair, ...theta1Inverse, ...theta2Inverse], 2);
  }

  if (caseName === "Case4") {
    return [
      ...repeat([...theta1Pair, ...theta2Pair], 2),
      ...repeat([...theta1Inverse, ...theta2Inverse], 2),
    ];
  }

  return repeat([...theta1Pair, ...theta2Pair], 4);
}

function familyLabel(family) {
  return family === "theta1" ? "Theta 1 family" : "Theta 2 family";
}

function renderPly(ply, index) {
  const palette = colors[ply.family];
  const x = 555 - index * 30;
  const y = 470 - index * 28;
  const labelFill = ply.angle >= 0 ? "#087443" : "#b42318";
  const topPoints = "0,130 138,210 420,52 282,-28";
  const sideLeft = "0,130 138,210 138,230 0,150";
  const sideRight = "138,210 420,52 420,72 138,230";
  const labelX = 426;
  const labelY = 36;

  return `
    <g transform="translate(${x} ${y})">
      <defs>
        <pattern id="ply-hatch-${index}" width="24" height="24" patternUnits="userSpaceOnUse" patternTransform="rotate(${-ply.angle})">
          <path d="M-6 12 H30" stroke="${labelFill}" stroke-width="3" stroke-linecap="round" opacity="0.82" />
        </pattern>
      </defs>
      <polygon points="${sideLeft}" fill="${palette.sideA}" />
      <polygon points="${sideRight}" fill="${palette.sideB}" />
      <polygon points="${topPoints}" fill="url(#top-${ply.family})" stroke="${palette.edge}" stroke-width="1.4" />
      <polygon points="${topPoints}" fill="url(#ply-hatch-${index})" opacity="0.88" />
      <polygon points="${topPoints}" fill="transparent" stroke="rgba(255,255,255,0.64)" stroke-width="1" />
      <line x1="400" y1="61" x2="${labelX}" y2="${labelY + 15}" stroke="#f4ff17" stroke-width="2.2" opacity="0.92" />
      <rect x="${labelX}" y="${labelY}" width="126" height="34" rx="7" fill="#102033" opacity="0.96" stroke="#f4ff17" stroke-width="1.8" />
      <text x="${labelX + 11}" y="${labelY + 24}" fill="#f4ff17" font-size="22" font-weight="950">Ply-${index + 1}</text>
      <text x="12" y="143" fill="#ffffff" font-size="12" font-weight="900">P${index + 1}</text>
    </g>
  `;
}

function renderStackSvg(sequence) {
  const plies = sequence.map((ply, index) => renderPly(ply, index)).join("");
  return `
    <svg viewBox="0 0 1160 760" role="img" aria-label="Dynamic Double-Double laminate ply stack">
      <defs>
        <linearGradient id="bg-plane" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0" stop-color="#1c334e" />
          <stop offset="0.56" stop-color="#2f4966" />
          <stop offset="1" stop-color="#8998a8" />
        </linearGradient>
        <linearGradient id="top-theta1" x1="0" x2="1">
          <stop offset="0" stop-color="${colors.theta1.topA}" />
          <stop offset="1" stop-color="${colors.theta1.topB}" />
        </linearGradient>
        <linearGradient id="top-theta2" x1="0" x2="1">
          <stop offset="0" stop-color="${colors.theta2.topA}" />
          <stop offset="1" stop-color="${colors.theta2.topB}" />
        </linearGradient>
        <filter id="stack-shadow" x="-20%" y="-20%" width="140%" height="150%">
          <feDropShadow dx="0" dy="14" stdDeviation="14" flood-color="#081426" flood-opacity="0.22" />
        </filter>
      </defs>

      <rect x="34" y="34" width="1092" height="700" rx="8" fill="url(#bg-plane)" />
      <g opacity="0.22" stroke="#edf7ff" stroke-width="1">
        <path d="M118 42 L992 524" />
        <path d="M70 94 L944 576" />
        <path d="M22 146 L896 628" />
        <path d="M214 660 L1088 178" />
        <path d="M48 536 L742 150" />
        <path d="M122 578 L816 192" />
        <path d="M196 620 L890 234" />
        <path d="M270 662 L964 276" />
      </g>

      <g filter="url(#stack-shadow)" opacity="0.96">
        <polygon points="98,456 574,704 1018,458 542,210" fill="#b9977f" />
        <polygon points="98,456 574,704 574,728 98,480" fill="#c8a78e" />
        <polygon points="574,704 1018,458 1018,482 574,728" fill="#98765f" />
        <path d="M138 468 L574 706 L976 482" fill="none" stroke="#ead3c2" stroke-width="2" opacity="0.44" />
      </g>

      <g filter="url(#stack-shadow)">
        ${plies}
      </g>

      <g transform="translate(66 680)" font-size="14" font-weight="820">
        <text x="0" y="0" fill="#ffffff">Dynamic Double-Double stack</text>
        <text x="0" y="24" fill="#d9e7f6">Layer positions are stylized; hatch direction and sequence come from inputs.</text>
      </g>
    </svg>
  `;
}

function renderSequenceList(sequence) {
  const topToBottom = [...sequence].reverse();
  controls.sequenceList.innerHTML = topToBottom
    .map((ply, index) => {
      const plyNumber = sequence.length - index;
      const signClass = ply.angle >= 0 ? "positive" : "negative";
      return `
        <li>
          <span class="ply-number">P${plyNumber}</span>
          <span class="sequence-main">
            <strong>${familyLabel(ply.family)}</strong>
            <span>${ply.family === "theta1" ? "Uses theta 1 input" : "Uses theta 2 input"}</span>
          </span>
          <span class="direction-chip ${signClass}">${formatAngle(ply.angle)}</span>
        </li>
      `;
    })
    .join("");
}

function renderSummary(sequence) {
  const positive = sequence.filter((ply) => ply.angle > 0).length;
  const negative = sequence.filter((ply) => ply.angle < 0).length;
  const families = new Set(sequence.map((ply) => ply.family));

  controls.plyCount.textContent = String(sequence.length);
  controls.positiveCount.textContent = String(positive);
  controls.negativeCount.textContent = String(negative);
  controls.familyCount.textContent = String(families.size);
  controls.formula.textContent = formulas[state.caseName];
}

function syncSequenceInspector() {
  controls.inspectorPanel.classList.toggle("is-collapsed", state.sequenceCollapsed);
  controls.sequenceToggle.setAttribute("aria-expanded", String(!state.sequenceCollapsed));
  controls.sequenceToggleText.textContent = state.sequenceCollapsed ? "Show list" : "Hide list";
}

function syncControls() {
  controls.theta1Range.value = String(state.theta1);
  controls.theta1Number.value = String(state.theta1);
  controls.theta1Readout.textContent = formatAngle(state.theta1);

  controls.theta2Range.value = String(state.theta2);
  controls.theta2Number.value = String(state.theta2);
  controls.theta2Readout.textContent = formatAngle(state.theta2);

  controls.caseButtons.forEach((button) => {
    const isActive = button.dataset.case === state.caseName;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });
}

function render() {
  syncControls();
  syncSequenceInspector();
  const sequence = buildSequence(state);
  controls.stackVisual.innerHTML = renderStackSvg(sequence);
  renderSequenceList(sequence);
  renderSummary(sequence);
}

function updateAngle(name, value) {
  state[name] = clampAngle(value);
  render();
}

controls.theta1Range.addEventListener("input", (event) => updateAngle("theta1", event.target.value));
controls.theta1Number.addEventListener("input", (event) => updateAngle("theta1", event.target.value));
controls.theta2Range.addEventListener("input", (event) => updateAngle("theta2", event.target.value));
controls.theta2Number.addEventListener("input", (event) => updateAngle("theta2", event.target.value));

controls.caseButtons.forEach((button) => {
  button.addEventListener("click", () => {
    state.caseName = button.dataset.case;
    render();
  });
});

controls.presetButtons.forEach((button) => {
  button.addEventListener("click", () => {
    Object.assign(state, presets[button.dataset.preset]);
    render();
  });
});

controls.sequenceToggle.addEventListener("click", () => {
  sequenceToggleTouched = true;
  state.sequenceCollapsed = !state.sequenceCollapsed;
  syncSequenceInspector();
});

mobileInspectorQuery.addEventListener("change", (event) => {
  if (sequenceToggleTouched) {
    return;
  }
  state.sequenceCollapsed = event.matches;
  syncSequenceInspector();
});

render();
