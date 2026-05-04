"""
╔═══════════════════════════════════════════════════════════════════╗
║            PHISHGUARD HEURISTIC RULES ENGINE                     ║
║         ⚙️ Rule-Based Detection (No ML)                          ║
╚═══════════════════════════════════════════════════════════════════╝

PURPOSE:
  Fast rule-based phishing detection without ML. Use heuristics
  (hard-coded rules) to detect common phishing patterns.

KEY METRICS:
  • Speed: ~0.05ms per URL (instant!)
  • Accuracy: Varies by rule quality
  • Rules: Currently 4 rules (can add 10+ more)
  • Best for: Quick pre-filtering, high-volume scanning

CURRENT RULES (4 total):
  1. Contains "free" keyword → Phishing signal
  2. Contains "login" without "secure" → Phishing signal
  3. URL longer than 75 characters → Phishing signal
  4. Uses HTTP (not HTTPS) → Security warning

POTENTIAL RULES TO ADD:
  • Domain age check (WHOIS)
  • SSL certificate validation
  • IP address instead of domain
  • Typosquatting detection
  • Google Safe Browsing API check
  • VirusTotal API check
  • Suspicious query parameters
  • Many subdomains (>3)
  • Special characters (@, #, etc)
  • Redirect chains

HOW IT WORKS:
  1. Convert URL to lowercase for case-insensitive check
  2. Check each rule in order
  3. Collect all triggered rules
  4. Return {triggered: bool, rules: [...], message: "..."}

USAGE:
  reason = get_heuristics_reason("https://verify-paypal.click")
  # Returns: {triggered: True, rules: [...], message: "..."}

VS ML DETECTION:
  ML (detector.py):
    • More accurate (90%+)
    • Slower (~0.11ms)
    • Learns from data
    • Black box
  
  Heuristics (this file):
    • Fast (~0.05ms)
    • Transparent (user sees rules)
    • Hard-coded (won't improve without coding)
    • Good for quick pre-check

RECOMMENDATION:
  Use BOTH: Heuristics first (fast filter), then ML (accuracy)

SEE ALSO:
  • ML_CODE_FLOW.md - Detailed code walkthrough
  • core/detector.py - ML detection
  • backend/routes/scan.py - How both are combined
"""

def get_heuristics_reason(url_text: str) -> dict:
    """Phân tích URL có dấu hiệu phishing không"""
    reasons = []
    url_lower = url_text.lower()

    # Rule 1: Từ khóa "free"
    if "free" in url_lower:
        reasons.append("Chứa từ 'free' - dấu hiệu phishing")
    
    # Rule 2: Login không secure
    if "login" in url_lower and "secure" not in url_lower:
        reasons.append("Yêu cầu login nhưng không có 'secure'")
    
    # Rule 3: URL quá dài
    if len(url_text) > 75:
        reasons.append("URL quá dài - dấu hiệu phishing")
    
    # Rule 4: HTTP không an toàn
    if url_text.startswith("http://"):
        reasons.append("Không dùng HTTPS - không an toàn")
    
    # Rule 5: Từ khóa cá cược (gambling keywords)
    gambling_keywords = ["casino", "bet", "xocdia", "thapcam", "cá cược", "tài xỉu", 
                         "poker", "blackjack", "roulette", "slot", "jackpot", "lottery"]
    if any(keyword in url_lower for keyword in gambling_keywords):
        reasons.append("Chứa từ khóa cá cược - có khả năng phishing hoặc scam")
    
    # Rule 6: Từ khóa ngân hàng/tài chính fake
    bank_keywords = ["verify", "confirm", "update", "secure", "login", "paypal", "bank", 
                     "account", "credential"]
    if sum(1 for keyword in bank_keywords if keyword in url_lower) >= 2:
        reasons.append("Quá nhiều từ khóa tài chính - dấu hiệu phishing")
    
    # Rule 7: Domain với số + ký tự đặc biệt
    domain_part = url_lower.split("://")[-1].split("/")[0]
    if domain_part.count(".") > 2 or any(char in domain_part for char in ["@", "#", "!"]):
        reasons.append("Domain có cấu trúc bất thường - dấu hiệu phishing")

    if not reasons:
        return {
            "triggered": False,
            "message": "Không có dấu hiệu phishing",
            "rules": []
        }
    else:
        return {
            "triggered": True,
            "message": " | ".join(reasons),
            "rules": reasons
        }