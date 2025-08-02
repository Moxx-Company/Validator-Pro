"""
Email validation service with DNS, MX, and SMTP checks
"""
import socket
import smtplib
import dns.resolver
import dns.exception
import asyncio
import concurrent.futures
from typing import Dict, List, Tuple, Optional
import time
from dataclasses import dataclass
import json
from utils import is_valid_email_syntax, extract_domain

@dataclass
class ValidationResult:
    email: str
    is_valid: bool
    syntax_valid: bool
    domain_exists: bool
    mx_record_exists: bool
    smtp_connectable: bool
    domain: str
    mx_records: List[str]
    error_message: Optional[str]
    validation_time: float

class EmailValidator:
    def __init__(self, timeout: float = 0.5, max_workers: int = 150):
        self.timeout = timeout
        self.max_workers = max_workers
        self.dns_resolver = dns.resolver.Resolver()
        self.dns_resolver.timeout = timeout
        self.dns_resolver.lifetime = timeout
        # Cache for DNS lookups to avoid repeated queries
        self.domain_cache = {}
        self.mx_cache = {}
        # Configure DNS resolver for maximum speed
        self.dns_resolver.cache = dns.resolver.LRUCache(max_size=1000)
    

    
    def check_domain_exists(self, domain: str) -> bool:
        """Check if domain exists using DNS A record lookup with caching"""
        if domain in self.domain_cache:
            return self.domain_cache[domain]
        
        try:
            self.dns_resolver.resolve(domain, 'A')
            self.domain_cache[domain] = True
            return True
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, Exception):
            self.domain_cache[domain] = False
            return False
        except Exception:
            self.domain_cache[domain] = False
            return False
    
    def get_mx_records(self, domain: str) -> List[str]:
        """Get MX records for domain with caching"""
        if domain in self.mx_cache:
            return self.mx_cache[domain]
        
        try:
            mx_records = self.dns_resolver.resolve(domain, 'MX')
            result = [str(mx.exchange).rstrip('.') for mx in mx_records]
            self.mx_cache[domain] = result
            return result
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, Exception):
            self.mx_cache[domain] = []
            return []
        except Exception:
            self.mx_cache[domain] = []
            return []
    
    def check_smtp_connectivity(self, mx_record: str, email: str) -> bool:
        """Ultra-fast SMTP connectivity check with timeout protection"""
        try:
            # Phase 1: Quick socket connection test (1 second timeout)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)  # Slightly longer timeout for reliability
            
            result = sock.connect_ex((mx_record, 25))
            sock.close()
            
            if result != 0:
                return False
            
            # Phase 2: SMTP handshake with timeout protection
            with smtplib.SMTP(timeout=2.0) as server:  # 2 second timeout
                server.connect(mx_record, 25)
                server.helo('validator.com')
                
                # Quick MAIL FROM and RCPT TO test
                server.mail('test@validator.com')
                code, message = server.rcpt(email)
                
                # Accept codes: 250 (OK), 251 (forwarded), 252 (cannot verify but will accept)
                return code in [250, 251, 252]
                
        except (socket.timeout, smtplib.SMTPException, ConnectionError, OSError):
            # Handle specific timeout and connection errors
            return False
        except Exception:
            # Handle any other unexpected errors
            return False
    
    def smart_smtp_check(self, mx_server: str, email: str) -> bool:
        """Enhanced SMTP check - fast but thorough validation"""
        if not mx_server:
            return False
        
        # Always perform SMTP check but with optimizations for speed
        try:
            return self.check_smtp_connectivity(mx_server, email)
        except Exception as e:
            # If SMTP check fails, still return False for accuracy
            return False
    
    def validate_single_email(self, email: str) -> ValidationResult:
        """Validate a single email address with timeout protection"""
        start_time = time.time()
        
        # Initialize result
        result = ValidationResult(
            email=email,
            is_valid=False,
            syntax_valid=False,
            domain_exists=False,
            mx_record_exists=False,
            smtp_connectable=False,
            domain="",
            mx_records=[],
            error_message=None,
            validation_time=0.0
        )
        
        # Add maximum validation time protection
        max_validation_time = 10.0  # 10 seconds max per email
        
        try:
            # Step 1: Syntax validation
            result.syntax_valid = is_valid_email_syntax(email)
            if not result.syntax_valid:
                result.error_message = "Invalid email syntax"
                result.validation_time = time.time() - start_time
                return result
            
            # Step 2: Extract domain
            domain = extract_domain(email)
            if not domain:
                result.error_message = "Could not extract domain"
                result.validation_time = time.time() - start_time
                return result
            
            result.domain = domain
            
            # Step 3: Check if domain exists
            result.domain_exists = self.check_domain_exists(domain)
            if not result.domain_exists:
                result.error_message = "Domain does not exist"
                result.validation_time = time.time() - start_time
                return result
            
            # Step 4: Get MX records
            mx_records = self.get_mx_records(domain)
            result.mx_records = mx_records
            result.mx_record_exists = len(mx_records) > 0
            
            if not result.mx_record_exists:
                result.error_message = "No MX records found"
                result.validation_time = time.time() - start_time
                return result
            
            # Step 5: Smart SMTP connectivity check
            # Always perform SMTP check for accuracy
            result.smtp_connectable = self.smart_smtp_check(mx_records[0] if mx_records else None, email)
            
            # Final validation decision - require ALL checks including SMTP
            result.is_valid = (
                result.syntax_valid and 
                result.domain_exists and 
                result.mx_record_exists and
                result.smtp_connectable  # SMTP check is REQUIRED for accurate validation
            )
            
            if not result.smtp_connectable:
                result.error_message = "SMTP server not reachable or email rejected"
            
        except Exception as e:
            result.error_message = f"Validation error: {str(e)}"
        
        result.validation_time = time.time() - start_time
        return result
    
    async def validate_email(self, email: str) -> Dict:
        """Async wrapper for single email validation"""
        result = self.validate_single_email(email)
        return {
            'is_valid': result.is_valid,
            'reason': result.error_message,
            'mx_record': result.mx_records[0] if result.mx_records else None,
            'smtp_check': result.smtp_connectable
        }
    
    async def validate_bulk_emails(self, emails: List[str], progress_callback=None) -> List[ValidationResult]:
        """Validate multiple emails concurrently with timeout protection"""
        results = []
        processed = 0
        
        # Use ThreadPoolExecutor for concurrent validation
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_email = {
                executor.submit(self.validate_single_email, email): email 
                for email in emails
            }
            
            # Process completed tasks with timeout protection
            for future in concurrent.futures.as_completed(future_to_email, timeout=300):  # 5 minute total timeout
                try:
                    # Get result with per-email timeout
                    result = future.result(timeout=15)  # 15 second timeout per email
                    results.append(result)
                    processed += 1
                    
                    # Call progress callback if provided
                    if progress_callback:
                        progress = int((processed / len(emails)) * 100)
                        await progress_callback(progress, processed, len(emails))
                        
                except concurrent.futures.TimeoutError:
                    # Handle timeout for individual email
                    email = future_to_email[future]
                    error_result = ValidationResult(
                        email=email,
                        is_valid=False,
                        syntax_valid=False,
                        domain_exists=False,
                        mx_record_exists=False,
                        smtp_connectable=False,
                        domain="",
                        mx_records=[],
                        error_message="Validation timeout - email took too long to process",
                        validation_time=15.0
                    )
                    results.append(error_result)
                    processed += 1
                    
                    if progress_callback:
                        progress = int((processed / len(emails)) * 100)
                        await progress_callback(progress, processed, len(emails))
                        
                except Exception as e:
                    email = future_to_email[future]
                    error_result = ValidationResult(
                        email=email,
                        is_valid=False,
                        syntax_valid=False,
                        domain_exists=False,
                        mx_record_exists=False,
                        smtp_connectable=False,
                        domain="",
                        mx_records=[],
                        error_message=f"Processing error: {str(e)}",
                        validation_time=0.0
                    )
                    results.append(error_result)
                    processed += 1
                    
                    if progress_callback:
                        progress = int((processed / len(emails)) * 100)
                        await progress_callback(progress, processed, len(emails))
        
        return results
    
    def results_to_dict(self, results: List[ValidationResult]) -> List[Dict]:
        """Convert validation results to dictionary format"""
        return [
            {
                'email': result.email,
                'is_valid': result.is_valid,
                'syntax_valid': result.syntax_valid,
                'domain_exists': result.domain_exists,
                'mx_record_exists': result.mx_record_exists,
                'smtp_connectable': result.smtp_connectable,
                'domain': result.domain,
                'mx_records': json.dumps(result.mx_records),
                'error_message': result.error_message,
                'validation_time': round(result.validation_time, 3)
            }
            for result in results
        ]
    
    def get_validation_summary(self, results: List[ValidationResult]) -> Dict:
        """Get summary statistics from validation results"""
        if not results:
            return {
                'total': 0,
                'valid': 0,
                'invalid': 0,
                'success_rate': 0.0,
                'avg_validation_time': 0.0
            }
        
        valid_count = sum(1 for r in results if r.is_valid)
        invalid_count = len(results) - valid_count
        avg_time = sum(r.validation_time for r in results) / len(results)
        
        return {
            'total': len(results),
            'valid': valid_count,
            'invalid': invalid_count,
            'success_rate': round((valid_count / len(results)) * 100, 2),
            'avg_validation_time': round(avg_time, 3)
        }
