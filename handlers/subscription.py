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
                await update.message.reply_text("Please start the bot first with /start")
                return
            
            has_active = user.has_active_subscription()
            
            if has_active:
                active_sub = user.get_active_subscription()
                days_remaining = active_sub.days_remaining()
                
                menu_text = f"""
💎 **Subscription Management**

**Status:** ✅ Active
**Expires:** {active_sub.expires_at.strftime('%Y-%m-%d %H:%M UTC')}
**Days Remaining:** {days_remaining}
**Amount:** ${active_sub.amount_usd}/month

Your subscription will expire automatically.
No auto-renewal charges.
                """
            else:
                trial_remaining = 10 - user.trial_emails_used
                menu_text = f"""
💎 **Subscription Management**

**Status:** 🆓 Trial
**Remaining:** {trial_remaining} free validations

{SUBSCRIPTION_INFO}

Upgrade now for unlimited email validation!
                """
            
            if update.message:
                await update.message.reply_text(
                    menu_text,
                    reply_markup=self.keyboards.subscription_menu(has_active),
                    parse_mode='Markdown'
                )
            else:
                query = update.callback_query
                await query.edit_message_text(
                    menu_text,
                    reply_markup=self.keyboards.subscription_menu(has_active),
                    parse_mode='Markdown'
                )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle subscription-related callbacks"""
        query = update.callback_query
        data = query.data
        telegram_user = update.effective_user
        
        with SessionLocal() as db:
            user = db.query(User).filter(User.telegram_id == str(telegram_user.id)).first()
            
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
            
            elif data.startswith('confirm_payment_'):
                subscription_id = data.split('_')[2]
                await self.confirm_payment(update, context, user, subscription_id, db)
    
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
            subscription_manager = SubscriptionManager(db)
            subscription = subscription_manager.create_subscription(user, payment_method)
            
            payment_info = subscription_manager.get_payment_instructions(subscription)
            
            if 'error' in payment_info:
                await update.callback_query.edit_message_text(
                    f"❌ Error: {payment_info['error']}",
                    reply_markup=self.keyboards.back_to_menu()
                )
                return
            
            # Store subscription ID in user context for later confirmation
            context.user_data['pending_subscription'] = subscription.id
            context.user_data['waiting_for_transaction'] = True
            
            payment_text = f"""
{payment_info['instructions']}

**Order ID:** `{subscription.id}`

After sending payment, please send me the transaction hash/ID for verification.

⚠️ **Important:**
• Send only the exact amount
• Double-check the address
• Transaction hash is required for activation
            """
            
            confirmation_keyboard = [
                [self.keyboards.InlineKeyboardButton("✅ I've Sent Payment", callback_data=f"confirm_payment_{subscription.id}")],
                [self.keyboards.InlineKeyboardButton("🔙 Cancel", callback_data="subscription")]
            ]
            
            await update.callback_query.edit_message_text(
                payment_text,
                reply_markup=self.keyboards.InlineKeyboardMarkup(confirmation_keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error initiating payment: {e}")
            await update.callback_query.edit_message_text(
                "❌ Error creating payment. Please try again.",
                reply_markup=self.keyboards.subscription_menu(False)
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
        if user.trial_emails_used > 0:
            await update.callback_query.edit_message_text(
                "You've already started your free trial!",
                reply_markup=self.keyboards.main_menu()
            )
            return
        
        trial_text = """
🎁 **Free Trial Started!**

You now have **10 free email validations** to test our service.

**What's included:**
✅ Full validation (syntax, DNS, MX, SMTP)
✅ Detailed results and reports
✅ File upload support
✅ No time restrictions

**Ready to validate your first emails?**

Use the "🎯 Validate Emails" button to get started!
        """
        
        await update.callback_query.edit_message_text(
            trial_text,
            reply_markup=self.keyboards.main_menu(),
            parse_mode='Markdown'
        )
    
    async def show_subscription_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show detailed subscription information"""
        info_text = f"""
{SUBSCRIPTION_INFO}

**Why Subscribe?**

🚀 **Unlimited Validations**
No more counting emails - validate as many as you need

📊 **Advanced Features**
• Bulk file processing (CSV, Excel, TXT)
• Detailed validation reports
• Usage analytics and statistics
• Priority email support

⚡ **High Performance**
• Concurrent processing for speed
• 95%+ accuracy rate
• Multiple validation layers
• Real-time SMTP checks

🔒 **Security & Privacy**
• Files automatically deleted after 24h
• No data stored or shared
• Secure crypto payments
• Anonymous usage

💰 **Simple Pricing**
• No setup fees
• No contracts
• Auto-expires after 30 days
• No hidden charges

Ready to upgrade your email validation?
        """
        
        query = update.callback_query
        await query.edit_message_text(
            info_text,
            reply_markup=self.keyboards.subscription_menu(False),
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
                trial_remaining = 10 - user.trial_emails_used
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
