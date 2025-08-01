#!/usr/bin/env python3
"""
Test script for unified trial system
"""

from database import SessionLocal
from models import User

def test_unified_trial():
    """Test the unified trial system"""
    print("=== Testing Unified Trial System ===")
    
    with SessionLocal() as db:
        # Create a test user
        test_user = User(
            telegram_id="test123",
            username="testuser",
            first_name="Test",
            last_name="User"
        )
        
        print(f"Initial state:")
        print(f"  Email trials used: {test_user.trial_emails_used}")
        print(f"  Phone trials used: {test_user.trial_phones_used}")
        print(f"  Total remaining: {test_user.get_trial_remaining()}")
        
        # Test email validation
        can_validate_emails = test_user.can_validate('email', 100)
        print(f"\nCan validate 100 emails: {can_validate_emails}")
        
        # Use some email trials
        test_user.use_trial_validations('email', 1000)
        print(f"\nAfter using 1000 email validations:")
        print(f"  Email trials used: {test_user.trial_emails_used}")
        print(f"  Phone trials used: {test_user.trial_phones_used}")
        print(f"  Total remaining: {test_user.get_trial_remaining()}")
        
        # Test phone validation
        can_validate_phones = test_user.can_validate('phone', 500)
        print(f"\nCan validate 500 phones: {can_validate_phones}")
        
        # Use some phone trials
        test_user.use_trial_validations('phone', 2000)
        print(f"\nAfter using 2000 phone validations:")
        print(f"  Email trials used: {test_user.trial_emails_used}")
        print(f"  Phone trials used: {test_user.trial_phones_used}")
        print(f"  Total remaining: {test_user.get_trial_remaining()}")
        
        # Test exceeding limit
        can_validate_more = test_user.can_validate('email', 3000)
        print(f"\nCan validate 3000 more emails: {can_validate_more}")
        
        # Test individual validation type methods
        can_validate_emails_old = test_user.can_validate_emails(1000)
        can_validate_phones_old = test_user.can_validate_phones(1000)
        print(f"\nUsing old methods:")
        print(f"  Can validate 1000 emails: {can_validate_emails_old}")
        print(f"  Can validate 1000 phones: {can_validate_phones_old}")

if __name__ == "__main__":
    test_unified_trial()