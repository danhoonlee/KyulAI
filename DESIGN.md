# Design

## Source of truth
- Status: Active
- Last refreshed: 2026-06-04
- Primary product surfaces: iOS and Android MVP apps for Laminate and Injection prediction.
- Evidence reviewed: `ios/InjectionMVP`, `ios/DDLaminateMVP`, `android/InjectionMVP`, `android/DDLaminateMVP`.

## Brand
- Personality: technical, precise, calm, high-trust engineering software.
- Trust signals: clear model/readiness status, legible charts, restrained colors, numeric hierarchy.
- Avoid: marketing-style hero layouts, decorative blobs, overly playful visuals, single-hue monotony.

## Product goals
- Goals: make prediction inputs fast to scan, make results and chart markers immediately interpretable, keep app names simple.
- Non-goals: full design-system rewrite, new navigation architecture, decorative illustration work.
- Success signals: users can distinguish Laminate from Injection visually and read the top result without hunting.

## Personas and jobs
- Primary personas: CAE/AI researchers, engineers, and internal testers.
- User jobs: check API readiness, select model/input set, run a forecast, inspect result curve and critical metrics.
- Key contexts of use: phone-first review, lab/office use, local and public API endpoints.

## Information architecture
- Primary navigation: single forecast screen with settings sheet and optional result detail.
- Core routes/screens: forecast inputs, latest result, full result.
- Content hierarchy: status, model/input controls, primary prediction button, result headline, chart, secondary metrics.

## Design principles
- Principle 1: results should read before decoration.
- Principle 2: Laminate and Injection should feel related but not identical.
- Tradeoffs: keep native controls and current code shape over custom-heavy components.

## Visual language
- Color: Injection uses steel/blue with molten orange-red accents; Laminate uses graphite/teal with red Pt accents.
- Typography: native rounded/bold headings, monospaced digits for measurements.
- Spacing/layout rhythm: compact cards with 8px radius and dense engineering information.
- Shape/radius/elevation: subtle cards, restrained borders, no nested card structures.
- Motion: no new motion for this polish pass.
- Imagery/iconography: SF Symbols/native icons where available; charts remain the main visual asset.

## Components
- Existing components to reuse: `AppTheme`, `AppCard`, primary/secondary buttons, native picker/menu fields, chart views.
- New/changed components: color tokens, result emphasis, chart tinting, Android card/button styling.
- Variants and states: ready/success green, warning amber, error red, primary action by app family.
- Token/component ownership: app-local native files for now.

## Accessibility
- Target standard: high contrast enough for phone use; preserve native text controls.
- Keyboard/focus behavior: unchanged.
- Contrast/readability: avoid light text on saturated backgrounds except white on primary buttons.
- Screen-reader semantics: unchanged in this pass.
- Reduced motion and sensory considerations: no new continuous animation.

## Responsive behavior
- Supported breakpoints/devices: iPhone, Android phones, SwiftUI preview/macOS build targets.
- Layout adaptations: keep existing scroll and grid behavior.
- Touch/hover differences: phone-first.

## Interaction states
- Loading: existing checking/predicting states.
- Empty: existing no-result state.
- Error: red status and existing alerts/messages.
- Success: green API status.
- Disabled: existing disabled predict button.
- Offline/slow network, if applicable: existing connection failure copy.

## Content voice
- Tone: concise engineering UI copy.
- Terminology: keep `Laminate`, `Injection`, `Pt`, `Sprue`, `Filling`, `Forecast`.
- Microcopy rules: avoid explaining UI mechanics inside the main app surface.

## Implementation constraints
- Framework/styling system: SwiftUI for iOS, native Android Kotlin Views for Android.
- Design-token constraints: maintain local app tokens rather than adding shared cross-platform tooling.
- Performance constraints: keep charts lightweight and static unless user-triggered.
- Compatibility constraints: SwiftPM/Xcode app hosts, Android Gradle debug APKs.
- Test/screenshot expectations: run Swift tests and Android debug builds after visual changes.

## Open questions
- [ ] Whether C2ES should eventually have a single shared brand palette across web, iOS, and Android.
