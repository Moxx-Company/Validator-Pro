"""
Subscription management handler
"""
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User, Subscription
from keyboards import Keyboards
from subscription_manager import SubscriptionManager
from config import SUBSCRIPTION_INFO
from utils import format_crypto_address

logger = logging.getLogger(__name__)

class SubscriptionHandler:
    def __init__(self):
        self.keyboards = Keyboards()
    
    async def show_subscription_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show subscription management menu"""
        telegram_user = update.effective_user
        
        with SessionLocal() as db:
            user = db.query(User).filter(User.telegram_id == str(telegram_user.id)).first()
            
            if not user:
                if update.message:
                    await update.message.reply_text("Please start the bot first with /start")
                else:
                    await update.callback_query.edit_message_text("Please start the bot first with /start")
                return
            
            has_active = user.has_active_subscription()
            
            if has_active:
                active_sub = user.get_active_subscription()
                days_remaining = active_sub.days_remaining()
                
                menu_text = f"""
💎 **Subscription**

**Status:** ✅ Active
**Expires:** {active_sub.expires_at.strftime('%m/%d/%Y')}
**Days left:** {days_remaining}
**Plan:** ${active_sub.amount_usd}/month

Auto-expires, no renewal charges.
                """
            else:
                from config import TRIAL_VALIDATION_LIMIT
                emails_used = user.trial_emails_used or 0
                phones_used = user.trial_phones_used or 0
                total_used = emails_used + phones_used
                trial_remaining = TRIAL_VALIDATION_LIMIT - total_used
                
                # Check if trial has been started (any validations used OR trial activated)
                trial_started = total_used > 0 or user.trial_activated
                
                menu_text = f"""
💎 **Subscription**

**Status:** 🆓 Trial {'Active' if trial_started else 'Available'}
**Used:** {emails_used} emails, {phones_used} phones
**Remaining:** {trial_remaining} free validations

{SUBSCRIPTION_INFO}

