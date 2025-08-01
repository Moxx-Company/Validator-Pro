"""
Phone number validation module using Google's libphonenumber
"""
import phonenumbers
from phonenumbers import geocoder, carrier, timezone
from phonenumbers.phonenumberutil import NumberParseException
import logging
from typing import Dict, List, Optional, Tuple
import asyncio
import concurrent.futures
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PhoneValidationResult:
    """Phone validation result container"""
    number: str
    is_valid: bool
    formatted_international: str = ""
    formatted_national: str = ""
    country_code: str = ""
    country_name: str = ""
    carrier_name: str = ""
    number_type: str = ""
    timezones: List[str] = None
    error_message: str = ""
    
    def __post_init__(self):
        if self.timezones is None:
            self.timezones = []

class PhoneValidator:
    """Phone number validator using Google's libphonenumber"""
    
    def __init__(self):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=20)
        
    def get_number_type(self, number_type: int) -> str:
        """Convert number type to human readable format"""
        types = {
            0: "Fixed Line",
            1: "Mobile",
            2: "Fixed Line or Mobile",
            3: "Toll Free",
            4: "Premium Rate",
            5: "Shared Cost",
            6: "VoIP",
            7: "Personal Number",
            8: "Pager",
            9: "UAN",
            10: "Voicemail",
            -1: "Unknown"
        }
        return types.get(number_type, "Unknown")
    
    def validate_single(self, phone_number: str, default_region: str = None) -> PhoneValidationResult:
        """Validate a single phone number"""
        try:
            # Try to parse the number
            if phone_number.startswith('+'):
                # International format
                parsed = phonenumbers.parse(phone_number, None)
            else:
                # Try with default region or common regions
                regions_to_try = [default_region] if default_region else ['US', 'GB', 'IN', 'CA', 'AU']
                parsed = None
                
                for region in regions_to_try:
                    try:
                        temp_parsed = phonenumbers.parse(phone_number, region)
                        if phonenumbers.is_valid_number(temp_parsed):
                            parsed = temp_parsed
                            break
                    except:
                        continue
                
                if not parsed:
                    # Try as international without +
                    try:
                        parsed = phonenumbers.parse(f"+{phone_number}", None)
                    except:
                        parsed = phonenumbers.parse(phone_number, 'US')  # Default fallback
            
            # Check if valid
            is_valid = phonenumbers.is_valid_number(parsed)
            
            if not is_valid:
                return PhoneValidationResult(
                    number=phone_number,
                    is_valid=False,
                    error_message="Invalid phone number format or number doesn't exist"
                )
            
            # Get formatted versions
            international = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
            national = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
            
            # Get country info
            country_code = f"+{parsed.country_code}"
            country_name = geocoder.country_name_for_number(parsed, "en")
            
            # Get carrier info (if available)
            carrier_name = carrier.name_for_number(parsed, "en") or "Unknown"
            
            # Get number type
            number_type = phonenumbers.number_type(parsed)
            type_string = self.get_number_type(number_type)
            
            # Get timezone info
            tz_list = timezone.time_zones_for_number(parsed)
            
            return PhoneValidationResult(
                number=phone_number,
                is_valid=True,
                formatted_international=international,
                formatted_national=national,
                country_code=country_code,
                country_name=country_name,
                carrier_name=carrier_name,
                number_type=type_string,
                timezones=list(tz_list),
                error_message=""
            )
            
        except NumberParseException as e:
            return PhoneValidationResult(
                number=phone_number,
                is_valid=False,
                error_message=f"Cannot parse number: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error validating phone {phone_number}: {e}")
            return PhoneValidationResult(
                number=phone_number,
                is_valid=False,
                error_message=f"Validation error: {str(e)}"
            )
    
    async def validate_batch_async(self, phone_numbers: List[str], default_region: str = None) -> List[PhoneValidationResult]:
        """Validate a batch of phone numbers asynchronously"""
        loop = asyncio.get_running_loop()
        
        # Create tasks for concurrent validation
        tasks = []
        for number in phone_numbers:
            task = loop.run_in_executor(
                self.executor,
                self.validate_single,
                number,
                default_region
            )
            tasks.append(task)
        
        # Wait for all validations to complete
        results = await asyncio.gather(*tasks)
        return results
    
    def extract_phone_numbers(self, text: str, default_region: str = None) -> List[str]:
        """Extract phone numbers from text"""
        phone_numbers = []
        
        # Try to find numbers with phonenumbers library
        for match in phonenumbers.PhoneNumberMatcher(text, default_region or "US"):
            phone_numbers.append(phonenumbers.format_number(match.number, phonenumbers.PhoneNumberFormat.E164))
        
        # Also try some common patterns if no matches found
        if not phone_numbers:
            import re
            # Common phone patterns
            patterns = [
                r'\+?\d{1,4}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{1,4}[\s.-]?\d{1,4}[\s.-]?\d{1,9}',
                r'\(\d{3}\)\s*\d{3}[\s.-]?\d{4}',  # US format (XXX) XXX-XXXX
                r'\d{3}[\s.-]\d{3}[\s.-]\d{4}',    # US format XXX-XXX-XXXX
                r'\+\d{1,3}\s?\d{4,14}',           # International format
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text)
                phone_numbers.extend(matches)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_numbers = []
        for num in phone_numbers:
            cleaned = ''.join(filter(str.isdigit, num))
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                unique_numbers.append(num)
        
        return unique_numbers