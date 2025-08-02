"""
Test script to manually trigger webhook for payment confirmation
"""
import requests
import json
import sys

def test_webhook(subscription_id=4):
    """Manually trigger webhook for testing"""
    
    # Get subscription details from database
    import os
    os.environ['DATABASE_URL'] = os.getenv('DATABASE_URL')
    
    from database import SessionLocal
    from models import Subscription, User
    
    with SessionLocal() as db:
        subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
        if not subscription:
            print(f"Subscription {subscription_id} not found")
            return
            
        user = db.query(User).filter(User.id == subscription.user_id).first()
        if not user:
            print(f"User not found for subscription {subscription_id}")
            return
            
        print(f"Testing webhook for:")
        print(f"- User ID: {user.id}")
        print(f"- Telegram ID: {user.telegram_id}")
        print(f"- Payment Address: {subscription.payment_address}")
        print(f"- Currency: {subscription.payment_currency_crypto}")
        print(f"- Amount: ${subscription.amount_usd}")
        
        # Simulate BlockBee webhook
        webhook_url = f"http://localhost:5000/webhook/blockbee/{user.id}/{subscription.payment_currency_crypto.lower()}/{subscription.amount_usd}"
        
        webhook_data = {
            "status": 1,  # 1 means confirmed
            "address_in": subscription.payment_address,
            "address_out": "test_address",
            "txid_in": "test_transaction_hash_123",
            "txid_out": "test_out_hash",
            "confirmations": 3,
            "value": int(subscription.payment_amount_crypto * 100000000),  # In satoshis
            "value_coin": subscription.payment_amount_crypto,
            "value_forwarded": subscription.payment_amount_crypto,
            "value_forwarded_coin": subscription.payment_amount_crypto,
            "coin": subscription.payment_currency_crypto.lower(),
            "price": subscription.amount_usd,
            "pending": 0
        }
        
        print(f"\nSending webhook to: {webhook_url}")
        print(f"Data: {json.dumps(webhook_data, indent=2)}")
        
        try:
            response = requests.post(webhook_url, json=webhook_data)
            print(f"\nResponse Status: {response.status_code}")
            print(f"Response Body: {response.text}")
            
            # Check if subscription was activated
            db.refresh(subscription)
            print(f"\nSubscription Status After: {subscription.status}")
            print(f"Activated At: {subscription.activated_at}")
            
        except Exception as e:
            print(f"Error sending webhook: {e}")

if __name__ == "__main__":
    subscription_id = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    test_webhook(subscription_id)