"""
Webhook handler for BlockBee cryptocurrency payment notifications
"""
import logging
from flask import Flask, request, jsonify
from database import SessionLocal
from models import User, Subscription
from datetime import datetime, timedelta
from config import SUBSCRIPTION_DURATION_DAYS

logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/webhook/blockbee', methods=['POST'])
def handle_blockbee_webhook():
    """Handle BlockBee payment webhook notifications"""
    try:
        # Get payment data from BlockBee
        data = request.json
        
        # Extract payment information
        user_id = request.args.get('user_id')
        currency = request.args.get('currency')
        amount_usd = float(request.args.get('amount_usd', 0))
        
        # Verify payment
        if not data.get('confirmed', False):
            return jsonify({'status': 'pending'}), 200
        
        # Find user and subscription
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == int(user_id)).first()
            if not user:
                logger.error(f"User not found: {user_id}")
                return jsonify({'error': 'User not found'}), 404
            
            # Find pending subscription for this user and currency
            subscription = db.query(Subscription).filter(
                Subscription.user_id == user.id,
                Subscription.status == 'pending',
                Subscription.payment_currency_crypto == currency.upper()
            ).first()
            
            if not subscription:
                logger.error(f"Subscription not found for user {user_id} and currency {currency}")
                return jsonify({'error': 'Subscription not found'}), 404
            
            # Verify payment amount
            amount_received = float(data.get('amount_received', 0))
            if amount_received < subscription.payment_amount_crypto * 0.95:  # Allow 5% tolerance
                logger.error(f"Insufficient payment: {amount_received} < {subscription.payment_amount_crypto}")
                return jsonify({'error': 'Insufficient payment'}), 400
            
            # Activate subscription
            subscription.status = 'active'
            subscription.activated_at = datetime.utcnow()
            subscription.expires_at = datetime.utcnow() + timedelta(days=SUBSCRIPTION_DURATION_DAYS)
            subscription.transaction_hash = data.get('txid_in')
            
            db.commit()
            
            logger.info(f"Subscription activated for user {user_id}")
            
            # TODO: Send confirmation message to user via Telegram
            
            return jsonify({'status': 'success'}), 200
            
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)