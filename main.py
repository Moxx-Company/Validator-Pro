"""
Validator Pro - Telegram Bot for Email & Phone Validation
Main entry point for the application
"""
import os
import logging
import threading
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram import Update, BotCommand
from handlers.start import StartHandler
from handlers.subscription import SubscriptionHandler  
from handlers.validation import ValidationHandler
from handlers.dashboard import DashboardHandler
from handlers.admin import AdminHandler
from keyboards import Keyboards
from database import init_database
from webhook_handler import create_webhook_app
from config import TELEGRAM_BOT_TOKEN

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Global bot application reference for webhook notifications
bot_application = None

async def send_payment_notification(user_id: int, subscription_id: int):
    """Send payment confirmation notification to user"""
    try:
        if bot_application:
            notification_text = f"""
✅ **Payment Confirmed!**

Your subscription has been activated successfully.

**Order ID:** `{subscription_id}`
**Status:** Active
**Duration:** 30 days
**Features:** Unlimited email & phone validation

You can now validate unlimited emails and phone numbers!
            """
            
            await bot_application.bot.send_message(
                chat_id=user_id,
                text=notification_text,
                parse_mode='Markdown'
            )
            logger.info(f"Payment notification sent to user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send payment notification: {e}")

def run_webhook_server():
    """Run the Flask webhook server in a separate thread"""
    app = create_webhook_app()
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

def setup_handlers(application):
    """Setup all bot handlers"""
    keyboards = Keyboards()
    start_handler = StartHandler()
    subscription_handler = SubscriptionHandler()
    validation_handler = ValidationHandler()
    dashboard_handler = DashboardHandler()
    admin_handler = AdminHandler()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start_handler.handle_start))
    application.add_handler(CommandHandler("dashboard", dashboard_handler.show_dashboard))
    application.add_handler(CommandHandler("subscription", subscription_handler.show_subscription_menu))
    application.add_handler(CommandHandler("admin", admin_handler.handle_admin_command))
    
    # Callback query handler
    async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        
        # Route callbacks to appropriate handlers
        if data.startswith(('validate_', 'upload_', 'job_', 'download_', 'details_', 'recent_jobs', 'enter_', 'start_validation', 'start_phone_validation')):
            await validation_handler.handle_callback(update, context)
        elif data.startswith(('admin_')):
            await admin_handler.handle_callback(update, context)
        elif data.startswith(('sub_', 'pay_', 'subscription')) or data in ('subscribe', 'start_trial'):
            await subscription_handler.handle_callback(update, context)
        elif data.startswith(('dashboard', 'usage_', 'recent_activity')):
            await dashboard_handler.handle_callback(update, context)
        elif data.startswith(('start_', 'onboard_', 'main_menu')) or data in ('help', 'user_guide', 'faq', 'contact_support'):
            await start_handler.handle_callback(update, context)
    
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.Document.ALL, validation_handler.handle_file_upload))
    
    async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        if user_data.get('waiting_for_broadcast'):
            await admin_handler.handle_broadcast_input(update, context)
        elif user_data.get('waiting_for_emails'):
            await validation_handler.handle_email_input(update, context)
        elif user_data.get('waiting_for_phones'):
            await validation_handler.handle_phone_input(update, context)
        elif user_data.get('waiting_for_transaction'):
            await subscription_handler.handle_transaction_hash(update, context)
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

async def setup_bot_commands(application):
    """Set up bot commands in the menu"""
    commands = [
        BotCommand("start", "Start the bot and show main menu"),
        BotCommand("admin", "Access admin panel (admin only)")
    ]
    await application.bot.set_my_commands(commands)

def main():
    """Main entry point"""
    try:
        # Initialize database
        init_database()
        logger.info("Database initialized successfully")
        
        # Start webhook server in background
        webhook_thread = threading.Thread(target=run_webhook_server, daemon=True)
        webhook_thread.start()
        logger.info("Webhook server started on port 5000")
        
        # Start the Telegram bot
        logger.info("Starting Telegram bot...")
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Set global bot reference for webhook notifications
        global bot_application
        bot_application = application
        
        setup_handlers(application)
        
        # Set up bot commands menu after application starts
        async def post_init(app):
            await setup_bot_commands(app)
        
        application.post_init = post_init
        
        logger.info("Bot started successfully")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == '__main__':
    main()
