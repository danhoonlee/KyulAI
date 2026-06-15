# Double-Double Laminate PPT Basis

Source: `data/PPT/Final ver2.pptx`

Extraction note: the PPT was first read through direct PPTX XML extraction and
then rechecked with `python-pptx==1.0.2` so slide tables and grouped text could
be verified more reliably.

This note captures the engineering assumptions and AI-relevant rules extracted
from the PPT so future modeling work can stay aligned with the Abaqus study.

## Problem Setup

- Structure: flat rectangular composite panel.
- Panel size: 6 in x 4 in.
- Boundary conditions described in the PPT:
  - simply supported on lateral edges,
  - clamped at x = 0 and x = a,
  - load applied from x = a.
- Material: Toray T800/3900S.
- Ply thickness: 0.0075 in.
- Total plies: 16.
- Primary study: Double-Double laminate angle/case search for improved
  transition load and post-impact/compression-after-impact relevance.

## Double-Double Case Scope

The current AI dataset/modeling scope uses Case2, Case3, and Case4.  Earlier
project notes define them as:

- Case2: `[[±theta1]/[±theta2]]4`
- Case3: `[[±theta1]/[±theta2]/[∓theta2]/[∓theta2]]2`
- Case4: `[([±theta1]/[±theta2])2 / ([∓theta1]/[∓theta2])2]`

The PPT also discusses Case1 and Case5, but those are not yet in the current
u3 forecast training set.

## Buckling And Transition Load Interpretation

- Critical buckling load can be obtained through linear eigenvalue buckling
  analysis for symmetric laminates.
- For unsymmetric laminates, eigenvalue buckling can overestimate the usable
  load because the B matrix is not zero and membrane-bending coupling appears.
- Transition load is more representative for imperfect nonlinear response.
- Imperfection seeding workflow:
  1. obtain buckling mode shape from eigenvalue analysis,
  2. scale one or more mode shapes as initial geometric imperfections,
  3. run nonlinear static analysis,
  4. identify transition load from force-displacement and/or u3 plots.

## Type Rules

Type 1:

- Force-displacement curve has a clear bilinear shape.
- Initial stiffness is nearly linear.
- Post-transition stiffness is also approximately linear.
- Transition load is the intersection of initial and post-transition fitted
  force-displacement lines.

Type 2:

- Initial stiffness is nearly linear.
- Post-transition region is curved.
- Knee point is somewhat unclear.
- u3 displacement plot is needed.
- Transition load is the average of the force-plot intersection and the
  u3-plot intersection.

Type 3:

- Initial stiffness is nearly linear.
- Post-transition region curves heavily.
- Force bilinear fitting is unreliable.
- u3 displacement plot is needed.
- Transition load is based on the u3-plot intersection.

## Observed Surface Patterns

The PPT groups the five cases into two response-surface patterns:

- Pattern I: Case1 and Case5.
  - Twin-ridge / center-basin style.
- Pattern II: Case2, Case3, and Case4.
  - Four-corner peak structure with low center region.
  - High-performing regions appear away from theta1 = theta2 = 0 deg.
  - Performance is dominated by nonzero ±45-degree-type angle combinations.

For Case2/3/4, the high-performing region is repeatedly described near:

- theta1 ≈ 44.13 deg
- theta2 ≈ -49.42 deg

## Reported Optimization Results

Transition-load view:

- Quasi benchmark: 12,344.8 lbs.
- Case2 best: 15,880.6 lbs.
- Case3 best: 15,916.5 lbs.
- Case4 best: 15,908.5 lbs.
- Case3 is reported as the best transition-load case among Case2/3/4.

Cost-function view:

- Cost function uses a 70% buckling / 30% flexural-rigidity weighting.
- Flexural rigidity proxy is the fundamental frequency from eigenvalue
  analysis.
- Quasi benchmark cost: 2.283682.
- Case2 best cost: 2.998788.
- Case3 best cost: 2.993270.
- Case4 best cost: 2.993247.
- Case2 is reported as the best cost-function case among Case2/3/4.
- Slide 25 contains a nearby text value that reads like `2.988788`, but the
  table and repeated result overview use `2.998788`; this note keeps the table
  value.

## AI Modeling Implications

Already reflected:

- The AI models use theta1, theta2, and Case as pre-simulation inputs.
- Current u3 forecast targets include Type, Pt, max displacement, max force,
  and approximate curve shape.
- First-pass XAI shows current predictions are dominated by angle periodicity
  and absolute angle descriptors.

Added after this PPT review:

- `laminate_physics.py` now supports Case2 in the CLT stack expansion.
- Extended physics features were added for future retraining:
  - normalized A/B/D matrix terms,
  - membrane-bending coupling descriptors,
  - bending and membrane anisotropy,
  - angle center/spread,
  - balance and symmetry-mismatch descriptors,
  - Case2/3/4 flags.
- `train_u3_forecast_models.py` now supports two feature sets:
  - `theta`: existing model-compatible feature set,
  - `theta_physics`: theta/case plus the extended physics feature pack.

Still useful to confirm:

- Exact Case1 and Case5 ply expansions if those cases are later added.
- Whether all Abaqus runs use the same material constants and boundary
  conditions shown in the PPT.
- Whether u3 fitting-line windows, slopes, and intersection points are saved or
  can be exported; those would strongly improve Type explanation.
