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
    """Create Flask app for webhook handling (Legacy System)"""
    app = Flask(__name__)
    
    @app.route('/')
    def health_check():
        """Health check endpoint for deployment"""
        return jsonify({
            'status': 'healthy',
            'service': 'Validator Pro Bot (Legacy)',
            'webhook': 'legacy'
        }), 200
    
    @app.route('/health')
    def health():
        """Additional health check endpoint"""
        return jsonify({'status': 'ok'}), 200

    @app.route('/webhook', methods=['POST'])
    @app.route('/webhook/blockbee', methods=['POST', 'GET'])
    def redirect_to_new_system():
        import requests
        try:
            # Preserve the original query string (order_id, uid, coin, ...)
            qs = request.query_string.decode()  # e.g. "order_id=24&uid=1&coin=ltc"
            fwd_url = f"http://localhost:5000/webhook" + (f"?{qs}" if qs else "")

            if request.method == 'POST':
                # Forward raw body + headers so signature verification can work internally
                headers = {"Content-Type": request.headers.get("Content-Type", "application/octet-stream")}
                sig = request.headers.get("x-ca-signature")
                if sig:
                    headers["x-ca-signature"] = sig
                raw = request.get_data(cache=False)
                resp = requests.post(fwd_url, data=raw, headers=headers, timeout=30)
            else:
                # GET has no body; forward only the query params as JSON (for testing/back-compat)
                resp = requests.post(fwd_url, json=request.args.to_dict(flat=True), timeout=30)

            logger.info(f"Forwarded webhook to new system: {resp.status_code}")
            return resp.text, resp.status_code
        except Exception as e:
            logger.error(f"Error forwarding webhook to new system: {e}")
            return "ok", 200

    
    # @app.route('/webhook', methods=['POST'])
    # @app.route('/webhook/blockbee', methods=['POST', 'GET'])
    # def redirect_to_new_system():
    #     """Redirect webhooks to new Payment API system"""
    #     import requests
    #     try:
    #         # Forward webhook to new payment API system
    #         webhook_data = request.get_json() or dict(request.args)
            
    #         # Make request to new system
    #         response = requests.post(
    #             'http://localhost:5000/webhook',
    #             json=webhook_data,
    #             timeout=30
    #         )
            
    #         logger.info(f"Forwarded webhook to new system: {response.status_code}")
    #         return response.text, response.status_code
            
    #     except Exception as e:
    #         logger.error(f"Error forwarding webhook to new system: {e}")
    #         return "ok", 200  # Always return ok to prevent retries
    
    @app.route('/webhook/blockbee/legacy', methods=['POST', 'GET'])
    @app.route('/webhook/blockbee/legacy/<user_id>/<currency>/<amount_usd>', methods=['POST'])
    def handle_blockbee_webhook_legacy(user_id=None, currency=None, amount_usd=None):
        """Handle BlockBee payment confirmations (Legacy System)"""
        try:
            # Log all webhook calls
            logger.info("=== BlockBee Webhook Received ===")
            logger.info(f"Method: {request.method}")
            logger.info(f"Path params: user_id={user_id}, currency={currency}, amount_usd={amount_usd}")
            logger.info(f"Query params: {dict(request.args)}")
            logger.info(f"Headers: {dict(request.headers)}")
            
            # BlockBee sends data as GET parameters by default
            if request.method == 'GET':
                data = dict(request.args)
            else:
                data = request.get_json() or {}
            
            logger.info(f"Webhook data: {data}")
            
            # BlockBee sends payment address as 'address_in' in real webhooks
            payment_address = data.get('address_in') or data.get('address')
            
            if not payment_address:
                logger.error("Missing payment address in webhook data")
                # Return ok even for errors to prevent retries
                return "ok", 200
            
            # Verify payment in BlockBee data
            # BlockBee uses string "1" not integer 1
            if str(data.get('status')) != '1':  # 1 means confirmed
                logger.info(f"Payment not confirmed yet: {data.get('status')}")
                # Still return ok for BlockBee
                return "ok", 200
            
            # Update subscription status - find by payment address
            with SessionLocal() as db:
                # Find subscription by payment address
                subscription = db.query(Subscription).filter(
                    Subscription.payment_address == payment_address
                ).filter(
                    Subscription.status == 'pending'
                ).first()
                
                if not subscription:
                    # Check if there's already an active subscription for this address
                    active_sub = db.query(Subscription).filter(
                        Subscription.payment_address == payment_address
                    ).filter(
                        Subscription.status == 'active'
                    ).first()
                    
                    if active_sub:
                        logger.info(f"Subscription already active for address {payment_address}, skipping duplicate notification")
                        return "ok", 200
                    
                    logger.error(f"No pending subscription found for address {payment_address}")
                    # Return ok even for errors
                    return "ok", 200
                

                
                # Check payment amount tolerance
                payment_amount = float(data.get('price', 0))
                expected_amount = float(subscription.amount_usd) if subscription.amount_usd else 0.0
                
                from config import TOLERANCE
                tolerance = TOLERANCE if TOLERANCE else 2  #
                # Only apply $2 tolerance when payment is less than expected
                if payment_amount < expected_amount:
                    shortage = expected_amount - payment_amount
                    if shortage > tolerance:
                        logger.warning(f"Payment ${payment_amount} is ${shortage:.2f} less than expected ${expected_amount} (exceeds ${tolerance} tolerance)")
                        # Still accept the payment but log the warning
                    else:
                        logger.info(f"Payment ${payment_amount} is ${shortage:.2f} less than expected ${expected_amount} (within ${tolerance} tolerance)")
                elif payment_amount > expected_amount:
                    overage = payment_amount - expected_amount
                    logger.info(f"Payment ${payment_amount} is ${overage:.2f} more than expected ${expected_amount} (overpayment accepted)")
                else:
                    logger.info(f"Payment ${payment_amount} matches expected amount exactly")
                
                # Always activate subscription - accept any overpayment, and underpayments within $3
                
                # Get the user's Telegram chat ID from subscription
                from models import User
                user = db.query(User).filter(User.id == subscription.user_id).first()
                telegram_chat_id = user.telegram_id if user else None
                
                # Activate subscription (already verified subscription exists above)
                if subscription:
                    subscription.status = 'active'
                    subscription.activated_at = datetime.utcnow()
                    subscription.expires_at = datetime.utcnow() + timedelta(days=30)
                    subscription.transaction_hash = data.get('txid_in', '')
                    
                    db.commit()
                    
                    logger.info(f"Subscription {subscription.id} activated for user {subscription.user_id}")
                
                # Send notification to user about successful payment
                try:
                    import requests
                    import json
                    from config import TELEGRAM_BOT_TOKEN
                    
                    logger.info(f"Attempting to send notification to chat_id: {telegram_chat_id}")
                    
                    # Send direct notification via Telegram API
                    notification_text = f"""✅ **Payment Confirmed!**

Your subscription has been activated successfully.

**Order ID:** `{subscription.id if subscription else 'Unknown'}`
**Status:** Active
**Duration:** 30 days
**Features:** Unlimited email & phone validation

You can now validate unlimited emails and phone numbers!"""
                    
                    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                    logger.info(f"Sending notification to Telegram API...")
                    
                    response = requests.post(telegram_url, json={
                        'chat_id': telegram_chat_id,
                        'text': notification_text,
                        'parse_mode': 'Markdown'
                    })
                    
                    logger.info(f"Telegram API response: {response.status_code} - {response.text}")
                    
                    if response.status_code == 200:
                        logger.info(f"✅ Payment notification sent successfully to user {subscription.user_id if subscription else 'unknown'} (chat_id: {telegram_chat_id})")
                    else:
                        logger.error(f"❌ Failed to send notification: {response.text}")
                        
                except Exception as e:
                    logger.error(f"❌ Exception in payment notification: {e}")
                
                # CRITICAL: BlockBee requires exactly "ok" response (not "*ok*")
                return "ok", 200
            
        except Exception as e:
            logger.error(f"Error processing BlockBee webhook: {e}")
            # Still return ok to prevent retries
            return "ok", 200
    
    @app.route('/webhook/test', methods=['GET'])
    def webhook_info():
        """Return webhook information"""
        from config import BLOCKBEE_WEBHOOK_URL
        return jsonify({
            'status': 'active',
            'webhook': 'BlockBee payment webhook',
            'url': BLOCKBEE_WEBHOOK_URL,
            'accepts': 'POST requests with payment data',
            'test_url': f"{request.host_url}webhook/test"
        })
    
    @app.route('/webhook/test', methods=['GET', 'POST'])
    def webhook_test():
        """Test endpoint for webhook connectivity"""
        logger.info("=== Webhook Test Called ===")
        logger.info(f"Method: {request.method}")
        logger.info(f"Headers: {dict(request.headers)}")
        if request.method == 'POST':
            data = request.get_json()
            logger.info(f"Body: {data}")
        
        return jsonify({
            'status': 'success',
            'message': 'Webhook test endpoint working',
            'method': request.method,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    @app.route('/webhook/logs', methods=['GET'])
    def webhook_logs():
        """Show recent webhook activity"""
        from models import Subscription
        with SessionLocal() as db:
            pending_subs = db.query(Subscription).filter(
                Subscription.status == 'pending'
            ).order_by(Subscription.created_at.desc()).limit(5).all()
            
            return jsonify({
                'pending_subscriptions': [
                    {
                        'id': s.id,
                        'user_id': s.user_id,
                        'address': s.payment_address,
                        'currency': s.payment_currency_crypto,
                        'created': s.created_at.isoformat() if s.created_at else None
                    } for s in pending_subs
                ]
            })
    
    return app

if __name__ == '__main__':
    app = create_webhook_app()
    app.run(host='0.0.0.0', port=5000, debug=False)