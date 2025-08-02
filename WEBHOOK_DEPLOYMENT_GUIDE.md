# BlockBee Webhook Deployment Guide

## Current Webhook Configuration

### Development URL
Current webhook endpoint: `https://c681cc6d-baff-4eb3-ac8a-6edb35307bf3-00-2ohumvzbpyg2l.janeway.replit.dev/webhook/blockbee`

### Production Deployment URL
When deployed via Replit Cloud Run, the webhook URL will automatically update to use the permanent deployment domain.

## Webhook URL Configuration Priority

The system checks for webhook URLs in this order:

1. **Custom Environment Variable**: `BLOCKBEE_WEBHOOK_URL` (highest priority)
2. **Replit Deployment URL**: `REPLIT_APP_URL` (for deployed apps)
3. **Replit Domains**: `REPLIT_DOMAINS` (current development)
4. **Legacy Format**: `REPL_SLUG.REPL_OWNER.repl.co`
5. **Fallback**: Generic replit.app domain

## Setting Permanent Webhook URL

### For Production Deployment
1. Deploy your app to Replit Cloud Run
2. The system will automatically use the deployment URL
3. No manual configuration needed

### For Custom Domain (Optional)
If you want to use a custom webhook URL:

```bash
# Set environment variable
export BLOCKBEE_WEBHOOK_URL="https://your-custom-domain.com/webhook/blockbee"
```

## Webhook Endpoints

### Main Payment Webhook
- **URL**: `/webhook/blockbee`
- **Method**: POST (for BlockBee payments)
- **Method**: GET (for status/info)
- **Format**: Accepts user_id, currency, amount_usd as path parameters

### Test Webhook
- **URL**: `/webhook/test`
- **Method**: GET/POST
- **Purpose**: Verify webhook connectivity

### Health Check
- **URL**: `/` or `/health`
- **Method**: GET
- **Purpose**: Deployment health verification

## Testing Webhook Connectivity

```bash
# Test basic connectivity
curl https://your-domain/webhook/blockbee

# Test webhook functionality
curl https://your-domain/webhook/test

# Test health endpoint
curl https://your-domain/
```

## BlockBee Integration

The webhook URL is automatically included in BlockBee payment address creation:

```
Callback URL format: https://domain/webhook/blockbee/{user_id}/{currency}/{amount_usd}
```

This allows BlockBee to send payment confirmations directly to your app when transactions are confirmed on the blockchain.

## Troubleshooting

### If webhooks aren't received:
1. Verify webhook URL is accessible externally
2. Check BlockBee logs for delivery attempts
3. Ensure HTTPS is working properly
4. Verify webhook returns "*ok*" response

### Manual payment activation:
If webhook fails, use the manual activation script:
```bash
python check_payment.py
```

## Security Notes

- All webhook URLs use HTTPS for security
- Webhook validation includes amount tolerance checking
- Payment data is logged for debugging
- Database transactions are atomic