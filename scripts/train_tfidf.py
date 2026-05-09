# =========================================================
# PHISHGUARD ML TRAINING SCRIPT
# Huấn luyện mô hình phát hiện URL phishing
# =========================================================

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
# ĐƯỜNG DẪN FILE
# =========================================================

# File dataset chứa URL + label
DATA_PATH = os.path.join("data", "dataset.csv")

# File model sau khi train xong
MODEL_PATH = os.path.join("models", "tfidf_lr.pkl")

# =========================================================
# LOAD DATASET
# =========================================================

print("=" * 70)
print("[INFO] Loading dataset...")
print("=" * 70)

# Đọc file CSV
df = pd.read_csv(DATA_PATH)

# Chỉ giữ 2 cột cần thiết
df = df[["url", "label"]]

# Xoá dòng bị null
df = df.dropna()

# Xoá URL bị trùng
df = df.drop_duplicates(subset=["url"])

# Chuẩn hoá label
# Ví dụ:
# "Phishing " → "phishing"
df["label"] = df["label"].str.lower().str.strip()

print(f"[INFO] Dataset loaded successfully")
print(f"[INFO] Total records: {len(df)}")

print("\n[INFO] Label distribution:")
print(df["label"].value_counts())

# =========================================================
# CHIA TRAIN / TEST
# =========================================================

print("\n" + "=" * 70)
print("[INFO] Splitting dataset...")
print("=" * 70)

# 80% train
# 20% test
#
# stratify giúp giữ đúng tỉ lệ phishing/safe
# random_state giúp kết quả luôn giống nhau
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

# Pipeline = TF-IDF + Logistic Regression
#
# URL
#   ↓
# TF-IDF vector
#   ↓
# Logistic Regression
#   ↓
# phishing / safe
pipeline = Pipeline([

    # =====================================================
    # TF-IDF VECTORIZER
    # =====================================================

    (
        "tfidf",

        TfidfVectorizer(
            analyzer='word',

            # ngram_range=(1,2)
            # (1,1) = unigram
            #   → login
            # (1,2) = unigram + bigram
            #   → login
            #   → secure
            #   → login secure
            # Giúp model hiểu context tốt hơn
            # Accuracy tăng nhẹ
            # RAM tăng nhẹ
            # =================================================
            ngram_range=(1, 2),
            # max_features=8000
            # Chỉ giữ 8000 feature quan trọng nhất
            # Tăng:
            #   → Accuracy tăng
            #   → RAM tăng
            # Giảm:
            #   → Train nhanh
            #   → Model nhẹ
            max_features=3500,
            dtype='float32',
            # =================================================
            # min_df=2
            min_df=2,
            # Bỏ token xuất hiện quá nhiều
            max_df=0.95,
            # Giảm ảnh hưởng của từ lặp nhiều lần
            sublinear_tf=True,
            lowercase=True,

            
            token_pattern=r'(?u)\b[\w.-]+\b'
        )
    ),

    # =====================================================
    # LOGISTIC REGRESSION
    # =====================================================

    (
        "clf",

        LogisticRegression(

            # =================================================
            # max_iter=500
            #
            # Số vòng tối ưu gradient descent
            #
            # Tăng:
            #   → hội tụ tốt hơn
            #   → train lâu hơn
            #
            # Nếu quá thấp:
            #   → model chưa học xong
            # =================================================
            max_iter=500,

            # =================================================
            # C=0.7
            #
            # Regularization strength
            #
            # C nhỏ:
            #   → model đơn giản hơn
            #   → ít overfit
            #
            # C lớn:
            #   → model fit mạnh hơn
            #   → dễ overfit
            # =================================================
            C=0.7,

            # =================================================
            # class_weight='balanced'
            #
            # Tự cân bằng phishing/safe
            #
            # Rất quan trọng nếu dataset lệch
            # =================================================
            class_weight='balanced',

            # =================================================
            # solver='liblinear'
            #
            # Optimizer cho Logistic Regression
            #
            # liblinear:
            #   → tốt cho text classification
            #   → ổn định với sparse matrix TF-IDF
            # =================================================
            solver='liblinear',

            # Giữ kết quả reproducible
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

# Học từ dữ liệu
pipeline.fit(X_train, y_train)

print("[INFO] Training completed successfully!")

# =========================================================
# TEST MODEL
# =========================================================

# Predict label
y_pred = pipeline.predict(X_test)

# Predict probability
y_probs = pipeline.predict_proba(X_test)

# Lấy index class phishing
classes = pipeline.named_steps["clf"].classes_

if "phishing" in classes:
    phishing_idx = list(classes).index("phishing")
else:
    phishing_idx = 1

# Xác suất phishing
phishing_probs = y_probs[:, phishing_idx]

# Convert label → binary
binary_y_test = (y_test == "phishing").astype(int)

# =========================================================
# EVALUATION
# =========================================================

print("\n" + "=" * 70)
print("[RESULT] MODEL PERFORMANCE")
print("=" * 70)

accuracy = accuracy_score(y_test, y_pred)
print(f"Accuracy : {accuracy:.4f}")

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

# Tạo folder models nếu chưa có
os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

# Lưu toàn bộ pipeline
joblib.dump(pipeline, MODEL_PATH)

print(f"[INFO] Pipeline saved to {MODEL_PATH}")

print("\n✅ Training completed successfully!")
