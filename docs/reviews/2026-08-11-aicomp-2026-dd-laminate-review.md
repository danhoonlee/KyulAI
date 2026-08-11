# AIComp 2026 Review for Double-Double Laminate AI

Reviewed: 2026-08-11

## Sources

- Official agenda: https://composites-ai.org/agenda/
- Official speakers: https://composites-ai.org/speakers/
- Official workshops: https://composites-ai.org/workshops/
- Official book of abstracts: https://composites-ai.org/wp-content/uploads/2026/08/BookofAbstracts-combined-compressed.pdf

AIComp 2026 was held in Vancouver on August 5-7, 2026. The program concentrated on design and
optimization, surrogate modelling, uncertainty quantification, physics-informed learning,
trustworthiness, inverse design, and composites-specific RAG. These topics align closely with the
current ImperialAX Double-Double Laminate work.

## Current Project Alignment

The project already implements several directions represented at AIComp 2026:

- Forward surrogate prediction from Case, theta values, panel geometry, and CLT-derived features.
- Type, Pt, Max. Force, Max. Displacement, and 128-point response-curve prediction.
- Tree, standalone GointMLP, and Teacher-Student Hybrid model families.
- Grouped Holdout validation across 6x4, 6x8, and 8x8 panels.
- Physics-derived XAI and local feature explanations.
- A composites-oriented RAG assistant with source-linked answers.
- A Pt-consistent output contract for the displayed P1-line intersection.

The current project is therefore not behind the conference's general direction. Its largest gaps are
formal uncertainty calibration, sequence-native laminate representation, optimization under
uncertainty, and independent validation of newer pseudo-labelled data.

## Most Relevant Presentations

### 1. Physics-Informed Bayesian Gaussian Processes for Accelerated Characterization

The abstract combines physics-guided descriptors, Gaussian Process Regression, uncertainty
quantification, and an acquisition function that chooses the next informative experiment. This is the
closest match to the project's next research step.

Application to DD:

- Replace the current screening-only Pt band with calibrated prediction intervals.
- Use grouped conformal prediction, deep ensembles, quantile models, GPR, or a calibrated Bayesian
  output layer depending on model family.
- Select the next Case/theta/panel simulation by expected improvement and uncertainty reduction.
- Stop adding data when a pre-defined confidence or coverage criterion is met.

### 2. AI-Enabled Forward Prediction and Inverse Design of Composite Materials

The plenary argues that useful composites AI should connect mechanically meaningful forward models
to inverse exploration of design space. This directly supports evolving Laminate Forecast from a
predictor into a constrained design assistant.

Application to DD:

- Keep the existing forward model as a fast surrogate.
- Add target-driven search such as: maximize Pt, require Type 1 probability above a threshold, and
  constrain panel geometry or allowable angle ranges.
- Return several diverse candidates rather than one nominal optimum because structure-property
  mappings can be non-unique.

### 3. Rapid Inverse Design Using Sequence-Based Deep Learning

This work encodes the actual ordered architecture as a sequence and learns it with an LSTM before
using the surrogate inside a genetic or evolutionary optimization loop. It is highly relevant to the
project's Case 5 and custom stacking-formula direction.

Application to DD:

- Move beyond only Case one-hot flags plus handcrafted descriptors.
- Encode each ply using angle, through-thickness position, thickness, material, sign-pair relation,
  and optional manufacturing constraints.
- Fuse a ply-sequence encoder with CLT/ABD and panel-geometry branches.
- Train on Case 2/3/4 first, then test whether it can transfer to held-out or newly generated stacking
  patterns.

### 4. Credibility Over Accuracy

The keynote distinguishes high score reporting from credible engineering use and emphasizes physical
fidelity, uncertainty, transferability, and validation infrastructure. This supports the project's strict
grouped Holdout protocol and highlights its remaining validation gaps.

Application to DD:

- Preserve the 546-row locked Holdout and report subgroup metrics by panel size, Case, and Type.
- Add calibration error, interval coverage, OOD detection, and failure-case tables.
- Keep pseudo-labelled 8x8 Type values visibly separate from human-reviewed labels.
- Add a small independent human review or new simulation set before making research-grade claims.

### 5. KPC-RAG for Composites Knowledge

The conference system uses curated and continuously governed composites knowledge, chunk overlap,
similarity cutoffs, low-temperature generation, ranked references, confidence information, and a QA
benchmark. It validates the project's RAG direction but also gives a concrete quality checklist.

Application to DD:

- Add a retrieval score cutoff and abstain when evidence is weak.
- Create a DD-specific benchmark covering Case formulas, CLT/ABD, Type definitions, Pt/P1, XAI,
  panel geometry, and model limitations.
- Measure answer faithfulness and citation correctness, not only whether an answer was returned.
- Record source version/date and review status so stale technical content can be identified.

### 6. Explainable Physics-Informed Machine Learning