Upgrade for unlimited access!
                """
            
            # Determine if trial has been started (don't show trial button if subscription is active)
            trial_started = has_active  # If subscription is active, consider trial "started" to hide button
            if not has_active:
                emails_used = user.trial_emails_used or 0
                phones_used = user.trial_phones_used or 0
                trial_started = bool((emails_used + phones_used) > 0 or user.trial_activated)
            
            if update.message:
                await update.message.reply_text(
                    menu_text,
                    reply_markup=self.keyboards.subscription_menu(has_active, trial_started),
                    parse_mode='Markdown'
                )
            else:
                query = update.callback_query
                await query.edit_message_text(
                    menu_text,
                    reply_markup=self.keyboards.subscription_menu(has_active, trial_started),
                    parse_mode='Markdown'
                )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle subscription-related callbacks"""
        query = update.callback_query
        data = query.data
        telegram_user = update.effective_user
        logger.info(f"SubscriptionHandler received: {data}")
        
        with SessionLocal() as db:
            user = db.query(User).filter(User.telegram_id == str(telegram_user.id)).first()
            
            if not user:
                await query.edit_message_text("Please start the bot first with /start")
                return
            
            if data == 'subscription':
                await self.show_subscription_menu(update, context)
            
            elif data == 'subscribe':
                await self.show_payment_methods(update, context)
            
            elif data == 'start_trial':
                await self.start_trial(update, context, user, db)
            
            elif data == 'sub_info':
                await self.show_subscription_info(update, context)
            
            elif data == 'sub_status':
                await self.show_subscription_status(update, context, user)
            
            elif data == 'payment_history':
                await self.show_payment_history(update, context, user)
            
            elif data.startswith('pay_'):
                # Handle both single currency codes (btc) and compound codes (usdt_trc20)
                payment_parts = data.split('_')[1:]
                if len(payment_parts) == 1:
                    payment_method = payment_parts[0]
                else:
                    payment_method = '_'.join(payment_parts)
                await self.initiate_payment(update, context, user, payment_method, db)
            
            elif data.startswith('check_payment_'):
                # Legacy handler - redirect to subscription menu since check button is removed
                await self.show_subscription_menu(update, context)
            
            elif data.startswith('confirm_payment_'):
                await self.confirm_demo_payment(update, context, user, db)
    
    async def show_payment_methods(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show payment method selection"""
        payment_text = """
💰 **Choose Payment Method**

We accept cryptocurrency payments for maximum privacy and security.

**Available Cryptocurrencies:**
• **Bitcoin (BTC)** - Most popular crypto
• **Ethereum (ETH)** - Fast and reliable
• **Litecoin (LTC)** - Fast transactions
• **Dogecoin (DOGE)** - Low fees
• **USDT (TRC20)** - Stable value, low fees
• **USDT (ERC20)** - Stable value, Ethereum network
• **TRON (TRX)** - Fast and cheap
• **BNB Smart Chain** - Low fees

**Payment Process:**
1. Select cryptocurrency
2. Send exact amount to provided address
3. Wait for blockchain confirmation
4. Subscription activated automatically

Select your preferred payment method:
        """
        
        query = update.callback_query
        await query.edit_message_text(
            payment_text,
            reply_markup=self.keyboards.payment_methods(),
            parse_mode='Markdown'
        )
    
    async def initiate_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, payment_method: str, db: Session):
        """Initiate payment process"""
        try:
            from config import SUPPORTED_CRYPTOS
            from services.blockbee_service import BlockBeeService
            
            if payment_method not in SUPPORTED_CRYPTOS:
                await update.callback_query.edit_message_text(
                    f"❌ Unsupported payment method: {payment_method}",
                    reply_markup=self.keyboards.back_to_menu()
                )
                return
            
            # Show processing message
            await update.callback_query.edit_message_text(
                "🔄 Creating payment address...\nPlease wait a moment.",
                parse_mode='Markdown'
            )
            
            # Create BlockBee service and generate payment address
            blockbee = BlockBeeService()
            payment_result = blockbee.create_payment_address(
                currency=payment_method,
                user_id=str(user.id),
                amount_usd=9.99
            )
            
            if not payment_result['success']:
                await update.callback_query.edit_message_text(
                    f"❌ Error creating payment: {payment_result.get('error', 'Unknown error')}",
                    reply_markup=self.keyboards.back_to_menu()
                )
                return
            
            # Check for existing pending subscription and cancel it first
            existing_pending = db.query(Subscription).filter(
                Subscription.user_id == user.id,
                Subscription.status == 'pending'
            ).first()
            
            if existing_pending:
                logger.info(f"Canceling existing pending subscription for user {user.id}")
                existing_pending.status = 'cancelled'
                db.commit()
            
            # Create pending subscription record
            subscription = Subscription(
                user_id=user.id,
                status='pending',
                amount_usd=9.99,
                currency='USD',
                payment_address=payment_result['address'],
                payment_amount_crypto=payment_result['amount_crypto'],
                payment_currency_crypto=payment_method.upper()
            )
            db.add(subscription)
            db.commit()
            db.refresh(subscription)
            
            logger.info(f"✅ Created NEW subscription with unique address: {payment_result['address']}")
            
            # Format payment instructions
            crypto_name = SUPPORTED_CRYPTOS[payment_method]
            payment_text = f"""
💰 **Payment Instructions - {crypto_name}**

**Amount:** {payment_result['amount_crypto']:.8f} {payment_method.upper()}
**USD Value:** $9.99

**Payment Address:**
`{payment_result['address']}`

⚠️ **Important:**
• Send EXACTLY {payment_result['amount_crypto']:.8f} {payment_method.upper()}
• Payment will be detected automatically
• Subscription activates after 1 confirmation
• Do not send from exchange (use personal wallet)

**Status:** Waiting for payment...
**Order ID:** `{subscription.id}`
            """
            
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [
                [InlineKeyboardButton("🔙 Cancel", callback_data="subscription")]
            ]
            
            await update.callback_query.edit_message_text(
                payment_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error initiating payment: {e}")
            await update.callback_query.edit_message_text(
                "❌ Error creating payment. Please try again.",
                reply_markup=self.keyboards.subscription_menu(False, True)
            )
    
    async def confirm_demo_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, db: Session):
        """Handle demo payment confirmation"""
        try:
            from datetime import datetime, timedelta
            
            # Create demo subscription
            subscription = Subscription(
                user_id=user.id,
                status='active',
                amount_usd=9.99,
                currency='USD',
                payment_currency_crypto='DEMO',
                activated_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=30),
                created_at=datetime.utcnow()
            )
            
            db.add(subscription)
            db.commit()
            
            confirmation_text = """
✅ **Demo Payment Confirmed!**

Your subscription has been activated for testing purposes.

**Status:** Active
**Duration:** 30 days
**Features:** Unlimited email & phone validation

Thank you for testing the Email & Phone Validator Pro!
            """
            
            await update.callback_query.edit_message_text(
                confirmation_text,
                reply_markup=self.keyboards.subscription_menu(True),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error confirming demo payment: {e}")
            await update.callback_query.edit_message_text(
                "❌ Error processing payment. Please try again.",
                reply_markup=self.keyboards.subscription_menu(False, True)
            )
    
    async def check_payment_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, subscription_id: str, db: Session):
        """Check payment status via BlockBee API"""
        try:
            subscription = db.query(Subscription).filter(
                Subscription.id == int(subscription_id),
                Subscription.user_id == user.id
            ).first()
            
            if not subscription:
                await update.callback_query.edit_message_text(
                    "❌ Payment not found.",
                    reply_markup=self.keyboards.subscription_menu(False, True)
                )
                return
            
            if subscription.status == 'active':
                await update.callback_query.edit_message_text(
                    "✅ Payment confirmed! Your subscription is already active.",
                    reply_markup=self.keyboards.subscription_menu(True)
                )
                return
            
            # Show current status
            from config import SUPPORTED_CRYPTOS
            crypto_name = SUPPORTED_CRYPTOS.get(subscription.payment_currency_crypto.lower(), subscription.payment_currency_crypto)
            
            status_text = f"""
💰 **Payment Status - {crypto_name}**

**Amount:** {subscription.payment_amount_crypto:.8f} {subscription.payment_currency_crypto}
**Address:** `{subscription.payment_address}`
**Status:** {subscription.status.title()}

⏳ Waiting for blockchain confirmation...
This usually takes 1-3 confirmations (5-30 minutes).

**Order ID:** `{subscription.id}`
            """
            
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh Status", callback_data=f"check_payment_{subscription.id}")],
                [InlineKeyboardButton("🔙 Back", callback_data="subscription")]
            ]
            
            await update.callback_query.edit_message_text(
                status_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error checking payment status: {e}")
            await update.callback_query.edit_message_text(
                "❌ Error checking payment status.",
                reply_markup=self.keyboards.subscription_menu(False, True)
            )
    
    async def handle_transaction_hash(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle transaction hash input"""
        if not context.user_data.get('waiting_for_transaction'):
            return
        
        tx_hash = update.message.text.strip()
        subscription_id = context.user_data.get('pending_subscription')
        
        if not subscription_id:
            await update.message.reply_text(
                "❌ No pending payment found. Please start the payment process again.",
                reply_markup=self.keyboards.subscription_menu(False)
            )
            return
        
        telegram_user = update.effective_user
        
        with SessionLocal() as db:
            user = db.query(User).filter(User.telegram_id == str(telegram_user.id)).first()
            subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
            
            if not subscription:
                await update.message.reply_text(
                    "❌ Subscription not found.",
                    reply_markup=self.keyboards.subscription_menu(False)
                )
                return
            
            # Store transaction hash
            subscription.transaction_hash = tx_hash
            db.commit()
            
            # Clear user state
            context.user_data['waiting_for_transaction'] = False
            context.user_data['pending_subscription'] = None
            
            confirmation_text = f"""
✅ **Transaction Hash Received**

**Transaction:** `{tx_hash}`
**Order ID:** `{subscription.id}`

We're verifying your payment on the blockchain. This usually takes a few minutes.

You'll receive a confirmation message once your subscription is activated.

**Status:** ⏳ Verifying payment...
            """
            
            await update.message.reply_text(
                confirmation_text,
                reply_markup=self.keyboards.subscription_menu(False),
                parse_mode='Markdown'
            )
            
            # In a real implementation, you'd verify the transaction here
            # For demo purposes, we'll activate immediately
            subscription_manager = SubscriptionManager(db)
            subscription_manager.activate_subscription(subscription)
            
            # Send activation confirmation
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="""
🎉 **Subscription Activated!**

Your Email Validator Pro subscription is now active!

**Benefits Unlocked:**
✅ Unlimited email validations
✅ Bulk file processing
✅ Priority support
✅ Advanced analytics

**Expires:** 30 days from now

Start validating unlimited emails now!
                """,
                reply_markup=self.keyboards.main_menu(),
                parse_mode='Markdown'
            )
    
    async def confirm_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, subscription_id: str, db: Session):
        """Confirm payment and request transaction hash"""
        context.user_data['pending_subscription'] = int(subscription_id)
        context.user_data['waiting_for_transaction'] = True
        
        confirm_text = """
📝 **Payment Confirmation**

Please send me the transaction hash (TxID) from your crypto wallet.

**Where to find transaction hash:**
• **Wallet apps:** Check transaction details
• **Exchanges:** Go to withdrawal history
• **Block explorers:** Copy transaction ID

**Example format:**
`1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b`

Just paste the transaction hash as a message.
        """
        
        query = update.callback_query
        await query.edit_message_text(
            confirm_text,
            reply_markup=self.keyboards.back_to_menu(),
            parse_mode='Markdown'
        )
    
    async def start_trial(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, db: Session):
        """Start free trial"""
        if user.trial_emails_used > 0 or user.trial_phones_used > 0 or user.trial_activated:
            await update.callback_query.edit_message_text(
                "You've already started your free trial!",
                reply_markup=self.keyboards.main_menu()
            )
            return
        
        # Mark trial as activated 
        user.trial_activated = True
        db.commit()
        
        from config import TRIAL_VALIDATION_LIMIT
        trial_text = f"""
🎁 **Free Trial Started!**

You now have **{TRIAL_VALIDATION_LIMIT:,} free validations** to test our service (emails + phones combined).

**What's included:**
✅ Full email validation (syntax, DNS, MX, SMTP)
✅ Phone validation (format, carrier, country)
✅ Detailed results and reports
✅ File upload support
✅ No time restrictions

**Ready to start validating?**

Choose Email or Phone validation to get started!
        """
        
        await update.callback_query.edit_message_text(
            trial_text,
            reply_markup=self.keyboards.main_menu(),
            parse_mode='Markdown'
        )
    
    async def show_subscription_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show detailed subscription information"""
        info_text = """
