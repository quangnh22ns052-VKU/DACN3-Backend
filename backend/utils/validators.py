"""
╔═══════════════════════════════════════════════════════════════════╗
║            PHISHGUARD INPUT VALIDATION UTILITIES                  ║
║         ✓ Xác thực URL & Văn bản Đầu vào                         ║
╚═══════════════════════════════════════════════════════════════════╝

TÊN FILE: backend/utils/validators.py

CÔNG DỤNG:
  - Kiểm tra và làm sạch (sanitize) dữ liệu từ người dùng
  - Xác thực định dạng URL (http, https, ftp)
  - Kiểm tra độ dài và ký tự hợp lệ
  - Ngăn chặn SQL injection, XSS
  - Trả về kết quả xác thực chi tiết

CÁC HÀM CHÍNH:
  • validate_input(text, input_type): Kiểm tra toàn bộ input
  • validate_url(url): Xác thực định dạng URL
  • validate_text(text): Xác thực văn bản
  • sanitize_input(text): Làm sạch dữ liệu

CÁCH SỬ DỤNG:
  from backend.utils.validators import validate_input
  result = validate_input("https://example.com", "url")
  if result["is_valid"]:
      clean_url = result["sanitized_url"]

SMART VALIDATION LOGIC (Mới - Fix 422 Error):
  ✅ ALLOW: http://vulnerable-site.com/search?q=<script>alert('XSS')</script>
     Tại sao? Query params là để TEST model phát hiện XSS, không phải tấn công thực
  ✅ ALLOW: https://example.com?user='test' (query param với quote)
     Tại sao? Apostrophe ở query param không phải SQL injection
  ❌ BLOCK: javascript://alert('xss') (dangerous protocol)
  ❌ BLOCK: ' UNION SELECT * (SQL injection keyword)

LƯU Ý:
  - URL phải có http:// hoặc https://
  - Độ dài tối đa: 2048 ký tự URL, 10000 ký tự text
  - HTML tags ở query params = ALLOWED (test payload)
  - Dangerous protocols = BLOCKED
"""
import re
from typing import Optional
from urllib.parse import urlparse
import validators

