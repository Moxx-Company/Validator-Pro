"""
Utility functions for the email validator bot
"""
import os
import re
import hashlib
from datetime import datetime, timedelta
from typing import List, Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def is_valid_email_syntax(email: str) -> bool:
    """Check if email has valid syntax"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def extract_domain(email: str) -> Optional[str]:
    """Extract domain from email address"""
    try:
        return email.split('@')[1].lower()
    except (IndexError, AttributeError):
        return None

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def generate_job_id() -> str:
    """Generate unique job ID"""
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    random_hash = hashlib.md5(str(datetime.utcnow().timestamp()).encode()).hexdigest()[:8]
    return f"job_{timestamp}_{random_hash}"

def create_progress_bar(percentage: float, length: int = 20) -> str:
    """Create a Unicode progress bar"""
    filled_length = int(length * percentage / 100)
    bar = '█' * filled_length + '░' * (length - filled_length)
    return f"[{bar}] {percentage:.1f}%"

def format_duration(seconds: int) -> str:
    """Format duration in human readable format"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m {seconds % 60}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"



def create_results_csv(results: List[dict], output_path: str) -> None:
    """Create CSV file with validation results"""
    df = pd.DataFrame(results)
    df.to_csv(output_path, index=False)

def clean_old_files(directory: str, max_age_hours: int = 24) -> None:
    """Clean up old files from directory"""
    cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
    
    try:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_time < cutoff_time:
                    os.remove(file_path)
    except Exception as e:
        print(f"Error cleaning old files: {e}")

def escape_markdown(text: str) -> str:
    """Escape markdown special characters"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def format_crypto_address(address: str, length: int = 16) -> str:
    """Format crypto address for display"""
    if len(address) <= length:
        return address
    return f"{address[:8]}...{address[-8:]}"

def validate_crypto_transaction(tx_hash: str, expected_amount: float, currency: str) -> bool:
    """Validate crypto transaction via BlockBee API"""
    from services.blockbee_service import BlockBeeService
    
    try:
        blockbee = BlockBeeService()
        # Use BlockBee's verification system instead of direct blockchain queries
        verification_result = blockbee.verify_payment(tx_hash)
        
        if verification_result.get('success'):
            amount_received = verification_result.get('amount_received', 0)
            is_confirmed = verification_result.get('confirmed', False)
            
            # Check if amount matches and payment is confirmed
            return is_confirmed and amount_received >= expected_amount
        
        return False
        
    except Exception as e:
        logger.error(f"Error validating crypto transaction: {e}")
        return False


