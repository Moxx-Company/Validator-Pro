"""
Test script to create a new payment with the fixed BlockBee integration
"""
import sys
sys.path.append('.')
from services.blockbee_service import BlockBeeService
import json

def test_new_payment():
    """Test creating a new payment address with fixed callback URL"""
    
    print("Testing Fixed BlockBee Integration")
    print("=" * 50)
    
    service = BlockBeeService()
    print(f"Webhook base URL: {service.webhook_url}")
    
    # Test payment creation
    test_params = {
        'currency': 'btc',
        'user_id': '999',  # Test user
        'amount_usd': 9.99
    }
    
    print(f"\nCreating test payment address...")
    print(f"Parameters: {json.dumps(test_params, indent=2)}")
    
    result = service.create_payment_address(**test_params)
    
    if result['success']:
        print(f"\n✅ SUCCESS: Payment address created")
        print(f"Address: {result['address']}")
        print(f"Amount: {result['amount_crypto']} BTC")
        print(f"USD Value: ${result['amount_usd']}")
        
        # Extract the callback URL that was used
        print(f"\n📡 Callback URL Format:")
        print(f"Base: {service.webhook_url}")
        print(f"With params: {service.webhook_url}?user_id=999&currency=btc&amount_usd=9.99&t=<timestamp>&uid=<unique_id>")
        
        print("\n🔍 Testing BlockBee logs endpoint...")
        import requests
        
        # Try to check if callback is registered
        logs_url = 'https://api.blockbee.io/btc/logs/'
        params = {
            'callback': service.webhook_url,
            'apikey': service.api_key
        }
        
        try:
            response = requests.get(logs_url, params=params)
            print(f"Logs response: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Logs data: {json.dumps(data, indent=2)}")
            else:
                print(f"Logs error: {response.text}")
        except Exception as e:
            print(f"Error checking logs: {e}")
            
    else:
        print(f"\n❌ FAILED: {result.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 50)
    print("Test complete. Check if callback URL is properly registered.")

if __name__ == "__main__":
    test_new_payment()