The presentation integrates physics through feature engineering and combines SHAP/permutation
importance with dependence and conditional-expectation analysis. This matches the current CLT XAI
approach but goes beyond feature-percentage bars.

Application to DD:

- Add partial-dependence or accumulated-local-effect plots for major CLT and geometry features.
- Show local sensitivity curves around the current theta/panel input.
- Separate predictive importance from physical causality in the UI and reports.

### 7. Physics-Led Generation of Missing Data

This work uses reduced-order physics to reconstruct missing composite properties rather than relying
on unconstrained synthetic data. It is relevant to generalizing beyond the three current panel sizes and
to future material-system inputs.

Application to DD:

- Prefer nondimensional geometry descriptors such as aspect ratio and slenderness over memorizing
  size labels.
- Add material properties, boundary conditions, thickness, and load descriptors when new simulation
  campaigns are available.
- Use physics-generated data only inside a calibrated operating envelope and keep it distinguishable
  from high-fidelity simulation data.

## Recommended Priority

### Immediate: Uncertainty and credibility layer

1. Freeze the existing locked Holdout.
2. Add calibrated Type probabilities and formal Pt/Max. Force prediction intervals.
3. Measure coverage, interval width, expected calibration error, and subgroup performance.
4. Replace or relabel the current heuristic reliability band once formal calibration is available.

### Next: Active-learning simulation planner

1. Score the full Case/theta/panel candidate grid.
2. Rank candidates by expected improvement, uncertainty, distance from known data, and feasibility.
3. Export a small next-simulation queue for human approval.
4. Retrain only after returned simulations pass data-quality and label review.

### Research upgrade: Ply-sequence-native model

1. Build an explicit ply-token dataset from canonical Case 2/3/4 stacks.
2. Train a sequence encoder fused with CLT and geometry features.
3. Hold out entire stacking-pattern families to test transfer, not only unseen angle pairs.
4. Use the successful model for Case 5/custom formula inverse design.

### Product quality: RAG benchmark and governance

1. Add retrieval thresholds and evidence-aware abstention.
2. Build and version a reviewed DD question-answer benchmark.
3. Report citation faithfulness and unsupported-claim rate.
4. Display source date and validation status in the assistant evidence panel.

## What Is Lower Priority Now

The NDE, XCT-image, acoustic-emission, impact-localization, and closed-loop manufacturing talks are
important but require sensor, image, or process-time-series data that the DD dataset does not currently
contain. They are better treated as separate future modules rather than added to the present Pt/curve
model prematurely.

## Bottom Line

The conference does not suggest replacing the current Tree/GointMLP/Hybrid portfolio with one new
large model. It supports a layered engineering workflow: physics-aware surrogate prediction,
calibrated uncertainty, constrained inverse design, targeted simulation acquisition, and transparent
validation. The highest-value next implementation is formal uncertainty calibration followed by an
active-learning simulation planner. A ply-sequence-native model is the most important architectural
research upgrade for supporting new stacking patterns beyond Case 2/3/4.

## Detailed Implementation Order

### Phase 0 - Freeze the reproducible baseline

Keep the 2,700-row three-size dataset, grouped development/Holdout split, canonical Case formulas,
feature schema, and three Pt-consistent model artifacts immutable as the comparison baseline. Record
dataset/model hashes, random seeds, package versions, subgroup metrics, and the pseudo-label lineage.
No future calibration or tuning may use the 546-row locked Holdout.

Deliverables:

- Versioned experiment manifest and model cards.
- One command that reproduces training and evaluation from the fixed manifest.
- Baseline Type, Pt, Max. Force, and curve metrics by Case, Type, and panel size.

### Phase 1 - Add formal calibration and prediction intervals

Create grouped inner folds inside the 2,154-row development set. Fit Type calibration using methods
such as temperature scaling or isotonic calibration, and fit Pt/Max. Force intervals using grouped
split-conformal or cross-conformal residuals. Evaluate only once on the locked Holdout after all
calibration decisions are frozen.

Deliverables:

- Calibrated Type probabilities.
- 80%, 90%, and 95% Pt and Max. Force prediction intervals.
- Brier score, negative log likelihood, expected calibration error, empirical interval coverage, and
  average interval width.
- Overall and subgroup calibration tables.

Promotion rule:

- The displayed confidence percentage must be empirically calibrated.
- A nominal 90% interval must report its actual locked-Holdout coverage and subgroup shortfalls.
- The existing heuristic reliability score remains labelled as design-space screening until replaced.

### Phase 2 - Separate uncertainty, coverage, and OOD risk

Do not compress every warning into one score. Expose model probability/calibration, distance to the
training design space, model-family disagreement, and prediction-interval width as separate signals.
Build an OOD score from canonical physics/geometry features and optionally the neural latent space.

Deliverables:

