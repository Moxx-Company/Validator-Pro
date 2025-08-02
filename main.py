"""
Telegram Bot for Bulk Email Validation
Main entry point for the application
"""
import os
import logging
import threading
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram import Update
from handlers.start import StartHandler
from handlers.subscription import SubscriptionHandler  
from handlers.validation import ValidationHandler
from handlers.dashboard import DashboardHandler
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
    
    # Command handlers
    application.add_handler(CommandHandler("start", start_handler.handle_start))
    application.add_handler(CommandHandler("dashboard", dashboard_handler.show_dashboard))
    application.add_handler(CommandHandler("subscription", subscription_handler.show_subscription_menu))
    
    # Callback query handler
    async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        
        # Route callbacks to appropriate handlers
        if data.startswith(('validate_', 'upload_', 'job_', 'download_', 'details_', 'recent_jobs', 'enter_', 'start_validation', 'start_phone_validation')):
            await validation_handler.handle_callback(update, context)
        elif data.startswith(('start_', 'onboard_', 'main_menu')):
            await start_handler.handle_callback(update, context)
        elif data.startswith(('sub_', 'pay_', 'subscription')) or data == 'subscribe':
            await subscription_handler.handle_callback(update, context)
        elif data.startswith(('dashboard', 'usage_', 'activity_')):
            await dashboard_handler.handle_callback(update, context)
    
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.Document.ALL, validation_handler.handle_file_upload))
    
    async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        if user_data.get('waiting_for_emails'):
            await validation_handler.handle_email_input(update, context)
        elif user_data.get('waiting_for_phones'):
            await validation_handler.handle_phone_input(update, context)
        elif user_data.get('waiting_for_transaction'):
            await subscription_handler.handle_transaction_hash(update, context)
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

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
        setup_handlers(application)
        logger.info("Bot started successfully")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == '__main__':
    main()
