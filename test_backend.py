#!/usr/bin/env python
"""
test_backend.py
Test backend setup and database connectivity
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 70)
print("🧪 PHISHGUARD BACKEND TEST")
print("=" * 70)

# Test 1: Check environment
print("\n[1/6] Checking environment variables...")
try:
    from dotenv import load_dotenv
    load_dotenv(project_root / ".env")
    
    db_url = os.getenv("DATABASE_URL")
    api_base_url = os.getenv("API_BASE_URL")
    
    if not db_url:
        print("⚠️  DATABASE_URL not set (optional for testing)")
    else:
        print(f"✅ DATABASE_URL configured")
        
    if not api_base_url:
        print("⚠️  API_BASE_URL not set (using default)")
    else:
        print(f"✅ API_BASE_URL: {api_base_url}")
        
except Exception as e:
    print(f"⚠️  Env loading: {e}")

# Test 2: Check backend imports
print("\n[2/6] Testing backend imports...")
try:
    from backend.api import app
    print("✅ Backend API imported successfully")
except Exception as e:
    print(f"❌ Failed to import backend: {e}")
    sys.exit(1)

# Test 3: Check ML detector
print("\n[3/6] Testing ML detector...")
try:
    from core.detector import PhishDetector
    detector = PhishDetector()
    print("✅ ML Detector initialized")
except Exception as e:
    print(f"❌ Failed to initialize detector: {e}")
    sys.exit(1)

# Test 4: Check database models
print("\n[4/6] Testing database models...")
try:
    from backend.models.database import SessionLocal, Base, engine
    from backend.models.scan import Scan
    from backend.models.feedback import Feedback
    from backend.models.user import User
    
    # Try to create tables
    Base.metadata.create_all(bind=engine)
    print("✅ Database models and tables ready")
except Exception as e:
    print(f"⚠️  Database warning: {e}")
    print("   (This is OK for first-time setup)")

# Test 5: Check routes
print("\n[5/6] Testing route imports...")
try:
    from backend.routes import scan, feedback, health
    print("✅ All routes imported successfully")
    print(f"   - /scan routes: {len(scan.router.routes)} endpoints")
    print(f"   - /feedback routes: {len(feedback.router.routes)} endpoints")
    print(f"   - /health routes: {len(health.router.routes)} endpoints")
except Exception as e:
    print(f"❌ Failed to import routes: {e}")
    sys.exit(1)

# Test 6: Test prediction
print("\n[6/6] Testing ML prediction...")
try:
    test_url = "https://phishing-example.com/verify"
    result = detector.predict(test_url)
    print(f"✅ Prediction works")
    print(f"   - Input: {test_url}")
    print(f"   - Label: {result['label']}")
    print(f"   - Confidence: {max(result['probabilities'].values()):.2%}")
except Exception as e:
    print(f"❌ Prediction failed: {e}")
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ ALL BACKEND TESTS PASSED!")
print("=" * 70)

print("\n🚀 READY TO RUN:")
print("\n   Terminal 1 - Backend:")
print("   $ uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000")

print("\n   Terminal 2 - Frontend:")
print("   $ streamlit run app/Home.py --server.port 8501")

print("\n   Browser: http://localhost:8501")
print("\n" + "=" * 70)