- Model confidence, data coverage, interval width, and OOD status as separate API fields.
- Residual-versus-OOD analysis proving whether higher risk scores correspond to larger errors.
- Explicit warnings for unseen geometry, stacking-pattern family, material, or boundary condition.

### Phase 3 - Build an offline active-learning simulator

Before requesting new simulations, replay active learning against the existing dataset. Begin with a
small training subset, rank the remaining known rows by uncertainty or acquisition score, reveal their
stored targets, retrain, and compare learning curves against random selection. This proves whether the
selection strategy would have saved simulations historically.

Candidate acquisition should combine:

- Expected Pt improvement.
- Probability of the requested Type.
- Prediction uncertainty or expected uncertainty reduction.
- Distance from already selected candidates to preserve batch diversity.
- Feasibility and angle/geometry constraints.

Deliverables:

- Active-learning replay report versus random sampling.
- A ranked next-simulation CSV containing Case, theta values, panel geometry, predicted outputs,
  uncertainty, acquisition score, and selection reason.
- No automatic simulation launch in the first version; a researcher approves the queue.

### Phase 4 - Run the first closed-loop data campaign

Select a small batch of high-value simulations, run the solver, ingest the returned curve/Pt data,
perform quality checks, and retrain from the full accumulated dataset. Compare uncertainty reduction
and performance improvement in the targeted regions.

Deliverables:

- Approved simulation batch and returned-data manifest.
- Automated curve/Pt quality checks and label-review status.
- Before/after calibration, error, and design-space coverage report.

### Phase 5 - Create a ply-sequence-native dataset and model

Expand every Case formula into the explicit ordered ply stack. Represent each ply with angle encodings,
normalized through-thickness position, thickness, material identifier, and optional pairing or
manufacturing flags. Fuse a compact sequence encoder with the current normalized CLT/ABD and panel
geometry branches.

Recommended validation is stricter than the current angle-group Holdout:

- Unseen theta combinations.
- Unseen panel geometry.
- Leave-one-Case or leave-one-pattern-family-out evaluation.
- Few-shot adaptation using a small number of samples from a new Case.

Deliverables:

- Canonical explicit-ply dataset.
- Small sequence model with Pt-consistent outputs.
- Ablation comparison: theta/case only, CLT/geometry, sequence only, and fused model.

Important limitation:

- Case 2/3/4 data can build the encoder, but credible Case 5 performance cannot be claimed without at
  least a small Case 5 simulation set for external evaluation or adaptation.

### Phase 6 - Add constrained inverse design

Use the calibrated forward surrogate inside an optimizer. Continuous Case/theta search can begin with
Bayesian optimization. Arbitrary discrete ply sequences are better handled with a genetic or
multi-objective evolutionary algorithm under explicit laminate constraints.

Example objectives and constraints:

- Maximize Pt and Type 1 probability.
- Minimize uncertainty and distance from validated design space.
- Constrain angle range, ply count, symmetry, balance, thickness, panel geometry, and manufacturing
  rules.
- Return a Pareto set of diverse candidates instead of one apparently exact optimum.

Every recommended design must show predicted performance, calibrated interval, coverage/OOD state,
constraint status, and whether high-fidelity verification has been completed.

### Phase 7 - Expand geometry, material, and boundary-condition generalization

The current three-size model has evidence for 6x4, 6x8, and 8x8 under the present material and test
configuration. General prediction over arbitrary sizes, materials, thicknesses, loads, or boundary
conditions requires new high-fidelity data. Add nondimensional descriptors and target-normalization
studies before adding raw condition variables without physical structure.

Useful future inputs include:

- Panel dimensions, thickness, aspect/slenderness ratios, and hole or cutout geometry when relevant.
- Lamina elastic properties, ply thickness, density, and strength/failure parameters.
- Boundary-condition and load descriptors.
- Solver settings and data-quality/provenance metadata.

### Phase 8 - Benchmark and govern the RAG assistant

Build a reviewed DD benchmark covering formulas, explicit ply stacks, CLT/ABD, Type definitions,
Pt/P1, XAI interpretation, prediction limitations, and source-aware questions. Evaluate retrieval and
generation separately.

Deliverables:

- Retrieval recall at k, citation precision, answer groundedness, unsupported-claim rate, and correct
  abstention rate.
- Similarity cutoff and evidence-aware refusal when no adequate source exists.
- Source version, publication date, and review status in the evidence panel.

### Phase 9 - Product rollout and research validation

Expose the new capabilities only after offline reports pass. The UI should distinguish a prediction,
calibrated uncertainty, design-space coverage, and research validation status. Keep an audit trail for
inputs, model version, prediction, explanation, recommendation, and later high-fidelity result.

Recommended rollout order:

1. Internal research preview.
2. Web preview with report export.
3. Main web deployment.
4. iOS and Android parity.
5. Research/publication claims only after independent validation and label review.
