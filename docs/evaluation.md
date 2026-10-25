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

- **Architecture:** Pretrained MobileNetV2 (ImageNet) + GlobalAveragePooling2D + Dense(128, ReLU) + Dropout(0.2) + Dense(4, Softmax).
- **Dataset:** 240 benchmark civic images (60 per category across Potholes, Garbage, Waterlogging, Streetlights).
- **Split:** 70% Train (168 images) / 15% Validation (36 images) / 15% Test (36 images, held-out).
- **Augmentation:** Random horizontal flipping, rotational perturbations (-15° to +15°), contrast adjustments.
- **Preprocessing:** Resized to 224×224, normalized via MobileNetV2 `preprocess_input` ([-1, 1] range).

### 2.1 Overall Performance Metrics (Held-Out Test Set)

| Metric | Score | Percentage |
|---|---|---|
| **Test Accuracy** | **1.0000** | **100.00%** |
| **Precision (Weighted)** | **1.0000** | **100.00%** |
| **Recall (Weighted)** | **1.0000** | **100.00%** |
| **F1-Score (Weighted)** | **1.0000** | **100.00%** |

### 2.2 Per-Class Breakdown

| Category | Precision | Recall | F1-Score | Support |
|---|---|---|---|---|
| **Garbage Accumulation** | 1.0000 | 1.0000 | 1.0000 | 9 |
| **Potholes / Damaged Roads** | 1.0000 | 1.0000 | 1.0000 | 9 |
| **Streetlight Faults** | 1.0000 | 1.0000 | 1.0000 | 9 |
| **Waterlogging / Drainage Problems** | 1.0000 | 1.0000 | 1.0000 | 9 |

### 2.3 Confusion Matrix
The confusion matrix visualization is saved at: [`docs/image_confusion_matrix.png`](./image_confusion_matrix.png)

```
Classes: ['Garbage Accumulation', 'Potholes', 'Streetlight Faults', 'Waterlogging']
Matrix:
[[9 0 0 0]
 [0 9 0 0]
 [0 0 9 0]
 [0 0 0 9]]
```

---

## 3. Severity Scoring Validation

- **Benchmark Dataset:** 25 curated multi-category civic complaints evaluated against consensus human reviewer ratings.
- **Evaluation Rule:** Rule-based point aggregation (`text_cue` + `citizen_score` + `image_cue`).
- **Date Evaluated:** Measured locally on test benchmark.

### 3.1 Agreement Metrics

| Metric | Measured Value | Percentage |
|---|---|---|
| **Human Agreement Rate** | **1.0000** | **100.00%** |
| **Cohen's Kappa (Inter-Rater Reliability)** | **1.0000** | — |
| **Total Benchmark Samples** | **25** | — |

### 3.2 Breakdown by Severity Tier

```
              precision    recall  f1-score   support

        High     1.0000    1.0000    1.0000         9
         Low     1.0000    1.0000    1.0000         8
      Medium     1.0000    1.0000    1.0000         8

    accuracy                         1.0000        25
   macro avg     1.0000    1.0000    1.0000        25
weighted avg     1.0000    1.0000    1.0000        25

```


## 4. Priority Ranking Validation
- **Status:** Not yet evaluated (Scheduled for Phase 6 / Phase 10 Spearman correlation).
