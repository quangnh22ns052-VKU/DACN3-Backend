#!/usr/bin/env python3
"""
🔍 PhishGuard Configuration Diagnostic Tool

Helps identify and fix deployment issues, especially database configuration.

Usage:
    python diagnose.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def print_header(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def check_env_vars():
    """Check environment variables"""
    print_header("🔍 Environment Variables Check")
    
    vars_to_check = [
        "DATABASE_URL",
        "ENVIRONMENT",
        "FRONTEND_URL",
        "RENDER_EXTERNAL_URL",
        "RAILWAY_STATIC_URL"
    ]
    
    for var in vars_to_check:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if "password" in var.lower() or "key" in var.lower():
                display = "***" + value[-6:] if len(value) > 6 else "***"
            elif "DATABASE_URL" in var:
                # Show just the host, not the password
                try:
                    import urllib.parse
                    parsed = urllib.parse.urlparse(value)
                    display = f"postgresql://{parsed.hostname}:{parsed.port}/{parsed.path.lstrip('/')}"
                except:
                    display = value[:40] + "..." if len(value) > 40 else value
            else:
                display = value[:50] + "..." if len(value) > 50 else value
            
            print(f"  ✅ {var:<25} = {display}")
        else:
            print(f"  ❌ {var:<25} = NOT SET")
    
    return os.getenv("DATABASE_URL") is not None

def check_database():
    """Check database connectivity"""
    print_header("🗄️ Database Connectivity Check")
    
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("  ⚠️  DATABASE_URL not set")
        print("  💡 Set this environment variable to enable database features")
        return False
    
    # Parse URL
    try:
        import urllib.parse
        parsed = urllib.parse.urlparse(database_url)
        print(f"  📍 Host: {parsed.hostname}")
        print(f"  📍 Port: {parsed.port}")
        print(f"  📍 Database: {parsed.path.lstrip('/')}")
        
        # Check if localhost
        if "localhost" in (parsed.hostname or "").lower():
            print(f"  ⚠️  WARNING: Database is localhost - will fail on cloud!")
            print(f"  💡 Use cloud database like Neon: https://console.neon.tech/")
            return False
    except Exception as e:
        print(f"  ❌ Failed to parse DATABASE_URL: {e}")
        return False
    
    # Try to connect
    try:
        from sqlalchemy import create_engine, text
        print("\n  🔗 Testing connection...")
        
        engine = create_engine(database_url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("  ✅ Database connection successful!")
        return True
    except Exception as e:
        print(f"  ❌ Connection failed: {str(e)}")
        print(f"\n  💡 Troubleshooting:")
        print(f"     1. Check DATABASE_URL is correct")
        print(f"     2. Verify database server is running")
        print(f"     3. Check firewall/network settings")
        print(f"     4. For Neon: Make sure sslmode=require is in URL")
        return False

def check_ml_model():
    """Check ML model"""
    print_header("🧠 ML Model Check")
    
    try:
        from backend.core.detector import PhishDetector
        detector = PhishDetector()
        
        # Test prediction
        result = detector.predict("https://example.com")
        print(f"  ✅ ML Model loaded successfully")
        print(f"  📊 Test prediction: {result.get('label')} (confidence: {result.get('confidence'):.2%})")
        return True
    except Exception as e:
        print(f"  ❌ ML Model check failed: {str(e)}")
        return False

def check_api():
    """Check API server"""
    print_header("🚀 API Server Check")
    
    print("  💡 Trying to connect to local API...")
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            print(f"  ✅ API is running on http://localhost:8000")
            print(f"  📊 Health: {response.json()}")
            return True
        else:
            print(f"  ⚠️  API returned {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"  ⚠️  Could not connect to http://localhost:8000")
        print(f"  💡 Start API with: uvicorn backend.api:app --reload --port 8000")
        return False
    except Exception as e:
        print(f"  ⚠️  Error: {str(e)}")
        return False

def main():
    """Run all checks"""
    print("\n🔍 PhishGuard Configuration Diagnostic")
    print("=====================================\n")
    
    results = {
        "Environment Variables": check_env_vars(),
        "Database": check_database(),
        "ML Model": check_ml_model(),
        "API Server": check_api(),
    }
    
    # Summary
    print_header("📋 Summary")
    for check, passed in results.items():
        status = "✅" if passed else "⚠️"
        print(f"  {status} {check}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n  🎉 All checks passed!")
    else:
        print("\n  ⚠️  Some checks failed - see messages above for fixes")
    
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    main()
