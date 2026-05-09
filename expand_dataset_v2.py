import pandas as pd

# File hiện tại
MAIN_DATASET = r"D:\DACN3-Split\Backend\data\dataset.csv"

# File mới cần thêm
NEW_DATASET = r"D:\DACN3-Split\Backend\data\dataset_converted.csv"

# Đọc dataset hiện tại
df_main = pd.read_csv(MAIN_DATASET)

# Đọc dataset mới
df_new = pd.read_csv(NEW_DATASET)

# Chuẩn hóa tên cột nếu cần
df_new = df_new.rename(columns={
    "type": "label"
})

# Chuẩn hóa label
df_new["label"] = df_new["label"].replace({
    "legitimate": "safe"
})

# Chỉ giữ đúng 2 cột cần thiết
df_new = df_new[["url", "label"]]

# Gộp dữ liệu
df_combined = pd.concat([df_main, df_new], ignore_index=True)

# Xóa URL trùng lặp
df_combined = df_combined.drop_duplicates(
    subset=["url"],
    keep="first"
)

# Lưu lại dataset chính
df_combined.to_csv(MAIN_DATASET, index=False)

# Thống kê
print("✅ Dataset merged successfully!")
print(f"Total URLs: {len(df_combined)}")
print(f"Phishing: {(df_combined['label'] == 'phishing').sum()}")
print(f"Safe: {(df_combined['label'] == 'safe').sum()}")

# Hiển thị vài dòng đầu
print(df_combined.head())