"""
TEN FILE: backend/models/scan.py

CONG DUNG:
  - Dinh nghia bang Scan trong database
  - Luu tru lich su cac lan quet URL/text
  - Luu ket qua phat hien phishing
  - Luu xac suat va thong tin khac

CTRUC BANG SCAN:
  * id: Khoa chinh (auto-increment)
  * user_id: Lien ket den User (foreign key)
  * input_text: URL hoac text da quet
  * result: Ket qua ("phishing" hoac "legitimate")
  * probability: Xac suat phishing (0.0 - 1.0)
  * heuristics: Cac quy tac duoc kich hoat
  * features: Top features dung gop
  * created_at: Thoi gian tao ban ghi
  * updated_at: Thoi gian cap nhat

USAGE:
  from backend.models.scan import Scan
  db.add(Scan(user_id=1, input_text="https://...", result="phishing"))
  db.commit()

TRUY VAN:
  scans = db.query(Scan).filter(Scan.result == "phishing").all()
  recent_scans = db.query(Scan).order_by(Scan.created_at.desc()).limit(10).all()
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.models.database import Base


class Scan(Base):
    """
    Scan model for storing phishing detection scan history.
    
    Each scan record tracks:
    - User who performed the scan
    - Input text/URL
    - ML model result
    - Heuristic-based result
    - Probability score
    - SHAP explanation
    
    Relationships:
        - user: Many-to-one with User
        - feedbacks: One-to-many with Feedback (user corrections)
    """
    
    __tablename__ = "scans"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Key to User (NULL for anonymous scans)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,  # Allow NULL for anonymous users
        index=True
    )
    
    # Input data
    input_text = Column(String(2048), nullable=False)  # URL or text to scan
    
    # Detection results
    result = Column(String(50), nullable=False)  # "PHISHING", "LEGITIMATE", "SUSPICIOUS"
    probability = Column(Float, nullable=False)  # 0.0 to 1.0
    
    # Individual detection methods results
    heuristic_result = Column(String(50))  # Result from rule-based detection
    ml_result = Column(String(50))  # Result from ML model
    
    # SHAP explanation as JSON string or text
    explanation = Column(Text, nullable=True)  # Feature importance scores
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    
    # Relationships
    user = relationship(
        "User",
        back_populates="scans"
    )
    feedbacks = relationship(
        "Feedback",
        back_populates="scan",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    def __repr__(self):
        return (
            f"<Scan(id={self.id}, user_id={self.user_id}, "
            f"result='{self.result}', probability={self.probability})>"
        )
