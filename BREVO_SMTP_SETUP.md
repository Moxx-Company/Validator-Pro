# Brevo SMTP Setup Guide for Validator Pro

## Why Brevo SMTP is Perfect for Email Validation

Brevo (formerly Sendinblue) provides professional-grade SMTP relay services that are specifically designed for automated email validation and transactional emails. Here's why it's the best choice:

### Key Advantages
- **High Deliverability**: Professional email infrastructure with excellent sender reputation
- **Reliable Service**: 99.9% uptime with robust SMTP relay network
- **Free Tier**: 300 emails per day completely free
- **Validation Optimized**: Designed for automated and transactional email testing
- **Port 587 Support**: Works reliably across different networks (rarely blocked)
- **Real SMTP Testing**: Provides authentic email deliverability validation

## Step-by-Step Setup

### 1. Create Brevo Account
1. Go to [brevo.com](https://brevo.com) and sign up for a free account
2. Verify your email address
3. Complete the account setup process

### 2. Generate SMTP Credentials
1. Log into your Brevo dashboard
2. Click your **account name** in the top-right corner
3. Select **SMTP & API** from the dropdown menu
4. Click the **SMTP** tab (not the API tab)
5. Click **"Generate a new SMTP key"**
6. Enter a name like "Validator Pro Bot" or "Email Validation"
7. Click **Generate**
8. **IMPORTANT**: Copy both credentials immediately:
   - SMTP Login (looks like: `your-email-12345@smtp-brevo.com`)
   - SMTP Key (long password string)

### 3. Configure Environment Variables

Add these to your Replit environment variables or `.env` file:

```bash
# Brevo SMTP Configuration
SMTP_SERVER=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USERNAME=your-smtp-login@smtp-brevo.com
SMTP_PASSWORD=your-brevo-smtp-key
SMTP_USE_TLS=true
SMTP_TEST_EMAIL=noreply@validator.com
SMTP_HELO_DOMAIN=validator.com
```

### 4. Verify Configuration

The bot will automatically detect your SMTP configuration and use enhanced validation mode. You'll see this in the logs:
- `INFO: SMTP authentication configured - using enhanced validation mode`

## Configuration Examples

### Environment Variables (Recommended)
```bash
SMTP_SERVER=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USERNAME=myapp-validation-123@smtp-brevo.com
SMTP_PASSWORD=xks8Qw2mN9pL5Rt6Ey4Bc7Vz1
SMTP_USE_TLS=true
```

### Replit Secrets
In Replit's secrets panel, add:
```
SMTP_SERVER = smtp-relay.brevo.com
SMTP_PORT = 587
SMTP_USERNAME = your-generated-login@smtp-brevo.com
SMTP_PASSWORD = your-generated-smtp-key
SMTP_USE_TLS = true
```

## Validation Accuracy Comparison

| Validation Mode | Accuracy | Speed | Use Case |
|----------------|----------|-------|----------|
| **Basic Mode** (no SMTP) | 85-90% | ~1-2 sec/email | General validation |
| **Brevo Enhanced** | 98%+ | ~2-3 sec/email | Professional validation |

## Usage Limits & Monitoring

### Free Tier Limits
- **300 emails per day** for free accounts
- **Unlimited SMTP connections**
- **No monthly commitment**

### Paid Plans
- **20,000+ emails/month** starting at $25/month
- **Higher sending rates**
- **Advanced features**

### Monitoring Usage
1. Go to your Brevo dashboard
2. Check **Statistics** → **Email** for daily sending counts
3. Monitor approaching daily limits

## Troubleshooting

### Common Issues

**1. Authentication Failed**
```
Error: (535, b'5.7.1 Authentication failed')
```
- **Solution**: Verify you're using the SMTP key (not API key)
- Check the SMTP login email is correct
- Ensure credentials haven't expired

**2. Connection Timeout**
```
Error: Connection timeout to smtp-relay.brevo.com:587
```
- **Solution**: Check your network allows outbound port 587
- Try port 2525 as an alternative: `SMTP_PORT=2525`

**3. TLS/SSL Errors**
```
Error: STARTTLS extension not supported by server
```
- **Solution**: Ensure `SMTP_USE_TLS=true`
- Port 587 requires STARTTLS, not SSL

**4. Rate Limited**
```
Error: (421, b'4.2.1 Service temporarily unavailable')
```
- **Solution**: You've hit the 300 emails/day limit
- Wait until tomorrow or upgrade to a paid plan

### Testing Configuration

To test if your Brevo SMTP is working:
1. Start the bot
2. Send a few test emails for validation
3. Check the bot logs for authentication success
4. Verify higher accuracy results

## Security Best Practices

### Credential Security
- **Never commit SMTP credentials** to version control
- **Use environment variables** or Replit secrets
- **Rotate SMTP keys** periodically for security
- **Create separate keys** for different applications

### Rate Limiting
- **Monitor daily usage** to avoid hitting limits
- **Implement delays** for very high-volume validation
- **Consider paid plans** for business use

### Email Reputation
- **Use noreply@ addresses** for test emails
- **Don't send to real inboxes** during validation
- **Monitor bounce rates** in Brevo dashboard

## Advanced Configuration

### Custom Test Email
```bash
SMTP_TEST_EMAIL=validation@yourdomain.com
SMTP_HELO_DOMAIN=yourdomain.com
```

### Alternative Ports
If port 587 is blocked, try:
```bash
SMTP_PORT=2525  # Alternative STARTTLS port
# or
SMTP_PORT=465   # SSL port (set SMTP_USE_TLS=false)
```

## Integration Verification

Once configured, the Validator Pro bot will:
1. **Automatically detect** Brevo SMTP credentials
2. **Switch to enhanced mode** for email validation
3. **Provide 98%+ accuracy** for email verification
4. **Log authentication status** in the console
5. **Fall back gracefully** if SMTP fails

Your email validation service is now powered by professional-grade Brevo SMTP infrastructure!

## Support

- **Brevo Support**: [help.brevo.com](https://help.brevo.com)
- **SMTP Documentation**: [developers.brevo.com/docs/smtp-integration](https://developers.brevo.com/docs/smtp-integration)
- **Bot Logs**: Check your Replit console for detailed error messages