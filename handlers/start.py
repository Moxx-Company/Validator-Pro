"""
Start and onboarding handler
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User
from keyboards import Keyboards
from config import WELCOME_MESSAGE, SUBSCRIPTION_INFO

logger = logging.getLogger(__name__)

class StartHandler:
    def __init__(self):
        self.keyboards = Keyboards()
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command and user registration"""
        telegram_user = update.effective_user
        
        with SessionLocal() as db:
            # Get or create user
            user = self.get_or_create_user(db, telegram_user)
            
            if not user.is_onboarded:
                await self.start_onboarding(update, context, user)
            else:
                await self.show_main_menu(update, context, user)
    
    def get_or_create_user(self, db: Session, telegram_user) -> User:
        """Get existing user or create new one"""
        user = db.query(User).filter(User.telegram_id == str(telegram_user.id)).first()
        
        if not user:
            user = User(
                telegram_id=str(telegram_user.id),
                username=telegram_user.username,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name,
                language_code=telegram_user.language_code or 'en'
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"Created new user: {user.telegram_id}")
        else:
            # Update user info
            user.username = telegram_user.username
            user.first_name = telegram_user.first_name
            user.last_name = telegram_user.last_name
            user.last_active = user.created_at.__class__.utcnow()
            db.commit()
        
        return user
    
    async def start_onboarding(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
        """Start the onboarding process"""
        welcome_text = f"""
👋 **Welcome to Email Validator Pro, {user.first_name or 'there'}!**

{WELCOME_MESSAGE}

🎁 **Free Trial:**
• Get 20,000 FREE validations (emails + phones combined)
• No credit card required
• Test both email and phone validation features
• See the quality of our professional validation

Ready to start validating?
        """
        
        if update.message:
            await update.message.reply_text(
                welcome_text,
                reply_markup=self.keyboards.onboarding(),
                parse_mode='Markdown'
            )
        else:
            query = update.callback_query
            await query.edit_message_text(
                welcome_text,
                reply_markup=self.keyboards.onboarding(),
                parse_mode='Markdown'
            )
    
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
        """Show main menu for existing users"""
        with SessionLocal() as db:
            user = db.query(User).filter(User.telegram_id == str(user.telegram_id)).first()
            
            # Check subscription status
            subscription_status = ""
            if user.has_active_subscription():
                active_sub = user.get_active_subscription()
                days_remaining = active_sub.days_remaining()
                subscription_status = f"💎 **Active Subscription** ({days_remaining} days remaining)"
            else:
                trial_remaining = 20000 - user.trial_validations_used
                subscription_status = f"🆓 **Trial:** {trial_remaining} validations remaining (emails + phones)"
            
            menu_text = f"""
🎯 **Email Validator Pro**

Welcome back, {user.full_name}!

{subscription_status}

**What would you like to do?**
            """
            
            if update.message:
                await update.message.reply_text(
                    menu_text,
                    reply_markup=self.keyboards.main_menu(),
                    parse_mode='Markdown'
                )
            else:
                query = update.callback_query
                await query.edit_message_text(
                    menu_text,
                    reply_markup=self.keyboards.main_menu(),
                    parse_mode='Markdown'
                )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle start-related callbacks"""
        query = update.callback_query
        data = query.data
        telegram_user = update.effective_user
        
        with SessionLocal() as db:
            user = db.query(User).filter(User.telegram_id == str(telegram_user.id)).first()
            
            if data == 'start_onboarding':
                await self.complete_onboarding(update, context, user, db)
            
            elif data == 'learn_more':
                await self.show_learn_more(update, context)
            
            elif data == 'main_menu':
                await self.show_main_menu(update, context, user)
    
    async def complete_onboarding(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, db: Session):
        """Complete the onboarding process"""
        user.is_onboarded = True
        db.commit()
        
        onboarding_complete_text = """
🎉 **Onboarding Complete!**

You're all set up and ready to start validating emails!

**Your Free Trial:**
• 50 email validations included
• Full access to all features
• No time limit on trial usage

**Next Steps:**
1. Try validating some emails
2. See our accuracy in action
3. Subscribe for unlimited access

Let's validate your first emails!
        """
        
        query = update.callback_query
        await query.edit_message_text(
            onboarding_complete_text,
            reply_markup=self.keyboards.main_menu(),
            parse_mode='Markdown'
        )
    
    async def show_learn_more(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show detailed information about the service"""
        learn_more_text = f"""
📊 **About Email Validator Pro**

**What We Do:**
Our advanced email validation service helps you clean your email lists and improve deliverability for cold email campaigns.

**Validation Process:**
✅ **Syntax Check** - Proper email format
✅ **Domain Validation** - Domain exists and is active  
✅ **MX Record Check** - Mail server is configured
✅ **SMTP Verification** - Server accepts emails

**Features:**
🎯 Bulk validation (CSV, Excel, TXT files)
📊 Detailed validation reports
📈 Usage statistics and analytics
⚡ Fast concurrent processing
🔒 Secure and private (files deleted after 24h)

**Pricing:**
{SUBSCRIPTION_INFO}

**Perfect For:**
• Cold email marketers
• Email list hygiene
• Newsletter campaigns
• Lead generation
• Marketing agencies

Ready to get started?
        """
        
        query = update.callback_query
        await query.edit_message_text(
            learn_more_text,
            reply_markup=self.keyboards.onboarding(),
            parse_mode='Markdown'
        )
