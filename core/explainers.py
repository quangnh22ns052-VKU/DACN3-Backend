"""
╔═══════════════════════════════════════════════════════════════════╗
║         PHISHGUARD FEATURE EXPLANATION ENGINE                    ║
║         🔍 Show WHY model made its prediction                   ║
╚═══════════════════════════════════════════════════════════════════╝

PURPOSE:
  Extract and rank features that influenced the ML prediction.
  Help user understand which keywords/patterns led to phishing label.

KEY METRICS:
  • Speed: ~0.05ms per URL
  • Output: Top 5 contributing features with scores
  • Method: Keyword extraction (NOT real SHAP yet)
  • Transparency: Shows what triggered the detection

HOW IT WORKS:
  1. Check for suspicious keywords in URL
     • "free", "login", "verify", "secure", "account", etc
  2. Score each found keyword
     • score = count × 0.3 (simple scoring)
  3. Check URL structure patterns
     • HTTP vs HTTPS
     • URL length
     • Subdomain count
     • Special characters (@, -, etc)
  4. Sort by score (highest first)
  5. Return top 5 features

CURRENT FEATURES CHECKED:
  Keyword features:
    • "free", "login", "verify", "secure", "account",
      "update", "bank", "click", "confirm", "password"
  
  Structure features:
    • http_vs_https (0.4 if HTTP)
    • long_url (score if > 75 chars)
    • many_subdomains (score if > 3 dots)
    • at_symbol (0.5 if @ present)
    • hyphen_in_domain (0.2 if - present)

EXAMPLE OUTPUT:
  {
    "top_features": {
      "verify": 0.3,
      "account": 0.3,
      "click": 0.3,
      "hyphen_in_domain": 0.2
    },
    "total_suspicious_signals": 4
  }

LIMITATIONS ⚠️:
  • NOT real SHAP (doesn't use model weights)
  • NOT real LIME (doesn't create local surrogate)
  • Hard-coded keyword list (not flexible)
  • Simple scoring (not probabilistic)
  
TODO - IMPROVE:
  Use real SHAP library:
    import shap
    explainer = shap.LinearExplainer(model, data)
    shap_values = explainer.shap_values(instance)
  
  This would:
    • Use actual model weights
    • Show positive/negative contributions
    • Be more accurate explanation

USAGE:
  explanation = get_shap_explanation("https://verify-account.click")
  # Returns: {top_features: {...}, total_suspicious_signals: N}

SEE ALSO:
  • ML_CODE_FLOW.md - Detailed code walkthrough
  • core/detector.py - ML prediction (these features explain it)
  • backend/routes/scan.py - Used in /scan endpoint
  • ML.md - Full system documentation
"""

import re

def get_shap_explanation(url_text: str) -> dict:
    """
    Phân tích các đặc trưng thực tế từ URL/text.
    """
    features = {}

    suspicious_keywords = [
        "free", "login", "verify", "secure", "account",
        "update", "bank", "click", "confirm", "password"
    ]

    text_lower = url_text.lower()

    for keyword in suspicious_keywords:
        if keyword in text_lower:
            # Tính score đơn giản: số lần xuất hiện / độ dài
            count = text_lower.count(keyword)
            features[keyword] = round(count * 0.3, 2)

    # Thêm các đặc trưng cấu trúc URL
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

    # Lấy top 5 features có score cao nhất
    top = dict(sorted(features.items(), key=lambda x: x[1], reverse=True)[:5])

    return {
        "top_features": top,
        "total_suspicious_signals": len(features)
    }