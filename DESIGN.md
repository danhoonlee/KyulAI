# Design

## Source of truth
- Status: Active
- Last refreshed: 2026-06-26
- Primary product surfaces: iOS and Android MVP apps for Laminate and Injection prediction; ImperialAX unified web workspace; DD Laminate web v2 and iOS Laminate v2 experiments; Injection v2 web app and flow prototype.
- Evidence reviewed: `ios/InjectionMVP`, `ios/DDLaminateMVP`, `android/InjectionMVP`, `android/DDLaminateMVP`, `src/frontend/imperialax`, `src/frontend/dd-laminate`, `src/frontend/simple-injection`, `design/Wanted Design System (Community).fig`, extracted `.fig` thumbnail and image package metadata.

## Brand
- Personality: technical, precise, calm, high-trust engineering software.
- Trust signals: clear model/readiness status, legible charts, restrained colors, numeric hierarchy.
- Avoid: marketing-style hero layouts, decorative blobs, overly playful visuals, single-hue monotony.

## Product goals
- Goals: make prediction inputs fast to scan, make results and chart markers immediately interpretable, keep app names simple, and explore a Wanted UI Kit-inspired v2 without losing the existing production-like screens.
- Non-goals: forced full design-system rewrite, destructive replacement of existing screens, decorative illustration work, or broad backend/API changes for a visual experiment.
- Success signals: users can distinguish Laminate from Injection visually, read the top result without hunting, and switch between Classic and v2 during review.

## Personas and jobs
- Primary personas: CAE/AI researchers, engineers, and internal testers.
- User jobs: check API readiness, select model/input set, run a forecast, inspect result curve and critical metrics.
- Key contexts of use: phone-first review, lab/office use, local and public API endpoints.

## Information architecture
- Primary navigation: login-gated unified workspace for ImperialAX; module-specific forecast screens inside each native app. The native unified app entry should mirror `ai.imperialax.com/index.html` for login, account status, workspace summary, and module card hierarchy.
- Core routes/screens: web login, web login Korean, module workspace, module workspace Korean, account/access dialogs, Laminate v2 forecast, Injection v2 forecast, forecast inputs, latest result, full result.
- Content hierarchy: account status, module access, compact research purpose when a module needs outside-audience context, model/input controls, primary prediction button, result headline, chart, secondary metrics.

## Design principles
- Principle 1: results should read before decoration.
- Principle 2: Laminate and Injection should feel related but not identical.
- Principle 3: v2 experiments must be reversible and separately addressable from Classic screens.
- Tradeoffs: keep native controls and current code shape over custom-heavy components; translate UI Kit style into ImperialAX workflows instead of copying demo assets literally.

## Visual language
- Color: Injection uses steel/blue with molten orange-red accents; Laminate Classic uses graphite/teal with red Pt accents; Laminate v2 uses a Wanted-inspired white canvas, black command surfaces, blue action accents, light grid texture, and green readiness states.
- Typography: native rounded/bold headings, monospaced digits for measurements; v2 web uses Pretendard-first typography for Korean/English consistency and permits heavier display titles as long as mobile text does not truncate.
- Spacing/layout rhythm: compact cards with 8px radius and dense engineering information; v2 uses compact workflow rows, deliberate wrapping for long headings, no-wrap only for short labels/chips, and two-panel input/result hierarchy.
- Shape/radius/elevation: subtle cards, restrained borders, no nested card structures; v2 keeps 8px radius, thin borders, and soft shadows.
- Motion: keep ambient movement restrained; Injection v2 may use
  user-triggered predicted filling-pressure/fill-front animation after a
  forecast completes.
- Imagery/iconography: SF Symbols/native icons where available; charts remain the main visual asset.

