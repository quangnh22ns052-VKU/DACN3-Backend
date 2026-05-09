"""
╔═══════════════════════════════════════════════════════════════════╗
║           PHISHGUARD ML MODEL TRAINING SCRIPT                    ║
║      🔨 Train TF-IDF + Logistic Regression Model                ║
╚═══════════════════════════════════════════════════════════════════╝

TÊN FILE: scripts/train_tfidf.py

CÔNG DỤNG:
  - Huấn luyện mô hình ML từ bộ dữ liệu (data/dataset.csv)
  - Xây dựng pipeline: TF-IDF vectorizer → Logistic Regression
  - Lưu mô hình đã huấn luyện vào models/tfidf_lr.pkl
  - Đánh giá hiệu suất: accuracy, precision, recall, F1
  - In báo cáo phân loại chi tiết

INPUT:
  • data/dataset.csv: Bộ dữ liệu huấn luyện
    Format: URL, label (phishing hoặc safe)
    Ví dụ:
    https://verify-amazon.click,phishing
    https://amazon.com,safe

OUTPUT:
  • models/tfidf_lr.pkl: Mô hình đã huấn luyện

CÁCH CHẠY:
  python scripts/train_tfidf.py

OPTIMIZED FOR:
  ✅ High Accuracy
  ✅ Better Phishing Detection
  ✅ Typo Domain Detection
  ✅ Fake Login URL Detection
  ✅ Obfuscated URL Detection
"""

import os
import joblib
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from sklearn.metrics import (
    classification_report,
    accuracy_score,
    roc_auc_score,
    confusion_matrix
)

# =========================================================
# PATHS
# =========================================================

DATA_PATH = os.path.join("data", "dataset.csv")
MODEL_PATH = os.path.join("models", "tfidf_lr.pkl")

# =========================================================
# LOAD DATASET
# =========================================================

print("=" * 70)
print("[INFO] Loading dataset...")
print("=" * 70)

df = pd.read_csv(DATA_PATH)

# Keep required columns only
df = df[["url", "label"]]

# Remove empty rows
df = df.dropna()

# Remove duplicate URLs
df = df.drop_duplicates(subset=["url"])

# Normalize labels
df["label"] = df["label"].str.lower().str.strip()

print(f"[INFO] Dataset loaded successfully")
print(f"[INFO] Total records: {len(df)}")

print("\n[INFO] Label distribution:")
print(df["label"].value_counts())

# =========================================================
# TRAIN / TEST SPLIT
# =========================================================

print("\n" + "=" * 70)
print("[INFO] Splitting dataset...")
print("=" * 70)

X_train, X_test, y_train, y_test = train_test_split(
    df["url"],
    df["label"],
    test_size=0.2,
    stratify=df["label"],
    random_state=42
)

print(f"[INFO] Training samples: {len(X_train)}")
print(f"[INFO] Testing samples : {len(X_test)}")

# =========================================================
# BUILD PIPELINE
# =========================================================

print("\n" + "=" * 70)
print("[INFO] Building ML pipeline...")
print("=" * 70)

pipeline = Pipeline([

    # =====================================================
    # TF-IDF VECTORIZER
    # =====================================================

    (
        "tfidf",

        TfidfVectorizer(

            # Character-level analysis
            analyzer='char_wb',

            # Character n-grams
            ngram_range=(3, 5),

            # Vocabulary size
            max_features=15000,

            # Ignore extremely rare patterns
            min_df=2,

            # Ignore extremely common patterns
            max_df=0.95,

            # Better TF scaling
            sublinear_tf=True,

            # Normalize text
            lowercase=True,
            strip_accents='unicode'
        )
    ),

    # =====================================================
    # LOGISTIC REGRESSION CLASSIFIER
    # =====================================================

    (
        "clf",

        LogisticRegression(

            # More optimization iterations
            max_iter=1000,

            # Better generalization
            C=0.5,

            # Handle imbalanced datasets
            class_weight='balanced',

            # Better for sparse text classification
            solver='liblinear',

            # Reproducible results
            random_state=42
        )
    )
])

# =========================================================
# TRAIN MODEL
# =========================================================

print("\n" + "=" * 70)
print("[INFO] Training Logistic Regression model...")
print("=" * 70)

pipeline.fit(X_train, y_train)

print("[INFO] Training completed successfully!")

# =========================================================
# PREDICTIONS
# =========================================================

y_pred = pipeline.predict(X_test)

# Predict probabilities
y_probs = pipeline.predict_proba(X_test)

# Find phishing probability column
classes = pipeline.named_steps["clf"].classes_

if "phishing" in classes:
    phishing_idx = list(classes).index("phishing")
else:
    phishing_idx = 1

phishing_probs = y_probs[:, phishing_idx]

# Convert labels to binary
binary_y_test = (y_test == "phishing").astype(int)

# =========================================================
# EVALUATION
# =========================================================

print("\n" + "=" * 70)
print("[RESULT] MODEL PERFORMANCE")
print("=" * 70)

# Accuracy
accuracy = accuracy_score(y_test, y_pred)
print(f"Accuracy : {accuracy:.4f}")

# ROC-AUC
roc_auc = roc_auc_score(binary_y_test, phishing_probs)
print(f"ROC-AUC  : {roc_auc:.4f}")

# =========================================================
# CLASSIFICATION REPORT
# =========================================================

print("\n" + "=" * 70)
print("[REPORT] Classification Report")
print("=" * 70)

print(classification_report(y_test, y_pred))

# =========================================================
# CONFUSION MATRIX
# =========================================================

print("\n" + "=" * 70)
print("[REPORT] Confusion Matrix")
print("=" * 70)

print(confusion_matrix(y_test, y_pred))

# =========================================================
# SAVE MODEL
# =========================================================

print("\n" + "=" * 70)
print("[INFO] Saving trained model...")
print("=" * 70)

# Create models directory if missing
os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

# Save full pipeline
joblib.dump(pipeline, MODEL_PATH)

print(f"[INFO] Pipeline saved to:")
print(f"[INFO] Pipeline (vectorizer+model) saved to {MODEL_PATH}")

# =========================================================
# MODEL CONFIGURATION
# =========================================================

print("\n" + "=" * 70)
print("[INFO] MODEL CONFIGURATION")
print("=" * 70)

print("""
TF-IDF SETTINGS
----------------------------
Analyzer        : char_wb
N-grams         : (3,5)
Max Features    : 15000
Min DF          : 2
Max DF          : 0.95
Sublinear TF    : True

LOGISTIC REGRESSION
----------------------------
Max Iterations  : 1000
C               : 0.5
Class Weight    : balanced
Solver          : liblinear
Random State    : 42
""")

print("\n✅ High-accuracy phishing detection model training completed!")

