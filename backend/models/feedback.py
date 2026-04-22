"""
TEN FILE: backend/models/feedback.py

CONG DUNG:
  - Dinh nghia bang Feedback trong database
  - Luu tru phan hoi tu nguoi dung
  - Ghi nhan dinh chinh khi du doan sai
  - Ghi nhan do tin tuong cua nguoi dung

CTRUC BANG FEEDBACK:
  * id: Khoa chinh (auto-increment)
  * scan_id: Lien ket den Scan (foreign key)
  * user_id: Lien ket den User (foreign key)
  * predicted_result: Ket qua du doan ("phishing"/"legitimate")
  * actual_result: Ket qua thuc te (neu co)
  * is_correct: Co dung khong (True/False)
  * confidence: Do tin tuong nguoi dung (0-100)
  * comment: Nhan xet hoac giai thich (optional)
  * rating: Danh gia tu 1-5 (optional)
  * created_at: Thoi gian tao phan hoi

USAGE:
  from backend.models.feedback import Feedback
  db.add(Feedback(scan_id=123, is_correct=False, actual_result="legitimate"))
  db.commit()

TRUY VAN:
  incorrect_predictions = db.query(Feedback).filter(Feedback.is_correct == False).all()
  user_feedback = db.query(Feedback).filter(Feedback.user_id == 1).all()
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.models.database import Base


class Feedback(Base):
    """
    Feedback model for storing user corrections and feedback.
    
    When users correct the model's prediction (e.g., it said PHISHING but it's LEGITIMATE),
    this feedback is stored to:
    1. Improve model accuracy
    2. Track false positives/false negatives
    3. Trigger model retraining when enough feedback accumulates
    
    Relationships:
        - scan: Many-to-one with Scan (feedback linked to a specific scan)
        - user: Many-to-one with User (who provided the feedback)
    """
    
    __tablename__ = "feedback"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    scan_id = Column(
        Integer,
        ForeignKey("scans.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # User's correction
    correct_label = Column(
        String(50),
        nullable=False
    )  # "PHISHING" or "LEGITIMATE" - what it actually was
    
    # User's comments
    user_feedback = Column(Text, nullable=True)  # Why user thinks this is wrong
    
    # Usefulness flag (for ranking feedback quality)
    is_useful = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    
    # Relationships
    scan = relationship(
        "Scan",
        back_populates="feedbacks"
    )
    user = relationship(
        "User",
        back_populates="feedbacks"
    )
    
    def __repr__(self):
        return (
            f"<Feedback(id={self.id}, scan_id={self.scan_id}, "
            f"correct_label='{self.correct_label}')>"
        )
