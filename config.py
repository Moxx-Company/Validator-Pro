"""
Configuration settings for the email validator bot
"""
import os

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'your_bot_token_here')

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///email_validator.db')

# Subscription Configuration
SUBSCRIPTION_PRICE_USD = 9.99
TRIAL_VALIDATION_LIMIT = 5000  # Combined limit for emails and phones
TRIAL_EMAIL_LIMIT = 5000  # Keep for backward compatibility
SUBSCRIPTION_DURATION_DAYS = 30

# Email Validation Configuration
MAX_CONCURRENT_VALIDATIONS = 50
VALIDATION_TIMEOUT = 10  # seconds
MAX_FILE_SIZE_MB = 10

# BlockBee Configuration
BLOCKBEE_API_KEY = os.getenv('BLOCKBEE_API_KEY', 'your_blockbee_api_key')
BLOCKBEE_WEBHOOK_URL = os.getenv('BLOCKBEE_WEBHOOK_URL', 'https://your-app.replit.app/webhook/blockbee')

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
🎯 **Welcome to Email & Phone Validator Pro!**

I help you validate bulk email lists and phone numbers with high accuracy.

✅ **Features:**
• Email validation (DNS, MX, SMTP checks)
• Phone validation (carrier, country detection)
• Bulk processing (CSV/Excel/TXT)
• Detailed validation reports
• Usage statistics & dashboard

📊 **Subscription:** $9.99/month
🆓 **Trial:** 5000 free validations (emails + phones)

Ready to get started?
"""

SUBSCRIPTION_INFO = """
💎 **Email & Phone Validator Pro Subscription**

**Price:** $9.99/month
**Duration:** 30 days
**Payment:** Cryptocurrency

**What's included:**
✅ Unlimited email validations
✅ Unlimited phone validations
✅ Bulk file processing
✅ Advanced deliverability checks
✅ Carrier & country detection
✅ Priority support
✅ Detailed analytics

Your subscription auto-expires after 30 days.
"""
