"""
╔═══════════════════════════════════════════════════════════════════╗
║                    PHISHGUARD ML DETECTOR                        ║
║         🤖 Machine Learning Prediction Engine                    ║
╚═══════════════════════════════════════════════════════════════════╝

PURPOSE:
  Load trained TF-IDF + Logistic Regression model and predict if
  a given URL/text is phishing or legitimate.

KEY METRICS:
  • Speed: ~0.11ms per URL (very fast)
  • Accuracy: ~90% baseline
  • Model: scikit-learn Pipeline (TF-IDF vectorizer + LogisticRegression)
  • Model file: models/tfidf_lr.pkl (8MB)

HOW IT WORKS:
  1. Load pretrained model from models/tfidf_lr.pkl
  2. Convert input text → 5000-dimensional TF-IDF vector
  3. Apply Logistic Regression classifier
  4. Return probability distribution [legitimate%, phishing%]
  5. Threshold decision at 0.5 → return label + probabilities

USAGE:
  detector = PhishDetector()
  result = detector.predict("https://example.com")
  # Returns: {"label": "phishing", "probabilities": {...}}

TUNING FOR SPEED vs ACCURACY:
  See ML_CODE_FLOW.md → PERFORMANCE TUNING section
  • Faster: Reduce max_features (5000→1000), use unigrams only (1,1)
  • Accurate: Increase max_features (5000→10000), add trigrams (1,3)
  • Balanced: Use 7500 features, max_iter=300, C=0.5

RELATED FILES:
  • scripts/train_tfidf.py - Train new model
  • core/heuristics.py - Rule-based detection
  • core/explainers.py - Feature explanations
  • backend/routes/scan.py - API endpoint

SEE ALSO:
  • ML_CODE_FLOW.md - Detailed code walkthrough
  • ML.md - ML system architecture
  • FILE_STRUCTURE.md - File organization guide
"""

import os
import joblib

MODEL_PATH = os.path.join("models", "tfidf_lr.pkl")

class PhishDetector:
    def __init__(self):
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model not found at {MODEL_PATH}. Train it first.")
        self.pipeline = joblib.load(MODEL_PATH)  # contains vectorizer + model

    def predict(self, text: str) -> dict:
        probs = self.pipeline.predict_proba([text])[0]
        classes = self.pipeline.classes_
        result = {
            "label": self.pipeline.predict([text])[0],
            "probabilities": {classes[i]: float(probs[i]) for i in range(len(classes))}
        }
        return result
