"""
backend/utils/response_formatter.py

Convert raw ML scores (0-2.0) → User-friendly output (0-100)
Make phishing detection results easy to understand for non-technical users.
"""

def normalize_score_to_100(raw_score: float) -> int:
    """
    Convert raw feature importance score (typically 0-2.5) → 0-100 scale
    
    Raw scores from LR coefficients × TF-IDF:
      - 0-0.3: Weak signal (0-20 points) ← Không đáng ngờ
      - 0.3-0.8: Medium signal (20-60 points) ← Có liên quan
      - 0.8-1.5: Strong signal (60-90 points) ← Rất nghi ngờ
      - 1.5+: Very strong signal (90-100 points) ← Chắc chắn phishing
    """
    if raw_score < 0.3:
        return int(raw_score * 60)  # 0-0.3 → 0-18
    elif raw_score < 0.8:
        return int(18 + (raw_score - 0.3) * 70)  # 0.3-0.8 → 18-53
    elif raw_score < 1.5:
        return int(53 + (raw_score - 0.8) * 52)  # 0.8-1.5 → 53-85
    else:
        return min(100, int(85 + (raw_score - 1.5) * 10))  # 1.5+ → 85-100


def get_star_rating(score_100: int) -> str:
    """
    Convert score (0-100) → star rating (⭐)
    
    0-20:   ⭐ (very weak)
    20-40:  ⭐⭐ (weak)
    40-60:  ⭐⭐⭐ (medium)
    60-80:  ⭐⭐⭐⭐ (strong)
    80-100: ⭐⭐⭐⭐⭐ (very strong)
    """
    import math
    stars = max(1, min(5, math.ceil(score_100 / 20)))
    return "⭐" * stars


def get_keyword_explanation(keyword: str, score_100: int) -> str:
    """Get user-friendly explanation for each keyword"""
    
    keyword_lower = keyword.lower()
    
    # Map keyword → explanation
    explanations = {
        # Verify/Confirm keywords (phishing indicators)
        "verify": "Lừa tính năng: 'Xác minh tài khoản' là cách phổ biến để đánh cắp thông tin",
        "confirm": "Lừa tính năng: Yêu cầu xác nhận/cập nhật là dấu hiệu phishing",
        "validate": "Lừa tính năng: Xác thực tài khoản bất thường có thể là scam",
        
        # Login/Authentication
        "login": "Yêu cầu đăng nhập: Phishing sites đóng giả trang login để lấy mật khẩu",
        "password": "Mật khẩu: Yêu cầu mật khẩu trên link đáng ngờ = phishing",
        "credential": "Thông tin xác thực: Phishing đánh cắp username/password",
        "authenticate": "Xác thực: Yêu cầu xác thực lại là lừa đánh cắp tài khoản",
        
        # Brand impersonation
        "paypal": "Giả mạo PayPal: Scammers dùng brand nổi tiếng để lừa tín tưởng",
        "amazon": "Giả mạo Amazon: Brand lớn thường bị scammer giả mạo",
        "apple": "Giả mạo Apple: Brand Apple được scammer lợi dụng để lừa",
        "microsoft": "Giả mạo Microsoft: Scam dạng 'cập nhật Windows' phổ biến",
        "google": "Giả mạo Google: Phishing sites giả mạo dịch vụ Google",
        "bank": "Giả mạo ngân hàng: Phishing lừa thông tin tài khoản ngân hàng",
        
        # Urgency/Action words
        "urgent": "Sự cấp thiết: 'Hành động ngay' là chiến thuật lừa phổ biến",
        "immediate": "Ngay lập tức: Yêu cầu hành động nhanh = dấu hiệu phishing",
        "action": "Hành động: Yêu cầu hành động ngay = dấu hiệu lừa",
        "required": "Cần thiết: 'Bắt buộc' để tạo áp lực lừa người dùng",
        "expired": "Hết hạn: 'Tài khoản hết hạn' là lừa đánh cắp thông tin",
        "suspended": "Tạm dừng: 'Tài khoản bị tạm dừng' = phishing scam",
        
        # Gambling/Scam keywords
        "casino": "Casino: Trang casino giả/phishing thường là scam tài chính",
        "bet": "Cá cược: Trang cá cược online lừa mất tiền",
        "poker": "Poker: Lừa tài chính qua game bài poker",
        "slot": "Slot machine: Lừa tiền qua game slot",
        "lottery": "Xổ số: Giải thưởng xổ số giả lừa tiền",
        "jackpot": "Giải lớn: Giải thưởng giả lừa tương tác",
        "xocdia": "Xóc đĩa: Scam cá cược Việt Nam",
        "thapcam": "Tháp cảm: Scam cá cược Việt Nam",
        "cá cược": "Cá cược: Lừa tài chính qua cá cược",
        
        # Technical/Protocol
        "http": "HTTP không an toàn: Nên dùng HTTPS để bảo vệ dữ liệu",
        "redirect": "Chuyển hướng: Redirect đến trang lừa là kỹ thuật phishing phổ biến",
        "data": "Dữ liệu: Yêu cầu dữ liệu cá nhân = phishing",
        "token": "Token: Yêu cầu token/key bảo mật = lừa",
        
        # Default
        "default": "Từ khóa liên quan đến phishing detection"
    }
    
    # Find matching explanation
    for keyword_pattern, explanation in explanations.items():
        if keyword_lower == keyword_pattern:
            return explanation
    
    return explanations["default"]


