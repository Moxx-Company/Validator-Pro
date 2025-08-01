"""
Telegram Bot for Bulk Email Validation
Main entry point for the application
"""
import os
import logging
import threading
from bot import EmailValidatorBot
from database import init_database
from webhook_handler import create_webhook_app

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

def main():
    """Main function to start the bot and webhook server"""
    try:
        # Initialize database
        init_database()
        logger.info("Database initialized successfully")
        
        # Start webhook server in a separate thread
        webhook_thread = threading.Thread(target=run_webhook_server, daemon=True)
        webhook_thread.start()
        logger.info("Webhook server started on port 5000")
        
        # Initialize and start bot
        bot = EmailValidatorBot()
        logger.info("Starting Telegram bot...")
        bot.run()
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == '__main__':
    main()
