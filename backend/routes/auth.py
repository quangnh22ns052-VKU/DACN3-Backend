"""
backend/routes/auth.py
Authentication endpoints - user registration and login
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import bcrypt
import logging

from backend.models.database import SessionLocal
from backend.models.user import User
from backend.utils.auth import AuthManager
from backend.config import Config

router = APIRouter()
logger = logging.getLogger(__name__)


# ================================================================
# Request/Response Schemas
# ================================================================

class RegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr
    username: str
    password: str
    
    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not v or len(v) < 3:
            raise ValueError("Username phải có ít nhất 3 ký tự")
        if len(v) > 50:
            raise ValueError("Username không được quá 50 ký tự")
        return v
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v or len(v) < 8:
            raise ValueError("Mật khẩu phải có ít nhất 8 ký tự")
        return v


class LoginRequest(BaseModel):
    """User login request"""
    email: str
    password: str


class UserResponse(BaseModel):
    """User response (without password hash)"""
    id: int
    email: str
    username: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    """Authentication response with token"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ================================================================
# Helper Functions
# ================================================================

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode(), password_hash.encode())


# ================================================================
# Endpoints
# ================================================================

@router.post("/register", response_model=AuthResponse)
def register(request: RegisterRequest):
    """
    Register a new user account.
    
    Args:
        email: User email (must be unique)
        username: User username (must be unique)
        password: User password (min 8 chars)
        
    Returns:
        AuthResponse with JWT token
        
    Raises:
        400: Email/username already exists
        422: Invalid input
    """
    db = SessionLocal()
    
    try:
        # 1. Check if email already exists
        existing_email = db.query(User).filter(User.email == request.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email này đã được đăng ký"
            )
        
        # 2. Check if username already exists
        existing_username = db.query(User).filter(User.username == request.username).first()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username này đã được sử dụng"
            )
        
        # 3. Hash password
        password_hash = hash_password(request.password)
        
        # 4. Create new user
        new_user = User(
            email=request.email,
            username=request.username,
            password_hash=password_hash,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        # 5. Save to database
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"✅ User registered: {request.email}")
        
        # 6. Generate JWT token
        access_token = AuthManager.create_access_token(
            data={"user_id": new_user.id, "email": new_user.email, "username": new_user.username}
        )
        
        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(new_user)
        )
        
    except HTTPException as http_err:
        logger.error(f"❌ Registration error: {http_err.detail}")
        db.rollback()
        raise http_err
        
    except Exception as err:
        logger.error(f"❌ Unexpected error during registration: {err}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi tạo tài khoản. Vui lòng thử lại."
        )
        
    finally:
        db.close()


@router.post("/login", response_model=AuthResponse)
def login(request: LoginRequest):
    """
    Login with email and password.
    
    Args:
        email: User email
        password: User password
        
    Returns:
        AuthResponse with JWT token
        
    Raises:
        401: Invalid credentials
        404: User not found
    """
    db = SessionLocal()
    
    try:
        # 1. Find user by email
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email hoặc mật khẩu không chính xác"
            )
        
        # 2. Verify password
        if not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email hoặc mật khẩu không chính xác"
            )
        
        # 3. Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản này đã bị vô hiệu hóa"
            )
        
        logger.info(f"✅ User logged in: {request.email}")
        
        # 4. Generate JWT token
        access_token = AuthManager.create_access_token(
            data={"user_id": user.id, "email": user.email, "username": user.username}
        )
        
        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(user)
        )
        
    except HTTPException as http_err:
        logger.error(f"❌ Login error: {http_err.detail}")
        raise http_err
        
    except Exception as err:
        logger.error(f"❌ Unexpected error during login: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi đăng nhập. Vui lòng thử lại."
        )
        
    finally:
        db.close()


@router.get("/me", response_model=UserResponse)
def get_current_user(user_info: dict = Depends(AuthManager.authenticate_user)):
    """
    Get current authenticated user information.
    
    Requires: Valid JWT token
    
    Returns:
        UserResponse with user details
    """
    db = SessionLocal()
    
    try:
        user_id = user_info.get("user_id")
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse.model_validate(user)
        
    finally:
        db.close()
