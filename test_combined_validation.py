#!/usr/bin/env python3
"""
Test script for combined email and phone validation
"""

import asyncio
from phone_validator import PhoneValidator
from email_validator import EmailValidator

async def test_phone_validation():
    """Test phone number validation"""
    print("=== Testing Phone Number Validation ===")
    
    validator = PhoneValidator()
    
    test_numbers = [
        "+1 555-123-4567",  # US format
        "+44 20 7946 0958",  # UK format
        "+91 98765 43210",   # India format
        "(555) 123-4567",    # US local
        "invalid-number",    # Invalid
        "+1234567890123456", # Too long
        "123",               # Too short
    ]
    
    results = await validator.validate_batch_async(test_numbers)
    
    for result in results:
        if result.is_valid:
            print(f"✅ {result.number}")
            print(f"   International: {result.formatted_international}")
            print(f"   Country: {result.country_name} ({result.country_code})")
            print(f"   Type: {result.number_type}")
            if result.carrier_name:
                print(f"   Carrier: {result.carrier_name}")
        else:
            print(f"❌ {result.number}: {result.error_message}")
        print()

async def test_email_validation():
    """Test email validation"""
    print("\n=== Testing Email Validation ===")
    
    validator = EmailValidator()
    
    test_emails = [
        "valid@gmail.com",
        "test@example.com",
        "invalid.email",
        "user@nonexistent-domain-xyz.com",
        "admin@google.com"
    ]
    
    results = await validator.validate_batch_async(test_emails, batch_size=5)
    
    for result in results:
        if result.is_valid:
            print(f"✅ {result.email}")
            print(f"   Domain: {result.domain}")
            print(f"   MX Records: {result.mx_exists}")
        else:
            print(f"❌ {result.email}: {result.error_message}")
        print()

async def test_extraction():
    """Test phone number extraction from text"""
    print("\n=== Testing Phone Number Extraction ===")
    
    validator = PhoneValidator()
    
    text = """
    Contact us at:
    - US Office: +1 (555) 123-4567
    - UK Office: +44 20 7946 0958
    - India Office: +91 98765 43210
    - Sales: 555-987-6543
    - Support: (800) 555-1234
    
    Email: support@example.com
    """
    
    numbers = validator.extract_phone_numbers(text)
    print(f"Found {len(numbers)} phone numbers:")
    for num in numbers:
        print(f"  - {num}")

async def main():
    """Run all tests"""
    await test_phone_validation()
    await test_email_validation()
    await test_extraction()

if __name__ == "__main__":
    asyncio.run(main())