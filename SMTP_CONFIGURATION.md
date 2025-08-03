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

### Brevo (Sendinblue) Configuration **[RECOMMENDED]**
```bash
SMTP_SERVER=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USERNAME=your-smtp-login@example.com
SMTP_PASSWORD=your-brevo-smtp-key
SMTP_USE_TLS=true
```

**Brevo Setup Steps:**
1. Log into your Brevo account
2. Go to account dropdown (top-right) → **SMTP & API**
3. Click the **SMTP** tab (not API tab)
4. Click **Generate a new SMTP key**
5. Name your key (e.g. "Validator Pro Bot")
6. Copy the SMTP login email and SMTP key immediately
7. Use these credentials in your environment variables

**Why Brevo is Recommended:**
- Professional email service with high deliverability
- Reliable SMTP relay with excellent uptime
- Free tier includes 300 emails/day
- Better reputation than personal email providers
- Designed for transactional/automated emails
- Port 587 works reliably (rarely blocked)

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

For production use, we highly recommend **Brevo SMTP**:
1. Sign up for a free Brevo account at brevo.com
2. Navigate to SMTP & API → SMTP tab
3. Generate a new SMTP key for your validation bot
4. Configure the credentials as shown above
5. Monitor your daily sending limits (300 free emails/day)

**Alternative: Gmail Setup**
1. Create a dedicated Gmail account for validation
2. Enable 2FA and generate an App Password
3. Set reasonable rate limits
4. Monitor usage and quotas

Brevo provides the best balance of accuracy, reliability, and professional email reputation for email validation services.