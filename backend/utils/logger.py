"""
╔═══════════════════════════════════════════════════════════════════╗
║              PHISHGUARD LOGGING UTILITIES                         ║
║         📝 Ghi nhật ký có cấu trúc (Structured Logging)           ║
╚═══════════════════════════════════════════════════════════════════╝

TÊN FILE: backend/utils/logger.py

CÔNG DỤNG:
  - Ghi nhật ký tất cả hoạt động API, ML, Database
  - Xuất log dưới dạng JSON để phân tích
  - Theo dõi lỗi, cảnh báo, và thông tin
  - Giúp debug và phân tích hiệu suất

CÁC LEVEL LOG:
  • DEBUG: Thông tin chi tiết cho phát triển
  • INFO: Thông tin chung về hoạt động
  • WARNING: Cảnh báo về vấn đề tiềm ẩn
  • ERROR: Lỗi nghiêm trọng
  • CRITICAL: Lỗi thảm họa

CÁCH SỬ DỤNG:
  from backend.utils.logger import get_logger
  logger = get_logger(__name__)
  logger.info("Scan started", extra={"url": url, "user_id": user_id})
  logger.error("ML prediction failed", exc_info=True)

DỊNH DẠNG LOG:
  {
    "timestamp": "2026-04-21T10:30:45Z",
    "level": "INFO",
    "module": "backend.routes.scan",
    "message": "Scan completed",
    "url": "https://example.com",
    "result": "phishing"
  }
"""
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
import sys

# Configure structured logging
class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logs"""
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'input_type'):
            log_entry['input_type'] = record.input_type
        if hasattr(record, 'input_length'):
            log_entry['input_length'] = record.input_length
        if hasattr(record, 'scan_result'):
            log_entry['scan_result'] = record.scan_result
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)

def setup_logging(level: str = "INFO", log_file: Optional[str] = None):
    """
    Setup structured logging configuration
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file to write logs to
    """
    # Create logger
    logger = logging.getLogger("phishguard")
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = StructuredFormatter()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name
    
    Args:
        name: Logger name
        
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(f"phishguard.{name}")

# Global logger instance
logger = get_logger(__name__)

def log_scan_attempt(
    user_id: str,
    input_text: str,
    input_type: str,
    request_id: Optional[str] = None
):
    """
    Log scan attempt
    
    Args:
        user_id: User identifier
        input_text: Input text being scanned
        input_type: Type of input (url/text)
        request_id: Optional request identifier
    """
    logger.info(
        "Scan attempt",
        extra={
            "user_id": user_id,
            "input_type": input_type,
            "input_length": len(input_text),
            "request_id": request_id
        }
    )

def log_scan_result(
    user_id: str,
    input_text: str,
    input_type: str,
    result: Dict[str, Any],
    request_id: Optional[str] = None
):
    """
    Log scan result
    
    Args:
        user_id: User identifier
        input_text: Input text that was scanned
        input_type: Type of input (url/text)
        result: Scan result dictionary
        request_id: Optional request identifier
    """
    logger.info(
        "Scan completed",
        extra={
            "user_id": user_id,
            "input_type": input_type,
            "input_length": len(input_text),
            "scan_result": result.get("result", {}),
            "request_id": request_id
        }
    )

def log_error(
    message: str,
    user_id: Optional[str] = None,
    input_type: Optional[str] = None,
    request_id: Optional[str] = None,
    exc_info: bool = True
):
    """
    Log error with structured format
    
    Args:
        message: Error message
        user_id: Optional user identifier
        input_type: Optional input type
        request_id: Optional request identifier
        exc_info: Include exception info
    """
    extra = {}
    if user_id:
        extra['user_id'] = user_id
    if input_type:
        extra['input_type'] = input_type
    if request_id:
        extra['request_id'] = request_id
    
    logger.error(
        message,
        extra=extra,
        exc_info=exc_info
    )

def log_security_event(
    event_type: str,
    user_id: str,
    details: Dict[str, Any],
    request_id: Optional[str] = None
):
    """
    Log security-related events
    
    Args:
        event_type: Type of security event
        user_id: User identifier
        details: Additional event details
        request_id: Optional request identifier
    """
    logger.warning(
        f"Security event: {event_type}",
        extra={
            "user_id": user_id,
            "event_type": event_type,
            "security_details": details,
            "request_id": request_id
        }
    )

def log_rate_limit_exceeded(
    user_id: str,
    request_id: Optional[str] = None
):
    """
    Log rate limit exceeded event
    
    Args:
        user_id: User identifier
        request_id: Optional request identifier
    """
    log_security_event(
        "rate_limit_exceeded",
        user_id,
        {"message": "Rate limit exceeded for user"},
        request_id
    )

def log_authentication_failure(
    user_id: str,
    failure_reason: str,
    request_id: Optional[str] = None
):
    """
    Log authentication failure
    
    Args:
        user_id: User identifier
        failure_reason: Reason for authentication failure
        request_id: Optional request identifier
    """
    log_security_event(
        "authentication_failure",
        user_id,
        {"failure_reason": failure_reason},
        request_id
    )

def log_input_validation_failure(
    user_id: str,
    input_text: str,
    validation_error: str,
    request_id: Optional[str] = None
):
    """
    Log input validation failure
    
    Args:
        user_id: User identifier
        input_text: Input text that failed validation
        validation_error: Validation error message
        request_id: Optional request identifier
    """
    log_security_event(
        "input_validation_failure",
        user_id,
        {
            "input_length": len(input_text),
            "validation_error": validation_error,
            "input_preview": input_text[:100] + "..." if len(input_text) > 100 else input_text
        },
        request_id
    )