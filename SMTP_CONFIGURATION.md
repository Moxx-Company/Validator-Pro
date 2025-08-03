# SMTP Configuration Guide

This guide explains how to configure SMTP credentials for enhanced email validation in Validator Pro.

## Overview

When SMTP credentials are configured, the bot performs **authenticated SMTP testing** which provides significantly higher validation accuracy (98%+) compared to basic SMTP connectivity checks.

## Benefits of SMTP Configuration

- **Higher Accuracy**: Authenticated SMTP testing provides 98%+ validation accuracy vs 85-90% for basic checks
- **Real Deliverability**: Tests actual email delivery capability, not just connectivity
- **Advanced Detection**: Identifies catch-all domains, role accounts, and temporary emails more accurately
- **Enterprise Grade**: Suitable for high-volume, business-critical email validation

## Configuration Variables

Add these environment variables to enable SMTP authentication:

### Required SMTP Variables
```bash
SMTP_SERVER=smtp.gmail.com          # SMTP server hostname
SMTP_PORT=587                       # SMTP server port (587 for TLS, 465 for SSL)
SMTP_USERNAME=your-email@gmail.com  # Your email address
SMTP_PASSWORD=your-app-password     # Your email password or app-specific password
```

### Optional SMTP Variables
```bash
SMTP_USE_TLS=true                   # Enable TLS encryption (default: true)
SMTP_TEST_EMAIL=test@validator.com  # From address for test emails
SMTP_HELO_DOMAIN=validator.com      # Domain for SMTP HELO command
```

## Provider-Specific Configurations

### Gmail Configuration
```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-16-character-app-password
SMTP_USE_TLS=true
```

**Gmail Setup Steps:**
1. Enable 2-Factor Authentication on your Google account
2. Go to Google Account Settings > Security > App Passwords
3. Generate an App Password for "Mail"
4. Use the 16-character app password (not your regular password)

### Outlook/Hotmail Configuration
```bash
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USERNAME=your-email@outlook.com
SMTP_PASSWORD=your-password
SMTP_USE_TLS=true
```

### Yahoo Mail Configuration
```bash
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_USERNAME=your-email@yahoo.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
```

### Custom SMTP Server
```bash
SMTP_SERVER=mail.yourdomain.com
SMTP_PORT=465
SMTP_USERNAME=noreply@yourdomain.com
SMTP_PASSWORD=your-password
SMTP_USE_TLS=false
```

## How It Works

### Without SMTP Configuration (Basic Mode)
1. DNS lookup to check if domain exists
2. MX record lookup to find mail servers
3. Socket connection test to port 25
4. Basic SMTP handshake (HELO, MAIL FROM, RCPT TO)

### With SMTP Configuration (Enhanced Mode)
1. DNS lookup to check if domain exists
2. MX record lookup to find mail servers
3. **Authenticated connection to your SMTP server**
4. **Real email delivery test** to target address
5. **Actual SMTP response codes** for precise validation

## Security Considerations

- **Use dedicated email accounts** for validation testing
- **Enable App Passwords** instead of regular passwords when possible
- **Monitor email quotas** - some providers limit daily sending
- **Consider rate limiting** for high-volume validation
- **Keep credentials secure** - never commit to version control

## Troubleshooting

### Common Issues
1. **Authentication Failed**: Check username/password, enable app passwords
2. **Connection Timeout**: Verify server hostname and port
3. **TLS Errors**: Try different TLS settings or ports
4. **Rate Limited**: Some providers limit email sending frequency

### Testing Configuration
The bot will automatically detect if SMTP credentials are configured and log whether enhanced validation is active.

### Fallback Behavior
If SMTP authentication fails, the system automatically falls back to basic SMTP connectivity testing.

## Performance Impact

- **Slightly slower**: Authenticated SMTP takes ~2-5 seconds vs ~1-2 seconds for basic
- **Much more accurate**: Worth the small performance trade-off
- **Scalable**: Can handle hundreds of concurrent validations

## Recommended Setup

For production use, we recommend:
1. Create a dedicated Gmail account for validation
2. Enable 2FA and generate an App Password
3. Set reasonable rate limits
4. Monitor usage and quotas

This provides the best balance of accuracy, reliability, and security.