"""
╔═══════════════════════════════════════════════════════════════════╗
║         PHISHGUARD FEATURE EXPLANATION ENGINE                    ║
║         🔍 SHAP-like Feature Importance từ LR Coefficients       ║
╚═══════════════════════════════════════════════════════════════════╝

PURPOSE:
  Giải thích tại sao ML model đưa ra prediction phishing/legit.
  Dùng Logistic Regression coefficients — không cần SHAP library.

METHOD:
  • Extract LR model coefficients (feature weights)
  • Multiply with TF-IDF values → feature importance
  • Fallback về heuristic nếu model chưa load được

HOW IT WORKS:
  1. Load Pipeline (TF-IDF + LR) từ tfidf_lr.pkl
  2. Tách TF-IDF vectorizer và LR model ra
  3. Transform URL text → TF-IDF vector
  4. Tính importance = |coefficient| × TF-IDF value
  5. Map TFIDF indices → token names → sort top 5

OUTPUT:
  {
    "top_features": {
      "verify": 0.42,
      "account": 0.31,
      "click": 0.28,
      "-": 0.19,
      "http": 0.15
    },
    "total_suspicious_signals": 5,
    "method": "shap"   ← LR coefficients (SHAP-like, không dùng thư viện)
  }

TƯƠNG THÍCH:
  • Giữ nguyên function name: get_shap_explanation(url_text)
  • Giữ nguyên output keys: top_features, total_suspicious_signals, method
  • Fallback automatic nếu model fail

SEE ALSO:
  • core/detector.py    — dùng cùng model pipeline
  • backend/routes/scan.py — gọi hàm này
  • models/tfidf_lr.pkl  — model được load
"""

import os
import re
import joblib  # ← Use joblib (train_tfidf.py saves with joblib.dump())
import logging
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Đường dẫn model (giống detector.py) ────────────────────────────────────
_BASE_DIR = Path(__file__).resolve().parent.parent   # thư mục Backend/
_MODEL_PATH = _BASE_DIR / "models" / "tfidf_lr.pkl"

# ── Cache model để không load lại mỗi request ───────────────────────────────
_pipeline   = None   # sklearn Pipeline (TF-IDF + LR)
_vectorizer = None   # TfidfVectorizer (bước đầu pipeline)
_lr_model   = None   # LogisticRegression (bước cuối pipeline)


def _load_model():
    """
    Load pipeline một lần duy nhất, cache lại.
    Tách vectorizer + lr để tính feature importance.
    """
    global _pipeline, _vectorizer, _lr_model

    if _lr_model is not None:
        return True  # đã load rồi

    if not _MODEL_PATH.exists():
        logger.warning(f"[Explainer] Không tìm thấy model tại {_MODEL_PATH}")
        return False

    try:
        with open(_MODEL_PATH, "rb") as f:
            _pipeline = joblib.load(f)

        # sklearn Pipeline: steps = [("tfidf", ...), ("lr", ...)]
        # Tên step có thể khác nhau — lấy theo thứ tự
        steps = _pipeline.steps
        _vectorizer = steps[-2][1]   # penultimate = TF-IDF
        _lr_model   = steps[-1][1]   # last        = LogisticRegression

        logger.info("[Explainer] Model loaded successfully. Using LR coefficients for feature importance.")
        return True

    except Exception as e:
        logger.error(f"[Explainer] Không load được model: {e}")
        return False


def _shap_explanation(url_text: str) -> dict:
    """
    Tính SHAP values thực sự từ TF-IDF + LR bằng model weights.
    Không cần SHAP library - dùng coefficient của LR model trực tiếp.
    """
    # Transform text → sparse TF-IDF vector → dense numpy array
    X = _vectorizer.transform([url_text]).toarray()   # shape (1, n_features)

    # Lấy coefficients từ Logistic Regression model (= feature importance)
    coefficients = _lr_model.coef_[0]  # shape (n_features,)
    
    # Map index → token name
    idx_to_token = {v: k for k, v in _vectorizer.vocabulary_.items()}

    # Chỉ lấy các token thực sự xuất hiện trong URL (X[0] > 0)
    nonzero_indices = np.where(X[0] > 0)[0]

    # Tính contribution = coefficient × TF-IDF value
    # Càng cao = càng khả năng là phishing
    token_scores = {}
    for idx in nonzero_indices:
        token = idx_to_token.get(idx, f"token_{idx}")
        # Feature importance = |coefficient| × TF-IDF value
        contribution = float(np.abs(coefficients[idx]) * X[0][idx])
        if contribution > 0:
            token_scores[token] = round(contribution, 4)

    # Sort theo contribution giảm dần, lấy top 5
    top = dict(sorted(token_scores.items(), key=lambda x: x[1], reverse=True)[:5])

    return {
        "top_features": top,
        "total_suspicious_signals": len(token_scores),
        "method": "shap"
    }


# ── Fallback heuristic (giữ nguyên logic cũ) ────────────────────────────────
def _heuristic_explanation(url_text: str) -> dict:
    """
    Fallback khi SHAP không khả dụng (model chưa load, shap chưa cài...).
    Giữ nguyên logic cũ để không break production.
    """
    features = {}
    suspicious_keywords = [
        "free", "login", "verify", "secure", "account",
        "update", "bank", "click", "confirm", "password"
    ]
    text_lower = url_text.lower()

    for keyword in suspicious_keywords:
        if keyword in text_lower:
            count = text_lower.count(keyword)
            features[keyword] = round(count * 0.3, 2)

    if url_text.startswith("http://"):
        features["http (not https)"] = 0.4
    if len(url_text) > 75:
        features["long_url"] = round(len(url_text) / 500, 2)
    if url_text.count(".") > 3:
        features["many_subdomains"] = round(url_text.count(".") * 0.1, 2)
    if "@" in url_text:
        features["at_symbol"] = 0.5
    if "-" in url_text:
        features["hyphen_in_domain"] = 0.2

    top = dict(sorted(features.items(), key=lambda x: x[1], reverse=True)[:5])

    return {
        "top_features": top,
        "total_suspicious_signals": len(features),
        "method": "heuristic"   # ← caller biết đây là fallback
    }


# ── Public API (giữ nguyên tên để không ảnh hưởng scan.py) ─────────────────
def get_shap_explanation(url_text: str) -> dict:
    """
    Điểm vào duy nhất — giữ nguyên signature cũ.

    Ưu tiên SHAP thực sự, fallback về heuristic nếu không dùng được.

    Args:
        url_text: URL hoặc message cần giải thích

    Returns:
        {
            "top_features": {token: shap_score, ...},
            "total_suspicious_signals": int,
            "method": "shap" | "heuristic"
        }
    """
    if _load_model():
        try:
            return _shap_explanation(url_text)
        except Exception as e:
            logger.warning(f"[Explainer] SHAP thất bại, dùng heuristic: {e}")

    return _heuristic_explanation(url_text)