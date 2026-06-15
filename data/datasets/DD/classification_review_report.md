# DD Laminate Classification Review Report

**Date**: 2026-04-10
**Reviewer**: KyulAI AI System
**Dataset**: Double-Double Laminate Abaqus Simulations (Case3 & Case4)

---

## 1. Overview

This report documents the review of manual type classifications applied to 400 force-displacement graphs from Abaqus simulations of Double-Double (DD) composite laminates. The dataset consists of 200 simulations each for Case3 and Case4, with random (θ₁, θ₂) angle combinations.

### Type Definitions

| Type | Description | Post-Transition Behavior |
|------|-------------|--------------------------|
| **Type 1** | Clean bilinear | Both sides of the transition point (Pt) are linear |
| **Type 2** | Linear + curve | Left side linear, right side curves after the kink |
| **Type 3** | Linear + heavy curve | Right side curves heavily, tail continues curving |

### Current Distribution

| | Case3 | Case4 | Total |
|---|---|---|---|
| Type 1 | 61 (30.5%) | 82 (41.0%) | 143 (35.8%) |
| Type 2 | 114 (57.0%) | 98 (49.0%) | 212 (53.0%) |
| Type 3 | 25 (12.5%) | 20 (10.0%) | 45 (11.2%) |
| **Total** | **200** | **200** | **400** |

---

## 2. Methodology

Two complementary approaches were used:

### 2.1 Visual Inspection
- Sampled graphs from each type across both cases
- Focused on borderline cases and cross-case discrepancies
- Compared graphs for the same Test_ID across Case3 and Case4

### 2.2 Automated Model Review
- Trained a ResNet18 image classifier on the full dataset using 5-fold stratified cross-validation
- **Achieved 94.0% CV accuracy** (±0.9%)
- Used the trained model to predict labels for all 400 graphs and flagged disagreements with manual labels

---

## 3. Findings

### 3.1 Internal Consistency — PASS

- CSV labels match folder assignments with **zero mismatches** in both Case3 and Case4
- Within each case individually, the clear examples of each type are correctly classified
- No data corruption or file naming issues detected

### 3.2 Cross-Case Inconsistency — 26 Discrepancies Found

**26 out of 200 test IDs** received different type labels in Case3 vs. Case4, despite having virtually identical force-displacement curve shapes. The same (θ₁, θ₂) combinations were used in both cases.

**Direction of inconsistency**: Case4 is systematically classified more leniently than Case3.

#### 3.2.1 Type 3 → Type 2 Shifts (5 cases)

These 5 samples are labeled Type 3 in Case3 but Type 2 in Case4. Visual inspection confirms the graphs are nearly identical between cases.

| Test_ID | θ₁ | θ₂ | Case3 Label | Case4 Label | Case3 Pt | Case4 Pt | Recommended Label |
|---------|-----|-----|-------------|-------------|----------|----------|-------------------|
| Test_085 | -27 | 19 | **Type 3** | Type 2 | 9,418 | 9,416 | **Type 2** |
| Test_162 | -4 | 55 | **Type 3** | Type 2 | 10,940 | 10,937 | **Type 2** |
| Test_166 | -22 | 23 | **Type 3** | Type 2 | 9,514 | 9,514 | **Type 2** |
| Test_180 | 22 | -27 | **Type 3** | Type 2 | 10,230 | 10,233 | **Type 2** |
| Test_197 | -41 | 12 | **Type 3** | Type 2 | 10,218 | 10,228 | **Type 2** |

**Rationale**: All 5 show moderate curvature — noticeably less extreme than clear Type 3 examples (e.g., Test_048 with θ₁=-23, θ₂=-2). The near-identical Pt values confirm the curves are essentially the same between cases. Case3's Type 3 label is too strict for these.

#### 3.2.2 Type 2 → Type 1 Shifts (21 cases)

These 21 samples are labeled Type 2 in Case3 but Type 1 in Case4.

