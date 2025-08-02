"""
Configuration settings for the email validator bot
"""
import os

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'your_bot_token_here')

# Admin Configuration
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID', '123456789')  # Replace with actual admin chat ID

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///email_validator.db')

# Subscription Configuration
SUBSCRIPTION_PRICE_USD = 9.99
TRIAL_VALIDATION_LIMIT = 1000  # Combined limit for emails and phones
TRIAL_EMAIL_LIMIT = 10000  # Keep for backward compatibility
SUBSCRIPTION_DURATION_DAYS = 30

# Email Validation Configuration
MAX_CONCURRENT_VALIDATIONS = 50
VALIDATION_TIMEOUT = 10  # seconds
MAX_FILE_SIZE_MB = 10

# BlockBee Configuration
BLOCKBEE_API_KEY = os.getenv('BLOCKBEE_API_KEY', 'your_blockbee_api_key')
BLOCKBEE_WEBHOOK_URL = os.getenv('REPLIT_DOMAINS', 'https://your-app.replit.app').split(',')[0] + '/webhook/blockbee' if os.getenv('REPLIT_DOMAINS') else 'https://your-app.replit.app/webhook/blockbee'

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

# Bot Messages
WELCOME_MESSAGE = """
🎯 **Validator Pro**

Validate bulk lists with high accuracy.

✅ **Features:**
• Email validation (DNS, MX, SMTP)
• Phone validation (carrier, country)
• Bulk processing (CSV/Excel/TXT)
• Detailed reports & analytics

📊 **$9.99/month** | 🆓 **1,000 free trials**

Ready to start?
"""

SUBSCRIPTION_INFO = """
💎 **Pro Subscription - $9.99/month**

**Includes:**
✅ Unlimited email & phone validation
✅ Bulk file processing
✅ Advanced deliverability checks
✅ Carrier & country detection
✅ Priority support & analytics

Auto-expires after 30 days.
"""
