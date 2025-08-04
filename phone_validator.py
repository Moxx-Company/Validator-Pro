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
        # Comprehensive regions covering 100+ countries/territories worldwide
        common_regions = [
            # Major Population Centers (Tier 1)
            'US',    # United States (1)
            'CN',    # China (86)
            'IN',    # India (91)
            'ID',    # Indonesia (62)
            'PK',    # Pakistan (92)
            'BR',    # Brazil (55)
            'NG',    # Nigeria (234)
            'BD',    # Bangladesh (880)
            'RU',    # Russia (7)
            'MX',    # Mexico (52)
            'JP',    # Japan (81)
            'PH',    # Philippines (63)
            'ET',    # Ethiopia (251)
            'VN',    # Vietnam (84)
            'EG',    # Egypt (20)
            'TR',    # Turkey (90)
            'IR',    # Iran (98)
            'DE',    # Germany (49)
            'TH',    # Thailand (66)
            'GB',    # United Kingdom (44)
            'FR',    # France (33)
            'IT',    # Italy (39)
            'ZA',    # South Africa (27)
            'TZ',    # Tanzania (255)
            'MM',    # Myanmar (95)
            'KR',    # South Korea (82)
            'CO',    # Colombia (57)
            'KE',    # Kenya (254)
            'ES',    # Spain (34)
            'UG',    # Uganda (256)
            'AR',    # Argentina (54)
            'DZ',    # Algeria (213)
            'SD',    # Sudan (249)
            'UA',    # Ukraine (380)
            'IQ',    # Iraq (964)
            'PL',    # Poland (48)
            'CA',    # Canada (1)
            'AF',    # Afghanistan (93)
            'MA',    # Morocco (212)
            'SA',    # Saudi Arabia (966)
            'UZ',    # Uzbekistan (998)
            'PE',    # Peru (51)
            'MY',    # Malaysia (60)
            'AO',    # Angola (244)
            'MZ',    # Mozambique (258)
            'GH',    # Ghana (233)
            'YE',    # Yemen (967)
            'NP',    # Nepal (977)
            'VE',    # Venezuela (58)
            'MG',    # Madagascar (261)
            'CM',    # Cameroon (237)
            'KP',    # North Korea (850)
            'CI',    # Ivory Coast (225)
            'AU',    # Australia (61)
            'NE',    # Niger (227)
            'LK',    # Sri Lanka (94)
            'BF',    # Burkina Faso (226)
            'ML',    # Mali (223)
            'RO',    # Romania (40)
            'MW',    # Malawi (265)
            'CL',    # Chile (56)
            'KZ',    # Kazakhstan (7)
            'ZM',    # Zambia (260)
            'GT',    # Guatemala (502)
            'EC',    # Ecuador (593)
            'SN',    # Senegal (221)
            'TD',    # Chad (235)
            'SO',    # Somalia (252)
            'ZW',    # Zimbabwe (263)
            'KH',    # Cambodia (855)
            'SY',    # Syria (963)
            'RW',    # Rwanda (250)
            'BO',    # Bolivia (591)
            'TN',    # Tunisia (216)
            'BE',    # Belgium (32)
            'BI',    # Burundi (257)
            'CU',    # Cuba (53)
            'TN',    # Tunisia (216)
            'GN',    # Guinea (224)
            'BJ',    # Benin (229)
            'HT',    # Haiti (509)
            'CZ',    # Czech Republic (420)
            'GR',    # Greece (30)
            'JO',    # Jordan (962)
            'PT',    # Portugal (351)
            'SE',    # Sweden (46)
            'AZ',    # Azerbaijan (994)
            'HU',    # Hungary (36)
            'BY',    # Belarus (375)
            'TJ',    # Tajikistan (992)
            'AT',    # Austria (43)
            'IL',    # Israel (972)
            'CH',    # Switzerland (41)
            'TG',    # Togo (228)
            'SL',    # Sierra Leone (232)
            'LY',    # Libya (218)
            'LR',    # Liberia (231)
            'NI',    # Nicaragua (505)
            'PA',    # Panama (507)
            'CR',    # Costa Rica (506)
            'IE',    # Ireland (353)
            'GE',    # Georgia (995)
            'HR',    # Croatia (385)
            'BA',    # Bosnia and Herzegovina (387)
            'BG',    # Bulgaria (359)
            'MK',    # North Macedonia (389)
            'LT',    # Lithuania (370)
            'SI',    # Slovenia (386)
            'LV',    # Latvia (371)
            'EE',    # Estonia (372)
            'MU',    # Mauritius (230)
            'CY',    # Cyprus (357)
            'FJ',    # Fiji (679)
            'RE',    # Reunion (262)
            'SG',    # Singapore (65)
            'NZ',    # New Zealand (64)
            'NO',    # Norway (47)
            'FI',    # Finland (358)
            'DK',    # Denmark (45)
            'SK',    # Slovakia (421)
            'AE',    # UAE (971)
            'QA',    # Qatar (974)
            'BH',    # Bahrain (973)
            'KW',    # Kuwait (965)
            'OM',    # Oman (968)
            'LB',    # Lebanon (961)
            'MN',    # Mongolia (976)
            'LA',    # Laos (856)
            'BT',    # Bhutan (975)
            'MD',    # Moldova (373)
            'RS',    # Serbia (381)
            'ME',    # Montenegro (382)
            'AL',    # Albania (355)
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
        
        # Enhanced region detection based on number length and starting digits
        if len(digits_only) == 10:
            # 10-digit numbers common in several countries
            likely_regions.extend(['US', 'CA', 'IN', 'AU', 'NZ'])
        elif len(digits_only) == 11:
            # 11-digit numbers - comprehensive country code detection
            if digits_only.startswith('1'):
                likely_regions.extend(['US', 'CA'])  # NANP countries
            elif digits_only.startswith('7'):
                likely_regions.extend(['RU', 'KZ'])  # Russia/Kazakhstan
            elif digits_only.startswith('20'):
                likely_regions.append('EG')  # Egypt
            elif digits_only.startswith('27'):
                likely_regions.append('ZA')  # South Africa
            elif digits_only.startswith('30'):
                likely_regions.append('GR')  # Greece
            elif digits_only.startswith('31'):
                likely_regions.append('NL')  # Netherlands
            elif digits_only.startswith('32'):
                likely_regions.append('BE')  # Belgium
            elif digits_only.startswith('33'):
                likely_regions.append('FR')  # France
            elif digits_only.startswith('34'):
                likely_regions.append('ES')  # Spain
            elif digits_only.startswith('36'):
                likely_regions.append('HU')  # Hungary
            elif digits_only.startswith('39'):
                likely_regions.append('IT')  # Italy
            elif digits_only.startswith('40'):
                likely_regions.append('RO')  # Romania
            elif digits_only.startswith('41'):
                likely_regions.append('CH')  # Switzerland
            elif digits_only.startswith('43'):
                likely_regions.append('AT')  # Austria
            elif digits_only.startswith('44'):
                likely_regions.append('GB')  # UK
            elif digits_only.startswith('45'):
                likely_regions.append('DK')  # Denmark
            elif digits_only.startswith('46'):
                likely_regions.append('SE')  # Sweden
            elif digits_only.startswith('47'):
                likely_regions.append('NO')  # Norway
            elif digits_only.startswith('48'):
                likely_regions.append('PL')  # Poland
            elif digits_only.startswith('49'):
                likely_regions.append('DE')  # Germany
            elif digits_only.startswith('51'):
                likely_regions.append('PE')  # Peru
            elif digits_only.startswith('52'):
                likely_regions.append('MX')  # Mexico
            elif digits_only.startswith('53'):
                likely_regions.append('CU')  # Cuba
            elif digits_only.startswith('54'):
                likely_regions.append('AR')  # Argentina
            elif digits_only.startswith('55'):
                likely_regions.append('BR')  # Brazil
            elif digits_only.startswith('56'):
                likely_regions.append('CL')  # Chile
            elif digits_only.startswith('57'):
                likely_regions.append('CO')  # Colombia
            elif digits_only.startswith('58'):
                likely_regions.append('VE')  # Venezuela
            elif digits_only.startswith('60'):
                likely_regions.append('MY')  # Malaysia
            elif digits_only.startswith('61'):
                likely_regions.append('AU')  # Australia
            elif digits_only.startswith('62'):
                likely_regions.append('ID')  # Indonesia
            elif digits_only.startswith('63'):
                likely_regions.append('PH')  # Philippines
            elif digits_only.startswith('64'):
                likely_regions.append('NZ')  # New Zealand
            elif digits_only.startswith('65'):
                likely_regions.append('SG')  # Singapore
            elif digits_only.startswith('66'):
                likely_regions.append('TH')  # Thailand
            elif digits_only.startswith('81'):
                likely_regions.append('JP')  # Japan
            elif digits_only.startswith('82'):
                likely_regions.append('KR')  # South Korea
            elif digits_only.startswith('84'):
                likely_regions.append('VN')  # Vietnam
            elif digits_only.startswith('86'):
                likely_regions.append('CN')  # China
            elif digits_only.startswith('90'):
                likely_regions.append('TR')  # Turkey
            elif digits_only.startswith('91'):
                likely_regions.append('IN')  # India
            elif digits_only.startswith('92'):
                likely_regions.append('PK')  # Pakistan
            elif digits_only.startswith('93'):
                likely_regions.append('AF')  # Afghanistan
            elif digits_only.startswith('94'):
                likely_regions.append('LK')  # Sri Lanka
            elif digits_only.startswith('95'):
                likely_regions.append('MM')  # Myanmar
            elif digits_only.startswith('98'):
                likely_regions.append('IR')  # Iran
        elif len(digits_only) == 12:
            # 12-digit numbers - country code + area + number
            if digits_only.startswith('212'):
                likely_regions.append('MA')  # Morocco
            elif digits_only.startswith('213'):
                likely_regions.append('DZ')  # Algeria
            elif digits_only.startswith('216'):
                likely_regions.append('TN')  # Tunisia
            elif digits_only.startswith('218'):
                likely_regions.append('LY')  # Libya
            elif digits_only.startswith('220'):
                likely_regions.append('GM')  # Gambia
            elif digits_only.startswith('221'):
                likely_regions.append('SN')  # Senegal
            elif digits_only.startswith('222'):
                likely_regions.append('MR')  # Mauritania
            elif digits_only.startswith('223'):
                likely_regions.append('ML')  # Mali
            elif digits_only.startswith('224'):
                likely_regions.append('GN')  # Guinea
            elif digits_only.startswith('225'):
                likely_regions.append('CI')  # Ivory Coast
            elif digits_only.startswith('226'):
                likely_regions.append('BF')  # Burkina Faso
            elif digits_only.startswith('227'):
                likely_regions.append('NE')  # Niger
            elif digits_only.startswith('228'):
                likely_regions.append('TG')  # Togo
            elif digits_only.startswith('229'):
                likely_regions.append('BJ')  # Benin
            elif digits_only.startswith('230'):
                likely_regions.append('MU')  # Mauritius
            elif digits_only.startswith('231'):
                likely_regions.append('LR')  # Liberia
            elif digits_only.startswith('232'):
                likely_regions.append('SL')  # Sierra Leone
            elif digits_only.startswith('233'):
                likely_regions.append('GH')  # Ghana
            elif digits_only.startswith('235'):
                likely_regions.append('TD')  # Chad
            elif digits_only.startswith('236'):
                likely_regions.append('CF')  # Central African Republic
            elif digits_only.startswith('237'):
                likely_regions.append('CM')  # Cameroon
            elif digits_only.startswith('238'):
                likely_regions.append('CV')  # Cape Verde
            elif digits_only.startswith('239'):
                likely_regions.append('ST')  # São Tomé and Príncipe
            elif digits_only.startswith('240'):
                likely_regions.append('GQ')  # Equatorial Guinea
            elif digits_only.startswith('241'):
                likely_regions.append('GA')  # Gabon
            elif digits_only.startswith('242'):
                likely_regions.append('CG')  # Republic of the Congo
            elif digits_only.startswith('243'):
                likely_regions.append('CD')  # Democratic Republic of the Congo
            elif digits_only.startswith('244'):
                likely_regions.append('AO')  # Angola
            elif digits_only.startswith('245'):
                likely_regions.append('GW')  # Guinea-Bissau
            elif digits_only.startswith('246'):
                likely_regions.append('IO')  # British Indian Ocean Territory
            elif digits_only.startswith('248'):
                likely_regions.append('SC')  # Seychelles
            elif digits_only.startswith('249'):
                likely_regions.append('SD')  # Sudan
            elif digits_only.startswith('250'):
                likely_regions.append('RW')  # Rwanda
            elif digits_only.startswith('251'):
                likely_regions.append('ET')  # Ethiopia
            elif digits_only.startswith('252'):
                likely_regions.append('SO')  # Somalia
            elif digits_only.startswith('253'):
                likely_regions.append('DJ')  # Djibouti
            elif digits_only.startswith('254'):
                likely_regions.append('KE')  # Kenya
            elif digits_only.startswith('255'):
                likely_regions.append('TZ')  # Tanzania
            elif digits_only.startswith('256'):
                likely_regions.append('UG')  # Uganda
            elif digits_only.startswith('257'):
                likely_regions.append('BI')  # Burundi
            elif digits_only.startswith('258'):
                likely_regions.append('MZ')  # Mozambique
            elif digits_only.startswith('260'):
                likely_regions.append('ZM')  # Zambia
            elif digits_only.startswith('261'):
                likely_regions.append('MG')  # Madagascar
            elif digits_only.startswith('262'):
                likely_regions.append('RE')  # Reunion
            elif digits_only.startswith('263'):
                likely_regions.append('ZW')  # Zimbabwe
            elif digits_only.startswith('264'):
                likely_regions.append('NA')  # Namibia
            elif digits_only.startswith('265'):
                likely_regions.append('MW')  # Malawi
            elif digits_only.startswith('266'):
                likely_regions.append('LS')  # Lesotho
            elif digits_only.startswith('267'):
                likely_regions.append('BW')  # Botswana
            elif digits_only.startswith('268'):
                likely_regions.append('SZ')  # Eswatini
            elif digits_only.startswith('269'):
                likely_regions.append('KM')  # Comoros
            elif digits_only.startswith('290'):
                likely_regions.append('SH')  # Saint Helena
            elif digits_only.startswith('291'):
                likely_regions.append('ER')  # Eritrea
            elif digits_only.startswith('297'):
                likely_regions.append('AW')  # Aruba
            elif digits_only.startswith('298'):
                likely_regions.append('FO')  # Faroe Islands
            elif digits_only.startswith('299'):
                likely_regions.append('GL')  # Greenland
            elif digits_only.startswith('350'):
                likely_regions.append('GI')  # Gibraltar
            elif digits_only.startswith('351'):
                likely_regions.append('PT')  # Portugal
            elif digits_only.startswith('352'):
                likely_regions.append('LU')  # Luxembourg
            elif digits_only.startswith('353'):
                likely_regions.append('IE')  # Ireland
            elif digits_only.startswith('354'):
                likely_regions.append('IS')  # Iceland
            elif digits_only.startswith('355'):
                likely_regions.append('AL')  # Albania
            elif digits_only.startswith('356'):
                likely_regions.append('MT')  # Malta
            elif digits_only.startswith('357'):
                likely_regions.append('CY')  # Cyprus
            elif digits_only.startswith('358'):
                likely_regions.append('FI')  # Finland
            elif digits_only.startswith('359'):
                likely_regions.append('BG')  # Bulgaria
            elif digits_only.startswith('370'):
                likely_regions.append('LT')  # Lithuania
            elif digits_only.startswith('371'):
                likely_regions.append('LV')  # Latvia
            elif digits_only.startswith('372'):
                likely_regions.append('EE')  # Estonia
            elif digits_only.startswith('373'):
                likely_regions.append('MD')  # Moldova
            elif digits_only.startswith('374'):
                likely_regions.append('AM')  # Armenia
            elif digits_only.startswith('375'):
                likely_regions.append('BY')  # Belarus
            elif digits_only.startswith('376'):
                likely_regions.append('AD')  # Andorra
            elif digits_only.startswith('377'):
                likely_regions.append('MC')  # Monaco
            elif digits_only.startswith('378'):
                likely_regions.append('SM')  # San Marino
            elif digits_only.startswith('380'):
                likely_regions.append('UA')  # Ukraine
            elif digits_only.startswith('381'):
                likely_regions.append('RS')  # Serbia
            elif digits_only.startswith('382'):
                likely_regions.append('ME')  # Montenegro
            elif digits_only.startswith('383'):
                likely_regions.append('Kosovo')  # Kosovo
            elif digits_only.startswith('385'):
                likely_regions.append('HR')  # Croatia
            elif digits_only.startswith('386'):
                likely_regions.append('SI')  # Slovenia
            elif digits_only.startswith('387'):
                likely_regions.append('BA')  # Bosnia and Herzegovina
            elif digits_only.startswith('389'):
                likely_regions.append('MK')  # North Macedonia
            elif digits_only.startswith('420'):
                likely_regions.append('CZ')  # Czech Republic
            elif digits_only.startswith('421'):
                likely_regions.append('SK')  # Slovakia
            elif digits_only.startswith('423'):
                likely_regions.append('LI')  # Liechtenstein
            elif digits_only.startswith('500'):
                likely_regions.append('FK')  # Falkland Islands
            elif digits_only.startswith('501'):
                likely_regions.append('BZ')  # Belize
            elif digits_only.startswith('502'):
                likely_regions.append('GT')  # Guatemala
            elif digits_only.startswith('503'):
                likely_regions.append('SV')  # El Salvador
            elif digits_only.startswith('504'):
                likely_regions.append('HN')  # Honduras
            elif digits_only.startswith('505'):
                likely_regions.append('NI')  # Nicaragua
            elif digits_only.startswith('506'):
                likely_regions.append('CR')  # Costa Rica
            elif digits_only.startswith('507'):
                likely_regions.append('PA')  # Panama
            elif digits_only.startswith('508'):
                likely_regions.append('PM')  # Saint Pierre and Miquelon
            elif digits_only.startswith('509'):
                likely_regions.append('HT')  # Haiti
            elif digits_only.startswith('590'):
                likely_regions.append('GP')  # Guadeloupe
            elif digits_only.startswith('591'):
                likely_regions.append('BO')  # Bolivia
            elif digits_only.startswith('592'):
                likely_regions.append('GY')  # Guyana
            elif digits_only.startswith('593'):
                likely_regions.append('EC')  # Ecuador
            elif digits_only.startswith('594'):
                likely_regions.append('GF')  # French Guiana
            elif digits_only.startswith('595'):
                likely_regions.append('PY')  # Paraguay
            elif digits_only.startswith('596'):
                likely_regions.append('MQ')  # Martinique
            elif digits_only.startswith('597'):
                likely_regions.append('SR')  # Suriname
            elif digits_only.startswith('598'):
                likely_regions.append('UY')  # Uruguay
            elif digits_only.startswith('599'):
                likely_regions.append('CW')  # Curaçao
            elif digits_only.startswith('670'):
                likely_regions.append('TL')  # East Timor
            elif digits_only.startswith('672'):
                likely_regions.append('NF')  # Norfolk Island
            elif digits_only.startswith('673'):
                likely_regions.append('BN')  # Brunei
            elif digits_only.startswith('674'):
                likely_regions.append('NR')  # Nauru
            elif digits_only.startswith('675'):
                likely_regions.append('PG')  # Papua New Guinea
            elif digits_only.startswith('676'):
                likely_regions.append('TO')  # Tonga
            elif digits_only.startswith('677'):
                likely_regions.append('SB')  # Solomon Islands
            elif digits_only.startswith('678'):
                likely_regions.append('VU')  # Vanuatu
            elif digits_only.startswith('679'):
                likely_regions.append('FJ')  # Fiji
            elif digits_only.startswith('680'):
                likely_regions.append('PW')  # Palau
            elif digits_only.startswith('681'):
                likely_regions.append('WF')  # Wallis and Futuna
            elif digits_only.startswith('682'):
                likely_regions.append('CK')  # Cook Islands
            elif digits_only.startswith('683'):
                likely_regions.append('NU')  # Niue
            elif digits_only.startswith('684'):
                likely_regions.append('AS')  # American Samoa
            elif digits_only.startswith('685'):
                likely_regions.append('WS')  # Samoa
            elif digits_only.startswith('686'):
                likely_regions.append('KI')  # Kiribati
            elif digits_only.startswith('687'):
                likely_regions.append('NC')  # New Caledonia
            elif digits_only.startswith('688'):
                likely_regions.append('TV')  # Tuvalu
            elif digits_only.startswith('689'):
                likely_regions.append('PF')  # French Polynesia
            elif digits_only.startswith('690'):
                likely_regions.append('TK')  # Tokelau
            elif digits_only.startswith('691'):
                likely_regions.append('FM')  # Federated States of Micronesia
            elif digits_only.startswith('692'):
                likely_regions.append('MH')  # Marshall Islands
            elif digits_only.startswith('850'):
                likely_regions.append('KP')  # North Korea
            elif digits_only.startswith('852'):
                likely_regions.append('HK')  # Hong Kong
            elif digits_only.startswith('853'):
                likely_regions.append('MO')  # Macau
            elif digits_only.startswith('855'):
                likely_regions.append('KH')  # Cambodia
            elif digits_only.startswith('856'):
                likely_regions.append('LA')  # Laos
            elif digits_only.startswith('880'):
                likely_regions.append('BD')  # Bangladesh
            elif digits_only.startswith('886'):
                likely_regions.append('TW')  # Taiwan
            elif digits_only.startswith('960'):
                likely_regions.append('MV')  # Maldives
            elif digits_only.startswith('961'):
                likely_regions.append('LB')  # Lebanon
            elif digits_only.startswith('962'):
                likely_regions.append('JO')  # Jordan
            elif digits_only.startswith('963'):
                likely_regions.append('SY')  # Syria
            elif digits_only.startswith('964'):
                likely_regions.append('IQ')  # Iraq
            elif digits_only.startswith('965'):
                likely_regions.append('KW')  # Kuwait
            elif digits_only.startswith('966'):
                likely_regions.append('SA')  # Saudi Arabia
            elif digits_only.startswith('967'):
                likely_regions.append('YE')  # Yemen
            elif digits_only.startswith('968'):
                likely_regions.append('OM')  # Oman
            elif digits_only.startswith('970'):
                likely_regions.append('PS')  # Palestine
            elif digits_only.startswith('971'):
                likely_regions.append('AE')  # UAE
            elif digits_only.startswith('972'):
                likely_regions.append('IL')  # Israel
            elif digits_only.startswith('973'):
                likely_regions.append('BH')  # Bahrain
            elif digits_only.startswith('974'):
                likely_regions.append('QA')  # Qatar
            elif digits_only.startswith('975'):
                likely_regions.append('BT')  # Bhutan
            elif digits_only.startswith('976'):
                likely_regions.append('MN')  # Mongolia
            elif digits_only.startswith('977'):
                likely_regions.append('NP')  # Nepal
            elif digits_only.startswith('992'):
                likely_regions.append('TJ')  # Tajikistan
            elif digits_only.startswith('993'):
                likely_regions.append('TM')  # Turkmenistan
            elif digits_only.startswith('994'):
                likely_regions.append('AZ')  # Azerbaijan
            elif digits_only.startswith('995'):
                likely_regions.append('GE')  # Georgia
            elif digits_only.startswith('996'):
                likely_regions.append('KG')  # Kyrgyzstan
            elif digits_only.startswith('998'):
                likely_regions.append('UZ')  # Uzbekistan
        elif len(digits_only) == 13:
            # 13-digit numbers
            if digits_only.startswith('234'):
                likely_regions.append('NG')  # Nigeria
            elif digits_only.startswith('1242'):
                likely_regions.append('BS')  # Bahamas
            elif digits_only.startswith('1246'):
                likely_regions.append('BB')  # Barbados
            elif digits_only.startswith('1264'):
                likely_regions.append('AI')  # Anguilla
            elif digits_only.startswith('1268'):
                likely_regions.append('AG')  # Antigua and Barbuda
            elif digits_only.startswith('1284'):
                likely_regions.append('VG')  # British Virgin Islands
            elif digits_only.startswith('1340'):
                likely_regions.append('VI')  # US Virgin Islands
            elif digits_only.startswith('1345'):
                likely_regions.append('KY')  # Cayman Islands
            elif digits_only.startswith('1441'):
                likely_regions.append('BM')  # Bermuda
            elif digits_only.startswith('1473'):
                likely_regions.append('GD')  # Grenada
            elif digits_only.startswith('1649'):
                likely_regions.append('TC')  # Turks and Caicos
            elif digits_only.startswith('1664'):
                likely_regions.append('MS')  # Montserrat
            elif digits_only.startswith('1670'):
                likely_regions.append('MP')  # Northern Mariana Islands
            elif digits_only.startswith('1671'):
                likely_regions.append('GU')  # Guam
            elif digits_only.startswith('1684'):
                likely_regions.append('AS')  # American Samoa
            elif digits_only.startswith('1721'):
                likely_regions.append('SX')  # Sint Maarten
            elif digits_only.startswith('1758'):
                likely_regions.append('LC')  # Saint Lucia
            elif digits_only.startswith('1767'):
                likely_regions.append('DM')  # Dominica
            elif digits_only.startswith('1784'):
                likely_regions.append('VC')  # Saint Vincent and the Grenadines
            elif digits_only.startswith('1787'):
                likely_regions.append('PR')  # Puerto Rico
            elif digits_only.startswith('1809'):
                likely_regions.append('DO')  # Dominican Republic
            elif digits_only.startswith('1829'):
                likely_regions.append('DO')  # Dominican Republic
            elif digits_only.startswith('1849'):
                likely_regions.append('DO')  # Dominican Republic
            elif digits_only.startswith('1868'):
                likely_regions.append('TT')  # Trinidad and Tobago
            elif digits_only.startswith('1869'):
                likely_regions.append('KN')  # Saint Kitts and Nevis
            elif digits_only.startswith('1876'):
                likely_regions.append('JM')  # Jamaica
            elif digits_only.startswith('1939'):
                likely_regions.append('PR')  # Puerto Rico
        
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