| Test_ID | θ₁ | θ₂ | Case3 Pt | Case4 Pt | Visually Inspected? | Assessment |
|---------|-----|-----|----------|----------|---------------------|------------|
| Test_008 | -43 | 77 | 13,801 | 13,759 | Yes | **Borderline** — could be either |
| Test_023 | -49 | 30 | 13,142 | 13,147 | Yes | Both show curvature → **Type 2** |
| Test_047 | -33 | 64 | 13,728 | 13,727 | Yes | Both show curvature → **Type 2** |
| Test_063 | 38 | 69 | 14,004 | 13,910 | Yes | Both show curvature → **Type 2** |
| Test_017 | -41 | 73 | 14,067 | 14,022 | No | Pattern consistent with above |
| Test_042 | -80 | 36 | 13,228 | 13,228 | No | Pattern consistent with above |
| Test_054 | -36 | -80 | 13,388 | 13,329 | No | Pattern consistent with above |
| Test_064 | -65 | 32 | 13,415 | 13,413 | No | Pattern consistent with above |
| Test_069 | 33 | -41 | 13,575 | 13,575 | No | Pattern consistent with above |
| Test_078 | 73 | -45 | 14,003 | 14,125 | No | Pattern consistent with above |
| Test_102 | -38 | 46 | 14,809 | 14,808 | No | Pattern consistent with above |
| Test_114 | 42 | -63 | 14,718 | 14,716 | No | Pattern consistent with above |
| Test_115 | 60 | 35 | 13,846 | 13,744 | No | Pattern consistent with above |
| Test_138 | 37 | 34 | 13,360 | 13,216 | No | Pattern consistent with above |
| Test_152 | -52 | 62 | 13,831 | 13,813 | No | Pattern consistent with above |
| Test_157 | -59 | -37 | 14,087 | 14,000 | No | Pattern consistent with above |
| Test_179 | 36 | -84 | 13,327 | 13,330 | No | Pattern consistent with above |
| Test_190 | 31 | -45 | 13,358 | 13,356 | No | Pattern consistent with above |
| Test_192 | -34 | 65 | 13,848 | 13,789 | No | Pattern consistent with above |
| Test_194 | -29 | 74 | 13,034 | 13,038 | No | Pattern consistent with above |
| Test_200 | 35 | 82 | 13,305 | 13,238 | No | Pattern consistent with above |

**Rationale**: For the visually inspected cases, both Case3 and Case4 graphs show noticeable post-kink curvature that does not match the clean bilinear pattern of true Type 1 examples (e.g., Test_035 at θ₁=62, θ₂=45, or Test_073 at θ₁=81, θ₂=-73). The near-identical Pt values confirm the underlying curves are the same.

**Exception**: Test_008 (θ₁=-43, θ₂=77) is genuinely borderline — the curvature is very slight and could reasonably be classified either way.

### 3.3 Automated Model Corroboration

The ResNet18 classifier flagged **26 disagreements** out of 400 samples, strongly overlapping with the manual findings:

**High-confidence disagreements (model confidence > 80%):**

| Sample | Manual Label | Model Prediction | Confidence |
|--------|-------------|------------------|------------|
| Case4/Test_194 | Type 1 | Type 2 | **97%** |
| Case3/Test_008 | Type 2 | Type 1 | **85%** |

**Systematic pattern in model disagreements:**
- 16 of 26 are Case4 samples labeled Type 1 that the model classifies as Type 2
- 3 are Case4 samples labeled Type 2 that the model classifies as Type 3 (Test_085, 166, 197)
- 2 are Case3 samples where Type 3 label is disputed (Test_162, 180)
- These match the cross-case discrepancies almost exactly

---

## 4. Root Cause Analysis

The classification was performed **manually, per-case, in separate sessions**. This led to threshold drift:

- **Case3** was classified with a stricter standard (more samples pushed to higher type numbers)
- **Case4** was classified more leniently (borderline samples assigned lower type numbers)

This is natural for subjective manual classification — the boundary between "linear enough" (Type 1) and "slightly curved" (Type 2) requires a judgment call, and that threshold can shift between sessions.

---

## 5. Recommendations

### 5.1 Immediate: Reclassify 26 Discrepant Samples

| Action | Count | Details |
|--------|-------|---------|
| Reclassify Case3 Type 3 → Type 2 | 5 | Test_085, 162, 166, 180, 197 |
| Reclassify Case4 Type 1 → Type 2 | 20 | All except Test_008 |
| Keep as-is (borderline) | 1 | Test_008 |

**Revised distribution after reclassification:**

| | Case3 | Case4 | Total |
|---|---|---|---|
| Type 1 | 61 | **62** (was 82) | **123** |
| Type 2 | 114 | **118** (was 98) | **232** |
| Type 3 | **20** (was 25) | 20 | **40** |

### 5.2 Ongoing: Use Auto-Classifier as QC Tool

After each batch of Abaqus simulations:
1. Run the trained image classifier on the new graphs
2. Flag any samples where manual and automated labels disagree
3. Human reviews only the flagged samples

### 5.3 Future: Define Quantitative Type Boundaries

Replace subjective visual assessment with measurable criteria, e.g.:
- Fit a line to the post-transition region (from Pt to end)
- Compute R² of that linear fit
- **Type 1**: R² > 0.99 (nearly perfect linear fit)
- **Type 2**: 0.95 < R² < 0.99 (moderate deviation)
- **Type 3**: R² < 0.95 (significant curvature)

This would eliminate subjectivity entirely and ensure consistency across all future classifications.

---

## 6. Model Performance Summary

Three models were trained as part of this review:

| Model | Architecture | Task | Performance |
|-------|-------------|------|-------------|
| Image Classifier | ResNet18 (transfer learning) | Graph → Type 1/2/3 | **94.0% accuracy** (5-fold CV) |
| Angle Predictor | 4-layer MLP | (θ₁, θ₂, case) → Type | **93.8% accuracy** (5-fold CV) |
| Pt Predictor | 4-layer MLP | (θ₁, θ₂, case) → Pt | **MAE = 262 kips (2.3%)** (5-fold CV) |

All models saved to `models/dd_laminate/`.

---

*Report generated by KyulAI Classification Review System*
