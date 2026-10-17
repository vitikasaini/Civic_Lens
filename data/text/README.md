# CivicLens V1.0 — Text Complaint Dataset

## 1. Overview
This dataset contains text descriptions of citizen grievance reports across the 4 fixed civic issue categories for CivicLens V1.0:
1. `Potholes / Damaged Roads` (200 samples)
2. `Garbage Accumulation` (200 samples)
3. `Waterlogging / Drainage Problems` (200 samples)
4. `Streetlight Faults` (200 samples)

- **Total Samples:** 800 records
- **File Format:** CSV (`data/text/complaints_dataset.csv`)
- **Columns:** `text` (string), `category` (string)

## 2. Methodology & Generation Source
Per **Decision 4** in `docs/decisions.md`:
Because there is no single standardized, open dataset containing raw colloquial citizen text specifically for these 4 Indian/municipal categories, this dataset was synthetically compiled using combinatorial templates mirroring real-world municipal 311 service request patterns (such as Boston 311, NYC 311, and FixMyStreet complaint patterns).

Key generation design aspects:
- Diverse urban location mentions (crossings, markets, metro stations, residential colonies).
- Severity cues matching the project plan (e.g. "accident", "deep", "foul smell", "knee-deep", "dark street", "flickering").
- Variations in sentence structure, casing, and lengths.
- Balanced distribution (exactly 200 samples per class) to avoid class bias.

## 3. License & Usage
- Open Academic / MIT for CivicLens development and testing.
