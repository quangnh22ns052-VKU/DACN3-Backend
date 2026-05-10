import os
import joblib
import pandas as pd
import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.utils import resample
from sklearn.metrics import (
    classification_report,
    accuracy_score,
    roc_auc_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score
)

DATA_PATH = os.path.join("data", "dataset.csv")
MODEL_PATH = os.path.join("models", "tfidf_lr.pkl")

# =========================================================
# LOAD & CLEAN
# =========================================================
print("=" * 70)
print("[INFO] Loading dataset...")
df = pd.read_csv(DATA_PATH)
df = df[["url", "label"]].dropna().drop_duplicates(subset=["url"])
df["label"] = df["label"].str.lower().str.strip()

print(f"[INFO] Total records: {len(df)}")
print("\n[INFO] Label distribution (before balance):")
print(df["label"].value_counts())
print(df["label"].value_counts(normalize=True).mul(100).round(1).astype(str) + "%")

# =========================================================
# BALANCE DATASET — undersample safe + oversample phishing
# =========================================================
print("\n" + "=" * 70)
print("[INFO] Balancing dataset...")

df_phishing = df[df["label"] == "phishing"]
df_safe     = df[df["label"] == "safe"]

# Target: 60,000 mỗi class
TARGET = 60_000

# Oversample phishing nếu thiếu
df_phishing_balanced = resample(
    df_phishing,
    replace=True,
    n_samples=TARGET,
    random_state=42
)

# Undersample safe
df_safe_balanced = resample(
    df_safe,
    replace=False,
    n_samples=TARGET,
    random_state=42
)

df_balanced = pd.concat([df_phishing_balanced, df_safe_balanced]).sample(
    frac=1, random_state=42
).reset_index(drop=True)

print(f"[INFO] Balanced dataset: {len(df_balanced)} records")
print(df_balanced["label"].value_counts())

# =========================================================
# TRAIN / TEST SPLIT — stratified
# =========================================================
X_train, X_test, y_train, y_test = train_test_split(
    df_balanced["url"],
    df_balanced["label"],
    test_size=0.2,
    stratify=df_balanced["label"],
    random_state=42
)

print(f"\n[INFO] Train: {len(X_train)} | Test: {len(X_test)}")

# =========================================================
# PIPELINE
# =========================================================
pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(
        analyzer='word',
        ngram_range=(1, 2),       # giảm từ (1,3) xuống để tránh overfit
        max_features=8000,        # tăng từ 5000 để bắt nhiều pattern hơn
        min_df=2,
        max_df=0.95,
        sublinear_tf=True,        # log(1+tf) thay vì tf thuần — giảm ảnh hưởng từ lặp nhiều
        lowercase=True,
        token_pattern=r'(?u)\b[\w.-]+\b'
    )),
    ("clf", LogisticRegression(
        max_iter=1000,
        C=0.5,                    # tăng regularization (giảm C) để giảm overfit
        class_weight='balanced',  # tự động cân bằng class weight trong loss
        solver='liblinear',
        random_state=42
    ))
])

# =========================================================
# CROSS-VALIDATION trước khi train chính thức
# =========================================================
print("\n" + "=" * 70)
print("[INFO] Running 5-fold cross-validation...")

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_scores = cross_val_score(pipeline, X_train, y_train, cv=cv, scoring='f1_macro', n_jobs=-1)

print(f"[CV] F1-macro per fold: {[round(s,4) for s in cv_scores]}")
print(f"[CV] Mean: {cv_scores.mean():.4f} | Std: {cv_scores.std():.4f}")

if cv_scores.std() > 0.01:
    print("[WARN] Std cao — có thể đang overfit hoặc data noise")

# =========================================================
# TRAIN CHÍNH THỨC
# =========================================================
print("\n" + "=" * 70)
print("[INFO] Training final model...")
pipeline.fit(X_train, y_train)
print("[INFO] Training completed!")

# =========================================================
# EVALUATION
# =========================================================
y_pred  = pipeline.predict(X_test)
y_probs = pipeline.predict_proba(X_test)

classes = pipeline.named_steps["clf"].classes_
phishing_idx   = list(classes).index("phishing") if "phishing" in classes else 1
phishing_probs = y_probs[:, phishing_idx]
binary_y_test  = (y_test == "phishing").astype(int)

print("\n" + "=" * 70)
print("[RESULT] MODEL PERFORMANCE")
print("=" * 70)
print(f"Accuracy  : {accuracy_score(y_test, y_pred):.4f}")
print(f"ROC-AUC   : {roc_auc_score(binary_y_test, phishing_probs):.4f}")
print(f"F1-macro  : {f1_score(y_test, y_pred, average='macro'):.4f}")
print(f"Precision : {precision_score(y_test, y_pred, pos_label='phishing'):.4f}")
print(f"Recall    : {recall_score(y_test, y_pred, pos_label='phishing'):.4f}")

print("\n" + "=" * 70)
print("[REPORT] Classification Report")
print(classification_report(y_test, y_pred))

cm = confusion_matrix(y_test, y_pred)
print("[REPORT] Confusion Matrix")
print(cm)

tn, fp, fn, tp = cm.ravel()
print(f"\n  True Positive  (phishing đúng) : {tp}")
print(f"  False Negative (phishing bỏ sót): {fn}  ← quan trọng nhất")
print(f"  False Positive (safe nhầm)      : {fp}")
print(f"  True Negative  (safe đúng)      : {tn}")
print(f"\n  False Negative Rate: {fn/(fn+tp)*100:.2f}%  (mục tiêu < 5%)")

# =========================================================
# SAVE
# =========================================================
os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
joblib.dump(pipeline, MODEL_PATH)
print(f"\n[INFO] Model saved to {MODEL_PATH}")
print("✅ Done!")