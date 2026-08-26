# ImperialAX Forecast Rebuild Concept Preview

## Purpose

This is a separately addressable information-architecture prototype based on `docs/imperialax-forecast-ui-rebuild-concept.md`. It does not replace the current v2 or workflow-redesign pages.

## Preview page

- Korean: `index-rebuild.ko.html`
- Public review route: `https://laminate.imperialax.com/v2`
- The operating root at `https://laminate.imperialax.com/` remains unchanged.

## Agreed decisions reflected

- Quick Screening and Deep Dive use a mutually exclusive `radiogroup`/`radio` pattern, not tab semantics.
- Type and probability share one primary metric card, producing four summary cards in total.
- Desktop sticky behavior applies at 1024px and above; below 1024px uses normal flow, scrollable pill tabs, and comparison cards.
- Visual styling follows the `(3)` flat guide: system sans-serif, only 400/500 weights, sentence-case labels, white cards, 0.5px hairlines, no gradients, and no box shadows.
- The model selector contains all six supported response models, grouped into 3-Size Pt-Consistent and production families.

## Implemented interactions

- session-persisted Quick Screening / Deep Dive radio mode with Arrow, Home, and End navigation
- accessible Summary / Curve / XAI / Design Space tabs with Arrow, Home, and End navigation
- live model metadata and prediction integration through the DD Laminate API, with deterministic preview fallback when the API is offline
- model-aware response curve with Pt, maximum force, and maximum displacement metrics
- deferred local XAI loading with method, summary, ranked physics features, and notes
- design-space loading with real map points, Case risk, nearest simulation, recommendation, and source note
- responsive canvas charts for the response curve and design space
- sortable run comparison with keyboard-accessible row reuse
- compact collapsible laminate preview inside the setup panel

## Scope note

The page remains separately addressable and does not replace the current operating route. When the local API is reachable it uses live model results; otherwise it clearly switches to deterministic concept data so the design remains reviewable.
