"""
TEN FILE: backend/models/user.py

CONG DUNG:
  - Dinh nghia bang User trong database
  - Luu tru thong tin nguoi dung
  - Quan ly authentication va authorization
  - Theo doi API usage va scan history

CTRUC BANG USER:
  * id: Khoa chinh (auto-increment)
  * username: Ten dang nhap duy nhat
  * email: Email duy nhat
  * password_hash: Mat khau ma hoa (luu hash, khong luu dung mat khau)
  * is_active: Co hoat dong khong (True/False)
  * is_admin: Co phai admin khong
  * created_at: Thoi gian tao tai khoan
  * last_login: Lan dang nhap gan day
  * api_quota: So lan quet toi da/thang
  * api_usage: Quan he 1-n voi APIUsage
  * scans: Quan he 1-n voi Scan
  * feedback: Quan he 1-n voi Feedback

USAGE:
  from backend.models.user import User
  user = User(username="john", email="john@example.com")
  db.add(user)
  db.commit()

TRUY VAN:
  user = db.query(User).filter(User.email == "john@example.com").first()
  active_users = db.query(User).filter(User.is_active == True).all()
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.models.database import Base
from datetime import datetime


class User(Base):
    """
    User model for storing user account information.
    
    Relationships:
        - scans: One-to-many with Scan (user can have many scans)
        - api_usage: One-to-many with APIUsage (track user's API calls)
        - feedbacks: One-to-many with Feedback (user's feedback submissions)
    """
    
    __tablename__ = "users"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Email - unique identifier for login
    email = Column(String(255), unique=True, index=True, nullable=False)
    
    # Username - display name
    username = Column(String(100), unique=True, index=True, nullable=False)
    
    # Password hash (bcrypt) - NEVER store plaintext passwords
    password_hash = Column(String(255), nullable=False)
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationships
    scans = relationship(
        "Scan",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    # Note: Commented out to avoid SQLAlchemy mapper initialization issues
    # when DATABASE_URL is not set or models not fully imported
    # api_usage = relationship(
    #     "APIUsage",
    #     back_populates="user",
    #     cascade="all, delete-orphan",
    #     lazy="dynamic"
    # )
    feedbacks = relationship(
        "Feedback",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', username='{self.username}')>"
