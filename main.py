"""
Telegram Bot for Bulk Email Validation
Main entry point for the application
"""
import os
import logging
from bot import EmailValidatorBot
from database import init_database

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

def main():
    """Main function to start the bot"""
    try:
        # Initialize database
        init_database()
        logger.info("Database initialized successfully")
        
        # Initialize and start bot
        bot = EmailValidatorBot()
        logger.info("Starting Telegram bot...")
        bot.run()
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == '__main__':
    main()
