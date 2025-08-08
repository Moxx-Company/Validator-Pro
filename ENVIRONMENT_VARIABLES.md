# Environment Variables Configuration

This document lists all configurable environment variables for the Validator Pro Telegram Bot system.

## Required Variables

These variables must be set for the application to function:

### `TELEGRAM_BOT_TOKEN`

- **Description**: Bot token obtained from BotFather
- **Example**: `1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789`
- **Used by**: Main bot application, payment notifications

### `ADMIN_CHAT_ID`

- **Description**: Telegram chat ID of the administrator
- **Example**: `123456789`
- **Used by**: Admin commands, system notifications

### `BLOCKBEE_API_KEY`

- **Description**: API key for BlockBee cryptocurrency payment processing
- **Example**: `STSFnOtVn6FaftBDj8OCZPiTVTxsmfZRnl5i36hIhIzwsuHP1mct0HpPX06NAR2O`
- **Used by**: Payment processing, webhook handling

## Optional Variables with Defaults

### Database Configuration

#### `DATABASE_URL`

- **Default**: `sqlite:///email_validator.db`
- **Description**: Database connection URL
- **Example**: `postgresql://user:password@host:port/database`

### Subscription & Pricing

#### `SUBSCRIPTION_PRICE_USD`

- **Default**: `5.00`
- **Description**: Monthly subscription price in USD
- **Type**: Float

#### `SUBSCRIPTION_DURATION_DAYS`

- **Default**: `30`
- **Description**: Subscription duration in days
- **Type**: Integer

#### `TRIAL_VALIDATION_LIMIT`

- **Default**: `1000`
- **Description**: Combined trial limit for emails and phones
- **Type**: Integer

#### `TRIAL_EMAIL_LIMIT`

- **Default**: `10000`
- **Description**: Legacy email trial limit (for backward compatibility)
- **Type**: Integer

### Email Validation Configuration

#### `MAX_CONCURRENT_VALIDATIONS`

- **Default**: `50`
- **Description**: Maximum concurrent email validations
- **Type**: Integer

#### `VALIDATION_TIMEOUT`

- **Default**: `10`
- **Description**: Validation timeout in seconds
- **Type**: Integer

#### `MAX_FILE_SIZE_MB`

- **Default**: `10`
- **Description**: Maximum upload file size in MB
- **Type**: Integer

#### `SMTP_TEST_EMAIL`

- **Default**: `test@validator.com`
- **Description**: Email address used for SMTP MAIL FROM commands
- **Example**: `noreply@yourdomain.com`

#### `SMTP_HELO_DOMAIN`

- **Default**: `validator.com`
- **Description**: Domain used for SMTP HELO commands
- **Example**: `yourdomain.com`

### Phone Validation Configuration

#### `DEFAULT_PHONE_REGION`

- **Default**: `US`
- **Description**: Default region code for phone number parsing
- **Example**: `GB`, `CA`, `AU`

#### `PHONE_VALIDATION_TIMEOUT`

- **Default**: `5`
- **Description**: Phone validation timeout in seconds
- **Type**: Integer

### Rate Limiting Configuration

#### `RATE_LIMIT_PER_MINUTE`

- **Default**: `120`
- **Description**: Maximum requests per minute per user
- **Type**: Integer

#### `MAX_CONCURRENT_VALIDATIONS_QUEUE`

- **Default**: `200`
- **Description**: Maximum concurrent validations in queue
- **Type**: Integer

### API URLs Configuration

#### `BLOCKBEE_BASE_URL`

- **Default**: `https://api.blockbee.io`
- **Description**: BlockBee API base URL
- **Example**: `https://api.blockbee.io`

#### `COINGECKO_API_BASE`

- **Default**: `https://api.coingecko.com/api/v3`
- **Description**: CoinGecko API base URL for crypto prices
- **Example**: `https://api.coingecko.com/api/v3`

#### `TELEGRAM_API_BASE`

- **Default**: `https://api.telegram.org`
- **Description**: Telegram API base URL
- **Example**: `https://api.telegram.org`

#### `WEBHOOK_BASE_URL`

- **Default**: `https://verifyemailphone.replit.app`
- **Description**: Base URL for webhook callbacks
- **Example**: `https://your-app.replit.app`

#### `BLOCKBEE_WEBHOOK_URL`

- **Default**: Automatically constructed from webhook base URL
- **Description**: Complete webhook URL for BlockBee callbacks
- **Override**: Set to manually override webhook URL

## File Processing Configuration

These are currently hardcoded but could be made configurable:

- **Allowed file extensions**: `.csv`, `.txt`, `.xlsx`, `.xls`
- **Results expiry**: 24 hours
- **Supported cryptocurrencies**: BTC, ETH, LTC, DOGE, USDT (TRC20/ERC20), TRX, BSC

## Development vs Production

### Development Settings

- Database: SQLite (default)
- Webhook URL: Local or development domain
- Lower rate limits for testing

### Production Settings

- Database: PostgreSQL (recommended)
- Webhook URL: Production domain
- Higher rate limits for production load

## Security Best Practices

1. **Never commit secrets to version control**
2. **Use Replit Secrets for all sensitive variables**
3. **Rotate API keys regularly**
4. **Use strong, unique values for required variables**
5. **Monitor usage and set appropriate rate limits**

## Example .env File

```bash
# Required
TELEGRAM_BOT_TOKEN=1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789
ADMIN_CHAT_ID=123456789
BLOCKBEE_API_KEY=your_blockbee_api_key_here

# Database
DATABASE_URL=postgresql://user:password@host:port/database

# Pricing
SUBSCRIPTION_PRICE_USD=5.00
SUBSCRIPTION_DURATION_DAYS=30

# Trial Limits
TRIAL_VALIDATION_LIMIT=1000
TRIAL_EMAIL_LIMIT=10000

# Validation Settings
MAX_CONCURRENT_VALIDATIONS=50
VALIDATION_TIMEOUT=10
MAX_FILE_SIZE_MB=10

# SMTP Settings
SMTP_TEST_EMAIL=noreply@yourdomain.com
SMTP_HELO_DOMAIN=yourdomain.com

# Phone Settings
DEFAULT_PHONE_REGION=US
PHONE_VALIDATION_TIMEOUT=5

# Rate Limiting
RATE_LIMIT_PER_MINUTE=120
MAX_CONCURRENT_VALIDATIONS_QUEUE=200

# API URLs (usually defaults are fine)
BLOCKBEE_BASE_URL=https://api.blockbee.io
COINGECKO_API_BASE=https://api.coingecko.com/api/v3
TELEGRAM_API_BASE=https://api.telegram.org
WEBHOOK_BASE_URL=https://your-app.replit.app
```

## Validation

The application will validate required environment variables on startup and throw errors if they are missing. Optional variables will use their default values if not provided.

---

**Last Updated**: August 2025  
**Version**: 1.0
