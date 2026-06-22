# DD Laminate Greenfield Flow Concept

Date: 2026-06-18

## Purpose

This is a discussion artifact for Version A of the from-scratch C2ES Laminate
product direction. It does not replace Classic or Wanted v2. It compares the
same guided single-candidate Decision Studio concept as a mobile-first wizard
and as a desktop-centered cockpit.

Prototype:

- `src/frontend/dd-laminate/greenfield-flow.html`
- `src/frontend/dd-laminate/greenfield-flow.css`

## Design Assumptions

- Primary users are CAE/AI researchers and engineers reviewing laminate
  candidates before simulation.
- The product should start from the decision to be made, then reveal technical
  inputs and model details progressively.
- Model names should remain understandable: Machine Learning, Deep Learning,
  and Dual run, while internal model keys stay out of the first-level UI.
- Pt and curve consistency should be treated as a first-class result quality
  signal.
- Outputs should end in a review package that can be shared or handed to
  simulation.

## Version A Mobile: Guided Phone Flow

Mobile-first guided flow for one laminate candidate at a time.

1. Run Setup
   - Starts with the engineering task: Response + Pt, u3 Pt, or CSV validation.
   - Shows project context and API readiness before any model/input work.

2. Laminate Builder
   - Makes theta/case choices visual through a stack preview.
   - Surfaces compact physics facts only after the user defines the candidate.

3. Model Strategy
   - Frames model choice as strategy: Machine Learning, Deep Learning, or Dual
     run.
   - Uses training coverage/readiness as trust context.

4. Forecast Progress
   - Shows a short trace of validation, feature generation, model execution, and
     Pt consistency checks.
   - Allows sparse-region warnings to appear before the result is trusted.

5. Decision Result
   - Prioritizes Type, Pt, u3 Pt, model agreement, and curve shape.
   - Treats Pt-curve consistency as a visible quality gate.

6. Explain and Compare
   - Keeps only the top feature drivers visible.
   - Compares ML vs DL as agreement or disagreement, not as raw architecture
     detail.

7. Review Package
   - Ends with PDF, CSV, simulation queue, and share-link actions.
   - Turns a forecast into a handoff artifact for team review.

## Version A Desktop: Guided Decision Cockpit

Desktop-first adaptation of the same Decision Studio concept. It should not
become the broad multi-candidate Research Workbench direction. The purpose is
to preserve Version A's clarity while using desktop space for persistent
context, preview, evidence, and handoff.

1. Persistent Run Setup
   - Left rail keeps run goal, API readiness, case family, run mode, and step
     progress visible.

2. Large Stack Canvas
   - Center-left canvas gives the laminate stack enough space to be inspected
     while theta and case are edited.

3. Live Result Preview
   - Center preview shows Type, Pt, ML/DL agreement, curve overlay, and Pt
     marker without changing pages.

4. Evidence Inspector
   - Right inspector holds model strategy, coverage, confidence gate, warnings,
     and top XAI drivers.

5. Handoff Actions
   - Export, queue simulation, and share-link actions are available after the
     decision evidence is reviewed.

## Team Discussion Questions

- Which Version A expression better fits the near-term product: mobile guided
  wizard or desktop decision cockpit?
- Should the product default to a single recommended model, or a Dual run when
  the case is research-oriented?
- Should sparse-region warnings block export, or only mark the result as lower
  confidence?
- Is Pt-curve consistency a result badge, a required validation step, or both?
- Should u3 live inside the same run setup, or remain a separate forecast mode?
- Which package outputs matter most for actual engineering review: PDF, CSV,
  simulation queue, or saved run link?

## Non-Goals

- This prototype does not change backend APIs.
- This prototype does not replace Classic or Wanted v2 screens.
- This prototype does not attempt pixel parity with the imported Figma kit.
