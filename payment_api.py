"""
BlockBee Payment API Integration
Handles crypto payment generation and webhook processing
"""
import os
import logging
import requests
import asyncio
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Boolean, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import UUID
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///payment_system.db')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# BlockBee API configuration
BLOCKBEE_API_KEY = os.getenv('BLOCKBEE_API_KEY', 'your_api_key_here')
BLOCKBEE_BASE_URL = 'https://api.blockbee.io'
WEBHOOK_BASE_URL = os.getenv('WEBHOOK_BASE_URL', 'https://verifyemailphone.replit.app')

# Telegram Bot configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_API_URL = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}'

class PaymentUser(Base):
    __tablename__ = 'payment_users'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)  # External user ID
    email = Column(String, unique=True, index=True)
    subscription_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PaymentOrder(Base):
    __tablename__ = 'payment_orders'
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True, index=True)
    user_id = Column(String, index=True)
    crypto_type = Column(String)  # BTC, USDT, etc.
    amount_fiat = Column(Float)  # Amount in USD
    amount_crypto = Column(Float, nullable=True)  # Amount in crypto
    payment_address = Column(String)
    qr_code_url = Column(String, nullable=True)
    status = Column(String, default='pending')  # pending, confirmed, expired
    confirmations_required = Column(Integer, default=1)
    confirmations_received = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)

class PaymentLog(Base):
    __tablename__ = 'payment_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, index=True)
    txid = Column(String)
    amount = Column(Float)
    confirmations = Column(Integer)
    status = Column(String)
    webhook_data = Column(Text)  # Store full webhook payload
    processed_at = Column(DateTime, default=datetime.utcnow)
    retry_count = Column(Integer, default=0)

# Create tables
Base.metadata.create_all(bind=engine)

# Flask app
app = Flask(__name__)

def get_db():
    """Get database session"""
    return SessionLocal()

def send_telegram_notification(user_id: str, order_id: str, subscription_expires: str):
    """Send payment confirmation notification via Telegram"""
    try:
        if not TELEGRAM_BOT_TOKEN:
            logger.warning("No Telegram bot token configured - skipping notification")
            return False
        
        # Try to parse user_id as Telegram chat ID
        try:
            chat_id = int(user_id)
        except ValueError:
            logger.warning(f"User ID '{user_id}' is not a valid Telegram chat ID - skipping notification")
            return False
        
        notification_text = f"""✅ **Payment Confirmed!**

Your cryptocurrency payment has been processed successfully.

**Order ID:** `{order_id}`
**Status:** Active
**Subscription:** 30 days
**Expires:** {subscription_expires[:10]}  

🎉 Your subscription is now active! You can now validate unlimited emails and phone numbers.

Thank you for choosing Validator Pro!"""
        
        # Send message via Telegram API
        telegram_url = f"{TELEGRAM_API_URL}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': notification_text,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True
        }
        
        response = requests.post(telegram_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"Payment notification sent to user {user_id}")
            return True
        else:
            logger.error(f"Failed to send Telegram notification: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {e}")
        return False

