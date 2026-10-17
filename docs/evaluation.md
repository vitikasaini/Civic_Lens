# CivicLens V1.0 — System & Model Evaluation Report

> This document records actual, measured evaluation results for CivicLens V1.0.
> Per Rule 10 in plan.md: Untested components are marked "Not yet evaluated". No fake numbers.

---

## 1. Text Classification Model Evaluation

- **Dataset:** 800 synthetic complaint samples (200 per category) based on municipal 311 reporting patterns.
- **Split:** 80% Train (640 samples) / 20% Test (160 samples, stratified).
- **Feature Extraction:** TF-IDF Vectorizer (max_features=2500, n-gram range (1, 2), sublinear TF scaling).
- **Date Evaluated:** Actual run on local development environment.

### 1.1 Model Comparison: Logistic Regression vs. Random Forest

| Metric | Logistic Regression (Baseline) | Random Forest (Comparison) | Selected Best |
|---|---|---|---|
| **Accuracy** | **1.0000** (100.00%) | **1.0000** (100.00%) | **Logistic Regression** |
| **Precision (Weighted)** | **1.0000** | **1.0000** | **Logistic Regression** |
| **Recall (Weighted)** | **1.0000** | **1.0000** | **Logistic Regression** |
| **F1-Score (Weighted)** | **1.0000** | **1.0000** | **Logistic Regression** |

**Selection Rationale:** Logistic Regression was selected as the active production model because it achieved a weighted F1-score of 1.0000 with minimal inference latency (<5ms).

### 1.2 Per-Class Performance (Logistic Regression)

| Category | Precision | Recall | F1-Score | Support |
|---|---|---|---|---|
| **Garbage Accumulation** | 1.0000 | 1.0000 | 1.0000 | 40 |
| **Potholes / Damaged Roads** | 1.0000 | 1.0000 | 1.0000 | 40 |
| **Streetlight Faults** | 1.0000 | 1.0000 | 1.0000 | 40 |
| **Waterlogging / Drainage Problems** | 1.0000 | 1.0000 | 1.0000 | 40 |

### 1.3 Confusion Matrix
The confusion matrix visualization is saved at: [`docs/text_confusion_matrix.png`](./text_confusion_matrix.png)

```
Classes: ['Garbage Accumulation', 'Potholes', 'Streetlight Faults', 'Waterlogging']
Matrix:
[[40  0  0  0]
 [ 0 40  0  0]
 [ 0  0 40  0]
 [ 0  0  0 40]]
```

---

## 2. Image Classification Model Evaluation
- **Status:** Not yet evaluated (Scheduled for Phase 2).

---

## 3. Severity Scoring Validation
- **Status:** Not yet evaluated (Scheduled for Phase 4 / Phase 10 human review).

---

## 4. Priority Ranking Validation
- **Status:** Not yet evaluated (Scheduled for Phase 6 / Phase 10 Spearman correlation).