💎 **Validator Pro**

**Benefits:**
✅ Unlimited email & phone validation
✅ Bulk CSV/Excel processing  
✅ Advanced analytics & reports
✅ Priority support

**Pricing:** $9.99/month (30 days)
**Payment:** Cryptocurrency only
**Trial:** 1,000 free validations

        """
        
        query = update.callback_query  
        telegram_user = update.effective_user
        
        with SessionLocal() as db:
            user = db.query(User).filter(User.telegram_id == str(telegram_user.id)).first()
            
            # Check if trial has been started
            trial_started = False
            if user:
                emails_used = user.trial_emails_used or 0
                phones_used = user.trial_phones_used or 0
                trial_started = bool((emails_used + phones_used) > 0)
        
        await query.edit_message_text(
            info_text,
            reply_markup=self.keyboards.subscription_menu(False, trial_started),
            parse_mode='Markdown'
        )
    
    async def show_subscription_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
        """Show detailed subscription status"""
        with SessionLocal() as db:
            user = db.query(User).filter(User.telegram_id == str(user.telegram_id)).first()
            
            if user.has_active_subscription():
                active_sub = user.get_active_subscription()
                days_remaining = active_sub.days_remaining()
                
                status_text = f"""
💎 **Subscription Status**

**Plan:** Email Validator Pro
**Status:** ✅ Active
**Activated:** {active_sub.activated_at.strftime('%Y-%m-%d %H:%M UTC')}
**Expires:** {active_sub.expires_at.strftime('%Y-%m-%d %H:%M UTC')}
**Days Remaining:** {days_remaining}

