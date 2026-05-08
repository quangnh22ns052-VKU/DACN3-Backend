import os
import pickle
from pathlib import Path

pkl_file = Path('models/tfidf_lr.pkl')

print(f"File exists: {pkl_file.exists()}")
if pkl_file.exists():
    print(f"File size: {os.path.getsize(pkl_file)} bytes")
    
    # Try to load
    try:
        with open(pkl_file, 'rb') as f:
            model = pickle.load(f)
        print("✅ Pickle load OK")
        print(f"Type: {type(model)}")
        print(f"Steps: {model.named_steps.keys()}")
    except Exception as e:
        print(f"❌ Pickle load failed: {e}")
else:
    print("❌ File not found")
    print(f"Looking in: {pkl_file.resolve()}")
