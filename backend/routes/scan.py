"""
backend/routes/scan.py
Endpoint quét URL / văn bản — tích hợp xác thực đầu vào,
xác thực người dùng, rate limiting, ghi nhật ký VÀ LƯU DATABASE.
"""

import uuid
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, field_validator
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime
import json
import logging

from core.detector import PhishDetector
from core.heuristics import get_heuristics_reason

from backend.utils.validators import InputValidator, validate_input
from backend.utils.auth import optional_auth, check_rate_limit, security
from backend.utils.logger import (
    log_scan_attempt,
    log_scan_result,
    log_error,
    log_rate_limit_exceeded,
    log_input_validation_failure,
)
from backend.models.database import SessionLocal
from backend.models.scan import Scan

router = APIRouter()
logger = logging.getLogger(__name__)
from backend.models.user import User

router = APIRouter()
_detector_instance = None

def get_detector():
    """Lazy load PhishDetector on first use (avoid import-time crashes)"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = PhishDetector()
    return _detector_instance


# ------------------------------------------------------------------ #
#  Request / Response schemas                                          #
# ------------------------------------------------------------------ #

class ScanRequest(BaseModel):
    text: str
    input_type: Optional[str] = "auto"  # "url" | "text" | "auto"

    @field_validator("text")
    @classmethod
    def text_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Trường 'text' không được để trống.")
        return v.strip()


class ScanResponse(BaseModel):
    request_id: str
    input: str
    input_type: str
    result: dict
    heuristics_reason: dict
    ml_features: dict
    feature_explanation: str


# ------------------------------------------------------------------ #
#  Hàm phụ trợ                                                         #
# ------------------------------------------------------------------ #

def _detect_input_type(text: str) -> str:
    """Tự động nhận dạng URL hay văn bản thuần."""
    return "url" if text.lower().startswith(("http://", "https://", "ftp://")) else "text"


def _validate(text: str, input_type: str, user_id: str, request_id: str) -> str:
    """
    Gọi InputValidator và ném HTTPException nếu không hợp lệ.
    Trả về chuỗi đã làm sạch.
    """
    validation = validate_input(text, input_type)

    if not validation["is_valid"]:
        log_input_validation_failure(
            user_id=user_id,
            input_text=text,
            validation_error=validation["error"],
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "VALIDATION_ERROR",
                "message": validation["error"],
            },
        )

    # Lấy giá trị đã làm sạch (key khác nhau tuỳ input_type)
    return validation.get("sanitized_url") or validation.get("sanitized_text") or text


# ------------------------------------------------------------------ #
#  Endpoint chính                                                       #
# ------------------------------------------------------------------ #

@router.post("", response_model=ScanResponse)
def scan_url_or_text(
    request: ScanRequest,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    request_id = str(uuid.uuid4())

    # --- 1. Xác thực người dùng (tuỳ chọn) -----------------------
    user_info = optional_auth(credentials)
    user_id = user_info.get("user_id", "anonymous")

    # --- 2. Kiểm tra rate limit -----------------------------------
    if not check_rate_limit(user_id):
        log_rate_limit_exceeded(user_id=user_id, request_id=request_id)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Bạn đã gửi quá nhiều yêu cầu. Vui lòng thử lại sau.",
            },
        )

    # --- 3. Xác định loại đầu vào --------------------------------
    input_type = (
        _detect_input_type(request.text)
        if request.input_type == "auto"
        else request.input_type
    )

    # --- 4. Xác thực & làm sạch đầu vào -------------------------
    clean_text = _validate(request.text, input_type, user_id, request_id)

    # --- 5. Ghi nhật ký bắt đầu quét ----------------------------
    log_scan_attempt(
        user_id=user_id,
        input_text=clean_text,
        input_type=input_type,
        request_id=request_id,
    )

# --- 6. Xử lý ML + lấy feature explanations ------------------
    try:
        # Get ML prediction (với threshold 0.4 thay vì 0.5)
        ml_prediction = get_detector().predict(clean_text, threshold=0.4)
        
        # Lấy heuristics analysis
        heuristics_reason = get_heuristics_reason(clean_text)
        
        # Lấy top features từ ML model
        top_features = ml_prediction.get("top_features", {})
        
        # Updated prediction with ML-based features
        prediction = {
            "label": ml_prediction["label"],
            "confidence": ml_prediction.get("confidence", 0.0),
            "probabilities": ml_prediction.get("probabilities", {}),
            "top_features": top_features
        }

    except Exception as exc:
        log_error(
            message=f"Lỗi xử lý quét: {exc}",
            user_id=user_id,
            input_type=input_type,
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "SCAN_ERROR",
                "message": "Đã xảy ra lỗi trong quá trình phân tích. Vui lòng thử lại.",
            },
        )

    # --- 7. Ghi nhật ký kết quả ----------------------------------
    result_payload = {
        "request_id":          request_id,
        "input":               clean_text,
        "input_type":          input_type,
        "result": {
            "label": prediction["label"],
            "confidence": prediction["confidence"],
            "probabilities": prediction.get("probabilities", {}),
        },
        "heuristics_reason":   heuristics_reason,
        "ml_features": prediction.get("top_features", {}),
        "feature_explanation": "Top ML keywords that contributed to this classification"
    }

    log_scan_result(
        user_id=user_id,
        input_text=clean_text,
        input_type=input_type,
        result=result_payload,
        request_id=request_id,
    )

    # --- 8. LƯU VÀO DATABASE ----------------------------------
    try:
        db = SessionLocal()
        
        # Prepare scan data - using ML confidence
        scan_record = Scan(
            user_id=user_id if user_id != "anonymous" else None,
            input_text=clean_text,
            result=prediction["label"].upper(),  # SAFE | SUSPICIOUS | PHISHING
            probability=float(prediction.get("confidence", 0.0)),
            ml_result=prediction.get("probabilities", {}).get("phishing", 0.0),
            heuristic_result="PHISHING" if heuristics_reason.get("triggered", False) else "LEGITIMATE",
            explanation=json.dumps({
                "ml_features": prediction.get("top_features", {}),
                "heuristics_rules": heuristics_reason.get("rules", []),
                "probabilities": prediction.get("probabilities", {})
            }, ensure_ascii=False),
            created_at=datetime.utcnow()
        )
        
        db.add(scan_record)
        db.commit()
        db.refresh(scan_record)
        
    except Exception as db_error:
        log_error(
            message=f"Lỗi lưu vào database: {db_error}",
            user_id=user_id,
            input_type=input_type,
            request_id=request_id,
        )
        result_payload["warning"] = f"Kết quả xử lý được trả về nhưng không lưu vào DB: {str(db_error)}"
        
    finally:
        if 'db' in locals():
            db.close()

    return result_payload


# ------------------------------------------------------------------ #
#  Endpoint: Get Scan History                                         #
# ------------------------------------------------------------------ #

@router.get("/history")
def get_scan_history(
    limit: int = 10,
    offset: int = 0,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    """
    Get scan history for authenticated user or all users.
    
    Args:
        limit: Number of results to return (default 10, max 100)
        offset: Number of results to skip (default 0)
        
    Returns:
        List of scan records with pagination info
        
    Requires: Valid JWT token (optional for demo, required in production)
    """
    from sqlalchemy import desc
    from backend.utils.auth import AuthManager
    
    # Validate limit
    limit = min(limit, 100)
    if limit < 1:
        limit = 10
    
    db = SessionLocal()
    
    try:
        # Get user info if authenticated
        user_id = None
        if credentials:
            try:
                user_info = AuthManager.authenticate_user(credentials)
                user_id = user_info.get("user_id")
            except:
                pass  # Continue without auth
        
        # Query scans
        if user_id:
            # Authenticated: get only user's scans
            query = db.query(Scan).filter(Scan.user_id == user_id)
        else:
            # Anonymous: get all recent scans (for demo)
            query = db.query(Scan)
        
        # Count total
        total = query.count()
        
        # Get paginated results
        scans = query.order_by(desc(Scan.created_at)).offset(offset).limit(limit).all()
        
        # Convert to response format
        results = []
        for scan in scans:
            results.append({
                "id": scan.id,
                "input_text": scan.input_text,
                "result": scan.result,
                "probability": scan.probability,
                "ml_result": scan.ml_result,
                "heuristic_result": scan.heuristic_result,
                "created_at": scan.created_at.isoformat() if scan.created_at else None
            })
        
        log_scan_attempt(
            user_id=user_id or "anonymous",
            input_text="GET /history",
            input_type="history",
            request_id="history_query"
        )
        
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "count": len(results),
            "scans": results
        }
        
    except Exception as err:
        logger.error(f"❌ Error retrieving scan history: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi lấy lịch sử quét. Vui lòng thử lại."
        )
        
    finally:
        db.close()


# ------------------------------------------------------------------ #
#  Endpoint: Get Scan Details                                         #
# ------------------------------------------------------------------ #

@router.get("/{scan_id}")
def get_scan_detail(
    scan_id: int,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    """
    Get detailed information about a specific scan.
    
    Args:
        scan_id: ID of the scan to retrieve
        
    Returns:
        Detailed scan information with explanation
    """
    db = SessionLocal()
    
    try:
        # Get scan
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy scan với ID: {scan_id}"
            )
        
        # Parse explanation if JSON string
        explanation = scan.explanation
        if explanation and isinstance(explanation, str):
            try:
                import json
                explanation = json.loads(explanation)
            except:
                pass
        
        logger.info(f"✅ Retrieved scan detail: ID={scan_id}")
        
        return {
            "id": scan.id,
            "user_id": scan.user_id,
            "input_text": scan.input_text,
            "result": scan.result,
            "probability": scan.probability,
            "ml_result": scan.ml_result,
            "heuristic_result": scan.heuristic_result,
            "explanation": explanation,
            "created_at": scan.created_at.isoformat() if scan.created_at else None
        }
        
    except HTTPException as http_err:
        raise http_err
        
    except Exception as err:
        logger.error(f"❌ Error retrieving scan detail: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi lấy chi tiết quét. Vui lòng thử lại."
        )
        
    finally:
        db.close()