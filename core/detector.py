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

    def predict(self, text: str, threshold: float = 0.4) -> dict:
        """
        Predict with custom threshold for conservative classification.
        
        Args:
            text: URL or text to analyze
            threshold: Phishing probability threshold (default 0.4)
                      - If phishing_prob >= threshold: "phishing"
                      - If phishing_prob >= 0.3: "suspicious" 
                      - Else: "safe"
        
        Returns: {
            "label": "safe" | "suspicious" | "phishing",
            "confidence": 0.0-1.0,
            "probabilities": {"phishing": float, "safe": float},
            "top_features": {"word1": score, "word2": score, ...}  # Top 5 TF-IDF words
        }
        """
        if self.pipeline is None:
            raise RuntimeError("Model not initialized")
        
        probs = self.pipeline.predict_proba([text])[0]
        classes = self.pipeline.classes_
        
        # Get phishing probability
        phishing_idx = list(classes).index("phishing") if "phishing" in classes else 1
        phishing_prob = float(probs[phishing_idx])
        
        # 3-level classification with custom threshold
        if phishing_prob >= threshold:
            label = "phishing"
            confidence = phishing_prob
        elif phishing_prob >= 0.3:
            label = "suspicious"
            confidence = phishing_prob
        else:
            label = "safe"
            confidence = 1.0 - phishing_prob
        
        # Extract top contributing features from TF-IDF
        top_features = self._get_top_features(text)
        
        result = {
            "label": label,
            "confidence": round(confidence, 4),
            "probabilities": {classes[i]: float(probs[i]) for i in range(len(classes))},
            "top_features": top_features  # NEW: ML-based features
        }
        return result
    
    def _get_top_features(self, text: str, n_features: int = 5) -> dict:
        """
        Extract top N contributing TF-IDF features from input text.
        Filter out generic words and keep only suspicious keywords.
        
        Returns dict: {"feature1": score, "feature2": score, ...}
        """
        try:
            vectorizer = self.pipeline.named_steps['tfidf']
            
            # Get TF-IDF vector for this text
            tfidf_vector = vectorizer.transform([text]).toarray()[0]
            
            # Get feature names
            feature_names = vectorizer.get_feature_names_out()
            
            # List of generic/non-suspicious words to filter out
            generic_words = {
                'http', 'https', 'www', 'com', 'net', 'org', 'io', 'co', 'uk',
                'a', 'the', 'is', 'to', 'from', 'in', 'at', 'by', 'for',
                'and', 'or', 'an', 'be', 'on', 'it', 'as', 'with', 'this'
            }
            
            # Phishing-related keywords to prioritize
            phishing_keywords = {
                'verify', 'confirm', 'update', 'account', 'click', 'login', 'password',
                'bank', 'paypal', 'amazon', 'apple', 'microsoft', 'free', 'prize',
                'urgent', 'immediate', 'action', 'required', 'suspended', 'confirm',
                'authenticate', 'credential', 'secure', 'payment', 'card', 'expire',
                'casino', 'bet', 'poker', 'slot', 'thapcam', 'xocdia', 'cá cược',
                'loan', 'credit', 'tax', 'claim', 'refund', 'inherit'
            }
            
            # Filter and score features
            filtered_features = {}
            for i, feature in enumerate(feature_names):
                if tfidf_vector[i] > 0:
                    # Skip generic words
                    if feature.lower() in generic_words:
                        continue
                    
                    # Boost score for phishing keywords
                    score = float(tfidf_vector[i])
                    if feature.lower() in phishing_keywords:
                        score = score * 1.5  # Boost phishing-related keywords
                    
                    filtered_features[feature] = score
            
            # Sort by score and get top N
            top_features = dict(
                sorted(filtered_features.items(), key=lambda x: x[1], reverse=True)[:n_features]
            )
            
            return top_features
            
        except Exception as e:
            import logging
            logging.warning(f"Failed to extract features: {e}")
            return {}
