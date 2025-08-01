"""
Utility functions for the email validator bot
"""
import os
import re
import hashlib
from datetime import datetime, timedelta
from typing import List, Optional
import pandas as pd

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

def create_progress_bar(percentage: int, length: int = 20) -> str:
    """Create a Unicode progress bar"""
    filled_length = int(length * percentage // 100)
    bar = '█' * filled_length + '░' * (length - filled_length)
    return f"[{bar}] {percentage}%"

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

def read_emails_from_file(file_path: str) -> List[str]:
    """Read emails from various file formats"""
    emails = []
    file_ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if file_ext == '.csv':
            df = pd.read_csv(file_path)
            # Try common column names for emails
            email_columns = ['email', 'Email', 'EMAIL', 'e-mail', 'E-mail']
            email_column = None
            
            for col in email_columns:
                if col in df.columns:
                    email_column = col
                    break
            
            if email_column:
                emails = df[email_column].dropna().astype(str).tolist()
            else:
                # If no email column found, try first column
                emails = df.iloc[:, 0].dropna().astype(str).tolist()
                
        elif file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
            # Similar logic as CSV
            email_columns = ['email', 'Email', 'EMAIL', 'e-mail', 'E-mail']
            email_column = None
            
            for col in email_columns:
                if col in df.columns:
                    email_column = col
                    break
            
            if email_column:
                emails = df[email_column].dropna().astype(str).tolist()
            else:
                emails = df.iloc[:, 0].dropna().astype(str).tolist()
                
        elif file_ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                emails = [line.strip() for line in f if line.strip()]
        
        # Filter out invalid email formats
        valid_emails = [email for email in emails if is_valid_email_syntax(email)]
        return valid_emails
        
    except Exception as e:
        raise Exception(f"Error reading file: {str(e)}")

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
    """Validate crypto transaction (placeholder implementation)"""
    # This would integrate with blockchain APIs like BlockCypher, Etherscan, etc.
    # For now, return True as placeholder
    return True

def get_crypto_price(currency: str) -> float:
    """Get current crypto price in USD"""
    try:
        import requests
        # Map currency names to CoinGecko IDs
        coin_mapping = {
            'btc': 'bitcoin',
            'bitcoin': 'bitcoin',
            'eth': 'ethereum', 
            'ethereum': 'ethereum',
            'ltc': 'litecoin',
            'litecoin': 'litecoin',
            'doge': 'dogecoin',
            'dogecoin': 'dogecoin',
            'usdt': 'tether',
            'usdt_trc20': 'tether',
            'usdt_erc20': 'tether',
            'trx': 'tron',
            'tron': 'tron',
            'bsc': 'binancecoin'
        }
        
        coin_id = coin_mapping.get(currency.lower())
        if not coin_id:
            return 1.0
        
        response = requests.get(
            f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get(coin_id, {}).get('usd', 1.0)
        
        return 1.0
        
    except Exception:
        return 1.0
