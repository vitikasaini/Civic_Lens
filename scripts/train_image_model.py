"""
Image Model Training and Evaluation Script for CivicLens V1.0.

Uses Transfer Learning with MobileNetV2:
- Pretrained ImageNet feature extractor (frozen base)
- Custom head: GlobalAveragePooling2D -> Dense(128, relu) -> Dropout(0.2) -> Dense(4, softmax)
- 70/15/15 stratified train/val/test split with zero data leakage
- Data augmentation on training split (rotations, flips, contrast)
- Evaluates test set and saves confusion matrix to docs/image_confusion_matrix.png
- Updates docs/evaluation.md with measured metrics
"""

import os
import ssl
import json
import random
from pathlib import Path
import numpy as np
import cv2
import matplotlib.pyplot as plt

# Handle SSL on systems with clock drift
ssl._create_default_https_context = ssl._create_unverified_context

import tensorflow as tf
from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2, preprocess_input
from tensorflow.keras import layers, models, optimizers
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
)

# Seed everything for deterministic reproducibility
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
tf.random.set_seed(SEED)

BASE_DIR = Path(__file__).resolve().parent.parent
IMAGE_DIR = BASE_DIR / "data" / "images"
MODELS_DIR = BASE_DIR / "backend" / "ml" / "models"
DOCS_DIR = BASE_DIR / "docs"

MODELS_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

# Standard category mapping
CATEGORY_MAP = {
    "potholes": "Potholes / Damaged Roads",
    "garbage": "Garbage Accumulation",
    "waterlogging": "Waterlogging / Drainage Problems",
    "streetlight": "Streetlight Faults",
}
CLASSES = sorted(list(CATEGORY_MAP.values()))
CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}


def load_dataset_filelist():
    """Gathers image file paths and labels, returning organized lists."""
    data = []
    for folder_name, canonical_name in CATEGORY_MAP.items():
        folder_path = IMAGE_DIR / folder_name
        files = sorted(list(folder_path.glob("*.jpg")) + list(folder_path.glob("*.png")))
        for f in files:
            data.append({"path": str(f), "filename": f.name, "category": canonical_name})
    return data


def augment_image(img: np.ndarray) -> np.ndarray:
    """Applies random augmentation: horizontal flip, mild rotation, brightness."""
    # Random horizontal flip
    if random.random() < 0.5:
        img = cv2.flip(img, 1)

    # Mild rotation (-15 to +15 deg)
    if random.random() < 0.5:
        angle = random.uniform(-15, 15)
        h, w = img.shape[:2]
        m = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        img = cv2.warpAffine(img, m, (w, h), borderMode=cv2.BORDER_REFLECT)

    # Mild brightness adjustment
    if random.random() < 0.5:
        factor = random.uniform(0.85, 1.15)
        img = np.clip(img.astype(np.float32) * factor, 0, 255).astype(np.uint8)

    return img


def load_and_preprocess(filepath: str, is_training: bool = False) -> np.ndarray:
    """Reads image, applies optional augmentation, converts BGR->RGB, and applies MobileNetV2 scaling."""
    img = cv2.imread(filepath)
    if img is None:
        raise ValueError(f"Failed to read image at: {filepath}")

    img = cv2.resize(img, (224, 224))
    if is_training:
        img = augment_image(img)

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32)
    return preprocess_input(img_rgb)


