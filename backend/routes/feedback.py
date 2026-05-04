# feedback.py
"""
backend/routes/feedback.py
Endpoint tập hợp phản hồi từ người dùng - để cải thiện mô hình ML
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, field_validator
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from backend.models.database import SessionLocal
from backend.models.feedback import Feedback
from backend.models.scan import Scan
from backend.utils.logger import log_error
from backend.utils.auth import AuthManager, security

router = APIRouter()
logger = logging.getLogger(__name__)

# ================================================================
# Request/Response Schemas
# ================================================================

class FeedbackRequest(BaseModel):
    """User feedback on a scan result"""
    scan_id: int
    correct_label: str  # "phishing" | "legitimate" | "suspicious"
    comment: Optional[str] = None
    
    @field_validator("correct_label")
    @classmethod
    def validate_label(cls, v: str) -> str:
        valid_labels = ["phishing", "legitimate", "suspicious"]
        if v.lower() not in valid_labels:
            raise ValueError(f"Nhãn phải là một trong: {', '.join(valid_labels)}")
        return v.lower()


class FeedbackResponse(BaseModel):
    """Response after feedback submission"""
    id: int
    scan_id: int
    correct_label: str
    created_at: datetime
    message: str
    
    class Config:
        from_attributes = True


# ================================================================
# Endpoints
# ================================================================

@router.post("", response_model=FeedbackResponse)
def submit_feedback(
    request: FeedbackRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Submit user feedback on a scan result.
    
    This helps improve the ML model via retraining.
    
    Requires: Valid JWT token (authenticated user)
    
    Args:
        scan_id: ID of the scan to provide feedback on
        correct_label: What the result should have been
        comment: Optional comment from user
        
    Returns:
        FeedbackResponse with saved feedback details
        
    Raises:
        401: Unauthorized (token required)
        404: Scan not found
        400: Invalid input
    """
    db = SessionLocal()
    
    try:
        # 1. Authenticate user
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Vui lòng đăng nhập để gửi phản hồi"
            )
        
        user_info = AuthManager.authenticate_user(credentials)
        user_id = user_info.get("user_id")
        
        # 2. Verify scan exists
        scan = db.query(Scan).filter(Scan.id == request.scan_id).first()
        if not scan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy scan với ID: {request.scan_id}"
            )
        
        # 3. Create feedback record
        feedback = Feedback(
            scan_id=request.scan_id,
            user_id=user_id,
            correct_label=request.correct_label,
            user_feedback=request.comment,
            created_at=datetime.utcnow()
        )
        
        # 4. Save to database
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        
        logger.info(f"✅ Feedback saved: ID={feedback.id}, Scan={scan.id}, User={user_id}, Label={request.correct_label}")
        
        # 5. Return response
        return FeedbackResponse(
            id=feedback.id,
            scan_id=feedback.scan_id,
            correct_label=feedback.correct_label,
            created_at=feedback.created_at,
            message=f"Cảm ơn phản hồi của bạn! Dữ liệu này sẽ giúp cải thiện mô hình PhishGuard."
        )
        
    except HTTPException as http_err:
        logger.error(f"❌ HTTP Error: {http_err}")
        db.rollback()
        raise http_err
        
    except Exception as err:
        logger.error(f"❌ Unexpected error: {err}")
        log_error(
            message=f"Lỗi xử lý feedback: {err}",
            user_id="unknown",
            input_type="feedback",
            request_id="N/A"
        )
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi xử lý phản hồi. Vui lòng thử lại."
        )
        
    finally:
        db.close()


@router.get("/scan/{scan_id}")
def get_feedback_for_scan(scan_id: int):
    """
    Get all feedback for a specific scan.
    
    Args:
        scan_id: ID of the scan
        
    Returns:
        List of feedback for this scan
    """
    db = SessionLocal()
    
    try:
        # 1. Verify scan exists
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy scan với ID: {scan_id}"
            )
        
        # 2. Get all feedback
        feedbacks = db.query(Feedback)\
            .filter(Feedback.scan_id == scan_id)\
            .order_by(Feedback.created_at.desc())\
            .all()
        
        logger.info(f"✅ Retrieved {len(feedbacks)} feedback records for scan {scan_id}")
        
        return {
            "scan_id": scan_id,
            "feedback_count": len(feedbacks),
            "feedbacks": feedbacks
        }
        
    except HTTPException as http_err:
        raise http_err
        
    except Exception as err:
        logger.error(f"❌ Error retrieving feedback: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi lấy phản hồi."
        )
        
    finally:
        db.close()


@router.get("/stats")
def feedback_stats():
    """
    Get feedback statistics for analytics.
    
    Returns:
        - total_feedback: Total feedback count
        - by_label: Breakdown by label
        - accuracy_correction_rate: % of scans that got feedback
    """
    db = SessionLocal()
    
    try:
        from sqlalchemy import func
        
        # Total feedback
        total = db.query(func.count(Feedback.id)).scalar()
        
        # Breakdown by label
        by_label = db.query(
            Feedback.correct_label,
            func.count(Feedback.id)
        ).group_by(Feedback.correct_label).all()
        
        # Total scans
        total_scans = db.query(func.count(Scan.id)).scalar()
        
        correction_rate = (total / total_scans * 100) if total_scans > 0 else 0
        
        logger.info(f"✅ Feedback stats: Total={total}, Scans={total_scans}")
        
        return {
            "total_feedback": total,
            "total_scans": total_scans,
            "feedback_by_label": {label: count for label, count in by_label},
            "correction_rate_percent": round(correction_rate, 2)
        }
        
    except Exception as err:
        logger.error(f"❌ Error getting feedback stats: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi lấy thống kê phản hồi."
        )
        
    finally:
        db.close()
