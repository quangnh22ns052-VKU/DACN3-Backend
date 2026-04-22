"""
Authentication Pydantic Schemas

Validation schemas for JWT tokens and authentication responses.
"""

from pydantic import BaseModel, Field
from typing import Optional


class TokenResponse(BaseModel):
    """
    Schema for JWT token response (POST /auth/login)
    """
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type (always 'bearer')")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800
            }
        }


class TokenPayload(BaseModel):
    """
    Schema for JWT token payload (internal use)
    """
    sub: int = Field(..., description="User ID")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")


class AuthResponse(BaseModel):
    """
    Schema for generic auth responses
    """
    success: bool
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "User registered successfully"
            }
        }
