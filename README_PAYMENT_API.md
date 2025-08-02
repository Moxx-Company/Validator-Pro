# BlockBee Payment API

A complete Python REST API for cryptocurrency payments using BlockBee's payment processing service. Features automatic subscription activation, webhook handling, and comprehensive payment tracking.

## Features

✅ **Multi-Cryptocurrency Support**: BTC, USDT, ETH, LTC, and more  
✅ **Automatic Payment Processing**: Real-time webhook integration  
✅ **Subscription Management**: 30-day automatic activation  
✅ **Payment Tracking**: Complete transaction logs with retry safety  
✅ **Duplicate Prevention**: Built-in protection against double processing  
✅ **Production Ready**: PostgreSQL database with proper indexing  

## Quick Start

### 1. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Set your BlockBee API key
BLOCKBEE_API_KEY=your_api_key_here
WEBHOOK_BASE_URL=https://your-domain.com
DATABASE_URL=postgresql://user:pass@host:port/db
```

### 2. Run the API Server

```bash
python payment_api.py
```

Server runs on `http://localhost:5001`

### 3. Create a Payment

```bash
curl -X POST http://localhost:5001/create-payment \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "crypto_type": "btc",
    "amount_usd": 10.0,
    "email": "user@example.com"
  }'
```

**Response:**
```json
{
  "success": true,
  "order_id": "order_abc123",
  "payment_address": "3ABC...XYZ",
  "amount_usd": 10.0,
  "amount_crypto": 0.00025,
  "crypto_type": "BTC",
  "qr_code_url": "https://api.blockbee.io/qr/...",
  "confirmations_required": 1,
  "message": "Send exactly 0.00025 BTC to the address above"
}
```

## API Endpoints

### Create Payment
**POST** `/create-payment`

Creates a new crypto payment address using BlockBee's API.

**Request Body:**
```json
{
  "user_id": "string",          // Required: Your internal user ID
  "crypto_type": "btc",         // Required: btc, usdt, eth, ltc
  "amount_usd": 10.0,          // Required: Amount in USD
  "email": "user@example.com"  // Optional: User email
}
```

### Payment Status
**GET** `/payment/{order_id}/status`

Get detailed payment status and subscription info.

**Response:**
```json
{
  "order_id": "order_abc123",
  "status": "confirmed",
  "payment_address": "3ABC...XYZ",
  "amount_fiat": 10.0,
  "amount_crypto": 0.00025,
  "crypto_type": "BTC",
  "confirmations_received": 1,
  "confirmations_required": 1,
  "created_at": "2025-08-02T12:00:00",
  "confirmed_at": "2025-08-02T12:15:00",
  "subscription_active": true,
  "subscription_expires": "2025-09-01T12:15:00"
}
```

### User Subscription
**GET** `/user/{user_id}/subscription`

Check user's subscription status.

**Response:**
```json
{
  "user_id": "user123",
  "subscription_active": true,
  "subscription_expires": "2025-09-01T12:15:00",
  "days_remaining": 29,
  "created_at": "2025-08-02T12:00:00"
}
```

### Webhook Endpoint
**POST** `/webhook`

Automatically processes BlockBee payment confirmations. This endpoint:

1. Receives payment confirmation from BlockBee
2. Validates payment against order
3. Activates 30-day subscription for user
4. Logs all payment details
5. Prevents duplicate processing

## Database Schema

### Payment Users
```sql
CREATE TABLE payment_users (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    subscription_expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Payment Orders
```sql
CREATE TABLE payment_orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    crypto_type VARCHAR(10) NOT NULL,
    amount_fiat DECIMAL(10,2) NOT NULL,
    amount_crypto DECIMAL(20,8),
    payment_address VARCHAR(255) NOT NULL,
    qr_code_url TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    confirmations_required INTEGER DEFAULT 1,
    confirmations_received INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMP
);
```

### Payment Logs
```sql
CREATE TABLE payment_logs (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(255),
    txid VARCHAR(255),
    amount DECIMAL(20,8),
    confirmations INTEGER,
    status VARCHAR(20),
    webhook_data TEXT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    retry_count INTEGER DEFAULT 0
);
```

## BlockBee Integration

The API uses BlockBee's `/create` endpoint with these parameters:

- **callback**: Your webhook URL
- **order_id**: Unique order identifier
- **value**: Amount in USD (auto-converted to crypto)
- **confirmations**: Set to 1 for fast processing
- **convert**: 1 (converts USD to crypto)
- **post**: 1 (webhook via POST)
- **json**: 1 (JSON responses)

## Webhook Security

The webhook endpoint implements several security measures:

1. **Idempotency**: Prevents duplicate payment processing
2. **Address Matching**: Validates payment address against orders
3. **Status Verification**: Only processes "confirmed" payments
4. **Error Handling**: Returns "ok" even on errors to prevent retries
5. **Comprehensive Logging**: All webhook calls are logged

## Testing

Run the complete test suite:

```bash
python test_payment_api.py
```

**Test Coverage:**
- ✅ Health check endpoint
- ✅ Payment creation with BlockBee
- ✅ Payment status tracking
- ✅ User subscription management
- ✅ Webhook processing simulation
- ✅ Subscription activation verification

## Deployment

### Replit Deployment

1. Set environment variables in Replit Secrets
2. Configure webhook URL: `https://your-repl.replit.app/webhook`
3. Start the server on port 5001

### Production Deployment

1. Use a production WSGI server (gunicorn)
2. Set up SSL/HTTPS for webhook security
3. Configure proper database connection pooling
4. Set up monitoring and logging

```bash
gunicorn -w 4 -b 0.0.0.0:5001 payment_api:app
```

## Error Handling

The API implements comprehensive error handling:

- **Payment Creation**: Validates input and handles BlockBee API errors
- **Webhook Processing**: Continues processing even on errors
- **Database Operations**: Proper transaction handling and rollback
- **Retry Logic**: Built-in retry counters for failed operations

## Supported Cryptocurrencies

- **Bitcoin (BTC)**
- **Ethereum (ETH)**
- **Tether USDT (USDT)**
- **Litecoin (LTC)**
- **And many more supported by BlockBee**

## License

MIT License - feel free to use in your projects!

## Support

For BlockBee API issues, visit: https://blockbee.io/docs/
For this implementation, check the test file for usage examples.