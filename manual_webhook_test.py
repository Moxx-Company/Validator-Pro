"""
Manual webhook test to simulate BlockBee payment confirmation
"""
import requests
import json
import sys
from database import SessionLocal
from models import Subscription

def trigger_webhook_for_pending_payment():
    """Manually trigger webhook for pending payment"""
    
    # Find pending subscription
    with SessionLocal() as db:
        pending_sub = db.query(Subscription).filter(
            Subscription.status == 'pending'
        ).order_by(Subscription.created_at.desc()).first()
        
        if not pending_sub:
            print("No pending subscriptions found")
            return
        
        print(f"Found pending subscription:")
        print(f"  ID: {pending_sub.id}")
        print(f"  User ID: {pending_sub.user_id}")
        print(f"  Address: {pending_sub.payment_address}")
        print(f"  Currency: {pending_sub.payment_currency_crypto}")
        print(f"  Amount: {pending_sub.payment_amount_crypto} {pending_sub.payment_currency_crypto}")
        
        # Simulate BlockBee webhook data
        webhook_data = {
            "status": "1",  # Confirmed
            "value": str(pending_sub.payment_amount_crypto),
            "address": pending_sub.payment_address,
            "txid_in": "simulated_transaction_hash",
            "confirmations": "1"
        }
        
        # Build webhook URL
        webhook_url = f"http://localhost:5000/webhook/blockbee/{pending_sub.user_id}/{pending_sub.payment_currency_crypto.lower()}/{pending_sub.amount_usd}"
        
        print(f"\nTriggering webhook to: {webhook_url}")
        print(f"With data: {json.dumps(webhook_data, indent=2)}")
        
        try:
            response = requests.post(
                webhook_url,
                json=webhook_data,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"\nResponse: {response.status_code}")
            print(f"Body: {response.text}")
            
            if response.text == "*ok*":
                print("\n✅ Webhook processed successfully!")
                print("Check your Telegram for the payment confirmation message.")
            else:
                print("\n❌ Unexpected response from webhook")
                
        except Exception as e:
            print(f"\nError calling webhook: {e}")

if __name__ == "__main__":
    print("Manual BlockBee Webhook Trigger")
    print("=" * 40)
    trigger_webhook_for_pending_payment()