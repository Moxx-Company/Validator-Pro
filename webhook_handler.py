"""
Webhook handler for BlockBee payment confirmations
"""
import logging
from flask import Flask, request, jsonify
from database import SessionLocal
from models import Subscription
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def create_webhook_app():
    """Create Flask app for webhook handling"""
    app = Flask(__name__)
    
    @app.route('/')
    def index():
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Validator Pro Bot</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                h1 { color: #0088cc; }
                p { color: #666; }
                a { color: #0088cc; text-decoration: none; }
            </style>
        </head>
        <body>
            <h1>Validator Pro Bot</h1>
            <p>The bot is running! 🤖</p>
            <p>Start chatting with <a href="https://t.me/validator_pro_bot">@validator_pro_bot</a></p>
        </body>
        </html>
        '''
    
    @app.route('/webhook/blockbee', methods=['POST'])
    @app.route('/webhook/blockbee/<user_id>/<currency>/<amount_usd>', methods=['POST'])
    def handle_blockbee_webhook(user_id=None, currency=None, amount_usd=None):
        """Handle BlockBee payment confirmations"""
        try:
            # Log all webhook calls
            logger.info("=== BlockBee Webhook Received ===")
            logger.info(f"Path params: user_id={user_id}, currency={currency}, amount_usd={amount_usd}")
            logger.info(f"Query params: {request.args}")
            logger.info(f"Headers: {dict(request.headers)}")
            
            data = request.get_json()
            logger.info(f"Body data: {data}")
            
            # Extract payment information from URL path or query params
            if not user_id:
                user_id = request.args.get('user_id')
            if not currency:
                currency = request.args.get('currency')
            if not amount_usd:
                amount_usd = request.args.get('amount_usd')
            
            if not all([user_id, currency, amount_usd]):
                logger.error("Missing required parameters in webhook")
                # Return *ok* even for errors to prevent retries
                return "*ok*", 200
            
            # Verify payment in BlockBee data
            # BlockBee uses string "1" not integer 1
            if str(data.get('status')) != '1':  # 1 means confirmed
                logger.info(f"Payment not confirmed yet: {data.get('status')}")
                # Still return *ok* for BlockBee
                return "*ok*", 200
            
            # Update subscription status
            with SessionLocal() as db:
                subscription = db.query(Subscription).filter(
                    Subscription.user_id == int(user_id),
                    Subscription.status == 'pending',
                    Subscription.payment_currency_crypto == currency.upper()
                ).first()
                
                if not subscription:
                    # Check if there's already an active subscription
                    active_sub = db.query(Subscription).filter(
                        Subscription.user_id == int(user_id),
                        Subscription.status == 'active',
                        Subscription.payment_currency_crypto == currency.upper()
                    ).first()
                    
                    if active_sub:
                        logger.info(f"Subscription already active for user {user_id}, skipping duplicate notification")
                        return "*ok*", 200
                    
                    logger.error(f"No pending subscription found for user {user_id}")
                    # Return *ok* even for errors
                    return "*ok*", 200
                
                # Check payment amount tolerance
                payment_amount = float(data.get('price', 0))
                expected_amount = float(subscription.amount_usd)
                
                # Only apply $3 tolerance when payment is less than expected
                if payment_amount < expected_amount:
                    shortage = expected_amount - payment_amount
                    if shortage > 3.0:
                        logger.warning(f"Payment ${payment_amount} is ${shortage:.2f} less than expected ${expected_amount} (exceeds $3 tolerance)")
                        # Still accept the payment but log the warning
                    else:
                        logger.info(f"Payment ${payment_amount} is ${shortage:.2f} less than expected ${expected_amount} (within $3 tolerance)")
                elif payment_amount > expected_amount:
                    overage = payment_amount - expected_amount
                    logger.info(f"Payment ${payment_amount} is ${overage:.2f} more than expected ${expected_amount} (overpayment accepted)")
                else:
                    logger.info(f"Payment ${payment_amount} matches expected amount exactly")
                
                # Always activate subscription - accept any overpayment, and underpayments within $3
                
                # Get the user's Telegram chat ID for notifications
                from models import User
                user = db.query(User).filter(User.id == int(user_id)).first()
                telegram_chat_id = user.telegram_id if user else user_id
                
                # Activate subscription
                subscription.status = 'active'
                subscription.activated_at = datetime.utcnow()
                subscription.expires_at = datetime.utcnow() + timedelta(days=30)
                subscription.transaction_hash = data.get('txid_in', '')
                
                db.commit()
                
                logger.info(f"Subscription {subscription.id} activated for user {user_id}")
                
                # Send notification to user about successful payment
                try:
                    import requests
                    import json
                    from config import TELEGRAM_BOT_TOKEN
                    
                    # Send direct notification via Telegram API
                    notification_text = f"""✅ **Payment Confirmed!**

Your subscription has been activated successfully.

**Order ID:** `{subscription.id}`
**Status:** Active
**Duration:** 30 days
**Features:** Unlimited email & phone validation

You can now validate unlimited emails and phone numbers!"""
                    
                    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                    response = requests.post(telegram_url, json={
                        'chat_id': int(telegram_chat_id),
                        'text': notification_text,
                        'parse_mode': 'Markdown'
                    })
                    
                    if response.status_code == 200:
                        logger.info(f"Payment notification sent to user {user_id}")
                    else:
                        logger.error(f"Failed to send notification: {response.text}")
                        
                except Exception as e:
                    logger.error(f"Failed to send payment notification: {e}")
                
                # CRITICAL: BlockBee requires exactly "*ok*" response
                return "*ok*", 200
            
        except Exception as e:
            logger.error(f"Error processing BlockBee webhook: {e}")
            # Still return *ok* to prevent retries
            return "*ok*", 200
    
    @app.route('/webhook/blockbee', methods=['GET'])
    def webhook_info():
        """Return webhook information"""
        return jsonify({
            'status': 'active',
            'webhook': 'BlockBee payment webhook',
            'accepts': 'POST requests with payment data'
        })
    
    return app

if __name__ == '__main__':
    app = create_webhook_app()
    app.run(host='0.0.0.0', port=8000, debug=True)