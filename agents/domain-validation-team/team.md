# Domain Validation Team

## Mission
Ensure all AI predictions are physically meaningful and quantify prediction uncertainty.

## Agents & Model Assignments
- **Physics Validator** (Opus): Checks predictions against physical laws and known bounds — safety-critical
- **Uncertainty Quantifier** (Sonnet): Implements UQ methods, calibrates confidence intervals
- **Comparison Analyst** (Sonnet): Systematic sim vs. experiment comparison

## Validation Checks
### Physical Consistency
- Conservation of mass/energy/momentum
- Positive-definiteness of stiffness tensors
- Stress within material failure envelope
- Fiber orientation tensor constraints (eigenvalues in [0,1], trace = 1)

### Statistical Validation
- Calibrated prediction intervals
- Out-of-distribution detection
- Cross-validation with held-out experimental data

### Engineering Validation
- Comparison against analytical solutions
- Process window sanity checks
- Failure mode consistency

## Code Location
- `src/validation/physics/` — Physical constraint checks
- `src/validation/uncertainty/` — UQ methods
- `src/validation/comparison/` — Sim vs experiment analysis

## Key Principle
A prediction that is statistically accurate but physically impossible is REJECTED.
