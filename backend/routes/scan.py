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

from core.detector import PhishDetector
from core.heuristics import get_heuristics_reason
from core.explainers import get_shap_explanation

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
from backend.models.user import User

router = APIRouter()
detector = PhishDetector()


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
    advanced_explanation: dict


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

@router.post("/", response_model=ScanResponse)
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

 # --- 6. Xử lý ML + heuristics + giải thích ------------------
    try:
        prediction        = detector.predict(clean_text)
        heuristics_reason = get_heuristics_reason(clean_text)
        shap_explanation  = get_shap_explanation(clean_text)

        # Wrap string → dict nếu cần
        if isinstance(heuristics_reason, str):
            heuristics_reason = {"message": heuristics_reason}
        if isinstance(shap_explanation, str):
            shap_explanation = {"message": shap_explanation}

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
        "result":              prediction,
        "heuristics_reason":   heuristics_reason,
        "advanced_explanation": shap_explanation,
    }

    log_scan_result(
        user_id=user_id,
        input_text=clean_text,
        input_type=input_type,
        result=result_payload,
        request_id=request_id,
    )

    # --- 8. LƯU VÀO DATABASE (NEW!) ----------------------------------
    try:
        db = SessionLocal()
        
        # Prepare scan data
        scan_record = Scan(
            user_id=user_id if user_id != "anonymous" else None,  # NULL for anonymous
            input_text=clean_text,
            result=prediction.get("label", "UNKNOWN").upper(),
            probability=float(prediction.get("probabilities", {}).get("phishing", 0.0)),
            ml_result=prediction.get("label", "UNKNOWN").upper(),
            heuristic_result=heuristics_reason.get("triggered", False) and "PHISHING" or "LEGITIMATE",
            explanation=json.dumps(shap_explanation, ensure_ascii=False),
            created_at=datetime.utcnow()
        )
        
        db.add(scan_record)
        db.commit()
        db.refresh(scan_record)
        
        log_scan_result(
            user_id=user_id,
            input_text=clean_text,
            input_type=input_type,
            result=f"Saved to DB with ID: {scan_record.id}",
            request_id=request_id,
        )
        
    except Exception as db_error:
        log_error(
            message=f"Lỗi lưu vào database: {db_error}",
            user_id=user_id,
            input_type=input_type,
            request_id=request_id,
        )
        # Don't fail the API call even if DB save fails
        # Log the error but still return the result
        result_payload["warning"] = f"Kết quả xử lý được trả về nhưng không lưu vào DB: {str(db_error)}"
        
    finally:
        if 'db' in locals():
            db.close()

    return result_payload