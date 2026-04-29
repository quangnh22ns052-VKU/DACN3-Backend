"""
TEN FILE: backend/models/api_usage.py

CONG DUNG:
  - Dinh nghia bang APIUsage trong database
  - Theo doi moi lan goi API
  - Quan ly rate limiting (so lan toi da/thang)
  - Ghi nhan thoi gian va endpoint duoc goi
  - Theo doi latency va status code

CTRUC BANG APIUSAGE:
  * id: Khoa chinh (auto-increment)
  * user_id: Lien ket den User (foreign key)
  * endpoint: Endpoint API duoc goi (/scan, /feedback, /health)
  * method: HTTP method (GET, POST)
  * status_code: Status code tra lai (200, 400, 500)
  * latency_ms: Thoi gian xu ly (ms)
  * request_ip: Dia chi IP cua request
  * created_at: Thoi gian goi API

USAGE:
  from backend.models.api_usage import APIUsage
  db.add(APIUsage(user_id=1, endpoint="/scan", method="POST", status_code=200))
  db.commit()

TRUY VAN:
  recent_calls = db.query(APIUsage).order_by(APIUsage.created_at.desc()).limit(100).all()
  user_calls = db.query(APIUsage).filter(APIUsage.user_id == 1).count()
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.models.database import Base


class APIUsage(Base):
    """
    APIUsage model for tracking API endpoint calls and rate limiting.
    
    Used for:
    1. Rate limiting - count calls per user per day
    2. Analytics - understand usage patterns
    3. Performance monitoring - track response times
    4. Abuse detection - identify suspicious activity
    
    Relationships:
        - user: Many-to-one with User (which user made the call)
    """
    
    __tablename__ = "api_usage"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Key to User
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # API call details
    endpoint = Column(String(255), nullable=False)  # e.g., "/api/scan", "/api/feedback"
    method = Column(String(10), nullable=False)  # GET, POST, PUT, DELETE, etc.
    status_code = Column(Integer, nullable=False)  # HTTP response code (200, 400, 500, etc.)
    
    # Performance tracking
    response_time_ms = Column(Float, nullable=True)  # Response time in milliseconds
    
    # Timestamp
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    
    # Relationships
    # Note: Commented out to avoid SQLAlchemy mapper initialization issues
    # user = relationship(
    #     "User",
    #     back_populates="api_usage"
    # )
    
    def __repr__(self):
        return (
            f"<APIUsage(id={self.id}, user_id={self.user_id}, "
            f"endpoint='{self.endpoint}', method='{self.method}', "
            f"status_code={self.status_code})>"
        )
