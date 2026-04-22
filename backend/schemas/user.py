"""
User Pydantic Schemas

Validation schemas for user registration, login, and responses.
"""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    """
    Schema for user registration (POST /auth/register)
    """
    email: EmailStr = Field(..., description="User's email address")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "username": "john_doe",
                "password": "secure_password_123"
            }
        }


class UserLogin(BaseModel):
    """
    Schema for user login (POST /auth/login)
    """
    email: EmailStr = Field(..., description="User's email")
    password: str = Field(..., description="User's password")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "secure_password_123"
            }
        }


class UserResponse(BaseModel):
    """
    Schema for returning user data (never includes password!)
    """
    id: int
    email: str
    username: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True  # Enable ORM mode - can populate from ORM objects
        json_schema_extra = {
            "example": {
                "id": 1,
                "email": "user@example.com",
                "username": "john_doe",
                "is_active": True,
                "created_at": "2026-04-16T10:30:00",
                "updated_at": "2026-04-16T10:30:00"
            }
        }
