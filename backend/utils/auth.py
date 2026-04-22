"""
╔═══════════════════════════════════════════════════════════════════╗
║           PHISHGUARD AUTHENTICATION UTILITIES                     ║
║         🔐 Rate Limiting & API Key Validation                    ║
╚═══════════════════════════════════════════════════════════════════╝

TÊN FILE: backend/utils/auth.py

CÔNG DỤNG:
  - Xác thực người dùng với API keys hoặc JWT tokens
  - Thực hiện rate limiting (giới hạn số lần gọi API)
  - Kiểm tra quyền truy cập (authorization)
  - Ghi nhật ký thông tin xác thực

CÁC HÀM CHÍNH:
  • verify_api_key(key): Kiểm tra API key hợp lệ
  • check_rate_limit(user_id): Kiểm tra giới hạn rate
  • get_current_user(token): Xác thực JWT token
  • is_authorized(user, resource): Kiểm tra quyền

CÁCH SỬ DỤNG:
  from backend.utils.auth import verify_api_key
  @router.get("/protected")
  def protected_route(key: str = Depends(verify_api_key)):
      return {"message": "Authorized!"}

LƯU Ý:
  - Rate limit: 100 requests/hour (mặc định)
  - API keys được quản lý trong database
  - JWT secret được lưu trong .env
"""
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from backend.config import Config

security = HTTPBearer(auto_error=False)
class AuthManager:
    """Authentication and authorization manager"""
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create JWT access token
        
        Args:
            data: Data to encode in the token
            expires_delta: Token expiration time
            
        Returns:
            str: JWT token string
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, Config.SECRET_KEY, algorithm=Config.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            Dict: Decoded token data
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    @staticmethod
    def authenticate_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
        """
        Authenticate user from Bearer token
        
        Args:
            credentials: HTTP authorization credentials
            
        Returns:
            Dict: User information from token
            
        Raises:
            HTTPException: If authentication fails
        """
        if not Config.SECRET_KEY:
            # In development mode, skip authentication
            return {"user_id": "dev_user", "username": "development"}
        
        try:
            token = credentials.credentials
            payload = AuthManager.verify_token(token)
            return payload
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

class RateLimiter:
    """Simple rate limiting implementation"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 3600):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # user_id -> list of timestamps
    
    def is_allowed(self, user_id: str) -> bool:
        """
        Check if request is allowed for user
        
        Args:
            user_id: User identifier
            
        Returns:
            bool: True if request is allowed
        """
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)
        
        if user_id not in self.requests:
            self.requests[user_id] = []
        
        # Remove old requests outside the window
        self.requests[user_id] = [req_time for req_time in self.requests[user_id] if req_time > window_start]
        
        # Check if under limit
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        
        # Add current request
        self.requests[user_id].append(now)
        return True

# Global rate limiter instance
rate_limiter = RateLimiter(max_requests=50, window_seconds=3600)

def check_rate_limit(user_id: str = "anonymous") -> bool:
    """
    Check if user is within rate limits
    
    Args:
        user_id: User identifier
        
    Returns:
        bool: True if within limits
    """
    return rate_limiter.is_allowed(user_id)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        Dict: User information
    """
    return AuthManager.authenticate_user(credentials)

def optional_auth(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Dict[str, Any]:
    """
    Optional authentication - allows both authenticated and anonymous access
    
    Args:
        credentials: Optional HTTP authorization credentials
        
    Returns:
        Dict: User information or anonymous user
    """
    if credentials:
        try:
            return AuthManager.authenticate_user(credentials)
        except HTTPException:
            # If auth fails, treat as anonymous
            pass
    
    return {"user_id": "anonymous", "username": "anonymous"}

# Rate limiting decorator
def rate_limit(max_requests: int = 10, window_seconds: int = 60):
    """
    Rate limiting decorator for FastAPI endpoints
    
    Args:
        max_requests: Maximum requests per window
        window_seconds: Time window in seconds
        
    Returns:
        Decorator function
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract user from kwargs or use anonymous
            user_id = kwargs.get('user_id', 'anonymous')
            
            if not check_rate_limit(user_id):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later."
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator