"""
Email validation handler
"""
import os
import logging
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User, ValidationJob, ValidationResult
from keyboards import Keyboards
from email_validator import EmailValidator
from file_processor import FileProcessor
from utils import create_progress_bar, format_duration, format_file_size
from config import MAX_FILE_SIZE_MB

logger = logging.getLogger(__name__)

class ValidationHandler:
    def __init__(self):
        self.keyboards = Keyboards()
        self.email_validator = EmailValidator()
        self.file_processor = FileProcessor()
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle validation-related callbacks"""
        query = update.callback_query
        data = query.data
        telegram_user = update.effective_user
        
        with SessionLocal() as db:
            user = db.query(User).filter(User.telegram_id == str(telegram_user.id)).first()
            
            if data == 'validate_emails':
                await self.show_validation_menu(update, context, user)
            
            elif data == 'upload_file':
                await self.show_file_upload_options(update, context)
            
            elif data == 'enter_emails':
                await self.start_email_input(update, context)
            
            elif data == 'recent_jobs':
                await self.show_recent_jobs(update, context, user, db)
            
            elif data.startswith('upload_'):
                file_type = data.split('_')[1]
                await self.prompt_file_upload(update, context, file_type)
            
            elif data.startswith('download_'):
                job_id = data.split('_')[1]
                await self.download_results(update, context, user, job_id, db)
            
            elif data.startswith('details_'):
                job_id = data.split('_')[1]
                await self.show_job_details(update, context, user, job_id, db)
    
    async def show_validation_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
        """Show email validation options"""
        with SessionLocal() as db:
            user = db.query(User).filter(User.telegram_id == str(user.telegram_id)).first()
            
            # Check user's validation capacity
            if user.has_active_subscription():
                capacity_info = "✅ **Unlimited validations**"
            else:
                remaining = 10 - user.trial_emails_used
                capacity_info = f"🆓 **Trial:** {remaining} validations remaining"
            
            menu_text = f"""
🎯 **Email Validation**

{capacity_info}

**How would you like to validate emails?**

📁 **Upload File** - CSV, Excel, or TXT files
✍️ **Enter Emails** - Type or paste email addresses
📊 **Recent Jobs** - View your validation history

**Supported formats:**
• CSV with email column
• Excel files (.xlsx, .xls)
• Text files (one email per line)
• Max file size: {MAX_FILE_SIZE_MB}MB
            """
            
            query = update.callback_query
            await query.edit_message_text(
                menu_text,
                reply_markup=self.keyboards.validation_menu(),
                parse_mode='Markdown'
            )
    
    async def show_file_upload_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show file upload format options"""
        upload_text = """
📁 **File Upload**

Choose your file format:

**📄 CSV File**
• Must have 'email' column or emails in first column
• UTF-8 encoding recommended

**📊 Excel File**
• .xlsx or .xls formats supported
• Emails in 'email' column or first column

**📝 Text File**
• One email address per line
• Plain text format (.txt)

Select your file type and then send the file:
        """
        
        query = update.callback_query
        await query.edit_message_text(
            upload_text,
            reply_markup=self.keyboards.file_upload_options(),
            parse_mode='Markdown'
        )
    
    async def prompt_file_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE, file_type: str):
        """Prompt user to upload specific file type"""
        context.user_data['expected_file_type'] = file_type
        
        file_types = {
            'csv': ('CSV', '.csv'),
            'excel': ('Excel', '.xlsx or .xls'),
            'txt': ('Text', '.txt')
        }
        
        type_name, extensions = file_types.get(file_type, ('File', 'supported'))
        
        prompt_text = f"""
📤 **Upload {type_name} File**

Please send me your {type_name.lower()} file with email addresses.

**Requirements:**
• Format: {extensions}
• Max size: {MAX_FILE_SIZE_MB}MB
• Emails should be in 'email' column or first column

Just drag and drop your file or click the attachment button and send it to me.
        """
        
        query = update.callback_query
        await query.edit_message_text(
            prompt_text,
            reply_markup=self.keyboards.back_to_menu(),
            parse_mode='Markdown'
        )
    
    async def start_email_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start manual email input process"""
        context.user_data['waiting_for_emails'] = True
        
        input_text = """
✍️ **Enter Email Addresses**

Send me email addresses to validate. You can:

• Type one email per line
• Paste multiple emails (separated by lines, commas, or spaces)
• Send multiple messages

**Example:**
