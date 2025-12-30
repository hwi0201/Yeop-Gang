#!/usr/bin/env python3
"""Simple import test to check for configuration errors."""

try:
    print("Testing imports...")
    from main import app
    print("✅ Main app imported successfully!")
    print(f"✅ App title: {app.title}")
    print("✅ All imports OK")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

