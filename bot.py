"""
Main Telegram bot implementation
"""
import os
import logging
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes
)
from database import get_db, init_database
from models import User, ValidationJob, Subscription
from keyboards import Keyboards
from config import TELEGRAM_BOT_TOKEN, WELCOME_MESSAGE
from handlers.start import StartHandler
from handlers.subscription import SubscriptionHandler
from handlers.validation import ValidationHandler
from handlers.dashboard import DashboardHandler
from utils import escape_markdown

logger = logging.getLogger(__name__)

class EmailValidatorBot:
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.application = None
        self.keyboards = Keyboards()
        
        # Initialize handlers
        self.start_handler = StartHandler()
        self.subscription_handler = SubscriptionHandler()
        self.validation_handler = ValidationHandler()
        self.dashboard_handler = DashboardHandler()
    
    def setup_handlers(self):
        """Setup all bot handlers"""
        app = self.application
        
        # Command handlers
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("dashboard", self.dashboard_command))
        app.add_handler(CommandHandler("subscription", self.subscription_command))
        
        # Callback query handlers
        app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Message handlers
        app.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        
        # Error handler
        app.add_error_handler(self.error_handler)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await self.start_handler.handle_start(update, context)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🤖 **Email Validator Pro - Help**

**Commands:**
• `/start` - Start the bot and show main menu
• `/help` - Show this help message
• `/dashboard` - View your dashboard
• `/subscription` - Manage subscription

**Features:**
• 🎯 Bulk email validation
• 📊 DNS & MX record checks
• 📁 File upload (CSV, Excel, TXT)  
• 📈 Usage statistics
• 💎 Monthly subscription

**File Formats Supported:**
• CSV files with email column
• Excel files (.xlsx, .xls)
• Text files (one email per line)

**Validation Process:**
1. Syntax validation
2. Domain existence check
3. MX record verification
4. SMTP connectivity test

**Need help?** Use the buttons below to navigate.
        """
        
        await update.message.reply_text(
            help_text,
            reply_markup=self.keyboards.help_menu(),
            parse_mode='Markdown'
        )
    
    async def dashboard_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /dashboard command"""
        await self.dashboard_handler.show_dashboard(update, context)
    
    async def subscription_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /subscription command"""
        await self.subscription_handler.show_subscription_menu(update, context)
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all callback queries"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        try:
            # Route callbacks to appropriate handlers
            if data.startswith(('start_', 'onboard_', 'main_menu')):
                await self.start_handler.handle_callback(update, context)
            
            elif data.startswith(('sub_', 'pay_', 'subscription')):
                await self.subscription_handler.handle_callback(update, context)
            
            elif data.startswith(('validate_', 'upload_', 'job_', 'download_', 'details_', 'recent_jobs', 'enter_')):
                await self.validation_handler.handle_callback(update, context)
            
            elif data.startswith(('dashboard', 'usage_', 'activity_')):
                await self.dashboard_handler.handle_callback(update, context)
            
            elif data == 'help':
                await self.show_help_menu(update, context)
            
            elif data == 'user_guide':
                await self.show_user_guide(update, context)
            
            elif data == 'faq':
                await self.show_faq(update, context)
            
            elif data == 'contact_support':
                await self.show_contact_support(update, context)
            
            else:
                await query.edit_message_text(
                    "❌ Unknown command. Please use the menu buttons.",
                    reply_markup=self.keyboards.main_menu()
                )
        
        except Exception as e:
            logger.error(f"Error handling callback {data}: {e}")
            await query.edit_message_text(
                "❌ An error occurred. Please try again.",
                reply_markup=self.keyboards.main_menu()
            )
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle file uploads"""
        await self.validation_handler.handle_file_upload(update, context)
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        # Check if user is in a specific state (like entering emails)
        user_data = context.user_data
        
        if user_data.get('waiting_for_emails'):
            await self.validation_handler.handle_email_input(update, context)
        elif user_data.get('waiting_for_phones'):
            await self.validation_handler.handle_phone_input(update, context)
        elif user_data.get('waiting_for_transaction'):
            await self.subscription_handler.handle_transaction_hash(update, context)
        else:
            # Default response
            await update.message.reply_text(
                "❌ Unknown command. Please use the menu buttons.",
                reply_markup=self.keyboards.main_menu()
            )
    
    async def show_help_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help menu"""
        help_text = """
