"""
Test script for subscription expiry notifications
Creates test subscriptions and runs expiry checks
"""
import asyncio
from datetime import datetime, timedelta
from database import SessionLocal, init_database
from models import User, Subscription
from subscription_expiry_notifier import run_expiry_check

async def create_test_subscriptions():
    """Create test subscriptions for expiry testing"""
    init_database()
    
    with SessionLocal() as db:
        # Create a test user (replace with your Telegram ID for testing)
        test_telegram_id = "123456789"  # Replace with your actual Telegram ID
        
        user = db.query(User).filter(User.telegram_id == test_telegram_id).first()
        if not user:
            user = User(
                telegram_id=test_telegram_id,
                username="test_user",
                first_name="Test",
                last_name="User"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Create subscription expiring in 3 days (for warning test)
        warning_subscription = Subscription(
            user_id=user.id,
            status='active',
            amount_usd=5.00,
            currency='USD',
            payment_currency_crypto='BTC',
            activated_at=datetime.utcnow() - timedelta(days=27),
            expires_at=datetime.utcnow() + timedelta(days=3),
            expiry_warning_sent=False
        )
        
        # Create subscription expiring today (for final notice test)  
        final_subscription = Subscription(
            user_id=user.id,
            status='active',
            amount_usd=5.00,
            currency='USD',
            payment_currency_crypto='ETH',
            activated_at=datetime.utcnow() - timedelta(days=29),
            expires_at=datetime.utcnow() + timedelta(hours=12),
            expiry_final_notice_sent=False
        )
        
        # Create expired subscription (for deactivation test)
        expired_subscription = Subscription(
            user_id=user.id,
            status='active',
            amount_usd=5.00,
            currency='USD',
            payment_currency_crypto='USDT',
            activated_at=datetime.utcnow() - timedelta(days=31),
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        
        db.add(warning_subscription)
        db.add(final_subscription)
        db.add(expired_subscription)
        db.commit()
        
        print("Created test subscriptions:")
        print(f"- Warning subscription (expires in 3 days): ID {warning_subscription.id}")
        print(f"- Final notice subscription (expires today): ID {final_subscription.id}")
        print(f"- Expired subscription: ID {expired_subscription.id}")
        print(f"- Test user Telegram ID: {test_telegram_id}")

async def test_expiry_notifications():
    """Test the expiry notification system"""
    print("Running expiry check...")
    await run_expiry_check()
    print("Expiry check completed!")

if __name__ == "__main__":
    print("=== Subscription Expiry Notification Test ===")
    print("\n1. Creating test subscriptions...")
    asyncio.run(create_test_subscriptions())
    
    print("\n2. Running expiry notifications...")
    asyncio.run(test_expiry_notifications())
    
    print("\n3. Test completed!")
    print("Check your Telegram bot for notifications if you used your real Telegram ID.")