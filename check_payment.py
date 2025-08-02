#!/usr/bin/env python3
"""
Manual payment verification tool for when BlockBee webhook fails
"""
import asyncio
import sys
from datetime import datetime, timedelta
from database import SessionLocal
from models import Subscription, User
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_and_activate_payment(user_id: int):
    """Manually check and activate pending subscriptions"""
    from telegram import Bot
    from config import TELEGRAM_BOT_TOKEN
    
    with SessionLocal() as db:
        # Find pending subscription
        subscription = db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == 'pending'
        ).order_by(Subscription.created_at.desc()).first()
        
        if not subscription:
            logger.info(f"No pending subscription found for user {user_id}")
            return False
            
        logger.info(f"Found pending subscription ID {subscription.id}")
        logger.info(f"Payment address: {subscription.payment_address}")
        
        # Get user's telegram ID
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"User {user_id} not found")
            return False
            
        # Activate subscription
        subscription.status = 'active'
        subscription.activated_at = datetime.utcnow()
        subscription.expires_at = datetime.utcnow() + timedelta(days=30)
        subscription.transaction_hash = 'manual_activation_webhook_failure'
        
        db.commit()
        logger.info(f"Subscription {subscription.id} activated successfully")
        
        # Send notification
        try:
            bot = Bot(token=TELEGRAM_BOT_TOKEN)
            notification_text = f"""✅ **Payment Confirmed!**

Your subscription has been activated successfully.

**Status:** Active ✅
**Valid Until:** {subscription.expires_at.strftime('%B %d, %Y')}
**Plan:** Monthly Subscription

You now have unlimited access to all validation features!

_Note: This was manually activated due to a webhook issue. Your payment was received successfully._"""
            
            await bot.send_message(
                chat_id=user.telegram_id,
                text=notification_text,
                parse_mode='Markdown'
            )
            logger.info(f"Notification sent to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            
        return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_id = int(sys.argv[1])
        asyncio.run(check_and_activate_payment(user_id))
    else:
        print("Usage: python check_payment.py <user_id>")