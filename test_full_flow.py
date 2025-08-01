#!/usr/bin/env python3
"""Test with the exact same file processing flow as the bot"""

import asyncio
from file_processor import FileProcessor
from phone_validator import PhoneValidator

async def test_full_validation_flow():
    """Test the complete validation flow that mirrors what the bot does"""
    
    # Step 1: Process file like the bot does
    processor = FileProcessor()
    phones = processor._read_phones_from_file('test_phones.txt')
    
    print(f"Step 1 - File processing:")
    print(f"Extracted {len(phones)} phone numbers from file")
    
    # Step 2: Validate using async batch method like the bot does
    validator = PhoneValidator()
    
    # Process in batches like the handler
    batch_size = 50
    valid_count = 0
    all_results = []
    
    for i in range(0, len(phones), batch_size):
        batch = phones[i:i + batch_size]
        print(f"\nStep 2 - Processing batch {i//batch_size + 1}: {len(batch)} numbers")
        
        # This is the exact same call the handler makes
        batch_results = await validator.validate_batch_async(batch)
        
        # Count valid results like the handler does
        for result in batch_results:
            all_results.append(result)
            if result.is_valid:
                valid_count += 1
                print(f"  ✅ {result.number} -> VALID")
            else:
                print(f"  ❌ {result.number} -> INVALID ({result.error_message})")
    
    # Step 3: Show final results like the handler does
    total_count = len(phones)
    invalid_count = total_count - valid_count
    success_rate = (valid_count / total_count) * 100
    
    print(f"\nStep 3 - Final Results:")
    print(f"Total numbers: {total_count}")
    print(f"Valid: {valid_count}")
    print(f"Invalid: {invalid_count}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    # The problem should be visible now
    if success_rate == 100.0:
        print("\n⚠️  BUG DETECTED: 100% success rate is unrealistic!")
        return False
    else:
        print("\n✅ Validation logic working correctly")
        return True

if __name__ == "__main__":
    asyncio.run(test_full_validation_flow())