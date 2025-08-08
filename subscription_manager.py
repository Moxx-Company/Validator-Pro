"""
Subscription management system
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from models import User, Subscription
from config import SUBSCRIPTION_PRICE_USD, SUBSCRIPTION_DURATION_DAYS, SUPPORTED_CRYPTOS
from services.blockbee_service import BlockBeeService
from utils import validate_crypto_transaction
import logging

logger = logging.getLogger(__name__)

class SubscriptionManager:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.blockbee = BlockBeeService()
    
    def create_subscription(self, user: User, payment_method: str) -> Subscription:
        """Create a new subscription for user"""
        # Validate payment method
        if payment_method not in SUPPORTED_CRYPTOS:
            raise ValueError(f"Unsupported payment method: {payment_method}")
        
        subscription = Subscription(
            user_id=user.id,
            status='pending',
            amount_usd=SUBSCRIPTION_PRICE_USD,
            currency='USD',
            payment_currency_crypto=payment_method.upper(),
            created_at=datetime.utcnow()
        )
        
        # Create payment address via BlockBee
        payment_data = self.blockbee.create_payment_address(
            payment_method, 
            str(user.id), 
            SUBSCRIPTION_PRICE_USD
        )
        
        if payment_data['success']:
            subscription.payment_address = payment_data['address']
            subscription.payment_amount_crypto = payment_data['amount_crypto']
            # Reference stored in BlockBee system, not needed in database
        else:
            logger.error(f"Failed to create payment address: {payment_data.get('error')}")
            subscription.status = 'failed'
        
        self.db_session.add(subscription)
        self.db_session.commit()
        return subscription
    

    
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
        """Get the active subscription for a user"""
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
                    "💎 Renew for just $5.00/month"
                ),
                'action': 'renew'
            }
        elif days_remaining <= 3:
            return {
                'title': '⚠️ Subscription Expiring Soon',
                'message': (
                    f"Your subscription expires in {days_remaining} day{'s' if days_remaining > 1 else ''}.\n\n"
                    "Don't lose access to unlimited email validation!\n\n"
                    "💎 Renew now for just $5.00/month"
                ),
                'action': 'renew'
            }
        elif days_remaining <= 7:
            return {
                'title': '📅 Subscription Reminder',
                'message': (
                    f"Your subscription expires in {days_remaining} days.\n\n"
                    "Consider renewing soon to avoid interruption.\n\n"
                    "💎 Renew for $5.00/month"
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
        
        # Get currency display name
        currency_names = {
            'btc': 'Bitcoin (BTC)',
            'eth': 'Ethereum (ETH)', 
            'ltc': 'Litecoin (LTC)',
            'doge': 'Dogecoin (DOGE)',
            'usdt_trc20': 'USDT (TRC20)',
            'usdt_erc20': 'USDT (ERC20)',
            'trx': 'TRON (TRX)',
            'bsc': 'BNB Smart Chain'
        }
        
        currency_name = currency_names.get(currency, currency.upper())
        
        instructions_text = f"""
💰 **{currency_name} Payment Instructions**

**Amount:** {amount} {currency.upper()}
**Address:** `{address}`

1. Send exactly {amount} {currency.upper()} to the address above
2. Wait for blockchain confirmation (10-30 minutes)
3. Your subscription will be activated automatically

⚠️ Important Notes:
• Send only {currency_name} to this address
• Double-check the amount and address
• Keep your transaction ID for support
⏰ Payment expires in 1 hour
        """
        
        return {
            'currency': currency,
            'amount': amount,
            'address': address,
            'instructions': instructions_text
        }
