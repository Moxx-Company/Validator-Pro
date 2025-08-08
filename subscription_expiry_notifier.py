"""
Subscription Expiry Notification System
Handles automated notifications for subscription expiries
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User, Subscription
from telegram import Bot
from telegram.error import TelegramError
from config import TELEGRAM_BOT_TOKEN, SUPPORT_EMAIL

logger = logging.getLogger(__name__)

class SubscriptionExpiryNotifier:
    def __init__(self):
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    async def check_expiring_subscriptions(self):
        """Check for subscriptions that need expiry notifications"""
        try:
            with SessionLocal() as db:
                # Get current time
                now = datetime.utcnow()
                three_days_from_now = now + timedelta(days=3)
                
                # Find subscriptions expiring in 3 days (warning notification)
                warning_subscriptions = db.query(Subscription).join(User).filter(
                    Subscription.status == 'active',
                    Subscription.expires_at <= three_days_from_now,
                    Subscription.expires_at > now,
                    Subscription.expiry_warning_sent != True  # Haven't sent warning yet
                ).all()
                
                # Find subscriptions expiring today (final notification)
                expiring_today_subscriptions = db.query(Subscription).join(User).filter(
                    Subscription.status == 'active',
                    Subscription.expires_at <= now + timedelta(hours=24),
                    Subscription.expires_at > now,
                    Subscription.expiry_final_notice_sent != True  # Haven't sent final notice
                ).all()
                
                # Send warning notifications (3 days before)
                for subscription in warning_subscriptions:
                    await self._send_expiry_warning(subscription, db)
                
                # Send final notifications (expiry day)
                for subscription in expiring_today_subscriptions:
                    await self._send_expiry_final_notice(subscription, db)
                
                # Check for expired subscriptions to deactivate
                await self._deactivate_expired_subscriptions(db)
                
        except Exception as e:
            logger.error(f"Error checking expiring subscriptions: {e}")
    
    async def _send_expiry_warning(self, subscription: Subscription, db: Session):
        """Send 3-day expiry warning notification"""
        try:
            user = subscription.user
            days_remaining = (subscription.expires_at - datetime.utcnow()).days + 1
            
            warning_message = f"""⚠️ **Subscription Expiry Warning**

Your Validator Pro subscription will expire in **{days_remaining} days**.

**Expiry Date:** {subscription.expires_at.strftime('%B %d, %Y')}
**Current Status:** Active
**Features:** Unlimited email & phone validation

**Renew now to avoid service interruption:**
• Go to /subscription menu
• Select your preferred cryptocurrency
• Complete payment to extend for another 30 days

Need help? Contact @{SUPPORT_EMAIL}."""

            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=warning_message,
                parse_mode='Markdown'
            )
            
            # Mark warning as sent
            subscription.expiry_warning_sent = True
            db.commit()
            
            logger.info(f"Sent expiry warning to user {user.telegram_id}")
            
        except TelegramError as e:
            logger.error(f"Failed to send expiry warning to user {subscription.user.telegram_id}: {e}")
        except Exception as e:
            logger.error(f"Error sending expiry warning: {e}")
    
    async def _send_expiry_final_notice(self, subscription: Subscription, db: Session):
        """Send final expiry notice (same day)"""
        try:
            user = subscription.user
            hours_remaining = int((subscription.expires_at - datetime.utcnow()).total_seconds() / 3600)
            
            final_message = f"""🚨 **Subscription Expires Today**

Your Validator Pro subscription expires in **{hours_remaining} hours**.

**Expiry Time:** {subscription.expires_at.strftime('%B %d, %Y at %H:%M UTC')}
**Current Status:** Active (expires soon)

**Action Required:**
• Use /subscription to renew immediately
• Your validation history will be preserved
• Avoid service interruption

**After expiry:**
• Limited to trial usage only
• Premium features will be disabled

Renew now to continue unlimited validation!"""

            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=final_message,
                parse_mode='Markdown'
            )
            
            # Mark final notice as sent
            subscription.expiry_final_notice_sent = True
            db.commit()
            
            logger.info(f"Sent final expiry notice to user {user.telegram_id}")
            
        except TelegramError as e:
            logger.error(f"Failed to send final notice to user {subscription.user.telegram_id}: {e}")
        except Exception as e:
            logger.error(f"Error sending final notice: {e}")
    
    async def _deactivate_expired_subscriptions(self, db: Session):
        """Deactivate subscriptions that have expired"""
        try:
            now = datetime.utcnow()
            expired_subscriptions = db.query(Subscription).join(User).filter(
                Subscription.status == 'active',
                Subscription.expires_at <= now
            ).all()
            
            for subscription in expired_subscriptions:
                # Deactivate subscription
                subscription.status = 'expired'
                
                # Send expiry confirmation
                await self._send_expiry_confirmation(subscription)
                
                logger.info(f"Deactivated expired subscription for user {subscription.user.telegram_id}")
            
            if expired_subscriptions:
                db.commit()
                logger.info(f"Deactivated {len(expired_subscriptions)} expired subscriptions")
                
        except Exception as e:
            logger.error(f"Error deactivating expired subscriptions: {e}")
    
    async def _send_expiry_confirmation(self, subscription: Subscription):
        """Send confirmation that subscription has expired"""
        try:
            user = subscription.user
            
            expiry_message = f"""📋 **Subscription Expired**

Your Validator Pro subscription has expired.

**Expired On:** {subscription.expires_at.strftime('%B %d, %Y at %H:%M UTC')}
**Status:** Expired
**Account:** Switched to trial mode

**What's Available:**
• Limited trial validations
• Access to validation history
• Basic support

**To Restore Full Access:**
Use /subscription to purchase a new subscription and restore unlimited validation features.

Thank you for using Validator Pro!"""

            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=expiry_message,
                parse_mode='Markdown'
            )
            
        except TelegramError as e:
            logger.error(f"Failed to send expiry confirmation to user {subscription.user.telegram_id}: {e}")
        except Exception as e:
            logger.error(f"Error sending expiry confirmation: {e}")

# Global notifier instance
expiry_notifier = SubscriptionExpiryNotifier()

async def run_expiry_check():
    """Run the expiry check - can be called by scheduler"""
    await expiry_notifier.check_expiring_subscriptions()

if __name__ == "__main__":
    # For testing purposes
    asyncio.run(run_expiry_check())