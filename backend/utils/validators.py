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

LƯU Ý:
  - URL phải có http:// hoặc https://
  - Độ dài tối đa: 5000 ký tự
  - Độ dài tối thiểu: 5 ký tự
"""
import re
from typing import Optional
from urllib.parse import urlparse
import validators

class InputValidator:
    """Comprehensive input validation for URLs and text"""
    
    # URL validation patterns
    URL_PATTERN = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|'  # ...or ipv4
        r'\[?[A-F0-9]*:[A-F0-9:]+\]?)'  # ...or ipv6
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
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
        
        # Check for SQL injection patterns
        sql_injection_patterns = [
            r"'.*'|'.*",
            r"'.*--",
            r"'.*\/\*.*\*\/",
            r"'.*union.*select",
            r"'.*drop.*table",
            r"'.*insert.*into",
            r"'.*update.*set",
            r"'.*delete.*from"
        ]
        
        for pattern in sql_injection_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                result['error'] = "Invalid URL format - potential SQL injection detected"
                return result
        
        # Check for XSS patterns
        xss_patterns = [
            r"<script.*?>.*?</script>",
            r"javascript:",
            r"vbscript:",
            r"data:text/html",
            r"<iframe.*?>.*?</iframe>",
            r"<object.*?>.*?</object>",
            r"<embed.*?>",
            r"<link.*?>",
            r"<meta.*?>"
        ]
        
        for pattern in xss_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                result['error'] = "Invalid URL format - potential XSS detected"
                return result
        
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
        
        # Use validators library for additional validation
        if not validators.url(url):
            result['error'] = "Invalid URL format"
            return result
        
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
        
        # Check for SQL injection patterns
        sql_injection_patterns = [
            r"'.*'|'.*",
            r"'.*--",
            r"'.*\/\*.*\*\/",
            r"'.*union.*select",
            r"'.*drop.*table",
            r"'.*insert.*into",
            r"'.*update.*set",
            r"'.*delete.*from"
        ]
        
        for pattern in sql_injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                result['error'] = "Invalid text format - potential SQL injection detected"
                return result
        
        # Check for XSS patterns
        xss_patterns = [
            r"<script.*?>.*?</script>",
            r"javascript:",
            r"vbscript:",
            r"data:text/html",
            r"<iframe.*?>.*?</iframe>",
            r"<object.*?>.*?</object>",
            r"<embed.*?>",
            r"<link.*?>",
            r"<meta.*?>"
        ]
        
        for pattern in xss_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                result['error'] = "Invalid text format - potential XSS detected"
                return result
        
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