"""
Configuration settings for the email validator bot
"""
import os

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

# Admin Configuration
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')
if not ADMIN_CHAT_ID:
    raise ValueError("ADMIN_CHAT_ID environment variable is required")

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///email_validator.db')

# Subscription Configuration
SUBSCRIPTION_PRICE_USD = 1 #float(os.getenv('SUBSCRIPTION_PRICE_USD', '1'))
TRIAL_VALIDATION_LIMIT = int(os.getenv('TRIAL_VALIDATION_LIMIT', '1000'))  # Combined limit for emails and phones
TRIAL_EMAIL_LIMIT = int(os.getenv('TRIAL_EMAIL_LIMIT', '10000'))  # Keep for backward compatibility
SUBSCRIPTION_DURATION_DAYS = int(os.getenv('SUBSCRIPTION_DURATION_DAYS', '30'))

# Email Validation Configuration
MAX_CONCURRENT_VALIDATIONS = int(os.getenv('MAX_CONCURRENT_VALIDATIONS', '50'))
VALIDATION_TIMEOUT = int(os.getenv('VALIDATION_TIMEOUT', '10'))  # seconds
MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '10'))

# Email SMTP Configuration (optional - for advanced email validation)
SMTP_SERVER = os.getenv('SMTP_SERVER')  # e.g., 'smtp.gmail.com'
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME')  # Your email address
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')  # Your app password
SMTP_USE_TLS = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
SMTP_TEST_EMAIL = os.getenv('SMTP_TEST_EMAIL', 'test@validator.com')
SMTP_HELO_DOMAIN = os.getenv('SMTP_HELO_DOMAIN', 'validator.com')

# Check if SMTP credentials are configured
SMTP_CONFIGURED = bool(SMTP_SERVER and SMTP_USERNAME and SMTP_PASSWORD)

# Phone Validation Configuration
DEFAULT_PHONE_REGION = os.getenv('DEFAULT_PHONE_REGION', 'US')
PHONE_VALIDATION_TIMEOUT = int(os.getenv('PHONE_VALIDATION_TIMEOUT', '5'))

# Rate Limiting Configuration
RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', '120'))
MAX_CONCURRENT_VALIDATIONS_QUEUE = int(os.getenv('MAX_CONCURRENT_VALIDATIONS_QUEUE', '200'))

# BlockBee Configuration
BLOCKBEE_API_KEY = os.getenv('BLOCKBEE_API_KEY')
if not BLOCKBEE_API_KEY:
    raise ValueError("BLOCKBEE_API_KEY environment variable is required")

BLOCKBEE_BASE_URL = os.getenv('BLOCKBEE_BASE_URL', 'https://api.blockbee.io')

# External API URLs
COINGECKO_API_BASE = os.getenv('COINGECKO_API_BASE', 'https://api.coingecko.com/api/v3')
TELEGRAM_API_BASE = os.getenv('TELEGRAM_API_BASE', 'https://api.telegram.org')
# Build proper HTTPS webhook URL from Replit domains
def get_webhook_url():
    # First try custom webhook URL for manual override
    custom_webhook = os.getenv('BLOCKBEE_WEBHOOK_URL')
    if custom_webhook:
        return custom_webhook
    
    # Use production webhook URL
    replit_url = os.getenv('REPLIT_DOMAINS')
    if replit_url:
        # Extract the main domain from REPLIT_DOMAINS if available
        domains = replit_url.split(',')
        main_domain = domains[0].strip() if domains else None
        if main_domain and main_domain.startswith('http'):
            return f"{main_domain}/webhook/blockbee"
    
    # Fallback to permanent production URL
    return "https://verifyemailphone.replit.app/webhook/blockbee"

BLOCKBEE_WEBHOOK_URL = get_webhook_url()

# Supported cryptocurrencies
SUPPORTED_CRYPTOS = {
    'btc': 'Bitcoin',
    'eth': 'Ethereum', 
    'ltc': 'Litecoin',
    'doge': 'Dogecoin',
    'usdt_trc20': 'USDT (TRC20)',
    'usdt_erc20': 'USDT (ERC20)',
    'trx': 'TRON',
    'bsc': 'BNB Smart Chain'
}

# File Processing
ALLOWED_FILE_EXTENSIONS = ['.csv', '.txt', '.xlsx', '.xls']
RESULTS_EXPIRY_HOURS = 24

# Bot Messages - Dynamic based on configuration
WELCOME_MESSAGE = f"""
🎯 **Validator Pro**

Validate bulk lists with high accuracy.

✅ **Features:**
• Email validation (DNS, MX, SMTP)
• Phone validation (carrier, country)
• Bulk processing (CSV/Excel/TXT)
• Detailed reports & analytics

📊 **${SUBSCRIPTION_PRICE_USD}/month** | 🆓 **{TRIAL_VALIDATION_LIMIT:,} free trials**

Ready to start?
"""

SUBSCRIPTION_INFO = f"""
💎 **Pro Subscription - ${SUBSCRIPTION_PRICE_USD}/month**

**Includes:**
✅ Unlimited email & phone validation
✅ Bulk file processing
✅ Advanced deliverability checks
✅ Carrier & country detection
✅ Priority support & analytics

Auto-expires after {SUBSCRIPTION_DURATION_DAYS} days.
"""
