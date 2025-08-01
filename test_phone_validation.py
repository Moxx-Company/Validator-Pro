#!/usr/bin/env python3
"""Test phone validation accuracy"""

import asyncio
from phone_validator import PhoneValidator

async def test_phone_validation():
    validator = PhoneValidator()
    
    # Test with a realistic mix of valid and invalid numbers
    test_numbers = [
        # Valid numbers from various countries
        '+911234567890',    # India - should be valid
        '+442012345678',    # UK - should be valid  
        '+33123456789',     # France - should be valid
        '+491234567890',    # Germany - should be valid
        '+12125551234',     # US - should be valid
        
        # Invalid numbers that should fail
        '1234',             # Too short - should be invalid
        '999999999999',     # Invalid format - should be invalid
        'abcdefg',          # Not a number - should be invalid
        '000000000',        # Invalid - should be invalid
        '+1555123456789',   # Too many digits - should be invalid
        '+99912345678',     # Invalid country code - should be invalid
        '5555555555',       # US fake number - might be invalid
    ]
    
    print("Testing phone validation with mixed valid/invalid numbers:")
    print("=" * 60)
    
    results = await validator.validate_batch_async(test_numbers)
    
    valid_count = 0
    invalid_count = 0
    
    for i, result in enumerate(results):
        status = "✅ VALID" if result.is_valid else "❌ INVALID"
        error_msg = f" ({result.error_message})" if result.error_message else ""
        print(f"{test_numbers[i]:20} -> {status}{error_msg}")
        
        if result.is_valid:
            valid_count += 1
        else:
            invalid_count += 1
    
    print("=" * 60)
    print(f"Results: {valid_count} valid, {invalid_count} invalid out of {len(results)} total")
    success_rate = (valid_count / len(results)) * 100
    print(f"Success rate: {success_rate:.1f}%")
    
    # This should NOT be 100% - there are clearly invalid numbers in the test
    if success_rate == 100.0 and invalid_count == 0:
        print("⚠️  WARNING: 100% success rate indicates validation logic may be too lenient!")
        return False
    else:
        print("✅ Validation logic appears to be working correctly")
        return True

if __name__ == "__main__":
    asyncio.run(test_phone_validation())