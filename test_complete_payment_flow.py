"""
Test complete payment flow with fixed BlockBee integration
"""
import sys
sys.path.append('.')
from services.blockbee_service import BlockBeeService
from database import SessionLocal
from models import Subscription, User
import datetime
import json
import requests

def test_complete_payment_flow():
    """Test the complete payment flow from creation to webhook"""
    
    print("Testing Complete Payment Flow")
    print("=" * 60)
    
    # Step 1: Create a test subscription in database
    test_user_id = 888
    test_currency = 'ltc'
    test_amount = 9.99
    
    with SessionLocal() as db:
        # Clean up any existing test data
        db.query(Subscription).filter(Subscription.user_id == test_user_id).delete()
        db.query(User).filter(User.id == test_user_id).delete()
        db.commit()
        
        # Create test user first
        test_user = User(
            id=test_user_id,
            telegram_id=888888888,
            username='test_user_888',
            first_name='Test',
            language_code='en'
        )
        db.add(test_user)
        db.commit()
        
        print(f"✅ Created test user ID: {test_user.id}")
        
        # Create new subscription
        subscription = Subscription(
            user_id=test_user_id,
            status='pending',
            amount_usd=test_amount,
            payment_currency_crypto=test_currency.upper(),
            created_at=datetime.datetime.utcnow(),
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=30)
        )
        db.add(subscription)
        db.commit()
        
        print(f"✅ Created test subscription ID: {subscription.id}")
        
        # Step 2: Create payment address via BlockBee
        service = BlockBeeService()
        result = service.create_payment_address(
            currency=test_currency,
            user_id=str(test_user_id),
            amount_usd=test_amount
        )
        
        if result['success']:
            payment_address = result['address']
            payment_amount = result['amount_crypto']
            
            print(f"✅ Payment address created: {payment_address}")
            print(f"   Amount: {payment_amount} {test_currency.upper()}")
            
            # Step 3: Update subscription with payment details
            subscription.payment_address = payment_address
            subscription.payment_amount_crypto = payment_amount
            db.commit()
            
            print(f"✅ Updated subscription with payment details")
            
            # Step 4: Simulate BlockBee webhook
            print(f"\n📡 Simulating BlockBee webhook...")
            
            webhook_data = {
                'address': payment_address,
                'status': '1',  # Confirmed
                'value': str(payment_amount),
                'txid_in': 'test_transaction_' + datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S'),
                'confirmations': '1'
            }
            
            # Send webhook to our endpoint
            webhook_url = 'http://localhost:5000/webhook/blockbee'
            headers = {'Content-Type': 'application/json'}
            
            response = requests.post(webhook_url, json=webhook_data, headers=headers)
            
            print(f"   Webhook response: {response.status_code}")
            print(f"   Response body: {response.text}")
            
            if response.status_code == 200 and response.text == 'ok':
                print(f"✅ Webhook processed successfully!")
                
                # Step 5: Verify subscription is activated
                db.refresh(subscription)
                if subscription.status == 'active':
                    print(f"✅ Subscription activated successfully!")
                    print(f"   User {test_user_id} should have received notification")
                else:
                    print(f"❌ Subscription not activated. Status: {subscription.status}")
            else:
                print(f"❌ Webhook failed")
                
        else:
            print(f"❌ Failed to create payment address: {result.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 60)
    print("Test complete!")

if __name__ == "__main__":
    test_complete_payment_flow()