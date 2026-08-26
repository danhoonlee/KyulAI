# ImperialAX Forecast Workflow Redesign Preview

## Source

This preview implements the in-scope requirements from `docs/imperialax-forecast-ui-redesign.md` and the prototype review fixes in `docs/imperialax-forecast-ui-redesign(2).md` without changing the production route.

## Preview pages

- Korean sample result: `index-redesign.ko.html?sample=1`
- English sample result: `index-redesign.html?sample=1`
- Remove `?sample=1` to use the normal API-driven empty state.

## Implemented

- desktop sticky setup panel with internal overflow protection
- sticky primary forecast action inside long desktop forms
- five-card core result summary
- response curve expanded by default
- XAI collapsed by default
- design-space and research analysis collapsed by default
- native `<details>/<summary>` keyboard behavior
- accordion state persisted for the browser-tab session
- loading spinner on the forecast action
- result highlight and mobile auto-scroll after a new forecast
- normal non-sticky one-column behavior at 1024px and below
- complete `sample=1` response-curve and design-space chart data
- populated sample model option, XAI features, Case risk, nearest simulations, and recommendations
- sample-data status that does not conflict with the local API-offline warning

## Review screenshots

- `.tmp/laminate_monotone_review/web/forecast-redesign-desktop.png`
- `.tmp/laminate_monotone_review/web/forecast-redesign-result.png`
- `.tmp/laminate_monotone_review/web/forecast-redesign-mobile-result.png`

## Explicitly deferred from the source specification

- Stack Lab formula-entry redesign
- Curve CSV drag-and-drop and upload progress
- cross-screen number-format normalization
- inline domain validation messages
- prediction-history comparison table and curve overlay
- dark mode