def format_ml_results(top_features: dict) -> list:
    """
    Format ML analysis results into user-friendly list
    
    Input:
      {
        "verify": 1.8525,
        "paypal": 1.3978,
        "account": 0.9639,
        "redirect": 0.4256,
        "http": 0.0504
      }
    
    Output:
      [
        {
          "rank": 1,
          "keyword": "verify",
          "score": 95,
          "score_bar": "████████████████████",
          "reason": "Lừa tính năng: 'Xác minh tài khoản'..."
        },
        ...
      ]
    """
    result = []
    
    for rank, (keyword, raw_score) in enumerate(top_features.items(), 1):
        score_100 = normalize_score_to_100(raw_score)
        
        # Generate visual bar (0-20 blocks for 0-100 score)
        bar_length = int(score_100 / 5)  # 20 blocks max
        score_bar = "█" * bar_length + "░" * (20 - bar_length)
        
        # Generate star rating
        stars = get_star_rating(score_100)
        
        result.append({
            "rank": rank,
            "keyword": keyword,
            "score": score_100,
            "score_bar": score_bar,
            "stars": stars,
            "reason": get_keyword_explanation(keyword, score_100)
        })
    
    return result


def format_heuristics_results(heuristics: dict) -> dict:
    """
    Format heuristics rules for user-friendly display
    
    Converts simple rule list into detailed analysis with
    severity indicators and explanations.
    
    Input: {"triggered": True, "rules": ["Không dùng HTTPS...", ...]}
    Output: {
      "method": "Rule-Based Detection",
      "triggered": True,
      "rules_formatted": [
        {"rule": "...", "severity": "HIGH", "emoji": "🔴"},
        ...
      ],
      "total_rules_triggered": 3
    }
    """
    triggered_rules = heuristics.get("rules", [])
    
    # Map rules to severity levels
    rule_severity_map = {
        "HTTP": "CRITICAL",  # Unencrypted
        "HTTPS": "CRITICAL",  # if NOT HTTPS
        "free": "HIGH",       # Common phishing keyword
        "verify": "HIGH",     # Common phishing keyword
        "login": "HIGH",      # Account access request
        "password": "CRITICAL",  # Direct password request
        "confirm": "HIGH",    # Confirmation request
        "update": "HIGH",     # Account update request
        "casino": "CRITICAL", # Gambling scam
        "cá cược": "CRITICAL",  # Vietnamese: Gambling scam
        "xóc đĩa": "CRITICAL",  # Vietnamese: Gambling scam
        "ngân hàng": "CRITICAL",  # Bank keywords
        "paypal": "HIGH",     # Spoofed payment service
        "tài chính": "HIGH",  # Financial keywords
        "thông tin": "MEDIUM",  # Information request
        "dữ liệu": "MEDIUM",  # Data request
        "domain": "MEDIUM",   # Domain structure issues
        "subdomain": "MEDIUM",  # Unusual subdomains
    }
    
    def get_rule_severity(rule_text: str) -> tuple:
        """Determine severity of a rule and return (severity, emoji, description)"""
        rule_lower = rule_text.lower()
        
        # Check for CRITICAL indicators
        if any(critical in rule_lower for critical in ["mật khẩu", "password", "casino", "cá cược", "xóc đĩa"]):
            return ("CRITICAL", "🔴", "Rất nguy hiểm - Dấu hiệu phishing mạnh mẽ")
        elif any(critical in rule_lower for critical in ["http://", "không an toàn", "không dùng https"]):
            return ("HIGH", "🟠", "Nguy hiểm cao - Kết nối không được bảo vệ")
        elif any(high in rule_lower for high in ["free", "verify", "confirm", "login", "paypal", "ngân hàng"]):
            return ("HIGH", "🟠", "Nguy hiểm cao - Dấu hiệu phishing phổ biến")
        elif any(med in rule_lower for med in ["thông tin", "dữ liệu", "domain", "url quá dài"]):
            return ("MEDIUM", "🟡", "Nguy hiểm trung bình - Nên cẩn thận")
        else:
            return ("LOW", "🟢", "Nguy hiểm thấp - Vẫn nên chú ý")
    
    formatted_rules = []
    for rule_text in triggered_rules:
        severity, emoji, description = get_rule_severity(rule_text)
        formatted_rules.append({
            "rule": rule_text,
            "severity": severity,
            "emoji": emoji,
            "description": description
        })
    
    return {
        "method": "Rule-Based Detection (Heuristics)",
        "triggered": len(triggered_rules) > 0,
        "rules_formatted": formatted_rules,
        "total_rules_triggered": len(triggered_rules),
        "summary": f"Phát hiện {len(triggered_rules)} dấu hiệu phishing dựa trên quy tắc" if triggered_rules else "Không phát hiện dấu hiệu phishing theo quy tắc"
    }