## Components
- Existing components to reuse: `AppTheme`, `AppCard`, primary/secondary buttons, native picker/menu fields, chart views, ImperialAX web module cards.
- New/changed components: color tokens, result emphasis, chart tinting, Android card/button styling, Android live laminate preview, web login/account/access panels, ImperialAX web-matched native login/workspace shell, ImperialAX `login-v2` prototype and ImperialAX module workspace shell, DD Laminate web v2 shell, DD Laminate research-purpose brief, Injection v2 compact setup blocks, Injection v2 Three.js parametric mold preview with predicted filling-pressure/fill-front map, Injection v2 six-screen flow prototype, and iOS `ContentViewV2`.
- Variants and states: ready/success green, warning amber, error red, primary action by app family.
- Token/component ownership: app-local native files for now.

## Accessibility
- Target standard: high contrast enough for phone use; preserve native text controls.
- Keyboard/focus behavior: unchanged.
- Contrast/readability: avoid light text on saturated backgrounds except white on primary buttons.
- Screen-reader semantics: unchanged in this pass.
- Reduced motion and sensory considerations: keep prediction pressure-map
  motion tied to the forecast result state and avoid extra decorative loops.

## Responsive behavior
- Supported breakpoints/devices: iPhone, Android phones, SwiftUI preview/macOS build targets.
- Layout adaptations: mobile web must not be a stacked desktop canvas; use compact
  phone-first headers, short process chips, and vertical module list cards with
  touch-sized actions. The DD Laminate v2 mobile input state should keep the
  active forecast form and primary prediction action inside one phone viewport;
  suppress secondary workflow/setup headers on mobile and use that space for a
  large angle-aware ply stack visual between model selection and theta controls.
  The ply visual should adapt to available mobile height: show the full stack
  aspect on tall/large phones and clamp down on short phones so the primary
  action remains reachable in the first viewport. Injection v2 may scroll on mobile because DOE
  geometry/process inputs are denser, but must hide secondary workflow summaries
  on phone widths, keep compact process controls and the primary prediction
  action visible in the first mobile viewport, and avoid horizontal overflow.
  Injection v2 should disable sticky setup panels on narrow or short windows so
  result review remains the primary scroll focus after prediction.
- Touch/hover differences: phone-first.

## Interaction states
- Loading: existing checking/predicting states.
- Empty: existing no-result state.
- Error: red status and existing alerts/messages.
- Success: green API status.
- Disabled: existing disabled predict button.
- Offline/slow network, if applicable: existing connection failure copy.
- 3D preview manipulation: Injection v2 Parametric Preview should match v1's
  free 360-degree drag rotation, plus wheel/button zoom and reset.
- Charts: Injection v2 Sprue Pressure should stay visually close to v1 with
  explicit x/y ticks, grid lines, axis labels, and a readable gradient pressure
  curve.
- DOE editing: Injection v2 should match v1 by switching Geometry or Process
  DOE selectors to `User input` when users manually edit the corresponding
  geometry/process fields.

## Content voice
- Tone: concise engineering UI copy.
- Terminology: keep `Laminate`, `Injection`, `Pt`, `Sprue`, `Filling`, `Forecast`.
- Microcopy rules: avoid explaining UI mechanics inside the main app surface; workspace titles should describe the product role (`Forecast Workspace`) rather than generic app wording. Research purpose copy may appear near the top of Laminate screens when it explains why the AI model exists, not how to operate controls.

## Implementation constraints
- Framework/styling system: SwiftUI for iOS, native Android Kotlin Views for Android, plain HTML/CSS/JavaScript for the ImperialAX web workspace and DD Laminate web app.
- Design-token constraints: maintain local app tokens rather than adding shared cross-platform tooling; v2 tokens live in `ContentViewV2.swift` and `styles-v2.css` until the direction is approved.
- Performance constraints: keep charts lightweight and static unless user-triggered.
- Compatibility constraints: SwiftPM/Xcode app hosts, Android Gradle debug APKs.
- Test/screenshot expectations: run Swift tests and Android debug builds after visual changes. For ImperialAX workspace changes, verify web/iOS/Android copy and hierarchy stay aligned; for v2 web/iOS visual work, also verify separate v2 route/screen rendering and capture at least one screenshot when practical.

## Open questions
- [ ] Whether ImperialAX should eventually have a single shared brand palette across web, iOS, and Android.
- [ ] Whether Wanted-inspired Laminate v2 should become the default after user review, or remain an experimental alternate surface.
