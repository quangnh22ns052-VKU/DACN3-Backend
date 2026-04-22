"""
Feedback Pydantic Schemas

Validation schemas for feedback submission and responses.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class FeedbackLabelEnum(str, Enum):
    """Enum for feedback labels"""
    PHISHING = "PHISHING"
    LEGITIMATE = "LEGITIMATE"


class FeedbackRequest(BaseModel):
    """
    Schema for submitting feedback (POST /api/feedback)
    """
    scan_id: int = Field(..., description="ID of the scan being corrected")
    correct_label: FeedbackLabelEnum = Field(..., description="What it actually is")
    user_feedback: Optional[str] = Field(None, max_length=500, description="User's comments")
    
    class Config:
        json_schema_extra = {
            "example": {
                "scan_id": 1,
                "correct_label": "LEGITIMATE",
                "user_feedback": "This is my company's domain, not phishing"
            }
        }


class FeedbackResponse(BaseModel):
    """
    Schema for returning feedback data
    """
    id: int
    scan_id: int
    user_id: int
    correct_label: FeedbackLabelEnum
    user_feedback: Optional[str]
    is_useful: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "scan_id": 1,
                "user_id": 1,
                "correct_label": "LEGITIMATE",
                "user_feedback": "This is my company's domain",
                "is_useful": True,
                "created_at": "2026-04-16T10:30:00"
            }
        }


class FeedbackStatsResponse(BaseModel):
    """
    Schema for returning feedback statistics
    """
    total_feedback: int
    phishing_corrections: int
    legitimate_corrections: int
    useful_feedback_count: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_feedback": 150,
                "phishing_corrections": 80,
                "legitimate_corrections": 70,
                "useful_feedback_count": 120
            }
        }
