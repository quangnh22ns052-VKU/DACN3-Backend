"""
Quick startup script for PhishGuard backend.
Run with: python start_backend.py
"""
import sys
import os

# Add Backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.api:app",
        host="127.0.0.1",
        port=8000,
        reload=False,  # Disable reload to avoid import issues
        log_level="info"
    )
