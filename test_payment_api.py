"""
Test script for BlockBee Payment API
Demonstrates how to create payments and handle webhooks
"""
import requests
import json
import time

# Configuration
API_BASE_URL = 'http://localhost:5001'  # Change to your deployed URL
TEST_USER_ID = 'test_user_123'

def test_create_payment():
    """Test payment creation"""
    print("=== Testing Payment Creation ===")
    
    # Create a payment
    payment_data = {
        'user_id': TEST_USER_ID,
        'crypto_type': 'btc',
        'amount_usd': 10.0,
        'email': 'test@example.com'
    }
    
    response = requests.post(f'{API_BASE_URL}/create-payment', json=payment_data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Payment created successfully!")
        print(f"Order ID: {result['order_id']}")
        print(f"Payment Address: {result['payment_address']}")
        print(f"Amount: {result['amount_crypto']} {result['crypto_type']}")
        print(f"QR Code: {result.get('qr_code_url', 'N/A')}")
        return result['order_id']
    else:
        print(f"❌ Failed to create payment: {response.text}")
        return None

def test_payment_status(order_id):
    """Test payment status check"""
    print(f"\n=== Testing Payment Status for {order_id} ===")
    
    response = requests.get(f'{API_BASE_URL}/payment/{order_id}/status')
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Payment status retrieved:")
        print(f"Status: {result['status']}")
        print(f"Confirmations: {result['confirmations_received']}/{result['confirmations_required']}")
        print(f"Subscription Active: {result['subscription_active']}")
    else:
        print(f"❌ Failed to get status: {response.text}")

def test_user_subscription():
    """Test user subscription status"""
    print(f"\n=== Testing User Subscription for {TEST_USER_ID} ===")
    
    response = requests.get(f'{API_BASE_URL}/user/{TEST_USER_ID}/subscription')
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ User subscription status:")
        print(f"Active: {result['subscription_active']}")
        print(f"Days Remaining: {result['days_remaining']}")
        print(f"Expires: {result.get('subscription_expires', 'Never')}")
    else:
        print(f"❌ Failed to get subscription: {response.text}")

def simulate_webhook(order_id, payment_address):
    """Simulate a webhook from BlockBee"""
    print(f"\n=== Simulating Webhook for {order_id} ===")
    
    # Simulate confirmed payment webhook
    webhook_data = {
        'order_id': order_id,
        'address_in': payment_address,
        'txid_in': 'test_transaction_123',
        'confirmations': 1,
        'status': 'confirmed',
        'value_coin': 0.00025,  # Example BTC amount
        'coin': 'btc'
    }
    
    response = requests.post(f'{API_BASE_URL}/webhook', json=webhook_data)
    
    if response.status_code == 200:
        print(f"✅ Webhook processed successfully")
        print(f"Response: {response.text}")
    else:
        print(f"❌ Webhook failed: {response.text}")

def test_health():
    """Test health endpoint"""
    print("=== Testing Health Check ===")
    
    response = requests.get(f'{API_BASE_URL}/health')
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Service is healthy: {result['status']}")
        print(f"Timestamp: {result['timestamp']}")
    else:
        print(f"❌ Health check failed: {response.text}")

def main():
    """Run all tests"""
    print("🚀 Starting BlockBee Payment API Tests\n")
    
    # Test health first
    test_health()
    
    # Create a payment
    order_id = test_create_payment()
    
    if order_id:
        # Check initial status
        test_payment_status(order_id)
        
        # Check user subscription (should be inactive)
        test_user_subscription()
        
        # Get payment details for webhook simulation
        response = requests.get(f'{API_BASE_URL}/payment/{order_id}/status')
        if response.status_code == 200:
            payment_data = response.json()
            payment_address = payment_data['payment_address']
            
            # Simulate webhook
            simulate_webhook(order_id, payment_address)
            
            # Wait a moment
            time.sleep(1)
            
            # Check status after webhook
            test_payment_status(order_id)
            
            # Check user subscription (should now be active)
            test_user_subscription()
    
    print("\n✅ All tests completed!")

if __name__ == '__main__':
    main()