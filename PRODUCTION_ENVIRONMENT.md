# Production Environment Configuration

## Required Environment Variables

### Core System Configuration
```bash
# Telegram Bot Configuration (REQUIRED)
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
ADMIN_CHAT_ID=your_telegram_user_id_for_admin_access

# Database Configuration 
DATABASE_URL=postgresql://username:password@host:port/database_name

# BlockBee Cryptocurrency Payment API (REQUIRED)
BLOCKBEE_API_KEY=your_blockbee_api_key_from_dashboard
BLOCKBEE_WEBHOOK_URL=https://yourdomain.replit.app/webhook/blockbee
```

### Optional SMTP Configuration (For Enhanced Email Validation)
```bash
# Gmail Configuration Example
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password
SMTP_USE_TLS=true
SMTP_TEST_EMAIL=test@validator.com
SMTP_HELO_DOMAIN=validator.com

# Outlook/Hotmail Configuration Example
# SMTP_SERVER=smtp-mail.outlook.com
# SMTP_PORT=587
# SMTP_USERNAME=your-email@outlook.com
# SMTP_PASSWORD=your-app-password

# Yahoo Configuration Example
# SMTP_SERVER=smtp.mail.yahoo.com
# SMTP_PORT=587
# SMTP_USERNAME=your-email@yahoo.com
# SMTP_PASSWORD=your-app-password
```

### System Configuration (Optional - Defaults Provided)
```bash
# Subscription & Pricing
SUBSCRIPTION_PRICE_USD=9.99
SUBSCRIPTION_DURATION_DAYS=30
TRIAL_VALIDATION_LIMIT=1000

# Performance Settings
MAX_CONCURRENT_VALIDATIONS=50
VALIDATION_TIMEOUT=10
MAX_FILE_SIZE_MB=10
RATE_LIMIT_PER_MINUTE=120

# Phone Validation
DEFAULT_PHONE_REGION=US
PHONE_VALIDATION_TIMEOUT=5

# API Endpoints
BLOCKBEE_BASE_URL=https://api.blockbee.io
COINGECKO_API_BASE=https://api.coingecko.com/api/v3
TELEGRAM_API_BASE=https://api.telegram.org
```

## How to Obtain Required Keys

### 1. Telegram Bot Token
1. Message @BotFather on Telegram
2. Use /newbot command
3. Follow prompts to create your bot
4. Copy the bot token provided
5. Get your Telegram user ID from @userinfobot

### 2. BlockBee API Key
1. Visit https://blockbee.io
2. Create account and verify email
3. Access API dashboard
4. Generate new API key
5. Configure supported cryptocurrencies

### 3. SMTP Credentials (Optional but Recommended)
#### Gmail:
1. Enable 2-factor authentication
2. Generate app-specific password in Google Account settings
3. Use this password, not your regular Gmail password

#### Outlook:
1. Enable 2-factor authentication in Microsoft account
2. Generate app password in security settings
3. Use app password for SMTP_PASSWORD

### 4. Database Setup
For PostgreSQL (recommended for production):
```bash
# Example connection string
DATABASE_URL=postgresql://validator_user:secure_password@db.server.com:5432/validator_db
```

## Production Deployment Checklist

### Pre-Deployment
- [ ] Obtain Telegram bot token from BotFather
- [ ] Get BlockBee API key and configure cryptocurrencies
- [ ] Set up PostgreSQL database
- [ ] Configure SMTP credentials (optional but recommended)
- [ ] Set ADMIN_CHAT_ID to your Telegram user ID

### Environment Setup
- [ ] Add all required environment variables to Replit Secrets
- [ ] Verify BLOCKBEE_WEBHOOK_URL points to your deployed app
- [ ] Test database connection
- [ ] Validate SMTP configuration if used

### Security Considerations
- [ ] Use strong, unique passwords for database
- [ ] Store all sensitive data in environment variables
- [ ] Never commit API keys to version control
- [ ] Use app-specific passwords for email providers
- [ ] Regularly rotate API keys and passwords

### Testing Before Launch
- [ ] Test email validation with various email types
- [ ] Test phone validation with international numbers
- [ ] Verify cryptocurrency payment flow end-to-end
- [ ] Test subscription activation via webhook
- [ ] Verify file upload and download functionality
- [ ] Test admin panel access and functions

## System Architecture

### Port Configuration
- **Port 5000**: BlockBee Payment API Server
- **Port 5001**: File Server (validation results downloads)
- **Port 5002**: Webhook Handler (internal bot communications)

### Service Dependencies
1. **PostgreSQL Database**: User data, subscriptions, validation results
2. **BlockBee API**: Cryptocurrency payment processing
3. **Telegram Bot API**: User interface and notifications
4. **SMTP Servers**: Enhanced email validation (optional)
5. **File Storage**: Temporary storage for uploaded files and results

### Monitoring & Maintenance
- Monitor webhook delivery success rates
- Track payment confirmation times
- Watch validation processing performance
- Monitor database storage usage
- Check SMTP authentication success rates

## Troubleshooting Common Issues

### Bot Not Responding
- Verify TELEGRAM_BOT_TOKEN is correct
- Check if bot is added to channels properly
- Ensure no conflicting bot instances

### Payment Issues
- Verify BLOCKBEE_API_KEY is valid
- Check webhook URL is accessible publicly
- Confirm cryptocurrency is enabled in BlockBee dashboard

### Email Validation Problems
- Test SMTP credentials separately
- Check firewall settings for SMTP ports
- Verify email provider app password settings

### Database Connection Issues
- Test DATABASE_URL connection string format
- Verify database server accessibility
- Check user permissions for database operations

## Support Contacts
- BlockBee Support: https://blockbee.io/support
- Telegram Bot Support: https://core.telegram.org/bots/support
- SMTP Provider Support: Contact your email provider

---
**Last Updated**: August 3, 2025
**System Status**: Production Ready
**Documentation Version**: 1.0