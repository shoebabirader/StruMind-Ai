#!/usr/bin/env python3
"""
Test script to verify backend setup
"""

import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all core modules can be imported"""
    try:
        from core.config import get_settings
        from core.exceptions import StrumindException
        from db.database import Base
        from api.v1.router import api_router
        from tasks.celery_app import celery_app
        print("✅ All core modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_config():
    """Test configuration loading"""
    try:
        from core.config import get_settings
        settings = get_settings()
        print(f"✅ Configuration loaded: {settings.APP_NAME}")
        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def test_fastapi_app():
    """Test FastAPI app creation"""
    try:
        from main import create_application
        app = create_application()
        print(f"✅ FastAPI app created: {app.title}")
        return True
    except Exception as e:
        print(f"❌ FastAPI app error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing StruMind Backend Setup...")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_config,
        test_fastapi_app,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Backend setup is working correctly!")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed. Please check the setup.")
        sys.exit(1)