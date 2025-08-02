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
👋 **Welcome to Validator Pro, {user.first_name or 'there'}!**

{WELCOME_MESSAGE}

🎁 **Free Trial:**
• Get 1,000 FREE validations (emails + phones combined)
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
                from config import TRIAL_VALIDATION_LIMIT
                trial_remaining = TRIAL_VALIDATION_LIMIT - user.trial_validations_used
                subscription_status = f"🆓 **Trial:** {trial_remaining} validations remaining (emails + phones)"
            
            menu_text = f"""
🎯 **Validator Pro**

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
            
            elif data == 'main_menu':
                await self.show_main_menu(update, context, user)
            
            elif data == 'help':
                await self.show_help_menu(update, context)
            
            elif data == 'user_guide':
                await self.show_user_guide(update, context)
            
            elif data == 'faq':
                await self.show_faq(update, context)
            
            elif data == 'contact_support':
                await self.show_contact_support(update, context)
    
    async def complete_onboarding(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, db: Session):
        """Complete the onboarding process"""
        user.is_onboarded = True
        db.commit()
        
        from config import TRIAL_VALIDATION_LIMIT
        
        onboarding_complete_text = f"""
🎉 **Onboarding Complete!**

You're all set up and ready to start validating!

**Your Free Trial:**
• {TRIAL_VALIDATION_LIMIT:,} validations included (emails + phones)
• Full access to all features
• Test both email and phone validation

**Next Steps:**
1. Choose Email or Phone validation
2. See our accuracy in action
3. Subscribe for unlimited access

Ready to validate your data!
        """
        
        query = update.callback_query
        await query.edit_message_text(
            onboarding_complete_text,
            reply_markup=self.keyboards.main_menu(),
            parse_mode='Markdown'
        )
    
    async def show_help_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help menu"""
        help_text = """
❓ **Help & Support**

Welcome to Validator Pro! Here's how to get the most out of our service:

**Quick Start:**
1. Click 'Start Trial' to get 1,000 free validations
2. Choose Email or Phone validation
3. Upload files or enter data manually
4. Download your detailed results

**Need assistance?**
• Check our User Guide for detailed instructions
• Browse FAQ for common questions  
• Contact support for personalized help

How can we help you today?
        """
        
        query = update.callback_query
        await query.edit_message_text(
            help_text,
            reply_markup=self.keyboards.help_menu(),
            parse_mode='Markdown'
        )
    
    async def show_user_guide(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user guide"""
        guide_text = """
📖 **User Guide**

**Email Validation:**
• Checks syntax, DNS, MX records, SMTP connectivity
• Accepts individual emails or bulk files
• Returns deliverability status and detailed reports

**Phone Validation:**
• Validates format and carrier information
• Detects country and number type
• Works with international phone numbers

**File Formats Supported:**
• CSV files (comma-separated)
• Excel files (.xlsx, .xls)
• Text files (one per line)

**Results Include:**
• Validation status (valid/invalid)
• Detailed error reasons
• Carrier info (for phones)
• Downloadable CSV reports

**Tips for Best Results:**
• Clean your data first
• Use international format for phones (+1234567890)
• Ensure email format is correct

Need more help? Contact our support team!
        """
        
        query = update.callback_query
        await query.edit_message_text(
            guide_text,
            reply_markup=self.keyboards.back_to_menu(),
            parse_mode='Markdown'
        )
    
    async def show_faq(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show frequently asked questions"""
        faq_text = """
❓ **Frequently Asked Questions**

**Q: How accurate is the validation?**
A: Our email validation achieves 95%+ accuracy using real-time SMTP checks. Phone validation uses Google's libphonenumber for industry-standard accuracy.

**Q: What's included in the free trial?**
A: 1,000 free validations (emails + phones combined) with full access to all features.

**Q: How much does a subscription cost?**
A: $9.99/month for unlimited validations, paid via cryptocurrency.

**Q: What file formats are supported?**
A: CSV, Excel (.xlsx/.xls), and plain text files.

**Q: Is my data secure?**
A: Yes, we use encrypted connections and don't store your validation data permanently.

**Q: Can I validate international phone numbers?**
A: Yes, we support phone numbers from all countries with proper country detection.

**Q: How long do results take?**
A: Email validation: 15-30 emails/second
Phone validation: 50+ phones/second

Still have questions? Contact our support team!
        """
        
        query = update.callback_query
        await query.edit_message_text(
            faq_text,
            reply_markup=self.keyboards.back_to_menu(),
            parse_mode='Markdown'
        )
    
    async def show_contact_support(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show contact support information"""
        support_text = """
💬 **Contact Support**

Our support team is here to help you succeed with Validator Pro.

**Get Help With:**
• Technical issues or errors
• Billing and subscription questions
• Feature requests and suggestions
• Data validation best practices
• Bulk processing assistance

**Response Times:**
• General inquiries: Within 24 hours
• Technical issues: Within 12 hours
• Billing questions: Within 6 hours

**How to Reach Us:**
Send us a message in this chat describing your issue, and our team will respond promptly.

**Include in Your Message:**
• Description of the problem
• Steps you've tried
• Screenshots if helpful
• Your subscription status

We're committed to providing excellent support for all Validator Pro users!
        """
        
        query = update.callback_query
        await query.edit_message_text(
            support_text,
            reply_markup=self.keyboards.back_to_menu(),
            parse_mode='Markdown'
        )
    