@app.route('/create-payment', methods=['POST'])
def create_payment():
    """
    Create a crypto payment using BlockBee's /pay API
    
    Expected JSON payload:
    {
        "user_id": "user123",
        "crypto_type": "btc",  # or "usdt", "eth", etc.
        "amount_usd": 10.0,
        "email": "user@example.com" (optional)
    }
    """
    try:
        data = request.get_json()
        
        # Validate input
        user_id = data.get('user_id')
        crypto_type = data.get('crypto_type', 'btc').lower()
        amount_usd = float(data.get('amount_usd', 10.0))
        email = data.get('email', '')
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        # Generate unique order ID
        order_id = f"order_{uuid.uuid4().hex[:12]}"
        
        # Prepare BlockBee API request
        callback_url = f"{WEBHOOK_BASE_URL}/webhook"
        
        # Use BlockBee's /pay endpoint
        blockbee_url = f"{BLOCKBEE_BASE_URL}/{crypto_type}/create/"
        
        payload = {
            'callback': callback_url,
            'apikey': BLOCKBEE_API_KEY,
            'order_id': order_id,
            'value': amount_usd,  # Amount in USD
            'confirmations': 1,
            'post': 1,  # Use POST for webhook
            'json': 1,  # JSON response
            'convert': 1  # Convert USD to crypto
        }
        
        logger.info(f"Creating BlockBee payment for order {order_id}")
        logger.info(f"Request URL: {blockbee_url}")
        logger.info(f"Payload: {payload}")
        
        # Make request to BlockBee
        response = requests.get(blockbee_url, params=payload, timeout=30)
        response.raise_for_status()
        
        blockbee_data = response.json()
        logger.info(f"BlockBee response: {blockbee_data}")
        
        if blockbee_data.get('status') != 'success':
            return jsonify({
                'error': 'Failed to generate payment address',
                'details': blockbee_data
            }), 400
        
        # Extract payment info
        payment_address = blockbee_data.get('address_in')
        qr_code_url = blockbee_data.get('qr_code')
        amount_crypto = blockbee_data.get('value_coin')
        
        # Store in database
        db = get_db()
        try:
            # Create or update user
            user = db.query(PaymentUser).filter(PaymentUser.user_id == user_id).first()
            if not user:
                user = PaymentUser(user_id=user_id, email=email)
                db.add(user)
            elif email and email != user.email:
                user.email = email
                user.updated_at = datetime.utcnow()
            
            # Create payment order
            payment_order = PaymentOrder(
                order_id=order_id,
                user_id=user_id,
                crypto_type=crypto_type.upper(),
                amount_fiat=amount_usd,
                amount_crypto=amount_crypto,
                payment_address=payment_address,
                qr_code_url=qr_code_url,
                status='pending',
                confirmations_required=1
            )
            
            db.add(payment_order)
            db.commit()
            
            # Return payment info to user
            return jsonify({
                'success': True,
                'order_id': order_id,
                'payment_address': payment_address,
                'amount_usd': amount_usd,
                'amount_crypto': amount_crypto,
                'crypto_type': crypto_type.upper(),
                'qr_code_url': qr_code_url,
                'confirmations_required': 1,
                'message': f'Send exactly {amount_crypto} {crypto_type.upper()} to the address above'
            })
        except Exception as db_e:
            db.rollback()
            logger.error(f"Database error creating payment: {db_e}")
            return jsonify({'error': f'Database error: {str(db_e)}'}), 500
        finally:
            db.close()
        
    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    BlockBee webhook endpoint
    Processes payment confirmations and activates subscriptions
    """
    try:
        # Get webhook data
        webhook_data = request.get_json() or {}
        
        # Also check query parameters (BlockBee sometimes sends data this way)
        if not webhook_data:
            webhook_data = dict(request.args)
        
        logger.info(f"Webhook received: {webhook_data}")
        
        # Extract important fields
        order_id = webhook_data.get('order_id')
        address_in = webhook_data.get('address_in')
        txid = webhook_data.get('txid_in', webhook_data.get('txid'))
        confirmations = int(webhook_data.get('confirmations', 0))
        status = webhook_data.get('status')
        amount = float(webhook_data.get('value_coin', 0))
        
        if not order_id and not address_in:
            logger.error("No order_id or address_in found in webhook")
            return "ok", 200  # Still return ok to prevent retries
        
        db = get_db()
        
        # Find payment order by order_id or address
        payment_order = None
        if order_id:
            payment_order = db.query(PaymentOrder).filter(PaymentOrder.order_id == order_id).first()
        elif address_in:
            payment_order = db.query(PaymentOrder).filter(PaymentOrder.payment_address == address_in).first()
        
        if not payment_order:
            logger.error(f"Payment order not found for order_id: {order_id}, address: {address_in}")
            return "ok", 200
        
        # Log the payment webhook
        payment_log = PaymentLog(
            order_id=payment_order.order_id,
            txid=txid or 'unknown',
            amount=amount,
            confirmations=confirmations,
            status=status or 'unknown',
            webhook_data=str(webhook_data)
        )
        db.add(payment_log)
        
        # Check if payment is confirmed
        if status == 'confirmed' or (confirmations >= payment_order.confirmations_required):
            
            # Prevent duplicate processing
            if payment_order.status == 'confirmed':
                logger.info(f"Order {payment_order.order_id} already confirmed, skipping")
                db.commit()
                return "ok", 200
            
            logger.info(f"Payment confirmed for order {payment_order.order_id}")
            
            # Update payment order status
            payment_order.status = 'confirmed'
            payment_order.confirmations_received = confirmations
            payment_order.confirmed_at = datetime.utcnow()
            
            # Activate 30-day subscription for user
            user = db.query(PaymentUser).filter(PaymentUser.user_id == payment_order.user_id).first()
            if user:
                # Extend subscription by 30 days from now or from current expiry
                current_expiry = user.subscription_expires_at
                if current_expiry and current_expiry > datetime.utcnow():
                    # Extend from current expiry
                    new_expiry = current_expiry + timedelta(days=30)
                else:
                    # Start from now
                    new_expiry = datetime.utcnow() + timedelta(days=30)
                
                user.subscription_expires_at = new_expiry
                user.updated_at = datetime.utcnow()
                
                logger.info(f"Activated 30-day subscription for user {user.user_id} until {new_expiry}")
                
                # Send Telegram notification to user
                try:
                    notification_sent = send_telegram_notification(
                        user_id=user.user_id,
                        order_id=payment_order.order_id,
                        subscription_expires=new_expiry.isoformat()
                    )
                    if notification_sent:
                        logger.info(f"Telegram notification sent to user {user.user_id}")
                    else:
                        logger.warning(f"Failed to send Telegram notification to user {user.user_id}")
                except Exception as notify_error:
                    logger.error(f"Error sending notification to user {user.user_id}: {notify_error}")
            
            db.commit()
            logger.info(f"Successfully processed payment confirmation for order {payment_order.order_id}")
            
        else:
            logger.info(f"Payment not yet confirmed: {confirmations}/{payment_order.confirmations_required} confirmations")
            payment_order.confirmations_received = confirmations
            db.commit()
        
        return "ok", 200
        
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        # Still return ok to prevent endless retries
        return "ok", 200
    finally:
        db.close()

@app.route('/payment/<order_id>/status', methods=['GET'])
def get_payment_status(order_id):
    """Get payment status for an order"""
    try:
        db = get_db()
        
        payment_order = db.query(PaymentOrder).filter(PaymentOrder.order_id == order_id).first()
        if not payment_order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Get user subscription info
        user = db.query(PaymentUser).filter(PaymentUser.user_id == payment_order.user_id).first()
        subscription_active = False
        subscription_expires = None
        
        if user and user.subscription_expires_at:
            subscription_active = user.subscription_expires_at > datetime.utcnow()
            subscription_expires = user.subscription_expires_at.isoformat()
        
        return jsonify({
            'order_id': payment_order.order_id,
            'status': payment_order.status,
            'payment_address': payment_order.payment_address,
            'amount_fiat': payment_order.amount_fiat,
            'amount_crypto': payment_order.amount_crypto,
            'crypto_type': payment_order.crypto_type,
            'confirmations_received': payment_order.confirmations_received,
            'confirmations_required': payment_order.confirmations_required,
            'created_at': payment_order.created_at.isoformat(),
            'confirmed_at': payment_order.confirmed_at.isoformat() if payment_order.confirmed_at else None,
            'subscription_active': subscription_active,
            'subscription_expires': subscription_expires
        })
        
    except Exception as e:
        logger.error(f"Error getting payment status: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/user/<user_id>/subscription', methods=['GET'])
def get_user_subscription(user_id):
    """Get user subscription status"""
    try:
        db = get_db()
        
        user = db.query(PaymentUser).filter(PaymentUser.user_id == user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        subscription_active = False
        days_remaining = 0
        
        if user.subscription_expires_at:
            subscription_active = user.subscription_expires_at > datetime.utcnow()
            if subscription_active:
                days_remaining = (user.subscription_expires_at - datetime.utcnow()).days
        
        return jsonify({
            'user_id': user.user_id,
            'subscription_active': subscription_active,
            'subscription_expires': user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
            'days_remaining': days_remaining,
            'created_at': user.created_at.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting user subscription: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/', methods=['GET'])
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'BlockBee Payment API (Default System)',
        'timestamp': datetime.utcnow().isoformat(),
        'port': 5000,
        'system': 'primary'
    })

if __name__ == '__main__':
    logger.info("Starting BlockBee Payment API server...")
    app.run(host='0.0.0.0', port=5000, debug=False)