def get_severity_level(confidence: float, label: str) -> tuple:
    # Safe và suspicious không phụ thuộc vào con số confidence
    if label == "safe":
        return ("SAFE", "✅", "success", "An toàn - Không phát hiện dấu hiệu phishing")
    
    if label == "suspicious":
        return ("MEDIUM", "🟡", "warning", "Nguy hiểm trung bình - Cần cẩn thận")
    
    # Chỉ phishing mới dùng confidence để phân mức độ
    if confidence >= 0.85:
        return ("CRITICAL", "🔴", "danger", "Nguy hiểm rất cao - Phishing có xác suất gần như chắc chắn")
    elif confidence >= 0.70:
        return ("HIGH", "🟠", "warning", "Nguy hiểm cao - Rất có khả năng là phishing")
    elif confidence >= 0.50:
        return ("MEDIUM", "🟡", "warning", "Nguy hiểm trung bình - Cần cẩn thận")
    else:
        return ("LOW", "🟢", "info", "Nguy hiểm thấp - Nhưng vẫn nên cẩn thận")

def format_scan_response(prediction: dict, heuristics: dict, shap_result: dict) -> dict:
    """
    Format complete scan response for end user
    
    Combines ML prediction + heuristics + SHAP explanation
    into single user-friendly response with consolidated display
    """
    
    confidence = prediction.get("confidence", 0)
    label = prediction.get("label", "unknown")
    
    severity_level, severity_emoji, severity_color, severity_desc = get_severity_level(confidence, label)
    
    # Format ML features
    ml_features = prediction.get("top_features", {})
    formatted_features = format_ml_results(ml_features)
    
    # Format heuristics using new consolidated formatter
    formatted_heuristics = format_heuristics_results(heuristics)
    
    return {
        # Quick summary
        "verdict": {
            "label": label,
            "severity": severity_level,
            "emoji": severity_emoji,
            "confidence": confidence,
            "confidence_percentage": f"{int(confidence*100)}%",
            "description": severity_desc
        },
        
        # ML Analysis (detailed)
        "ml_analysis": {
            "method": "Machine Learning (TF-IDF + Logistic Regression)",
            "top_features": formatted_features,
            "total_signals_detected": len(ml_features)
        },
        
        # Heuristics (rule-based) - NOW WITH DETAILED FORMATTING
        "heuristics_analysis": formatted_heuristics,
        
        # User recommendations
        "recommendations": {
            "short": _get_short_recommendation(label, confidence),
            "long": _get_detailed_recommendation(label, formatted_heuristics.get("rules_formatted", [])),
            "actions": _get_action_items(label)
        }
    }