class InputValidator:
    """Comprehensive input validation for URLs and text"""
    
    # URL validation patterns
    # Allow any characters after domain (path, query, fragment)
    # This permits test payloads like: ?q=<script> or ?q=1' UNION SELECT
    # Security: Dangerous protocols (javascript:, data:) caught separately
    URL_PATTERN = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|'  # ...or ipv4
        r'\[?[A-F0-9]*:[A-F0-9:]+\]?)'  # ...or ipv6
        r'(?::\d+)?'  # optional port
        r'.*$', re.IGNORECASE  # path, query, fragment - allow anything
    )
    
    # Maximum input lengths
    MAX_URL_LENGTH = 2048
    MAX_TEXT_LENGTH = 10000
    
    # Allowed URL schemes
    ALLOWED_SCHEMES = {'http', 'https', 'ftp', 'ftps'}
    
    @classmethod
    def validate_url(cls, url: str) -> dict:
        """
        Validate URL input with comprehensive checks
        
        Returns:
            dict: Validation result with 'is_valid', 'error', and 'sanitized_url'
        """
        result = {
            'is_valid': False,
            'error': None,
            'sanitized_url': None
        }
        
        # Check if URL is None or empty
        if not url or not url.strip():
            result['error'] = "URL cannot be empty"
            return result
        
        # Strip whitespace
        url = url.strip()
        
        # Check length
        if len(url) > cls.MAX_URL_LENGTH:
            result['error'] = f"URL too long (max {cls.MAX_URL_LENGTH} characters)"
            return result
        
        # ===== FIX: SQL injection detection (query params allowed for testing) =====
        # STRATEGY: Parse URL and check SQL patterns ONLY in base URL, not query params
        # 
        # WHY? Backend doesn't execute query params against database.
        # ML model NEEDS to see SQL keywords in payloads to learn detection.
        # Test case: http://site.com/search?q=1' UNION SELECT ... (SHOULD BE ALLOWED)
        #
        # Attack patterns (BLOCK in path):
        #   • /path?'; DROP TABLE -- (destructive)
        #   • /admin?id=1 OR 1=1 (logic bypass)  ← Only check if in PATH, not query param
        #
        # Safe patterns (ALLOW):
        #   • https://example.com?user='test' (query param - for model testing)
        #   • https://example.com?q=1' UNION SELECT ... (test payload - for ML testing)
        #   • https://user's-site.com (apostrophe in domain)
        
        try:
            parsed = urlparse(url)
            # Check SQL injection ONLY in path/netloc, NOT in query string
            base_url_parts = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            sql_injection_patterns = [
                # These are real attack vectors in the URL structure itself
                r"';?\s*(DROP|DELETE|INSERT|UPDATE|CREATE|TRUNCATE)",  # '; DROP
                r"admin\s+.*?['\"]\s*(OR|AND)\s+",                    # admin' OR
                r"['\"]?\s*OR\s+['\"]?1['\"]?\s*=\s*['\"]?1",         # ' OR '1'='1
                r"union.*?select",                                      # UNION SELECT (only in path)
            ]
            
            for pattern in sql_injection_patterns:
                if re.search(pattern, base_url_parts, re.IGNORECASE):
                    result['error'] = "Invalid URL format - potential SQL injection detected"
                    return result
        except Exception:
            # If parsing fails, log but continue
            pass
        
        # ===== FIX: XSS detection - Allow HTML tags in query params (test case) =====
        # Allow: http://vulnerable-site.com/search?q=<script>alert('XSS')</script>
        #        (This is legitimate security testing!)
        # Block: javascript://alert('xss')
        #        (This is actual XSS attack)
        #
        # Strategy: Parse URL, check XSS only in scheme/netloc/path, NOT in query
        # Why? Query params can contain test payloads (intended to test model)
        
        try:
            parsed = urlparse(url)
            # Reconstruct URL without query params for XSS check
            url_without_query = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            # Only check dangerous XSS patterns in URL structure itself
            xss_patterns = [
                r"javascript:",      # javascript: protocol
                r"vbscript:",        # vbscript: protocol
                r"data:text/html",   # data: protocol with HTML
                r"data:application/x-sh",  # data: protocol with shell
            ]
            
            for pattern in xss_patterns:
                if re.search(pattern, url_without_query, re.IGNORECASE):
                    result['error'] = "Invalid URL format - potential XSS detected"
                    return result
            
            # ⚠️ Allow raw HTML tags in query params
            # Reason: They're test payloads for model testing, not actual attacks
            # Backend won't execute them (just passes to model for analysis)
            # Example: ?q=<script>alert('xss')</script> is safe on backend
            
        except Exception:
            # If parsing fails, continue anyway (URL probably malformed but let next check handle)
            pass
        
        # Basic URL format validation
        if not cls.URL_PATTERN.match(url):
            result['error'] = "Invalid URL format"
            return result
        
        # Parse URL to check scheme
        try:
            parsed = urlparse(url)
            if parsed.scheme.lower() not in cls.ALLOWED_SCHEMES:
                result['error'] = f"Unsupported URL scheme. Allowed: {', '.join(cls.ALLOWED_SCHEMES)}"
                return result
        except Exception:
            result['error'] = "Invalid URL format"
            return result
        
        # Validate URL with external library (lenient - if it fails, log warning but allow)
        try:
            if not validators.url(url):
                # Don't block - external validator can be overly strict
                # Log but continue (lenient mode for development)
                pass
        except Exception:
            # If validators library crashes, continue anyway
            pass
        
        # Sanitize URL
        sanitized_url = cls._sanitize_url(url)
        result['is_valid'] = True
        result['sanitized_url'] = sanitized_url
        
        return result
    
    @classmethod
    def validate_text(cls, text: str) -> dict:
        """
        Validate text input for scanning
        
        Returns:
            dict: Validation result with 'is_valid', 'error', and 'sanitized_text'
        """
        result = {
            'is_valid': False,
            'error': None,
            'sanitized_text': None
        }
        
        # Check if text is None or empty
        if not text or not text.strip():
            result['error'] = "Text cannot be empty"
            return result
        
        # Strip whitespace
        text = text.strip()
        
        # Check length
        if len(text) > cls.MAX_TEXT_LENGTH:
            result['error'] = f"Text too long (max {cls.MAX_TEXT_LENGTH} characters)"
            return result
        
        # ===== FIX: SQL injection detection (less aggressive) =====
        # OLD: Blocked ANY single quote r"'.*'|'.*" → Too strict!
        # NEW: Only block SQL keywords after quote
        
        sql_injection_patterns = [
            r"'\s*(AND|OR|NOT)\s+",           # ' AND, ' OR, ' NOT
            r"'\s*;\s*(DROP|DELETE|INSERT|UPDATE|CREATE)",  # '; DROP
            r"'\s*UNION\s+SELECT",            # ' UNION SELECT
            r"'\s*--",                        # ' --
            r"'\s*\/\*.*?\*\/",             # ' /* */
            r"admin.*'.*'\s*=\s*'",           # admin'='
            r"\=\s*'.*'\s*(AND|OR|UNION)",   # = 'x' AND
        ]
        
        for pattern in sql_injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                result['error'] = "Invalid text format - potential SQL injection detected"
                return result
        
        # ===== FIX: XSS detection for text - Allow HTML tags (test case) =====
        # Allow: <script>alert('xss')</script>
        #        (This is for model to analyze, not to execute)
        # Block: javascript: protocol, data: protocol
        #        (These are actual attack vectors)
        
        xss_patterns = [
            r"javascript:",        # javascript: protocol
            r"vbscript:",          # vbscript: protocol
            r"data:text/html",     # data: protocol with HTML
            r"data:application/x-sh",  # data: protocol with shell
        ]
        
        for pattern in xss_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                result['error'] = "Invalid text format - potential XSS detected"
                return result
        
        # ⚠️ Allow raw HTML tags in text
        # Reason: They're test payloads for model to detect phishing/malicious patterns
        # Backend won't render/execute them (just passes to ML model for analysis)
        
        # Sanitize text
        sanitized_text = cls._sanitize_text(text)
        result['is_valid'] = True
        result['sanitized_text'] = sanitized_text
        
        return result
    
    @staticmethod
    def _sanitize_url(url: str) -> str:
        """Basic URL sanitization"""
        # Remove null bytes
        url = url.replace('\x00', '')
        
        # Normalize whitespace
        url = ' '.join(url.split())
        
        return url
    
    @staticmethod
    def _sanitize_text(text: str) -> str:
        """Basic text sanitization"""
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text


def validate_input(input_data: str, input_type: str = 'url') -> dict:
    """
    Main validation function
    
    Args:
        input_data: The input string to validate
        input_type: Type of input ('url' or 'text')
    
    Returns:
        dict: Validation result
    """
    if input_type.lower() == 'url':
        return InputValidator.validate_url(input_data)
    elif input_type.lower() == 'text':
        return InputValidator.validate_text(input_data)
    else:
        return {
            'is_valid': False,
            'error': f"Unsupported input type: {input_type}",
            'sanitized_input': None
        }