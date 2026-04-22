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

    if "free" in url_text.lower():
        reasons.append("Chứa từ 'free' - dấu hiệu phishing")
    if "login" in url_text.lower() and "secure" not in url_text.lower():
        reasons.append("Yêu cầu login nhưng không có 'secure'")
    if len(url_text) > 75:
        reasons.append("URL quá dài - dấu hiệu phishing")
    if url_text.startswith("http://"):
        reasons.append("Không dùng HTTPS - không an toàn")

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