def _get_short_recommendation(label: str, confidence: float) -> str:
    """Get short user recommendation"""
    if label == "phishing" and confidence >= 0.85:
        return "🚫 KHÔNG NÊN NHẤN VÀO LINK NÀY! Đây là phishing với xác suất rất cao."
    elif label == "phishing" and confidence >= 0.70:
        return "⚠️  CẨN THẬN! Link này rất có thể là phishing."
    elif label == "phishing":
        return "⚠️  Cần cẩn thận với link này - có dấu hiệu phishing."
    elif label == "suspicious":
        return "🟡 NGHI NGỜ: Link này có dấu hiệu bất thường, nên cẩn thận."
    else:
        return "✅ Không phát hiện dấu hiệu phishing rõ ràng (nhưng vẫn nên cẩn thận)."


def _get_detailed_recommendation(label: str, formatted_rules: list) -> str:
    """Get detailed explanation based on label and formatted heuristic rules"""
    if label == "phishing":
        # Extract rule text from formatted rules
        rule_texts = [rule.get("rule", "") for rule in formatted_rules] if isinstance(formatted_rules, list) and formatted_rules and isinstance(formatted_rules[0], dict) else formatted_rules
        
        if rule_texts:
            return f"Phát hiện {len(rule_texts)} dấu hiệu phishing: " + " | ".join(rule_texts[:2])
        return "Mô hình ML phát hiện dấu hiệu phishing mạnh mẽ."
    return "Không phát hiện dấu hiệu phishing đáng kể."


def _get_action_items(label: str) -> list:
    """Get recommended actions"""
    if label == "phishing":
        return [
            "1. ❌ KHÔNG nhấn vào link hoặc tải file",
            "2. ❌ KHÔNG nhập thông tin cá nhân / mật khẩu",
            "3. 📧 Báo cáo email/link cho nhà cung cấp email (Gmail, Outlook, etc)",
            "4. 📱 Nếu về tài khoản ngân hàng, liên hệ ngân hàng qua số điện thoại chính thức",
            "5. 🗑️  Xóa email và không chia sẻ với người khác"
        ]
    elif label == "suspicious":
        return [
            "1. ⚠️  Cẩn thận trước khi nhấn vào link",
            "2. 🔍 Kiểm tra địa chỉ email/URL xem có hợp lệ không",
            "3. 📞 Liên hệ trực tiếp công ty/tổ chức bằng số điện thoại chính thức",
            "4. ❌ Không nhập thông tin cá nhân trên link này"
        ]
    else:
        return [
            "1. ✅ Link này dường như an toàn",
            "2. 🔍 Vẫn nên kiểm tra địa chỉ URL trước khi nhấn",
            "3. 🔐 Nếu yêu cầu mật khẩu, hãy chắc chắn đó là trang chính thức"
        ]


if __name__ == "__main__":
    # Test example
    test_prediction = {
        "label": "phishing",
        "confidence": 0.87,
        "top_features": {
            "verify": 1.8525,
            "paypal": 1.3978,
            "account": 0.9639,
            "redirect": 0.4256,
            "http": 0.0504
        }
    }
    
    test_heuristics = {
        "triggered": True,
        "rules": [
            "Không dùng HTTPS - không an toàn",
            "Chứa từ 'verify' + 'account' - dấu hiệu phishing",
            "URL quá dài (78 ký tự) - có thể ẩn domain thực"
        ]
    }
    
    test_shap = {
        "method": "shap",
        "top_features": test_prediction["top_features"]
    }
    
    result = format_scan_response(test_prediction, test_heuristics, test_shap)
    
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