❓ **Need Help?**

Choose what you'd like to learn about:

• **User Guide** - Step-by-step instructions
• **FAQ** - Frequently asked questions  
• **Contact Support** - Get personal help
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

**Getting Started:**
1. Start with `/start` command
2. Complete onboarding process
3. Try the free trial (10 emails)
4. Subscribe for unlimited access

**Validating Emails:**
1. Click "🎯 Validate Emails"
2. Choose upload method:
   • Upload file (CSV/Excel/TXT)
   • Enter emails manually
3. Wait for processing
4. Download results

**File Formats:**
• **CSV:** Column named 'email' or first column
• **Excel:** Same as CSV, supports .xlsx/.xls
• **TXT:** One email per line

**Understanding Results:**
• ✅ **Valid:** Email passed all checks
• ❌ **Invalid:** Email failed validation
• **Details:** Shows specific failure reasons

**Managing Subscription:**
• View status in Dashboard
• Renew before expiration
• Payment via cryptocurrency
        """
        
        query = update.callback_query
        await query.edit_message_text(
            guide_text,
            reply_markup=self.keyboards.back_to_menu(),
            parse_mode='Markdown'
        )
    
    async def show_faq(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show FAQ"""
        faq_text = """
❓ **Frequently Asked Questions**

**Q: How accurate is the validation?**
A: We perform multiple checks: syntax, DNS lookup, MX records, and SMTP connectivity. Accuracy is typically 95%+.

**Q: What file formats are supported?**
A: CSV, Excel (.xlsx/.xls), and TXT files. Max size: 10MB.

**Q: How long does validation take?**
A: Depends on list size. Typically 1-5 seconds per email with concurrent processing.

**Q: What payment methods do you accept?**
A: Bitcoin, Ethereum, and USDT via secure crypto payments.

**Q: Can I cancel my subscription?**
A: Subscriptions expire automatically after 30 days. No automatic renewal.

**Q: Is my data secure?**
A: Yes. Files are deleted after 24 hours. We don't store your email lists.

**Q: What if validation fails?**
A: Results show specific error reasons. Common issues: invalid syntax, non-existent domain, no MX records.
        """
        
        query = update.callback_query
        await query.edit_message_text(
            faq_text,
            reply_markup=self.keyboards.back_to_menu(),
            parse_mode='Markdown'
        )
    
    async def show_contact_support(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show contact support info"""
        support_text = """
💬 **Contact Support**

Need personal assistance? We're here to help!

**Support Options:**
• Email: support@emailvalidatorpro.com
• Telegram: @EmailValidatorSupport
• Response time: Within 24 hours

**Before contacting support:**
1. Check the FAQ for common questions
2. Try restarting the bot with /start
3. Ensure your file format is supported

**Include in your message:**
• Your Telegram username
• Description of the issue
• Screenshots if applicable
• Error messages (if any)

We'll get back to you as soon as possible!
        """
        
        query = update.callback_query
        await query.edit_message_text(
            support_text,
            reply_markup=self.keyboards.back_to_menu(),
            parse_mode='Markdown'
        )
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        # Try to send error message to user
        try:
            if update.effective_message:
                await update.effective_message.reply_text(
                    "❌ An unexpected error occurred. Please try again or contact support.",
                    reply_markup=self.keyboards.main_menu()
                )
        except:
            pass
    
    def run(self):
        """Start the bot"""
        try:
            # Create application
            self.application = Application.builder().token(self.token).build()
            
            # Setup handlers
            self.setup_handlers()
            
            # Start polling
            logger.info("Bot started successfully")
            self.application.run_polling(allowed_updates=Update.ALL_TYPES)
            
        except Exception as e:
            logger.error(f"Failed to run bot: {e}")
            raise