**Payment Info:**
• Amount: ${active_sub.amount_usd}
• Currency: {active_sub.payment_currency_crypto or 'USD'}
• Order ID: {active_sub.id}

**Usage:** Unlimited validations ♾️

Your subscription will expire automatically on the date above.
                """
            else:
                from config import TRIAL_EMAIL_LIMIT
                trial_remaining = TRIAL_EMAIL_LIMIT - user.trial_emails_used
                status_text = f"""
🆓 **Trial Status**

**Plan:** Free Trial
**Status:** Active
**Remaining:** {trial_remaining} validations
**Used:** {user.trial_emails_used} validations

**Upgrade Benefits:**
• Unlimited email validations
• Bulk file processing
• Priority support
• Advanced analytics

Ready to upgrade?
                """
            
            query = update.callback_query
            await query.edit_message_text(
                status_text,
                reply_markup=self.keyboards.subscription_menu(user.has_active_subscription()),
                parse_mode='Markdown'
            )
    
    async def show_payment_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
        """Show payment history"""
        with SessionLocal() as db:
            subscriptions = db.query(Subscription).filter(Subscription.user_id == user.id).order_by(Subscription.created_at.desc()).all()
            
            if not subscriptions:
                history_text = """
📜 **Payment History**

No payments found.

Start your first subscription to see payment history here.
                """
            else:
                history_text = "📜 **Payment History**\n\n"
                
                for sub in subscriptions[:5]:  # Show last 5 subscriptions
                    status_emoji = {
                        'active': '✅',
                        'expired': '⏰',
                        'pending': '⏳',
                        'cancelled': '❌'
                    }.get(sub.status, '❓')
                    
                    history_text += f"""
**Order #{sub.id}**
Status: {status_emoji} {sub.status.title()}
Amount: ${sub.amount_usd}
Date: {sub.created_at.strftime('%Y-%m-%d')}
{'Expires: ' + sub.expires_at.strftime('%Y-%m-%d') if sub.expires_at else ''}

---
                    """
            
            query = update.callback_query
            await query.edit_message_text(
                history_text,
                reply_markup=self.keyboards.back_to_menu(),
                parse_mode='Markdown'
            )
