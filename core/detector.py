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
import logging
import warnings
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)
MODEL_PATH = os.path.join("models", "tfidf_lr.pkl")
DATA_PATH = os.path.join("data", "dataset.csv")

class PhishDetector:
    def __init__(self):
        """Load model with automatic retraining on version mismatch"""
        self.pipeline = None
        
        # Try to load existing model
        if os.path.exists(MODEL_PATH):
            try:
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    self.pipeline = joblib.load(MODEL_PATH)
                    
                    # Check for version warnings
                    version_warnings = [warning for warning in w 
                                      if "InconsistentVersionWarning" in str(warning.category)]
                    if version_warnings:
                        logger.warning(f"⚠️  Model version mismatch detected. Retraining...")
                        self.pipeline = None
                        
            except Exception as e:
                logger.warning(f"⚠️  Failed to load model: {str(e)}. Attempting retrain...")
                self.pipeline = None
        
        # Retrain if load failed
        if self.pipeline is None:
            logger.info("🔄 Retraining model from data...")
            self._retrain_model()
    
    def _retrain_model(self):
        """Train new model from dataset"""
        try:
            if not os.path.exists(DATA_PATH):
                raise FileNotFoundError(f"Training data not found at {DATA_PATH}")
            
            # Load dataset
            df = pd.read_csv(DATA_PATH)
            X = df.iloc[:, 0].values  # URLs
            y = df.iloc[:, 1].values  # Labels
            
            # Train pipeline
            self.pipeline = Pipeline([
                ('tfidf', TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
                ('lr', LogisticRegression(max_iter=200, random_state=42))
            ])
            self.pipeline.fit(X, y)
            
            # Save new model
            os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
            joblib.dump(self.pipeline, MODEL_PATH)
            logger.info(f"✅ Model retrained and saved to {MODEL_PATH}")
            
        except Exception as e:
            logger.error(f"❌ Failed to retrain model: {str(e)}")
            raise

    def predict(self, text: str) -> dict:
        if self.pipeline is None:
            raise RuntimeError("Model not initialized")
        
        probs = self.pipeline.predict_proba([text])[0]
        classes = self.pipeline.classes_
        result = {
            "label": self.pipeline.predict([text])[0],
            "probabilities": {classes[i]: float(probs[i]) for i in range(len(classes))}
        }
        return result
