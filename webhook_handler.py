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
    
    @app.route('/webhook/blockbee', methods=['POST'])
    @app.route('/webhook/blockbee/<user_id>/<currency>/<amount_usd>', methods=['POST'])
    def handle_blockbee_webhook(user_id=None, currency=None, amount_usd=None):
        """Handle BlockBee payment confirmations"""
        try:
            data = request.get_json()
            
            # Log the webhook data for debugging
            logger.info(f"BlockBee webhook received: {data}")
            
            # Extract payment information from URL path or query params
            if not user_id:
                user_id = request.args.get('user_id')
            if not currency:
                currency = request.args.get('currency')
            if not amount_usd:
                amount_usd = request.args.get('amount_usd')
            
            if not all([user_id, currency, amount_usd]):
                logger.error("Missing required parameters in webhook")
                return jsonify({'status': 'error', 'message': 'Missing parameters'}), 400
            
            # Verify payment in BlockBee data
            if data.get('status') != 1:  # 1 means confirmed
                logger.info(f"Payment not confirmed yet: {data.get('status')}")
                return jsonify({'status': 'pending'}), 200
            
            # Update subscription status
            with SessionLocal() as db:
                subscription = db.query(Subscription).filter(
                    Subscription.user_id == int(user_id),
                    Subscription.status == 'pending',
                    Subscription.payment_currency_crypto == currency.upper()
                ).first()
                
                if not subscription:
                    logger.error(f"No pending subscription found for user {user_id}")
                    return jsonify({'status': 'error', 'message': 'Subscription not found'}), 404
                
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
                
                return jsonify({'status': 'success'}), 200
            
        except Exception as e:
            logger.error(f"Error processing BlockBee webhook: {e}")
            return jsonify({'status': 'error', 'message': 'Internal error'}), 500
    
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