def main():
    print("Loading image file list from:", IMAGE_DIR)
    all_files = load_dataset_filelist()
    print(f"Total images found: {len(all_files)}")

    # Group by category for stratified 70 / 15 / 15 split
    by_category = {}
    for item in all_files:
        by_category.setdefault(item["category"], []).append(item)

    train_items, val_items, test_items = [], [], []

    for cat, items in by_category.items():
        random.shuffle(items)
        n = len(items)
        n_train = int(n * 0.70)
        n_val = int(n * 0.15)

        cat_train = items[:n_train]
        cat_val = items[n_train:n_train + n_val]
        cat_test = items[n_train + n_val:]

        train_items.extend(cat_train)
        val_items.extend(cat_val)
        test_items.extend(cat_test)

    print(f"Split sizes -> Train: {len(train_items)} | Val: {len(val_items)} | Test: {len(test_items)}")

    # Verify zero data leakage
    train_filenames = {item["filename"] for item in train_items}
    val_filenames = {item["filename"] for item in val_items}
    test_filenames = {item["filename"] for item in test_items}

    assert not (train_filenames & val_filenames), "Data leakage between train and val!"
    assert not (train_filenames & test_filenames), "Data leakage between train and test!"
    assert not (val_filenames & test_filenames), "Data leakage between val and test!"
    print("Verification: Zero data leakage across splits confirmed.")

    # Save split manifest for inspection/testing
    split_manifest = {
        "train": [it["filename"] for it in train_items],
        "val": [it["filename"] for it in val_items],
        "test": [it["filename"] for it in test_items],
    }
    with open(MODELS_DIR / "image_split_manifest.json", "w") as f:
        json.dump(split_manifest, f, indent=2)

    # Prepare numpy arrays
    print("Preprocessing image arrays...")
    X_train = np.array([load_and_preprocess(it["path"], is_training=True) for it in train_items])
    y_train = np.array([CLASS_TO_IDX[it["category"]] for it in train_items])

    X_val = np.array([load_and_preprocess(it["path"], is_training=False) for it in val_items])
    y_val = np.array([CLASS_TO_IDX[it["category"]] for it in val_items])

    X_test = np.array([load_and_preprocess(it["path"], is_training=False) for it in test_items])
    y_test = np.array([CLASS_TO_IDX[it["category"]] for it in test_items])

    # Convert targets to one-hot vectors
    y_train_cat = tf.keras.utils.to_categorical(y_train, num_classes=4)
    y_val_cat = tf.keras.utils.to_categorical(y_val, num_classes=4)

    # Build Transfer Learning Model
    print("\n--- Constructing MobileNetV2 Transfer Learning Architecture ---")
    base_model = MobileNetV2(
        input_shape=(224, 224, 3),
        include_top=False,
        weights="imagenet",
    )
    base_model.trainable = False  # Freeze pretrained feature extraction layers

    inputs = tf.keras.Input(shape=(224, 224, 3))
    x = base_model(inputs, training=False)
    x = layers.GlobalAveragePooling2D(name="global_avg_pool")(x)
    x = layers.Dense(128, activation="relu", name="dense_128")(x)
    x = layers.Dropout(0.2, name="dropout")(x)
    outputs = layers.Dense(4, activation="softmax", name="predictions")(x)

    model = models.Model(inputs, outputs, name="CivicLens_MobileNetV2")

    model.compile(
        optimizer=optimizers.Adam(learning_rate=1e-3),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )

    model.summary()

    # Train model
    print("\n--- Training Model ---")
    epochs = 8
    history = model.fit(
        X_train,
        y_train_cat,
        validation_data=(X_val, y_val_cat),
        epochs=epochs,
        batch_size=16,
        verbose=1,
    )

    # Verify loss decreased
    initial_loss = history.history["loss"][0]
    final_loss = history.history["loss"][-1]
    print(f"Initial Epoch Loss: {initial_loss:.4f} -> Final Epoch Loss: {final_loss:.4f}")
    assert final_loss < initial_loss, "Model loss did not decrease during training!"

    # Evaluate on held-out test set
    print("\n--- Evaluating on Held-Out Test Set ---")
    y_pred_probs = model.predict(X_test)
    y_pred = np.argmax(y_pred_probs, axis=1)

    test_acc = accuracy_score(y_test, y_pred)
    p_w, r_w, f1_w, _ = precision_recall_fscore_support(y_test, y_pred, average="weighted")
    print(f"Test Accuracy: {test_acc:.4f} ({test_acc * 100:.2f}%) | Weighted F1: {f1_w:.4f}")

    report_dict = classification_report(y_test, y_pred, target_names=CLASSES, output_dict=True)
    report_text = classification_report(y_test, y_pred, target_names=CLASSES)
    print("\nClassification Report (Test Set):")
    print(report_text)

    # Confusion Matrix
    cm = confusion_matrix(y_test, y_pred)
    fig, ax = plt.subplots(figsize=(8, 6))
    disp = ConfusionMatrixDisplay(
        confusion_matrix=cm,
        display_labels=[c.split("/")[0].strip() for c in CLASSES],
    )
    disp.plot(cmap=plt.cm.Greens, ax=ax, values_format="d")
    plt.title("Confusion Matrix — MobileNetV2 (Test Set)", fontsize=13)
    plt.tight_layout()

    cm_path = DOCS_DIR / "image_confusion_matrix.png"
    plt.savefig(cm_path, dpi=200)
    plt.close()
    print(f"Confusion matrix saved to: {cm_path}")

    # Save model and classes
    model_save_path = MODELS_DIR / "image_model.keras"
    model.save(str(model_save_path))
    print(f"Saved trained image model to: {model_save_path}")

    classes_save_path = MODELS_DIR / "image_classes.json"
    with open(classes_save_path, "w") as f:
        json.dump(CLASSES, f, indent=2)
    print(f"Saved class index mapping to: {classes_save_path}")

    # Update docs/evaluation.md with measured metrics
    eval_file = DOCS_DIR / "evaluation.md"
    current_content = eval_file.read_text(encoding="utf-8") if eval_file.exists() else ""

    image_eval_section = f"""## 2. Image Classification Model Evaluation

- **Architecture:** Pretrained MobileNetV2 (ImageNet) + GlobalAveragePooling2D + Dense(128, ReLU) + Dropout(0.2) + Dense(4, Softmax).
- **Dataset:** 240 benchmark civic images (60 per category across Potholes, Garbage, Waterlogging, Streetlights).
- **Split:** 70% Train (168 images) / 15% Validation (36 images) / 15% Test (36 images, held-out).
- **Augmentation:** Random horizontal flipping, rotational perturbations (-15° to +15°), contrast adjustments.
- **Preprocessing:** Resized to 224×224, normalized via MobileNetV2 `preprocess_input` ([-1, 1] range).

### 2.1 Overall Performance Metrics (Held-Out Test Set)

| Metric | Score | Percentage |
|---|---|---|
| **Test Accuracy** | **{test_acc:.4f}** | **{test_acc * 100:.2f}%** |
| **Precision (Weighted)** | **{p_w:.4f}** | **{p_w * 100:.2f}%** |
| **Recall (Weighted)** | **{r_w:.4f}** | **{r_w * 100:.2f}%** |
| **F1-Score (Weighted)** | **{f1_w:.4f}** | **{f1_w * 100:.2f}%** |

### 2.2 Per-Class Breakdown

| Category | Precision | Recall | F1-Score | Support |
|---|---|---|---|---|
"""
    for c in CLASSES:
        m = report_dict[c]
        image_eval_section += f"| **{c}** | {m['precision']:.4f} | {m['recall']:.4f} | {m['f1-score']:.4f} | {int(m['support'])} |\n"

    image_eval_section += f"""
### 2.3 Confusion Matrix
The confusion matrix visualization is saved at: [`docs/image_confusion_matrix.png`](./image_confusion_matrix.png)

```
Classes: {[c.split('/')[0].strip() for c in CLASSES]}
Matrix:
{cm}
```
"""

    if "## 2. Image Classification Model Evaluation" in current_content:
        # Replace the placeholder section
        parts = current_content.split("## 2. Image Classification Model Evaluation")
        rest = parts[1].split("## 3. Severity Scoring Validation")
        updated_content = parts[0] + image_eval_section + "\n---\n\n## 3. Severity Scoring Validation" + rest[1]
    else:
        updated_content = current_content + "\n\n" + image_eval_section

    eval_file.write_text(updated_content, encoding="utf-8")
    print(f"Updated docs/evaluation.md with measured image metrics.")


if __name__ == "__main__":
    main()
