"""
Subscription management system
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from models import User, Subscription
from config import SUBSCRIPTION_PRICE_USD, SUBSCRIPTION_DURATION_DAYS
from utils import get_crypto_price, validate_crypto_transaction
import uuid

class SubscriptionManager:
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def create_subscription(self, user: User, payment_method: str) -> Subscription:
        """Create a new subscription for user"""
        subscription = Subscription(
            user_id=user.id,
            status='pending',
            amount_usd=SUBSCRIPTION_PRICE_USD,
            currency='USD'
        )
        
        # Set crypto payment details based on payment method
        if payment_method in ['bitcoin', 'ethereum', 'usdt']:
            crypto_price = get_crypto_price(payment_method)
            crypto_amount = SUBSCRIPTION_PRICE_USD / crypto_price
            
            subscription.payment_currency_crypto = payment_method.upper()
            subscription.payment_amount_crypto = round(crypto_amount, 8)
            subscription.payment_address = self._generate_payment_address(payment_method)
        
        self.db_session.add(subscription)
        self.db_session.commit()
        return subscription
    
    def _generate_payment_address(self, currency: str) -> str:
        """Generate payment address for crypto currency"""
        # This would typically integrate with a crypto payment processor
        # For demo purposes, return a mock address
        addresses = {
            'bitcoin': f"bc1q{uuid.uuid4().hex[:32]}",
            'ethereum': f"0x{uuid.uuid4().hex[:40]}",
            'usdt': f"0x{uuid.uuid4().hex[:40]}"
        }
        return addresses.get(currency, f"address_{uuid.uuid4().hex[:16]}")
    
    def check_payment_status(self, subscription: Subscription) -> bool:
        """Check if payment has been received for subscription"""
        if not subscription.transaction_hash:
            return False
        
        # Validate transaction on blockchain
        is_valid = validate_crypto_transaction(
            subscription.transaction_hash,
            subscription.payment_amount_crypto,
            subscription.payment_currency_crypto
        )
        
        if is_valid:
            self.activate_subscription(subscription)
            return True
        
        return False
    
    def activate_subscription(self, subscription: Subscription) -> None:
        """Activate a subscription"""
        subscription.activate()
        self.db_session.commit()
    
    def get_active_subscription(self, user: User) -> Optional[Subscription]:
        """Get user's active subscription"""
        return user.get_active_subscription()
    
    def check_subscription_expiry(self, user: User) -> Dict[str, Any]:
        """Check subscription expiry status"""
        active_sub = self.get_active_subscription(user)
        
        if not active_sub:
            return {
                'has_subscription': False,
                'is_expired': True,
                'days_remaining': 0,
                'expires_at': None
            }
        
        days_remaining = active_sub.days_remaining()
        is_expired = days_remaining <= 0
        
        return {
            'has_subscription': True,
            'is_expired': is_expired,
            'days_remaining': days_remaining,
            'expires_at': active_sub.expires_at,
            'subscription': active_sub
        }
    
    def get_subscription_history(self, user: User) -> list:
        """Get user's subscription history"""
        return user.subscriptions
    
    def cancel_subscription(self, subscription: Subscription) -> None:
        """Cancel a subscription"""
        subscription.status = 'cancelled'
        self.db_session.commit()
    
    def send_expiry_notification(self, user: User, days_remaining: int) -> Dict[str, str]:
        """Generate expiry notification message"""
        if days_remaining <= 0:
            return {
                'title': '❌ Subscription Expired',
                'message': (
                    "Your Email Validator Pro subscription has expired.\n\n"
                    "To continue validating unlimited emails, please renew your subscription.\n\n"
                    "💎 Renew for just $29.99/month"
                ),
                'action': 'renew'
            }
        elif days_remaining <= 3:
            return {
                'title': '⚠️ Subscription Expiring Soon',
                'message': (
                    f"Your subscription expires in {days_remaining} day{'s' if days_remaining > 1 else ''}.\n\n"
                    "Don't lose access to unlimited email validation!\n\n"
                    "💎 Renew now for just $29.99/month"
                ),
                'action': 'renew'
            }
        elif days_remaining <= 7:
            return {
                'title': '📅 Subscription Reminder',
                'message': (
                    f"Your subscription expires in {days_remaining} days.\n\n"
                    "Consider renewing soon to avoid interruption.\n\n"
                    "💎 Renew for $29.99/month"
                ),
                'action': 'remind'
            }
        
        return {}
    
    def get_payment_instructions(self, subscription: Subscription) -> Dict[str, str]:
        """Get payment instructions for subscription"""
        if not subscription.payment_currency_crypto:
            return {'error': 'No payment method configured'}
        
        currency = subscription.payment_currency_crypto.lower()
        amount = subscription.payment_amount_crypto
        address = subscription.payment_address
        
        instructions = {
            'bitcoin': f"""
💰 **Bitcoin Payment Instructions**

**Amount:** {amount} BTC
**Address:** `{address}`

1. Send exactly {amount} BTC to the address above
2. Wait for blockchain confirmation
3. Your subscription will be activated automatically

⚠️ Send only Bitcoin to this address
⏰ Payment expires in 1 hour
            """,
            'ethereum': f"""
💰 **Ethereum Payment Instructions**

**Amount:** {amount} ETH
**Address:** `{address}`

1. Send exactly {amount} ETH to the address above
2. Wait for blockchain confirmation
3. Your subscription will be activated automatically

⚠️ Send only Ethereum to this address
⏰ Payment expires in 1 hour
            """,
            'usdt': f"""
💰 **USDT Payment Instructions**

**Amount:** {amount} USDT
**Address:** `{address}`
**Network:** Ethereum (ERC-20)

1. Send exactly {amount} USDT to the address above
2. Wait for blockchain confirmation
3. Your subscription will be activated automatically

⚠️ Send only USDT (ERC-20) to this address
⏰ Payment expires in 1 hour
            """
        }
        
        return {
            'currency': currency,
            'amount': amount,
            'address': address,
            'instructions': instructions.get(currency, 'Payment instructions not available')
        }
