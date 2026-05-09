
import pandas as pd

# =========================================================
# FILE DATASET
# =========================================================

DATASET_PATH = r"D:\DACN3-Split\Backend\data\dataset.csv"

# =========================================================
# LOAD DATASET
# =========================================================

print("=" * 60)
print("[INFO] Loading dataset...")
print("=" * 60)

df = pd.read_csv(DATASET_PATH)

print(f"Total before reduction: {len(df)}")

print("\nLabel distribution BEFORE:")
print(df["label"].value_counts())

# =========================================================
# TÁCH RIÊNG SAFE / PHISHING
# =========================================================

df_safe = df[df["label"] == "safe"]
df_phishing = df[df["label"] == "phishing"]

# =========================================================
# GIỮ LẠI 80% MỖI LOẠI
# =========================================================
#
# frac=0.8 nghĩa là giữ lại 80%
# random_state giúp reproducible
#

df_safe_reduced = df_safe.sample(
    frac=0.8,
    random_state=42
)

df_phishing_reduced = df_phishing.sample(
    frac=0.8,
    random_state=42
)

# =========================================================
# GỘP LẠI
# =========================================================

df_reduced = pd.concat([
    df_safe_reduced,
    df_phishing_reduced
])

# Shuffle dataset
df_reduced = df_reduced.sample(
    frac=1,
    random_state=42
).reset_index(drop=True)

# =========================================================
# SAVE
# =========================================================

df_reduced.to_csv(DATASET_PATH, index=False)

# =========================================================
# STATS
# =========================================================

print("\n" + "=" * 60)
print("[INFO] Dataset reduced successfully!")
print("=" * 60)

print(f"Total after reduction: {len(df_reduced)}")

print("\nLabel distribution AFTER:")
print(df_reduced["label"].value_counts())

print("\n✅ Reduced 20% equally from both classes.")

