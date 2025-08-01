#!/usr/bin/env python3
"""
Simple test bot to verify telegram imports work
"""

try:
    print("Testing telegram imports...")
    
    # Test import methods
    import telegram
    print(f"✓ telegram module imported: {type(telegram)}")
    
    # Check what's available in the telegram module
    print("Available in telegram module:", dir(telegram))
    
    # Try alternative imports
    try:
        from telegram import Bot, Update
        print("✓ Direct imports successful")
    except ImportError as e:
        print(f"✗ Direct imports failed: {e}")
        
        # Try accessing through module
        try:
            Bot = telegram.Bot
            Update = telegram.Update
            print("✓ Module access successful")
        except AttributeError as e:
            print(f"✗ Module access failed: {e}")
    
    # Test if telegram.ext is available
    try:
        from telegram.ext import Application
        print("✓ telegram.ext imports successful")
    except ImportError as e:
        print(f"✗ telegram.ext imports failed: {e}")
        
    print("Testing completed")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()