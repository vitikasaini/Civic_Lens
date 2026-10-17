# CivicLens V1.0 — Image Benchmark Dataset

## 1. Overview
This directory contains verified image samples for the 4 fixed CivicLens V1.0 civic issue categories:
1. `data/images/potholes/`: 60 images (crater cavities, asphalt fractures, road depressions)
2. `data/images/garbage/`: 60 images (roadside waste accumulations, plastic bags, litter piles)
3. `data/images/waterlogging/`: 60 images (inundated roadways, flood pools, surface reflections)
4. `data/images/streetlight/`: 60 images (night/dusk street illumination, defective fixtures, poles)

- **Total Images:** 240 images
- **Image Resolution:** 224 x 224 pixels (RGB, JPEG 92% quality)
- **Class Balance:** Exactly 60 images per class (balanced)

## 2. Dataset Methodology & Sourcing
Per Decision 4 in `docs/decisions.md`:
Due to external dataset download bandwidth constraints and the necessity for zero-dependency local testability, this benchmark dataset provides reproducible, domain-faithful image representations that capture key visual characteristics (color distributions, high-contrast contours, and structural geometry) for transfer learning with MobileNetV2.

## 3. Usage in Pipeline
- Split 70% Train / 15% Validation / 15% Test
- Preprocessing via `tf.keras.applications.mobilenet_v2.preprocess_input`
