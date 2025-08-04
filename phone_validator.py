"""
Phone number validation module using Google's libphonenumber
"""
import phonenumbers
from phonenumbers import geocoder, carrier, timezone
from phonenumbers.phonenumberutil import NumberParseException
import logging
import signal
from typing import Dict, List, Optional, Tuple
import asyncio
import concurrent.futures
from dataclasses import dataclass
from config import DEFAULT_PHONE_REGION, PHONE_VALIDATION_TIMEOUT

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
    timezones: Optional[List[str]] = None
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
    
    def validate_single(self, phone_number: str, default_region: Optional[str] = None) -> PhoneValidationResult:
        """Validate a single phone number with timeout protection"""
        import threading
        import time
        
        # Cross-platform timeout implementation using threading
        result_container = {'result': None, 'completed': False}
        
        def validation_worker():
            try:
                result_container['result'] = self._validate_phone_internal(phone_number, default_region)
                result_container['completed'] = True
            except Exception as e:
                result_container['result'] = PhoneValidationResult(
                    number=phone_number,
                    is_valid=False,
                    error_message=f"Validation error: {str(e)}"
                )
                result_container['completed'] = True
        
        # Start validation in a separate thread
        worker_thread = threading.Thread(target=validation_worker, daemon=True)
        worker_thread.start()
        
        # Wait for completion with timeout
        worker_thread.join(timeout=PHONE_VALIDATION_TIMEOUT)
        
        if result_container['completed']:
            return result_container['result']
        else:
            # Timeout occurred
            return PhoneValidationResult(
                number=phone_number,
                is_valid=False,
                error_message="Phone validation timed out"
            )
    
    def _validate_phone_internal(self, phone_number: str, default_region: Optional[str] = None) -> PhoneValidationResult:
        """Internal phone validation method"""
        
        # Clean the input first
        phone_number = phone_number.strip()
        if not phone_number:
            return PhoneValidationResult(
                number=phone_number,
                is_valid=False,
                error_message="Empty phone number"
            )
        
        parsing_errors = []  # Initialize at function start to ensure it's always defined
        try:
            parsed = None
            
            # Try parsing with international format first (has + prefix)
            if phone_number.startswith('+'):
                try:
                    parsed = phonenumbers.parse(phone_number, None)
                except NumberParseException as e:
                    parsing_errors.append(f"International format: {str(e)}")
            
            # If we don't have a parsed number yet, try with specified region
            if not parsed and default_region:
                try:
                    parsed = phonenumbers.parse(phone_number, default_region)
                except NumberParseException as e:
                    parsing_errors.append(f"Region {default_region}: {str(e)}")
            
            # If still no success, try intelligent region detection
            if not parsed:
                parsed = self._try_parse_with_common_regions(phone_number, parsing_errors)
            
            # If we still couldn't parse the number, return error
            if not parsed:
                error_msg = "Could not parse phone number for any region"
                if parsing_errors:
                    error_msg += f". Tried: {'; '.join(parsing_errors[:5])}"
                return PhoneValidationResult(
                    number=phone_number,
                    is_valid=False,
                    error_message=error_msg
                )
            
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
            # If all parsing attempts failed, provide helpful error message
            try:
                if parsing_errors:
                    error_msg = f"Could not parse phone number. Tried: {'; '.join(parsing_errors[:3])}"
                else:
                    error_msg = f"Cannot parse number: {str(e)}"
            except NameError:
                # parsing_errors not defined - fallback error message
                error_msg = f"Cannot parse number: {str(e)}"
            
            return PhoneValidationResult(
                number=phone_number,
                is_valid=False,
                error_message=error_msg
            )
        except Exception as e:
            logger.error(f"Error validating phone {phone_number}: {e}")
            return PhoneValidationResult(
                number=phone_number,
                is_valid=False,
                error_message=f"Validation error: {str(e)}"
            )
    
    def _try_parse_with_common_regions(self, phone_number: str, parsing_errors: list) -> Optional[phonenumbers.PhoneNumber]:
        """
        Try parsing phone number against common regions when no country code is provided.
        Uses intelligent region detection based on number patterns and length.
        """
        # Define regions to try in order of global usage and number pattern likelihood
        common_regions = [
            'US',    # North America (1)
            'GB',    # United Kingdom (44)
            'DE',    # Germany (49)
            'FR',    # France (33)
            'IN',    # India (91)
            'CN',    # China (86)
            'BR',    # Brazil (55)
            'IT',    # Italy (39)
            'ES',    # Spain (34)
            'RU',    # Russia (7)
            'JP',    # Japan (81)
            'KR',    # South Korea (82)
            'AU',    # Australia (61)
            'CA',    # Canada (1)
            'MX',    # Mexico (52)
            'AR',    # Argentina (54)
            'TR',    # Turkey (90)
            'EG',    # Egypt (20)
            'ZA',    # South Africa (27)
            'NG',    # Nigeria (234)
            'PK',    # Pakistan (92)
            'BD',    # Bangladesh (880)
            'ID',    # Indonesia (62)
            'TH',    # Thailand (66)
            'VN',    # Vietnam (84)
            'PH',    # Philippines (63)
            'MY',    # Malaysia (60)
            'SG',    # Singapore (65)
            'AE',    # UAE (971)
            'SA',    # Saudi Arabia (966)
            'IL',    # Israel (972)
        ]
        
        # Try to detect likely region based on number characteristics
        likely_regions = self._detect_likely_regions(phone_number)
        
        # Combine likely regions with common regions, prioritizing likely ones
        regions_to_try = likely_regions + [r for r in common_regions if r not in likely_regions]
        
        for region in regions_to_try:
            try:
                parsed = phonenumbers.parse(phone_number, region)
                # Only return if the parsed number is actually valid
                if phonenumbers.is_valid_number(parsed):
                    return parsed
            except NumberParseException as e:
                parsing_errors.append(f"Region {region}: {str(e)}")
                continue
        
        return None
    
    def _detect_likely_regions(self, phone_number: str) -> list:
        """
        Detect likely regions based on phone number patterns and characteristics.
        """
        likely_regions = []
        
        # Remove all non-digits for analysis
        digits_only = ''.join(filter(str.isdigit, phone_number))
        
        # Region detection based on number length and starting digits
        if len(digits_only) == 10:
            # 10-digit numbers are common in US, Canada, some others
            likely_regions.extend(['US', 'CA'])
        elif len(digits_only) == 11:
            # 11-digit numbers common in many countries
            if digits_only.startswith('1'):
                likely_regions.extend(['US', 'CA'])  # NANP countries
            elif digits_only.startswith('7'):
                likely_regions.append('RU')  # Russia/Kazakhstan
            elif digits_only.startswith('44'):
                likely_regions.append('GB')  # UK
            elif digits_only.startswith('49'):
                likely_regions.append('DE')  # Germany
            elif digits_only.startswith('33'):
                likely_regions.append('FR')  # France
            elif digits_only.startswith('39'):
                likely_regions.append('IT')  # Italy
            elif digits_only.startswith('34'):
                likely_regions.append('ES')  # Spain
        elif len(digits_only) == 12:
            # 12-digit numbers
            if digits_only.startswith('91'):
                likely_regions.append('IN')  # India
            elif digits_only.startswith('86'):
                likely_regions.append('CN')  # China
            elif digits_only.startswith('55'):
                likely_regions.append('BR')  # Brazil
        elif len(digits_only) == 13:
            # 13-digit numbers
            if digits_only.startswith('234'):
                likely_regions.append('NG')  # Nigeria
            elif digits_only.startswith('880'):
                likely_regions.append('BD')  # Bangladesh
        
        # Pattern-based detection for common formats
        if phone_number.replace(' ', '').replace('-', '').replace('(', '').replace(')', ''):
            # US/Canada format detection (XXX) XXX-XXXX or XXX-XXX-XXXX
            if any(pattern in phone_number for pattern in ['(', ')', '-']) and len(digits_only) == 10:
                likely_regions.extend(['US', 'CA'])
        
        return likely_regions
    
    async def validate_batch_async(self, phone_numbers: List[str], default_region: Optional[str] = None) -> List[PhoneValidationResult]:
        """Validate a batch of phone numbers asynchronously with timeout protection"""
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
        
        # Wait for all validations to complete with timeout protection
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), 
                timeout=120.0  # 2 minute timeout for batch
            )
            
            # Handle any exceptions in results
            final_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    # Create error result for failed validation
                    error_result = PhoneValidationResult(
                        number=phone_numbers[i],
                        is_valid=False,
                        error_message=f"Validation timeout or error: {str(result)}"
                    )
                    final_results.append(error_result)
                else:
                    final_results.append(result)
            
            return final_results
            
        except asyncio.TimeoutError:
            # If entire batch times out, return error results for all
            logger.error(f"Phone validation batch timed out for {len(phone_numbers)} numbers")
            return [
                PhoneValidationResult(
                    number=number,
                    is_valid=False,
                    error_message="Batch validation timeout - number took too long to process"
                ) for number in phone_numbers
            ]
    
    def extract_phone_numbers(self, text: str, default_region: Optional[str] = None) -> List[str]:
        """Extract phone numbers from text"""
        phone_numbers = []
        
        # Try to find numbers with phonenumbers library
        region = default_region or "US"
        for match in phonenumbers.PhoneNumberMatcher(text, region):
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