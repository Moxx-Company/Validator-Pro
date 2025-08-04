"""
Email validation handler
"""
import os
import logging
import asyncio
import json
import time
import concurrent.futures
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User, ValidationJob, ValidationResult
from keyboards import Keyboards
from email_validator import EmailValidator, ValidationResult as EmailValidationResult
from phone_validator import PhoneValidator, PhoneValidationResult
from file_processor import FileProcessor
from utils import create_progress_bar, format_duration, format_file_size
from config import MAX_FILE_SIZE_MB
from progress_tracker import progress_tracker

logger = logging.getLogger(__name__)

class ValidationHandler:
    def __init__(self):
        self.keyboards = Keyboards()
        self.email_validator = EmailValidator()
        self.phone_validator = PhoneValidator()
        self.file_processor = FileProcessor()
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle validation-related callbacks"""
        query = update.callback_query
        if not query:
            return
            
        data = query.data
        if not data:
            return
            
        telegram_user = update.effective_user
        if not telegram_user:
            return
        
        with SessionLocal() as db:
            user = db.query(User).filter(User.telegram_id == str(telegram_user.id)).first()
            
            if data == 'validate_emails':
                if not user:
                    await query.edit_message_text("❌ User not found. Please start with /start")
                    return
                await self.show_validation_menu(update, context, user, 'email')
            
            elif data == 'validate_phones':
                if not user:
                    await query.edit_message_text("❌ User not found. Please start with /start")  
                    return
                await self.show_validation_menu(update, context, user, 'phone')
            
            elif data == 'upload_file':
                await self.show_file_upload_options(update, context, 'email')
                
            elif data and data.startswith('upload_file_'):
                validation_type = data.split('_')[-1]  # email or phone  
                if context.user_data is not None:
                    context.user_data['validation_type'] = validation_type
                await self.show_file_upload_options(update, context, validation_type)
            
            elif data and data.startswith('recent_jobs_'):
                validation_type = data.split('_')[-1]  # emails or phones  
                await self.show_recent_jobs(update, context, user, db)
            
            elif data == 'enter_emails':
                await self.start_email_input(update, context)
                
            elif data == 'enter_phones':
                await self.start_phone_input(update, context)
            
            elif data == 'recent_jobs':
                await self.show_recent_jobs(update, context, user, db)
            
            elif data and data.startswith('upload_'):
                file_type = data.split('_')[1]
                await self.prompt_file_upload(update, context, file_type)
            
            elif data and data.startswith('download_'):
                job_id = data.split('_')[1]
                if user:
                    await self.download_results(update, context, user, job_id, db)
            
            elif data and data.startswith('details_'):
                job_id = data.split('_')[1]
                if user:
                    await self.show_job_details(update, context, user, job_id, db)
            
            elif data == 'start_validation':
                await self.start_validation_from_input(update, context)
                
            elif data == 'start_phone_validation':
                logger.info(f"Processing start_phone_validation callback")
                await self.start_phone_validation_from_input(update, context)
            
            elif data == 'job_history':
                await self.show_job_history(update, context, user, db, 0)
            
            elif data.startswith('history_page_'):
                page = int(data.split('_')[-1])
                await self.show_job_history(update, context, user, db, page)
    
    async def show_validation_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, validation_type: str = 'email'):
        """Show validation options for email or phone"""
        # Store validation type in user context
        if context.user_data is not None:
            context.user_data['validation_type'] = validation_type
        
        with SessionLocal() as db:
            if user:
                user = db.query(User).filter(User.telegram_id == str(user.telegram_id)).first()
            
            # Check user's validation capacity
            if user and hasattr(user, 'has_active_subscription') and user.has_active_subscription():
                capacity_info = "✅ Unlimited validations"
            elif user and hasattr(user, 'get_trial_remaining'):
                remaining = user.get_trial_remaining()
                capacity_info = f"🆓 Trial: {remaining} validations remaining"
            else:
                capacity_info = "🆓 Trial: 1000 validations remaining"
            
            if validation_type == 'email':
                title = "📧 Email Validation"
                item_name = "emails"
                format_info = """Supported formats:
• CSV with email column
• Excel files (.xlsx, .xls)
• Text files (one email per line)
• Max file size: 10MB"""
            else:
                title = "📱 Phone Number Validation"
                item_name = "phone numbers"
                format_info = """Supported formats:
• CSV with phone column
• Excel files (.xlsx, .xls)
• Text files (one number per line)
• International format supported
• Max file size: 10MB"""
            
            menu_text = f"""{title}

{capacity_info}

How would you like to validate {item_name}?

📁 Upload File - CSV, Excel, or TXT files
✍️ Enter {item_name.title()} - Type or paste {item_name}
📊 Recent Jobs - View your validation history

{format_info}"""
            
            query = update.callback_query
            await query.edit_message_text(
                menu_text,
                reply_markup=self.keyboards.validation_menu(validation_type)
            )
    
    async def show_file_upload_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE, validation_type: str = 'email'):
        """Show file upload format options"""
        context.user_data['validation_type'] = validation_type
        
        if validation_type == 'email':
            item_name = "email addresses"
            column_info = "• Must have 'email' column or emails in first column"
            line_format = "• One email address per line"
        else:
            item_name = "phone numbers"
            column_info = "• Must have 'phone' or 'phone_number' column or numbers in first column"
            line_format = "• One phone number per line (international format supported)"
            
        upload_text = f"""📁 File Upload

Choose your file format for {item_name}:

📄 CSV File
{column_info}
• UTF-8 encoding recommended

📊 Excel File
• .xlsx or .xls formats supported
{column_info}

📝 Text File
{line_format}
• Plain text format (.txt)

Select your file type and then send the file:"""
        
        query = update.callback_query
        await query.edit_message_text(
            upload_text,
            reply_markup=self.keyboards.file_upload_options()
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
        context.user_data['validation_type'] = 'email'
        context.user_data['waiting_for_emails'] = True
        context.user_data['collected_emails'] = []
        
        input_text = """
✍️ **Enter Email Addresses**

Send me email addresses to validate. You can:

• Type one email per line
• Paste multiple emails (separated by lines, commas, or spaces)
• Send multiple messages

**Example:**
john@example.com
jane@test.com
support@company.org

When you're done, click "Start Validation" below or type /done.
        """
        
        query = update.callback_query
        await query.edit_message_text(
            input_text,
            reply_markup=self.keyboards.email_input_menu(),
            parse_mode='Markdown'
        )
    
    async def handle_email_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle email input from user"""
        text = update.message.text.strip()
        
        # Check for done command
        if text.lower() == '/done':
            await self.start_validation_from_input(update, context)
            return
        
        # Extract emails from text
        import re
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        found_emails = re.findall(email_pattern, text)
        
        if not found_emails:
            await update.message.reply_text(
                "❌ No valid email addresses found. Please enter valid emails or click 'Start Validation' when done.",
                reply_markup=self.keyboards.email_input_menu()
            )
            return
        
        # Add to collected emails
        if 'collected_emails' not in context.user_data:
            context.user_data['collected_emails'] = []
        
        context.user_data['collected_emails'].extend(found_emails)
        
        # Remove duplicates
        unique_emails = list(dict.fromkeys(context.user_data['collected_emails']))
        context.user_data['collected_emails'] = unique_emails
        
        await update.message.reply_text(
            f"✅ Added {len(found_emails)} email(s). Total collected: {len(unique_emails)}\n\n"
            "Send more emails or click 'Start Validation' below.",
            reply_markup=self.keyboards.email_input_menu()
        )
    
    async def start_validation_from_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start validation from manually entered emails"""
        emails = context.user_data.get('collected_emails', [])
        
        if not emails:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    "❌ No emails entered. Please enter some emails first.",
                    reply_markup=self.keyboards.email_input_menu()
                )
            else:
                await update.message.reply_text(
                    "❌ No emails entered. Please enter some emails first.",
                    reply_markup=self.keyboards.email_input_menu()
                )
            return
        
        # Clear input state
        context.user_data['waiting_for_emails'] = False
        context.user_data['collected_emails'] = []
        
        # Get user
        telegram_user = update.effective_user
        with SessionLocal() as db:
            user = db.query(User).filter(User.telegram_id == str(telegram_user.id)).first()
            
            if not user:
                message = "❌ User not found. Please start with /start"
                if update.callback_query:
                    await update.callback_query.edit_message_text(message, reply_markup=self.keyboards.main_menu())
                else:
                    await update.message.reply_text(message, reply_markup=self.keyboards.main_menu())
                return
            
            # Check credits using unified trial system
            if not user.has_active_subscription():
                remaining = user.get_trial_remaining()
                if len(emails) > remaining:
                    message = (f"❌ You entered {len(emails)} emails, but only have {remaining} trial validations remaining.\n\n"
                              "Please subscribe for unlimited access.")
                    if update.callback_query:
                        await update.callback_query.edit_message_text(message, reply_markup=self.keyboards.subscription_prompt())
                    else:
                        await update.message.reply_text(message, reply_markup=self.keyboards.subscription_prompt())
                    return
            
            # Start validation
            message_text = f"🔄 Starting validation of {len(emails)} emails..."
            if update.callback_query:
                message = await update.callback_query.edit_message_text(message_text)
            else:
                message = await update.message.reply_text(message_text)
            
            await self.process_email_validation(message, user, emails, db, "Manual Input")
    
    async def start_phone_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start manual phone number input process"""
        context.user_data['validation_type'] = 'phone'
        context.user_data['waiting_for_phones'] = True
        context.user_data['collected_phones'] = []
        
        input_text = """
📱 **Enter Phone Numbers**

Send me phone numbers to validate. You can:

• Type one number per line
• Include country code (+1234567890) or local format
• Send multiple messages

**Examples:**
+1 555-123-4567
+44 20 7946 0958
+91 98765 43210
(555) 123-4567

When you're done, click "Start Validation" below.
        """
        
        query = update.callback_query
        await query.edit_message_text(
            input_text,
            reply_markup=self.keyboards.phone_input_initial(),
            parse_mode='Markdown'
        )
    
    async def handle_phone_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle phone number input from user"""
        text = update.message.text.strip()
        
        # Check for done command
        if text.lower() == '/done':
            await self.start_phone_validation_from_input(update, context)
            return
        
        # Extract phone numbers from text
        found_phones = self.phone_validator.extract_phone_numbers(text)
        
        if not found_phones:
            await update.message.reply_text(
                "❌ No valid phone numbers found. Please enter valid phone numbers.",
                reply_markup=self.keyboards.phone_input_initial()
            )
            return
        
        # Add to collected phones
        if 'collected_phones' not in context.user_data:
            context.user_data['collected_phones'] = []
        
        context.user_data['collected_phones'].extend(found_phones)
        
        # Remove duplicates
        unique_phones = list(dict.fromkeys(context.user_data['collected_phones']))
        context.user_data['collected_phones'] = unique_phones
        
        await update.message.reply_text(
            f"✅ Added {len(found_phones)} phone number(s). Total collected: {len(unique_phones)}\n\n"
            "Send more numbers or click 'Start Validation' below.",
            reply_markup=self.keyboards.phone_input_menu(has_numbers=True)
        )
    
    async def start_phone_validation_from_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start validation from manually entered phone numbers"""
        logger.info(f"start_phone_validation_from_input called")
        phones = context.user_data.get('collected_phones', [])
        logger.info(f"Found {len(phones)} phones in user_data: {phones}")
        
        if not phones:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    "❌ No phone numbers entered. Please enter some numbers first.",
                    reply_markup=self.keyboards.phone_input_initial()
                )
            else:
                await update.message.reply_text(
                    "❌ No phone numbers entered. Please enter some numbers first.",
                    reply_markup=self.keyboards.phone_input_initial()
                )
            return
        
        # Clear input state
        if context.user_data:
            context.user_data['waiting_for_phones'] = False
            context.user_data['collected_phones'] = []
        
        # Get user
        telegram_user = update.effective_user
        with SessionLocal() as db:
            user = db.query(User).filter(User.telegram_id == str(telegram_user.id)).first()
            
            if not user:
                message = "❌ User not found. Please start with /start"
                if update.callback_query:
                    await update.callback_query.edit_message_text(message, reply_markup=self.keyboards.main_menu())
                else:
                    await update.message.reply_text(message, reply_markup=self.keyboards.main_menu())
                return
            
            # Check credits using unified trial system
            if not user.has_active_subscription():
                remaining = user.get_trial_remaining()
                if len(phones) > remaining:
                    message = (f"❌ You entered {len(phones)} phone numbers, but only have {remaining} trial validations remaining.\n\n"
                              "Please subscribe for unlimited access.")
                    if update.callback_query:
                        await update.callback_query.edit_message_text(message, reply_markup=self.keyboards.subscription_prompt())
                    else:
                        await update.message.reply_text(message, reply_markup=self.keyboards.subscription_prompt())
                    return
            
            # Start validation
            message_text = f"🔄 Starting validation of {len(phones)} phone numbers..."
            if update.callback_query:
                message = await update.callback_query.edit_message_text(message_text)
            else:
                message = await update.message.reply_text(message_text)
            
            await self.process_phone_validation(message, user, phones, db, "Manual Input")
    
    async def process_phone_validation(self, message, user: User, phone_numbers: list, db: Session, filename: str = None):
        """Process phone number validation and update progress"""
        from rate_limiter import validation_queue
        
        # Acquire validation slot
        await validation_queue.acquire()
        
        try:
            # Create validation job
            job = ValidationJob(
                user_id=user.id,
                validation_type='phone',
                total_items=len(phone_numbers),
                filename=filename or "Manual Input",
                status="processing"
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            
            # Start progress tracking
            progress_tracker.start_job(job.id, len(phone_numbers), 'phone')
            
            # Update message
            await message.edit_text(
                f"🔄 Validating {len(phone_numbers)} phone numbers...\n"
                f"Progress: 0/{len(phone_numbers)} (0%)",
                reply_markup=None
            )
            
            # Process phone numbers in batches
            batch_size = 50
            validated_count = 0
            valid_count = 0
            start_time = time.time()
            
            for i in range(0, len(phone_numbers), batch_size):
                batch = phone_numbers[i:i + batch_size]
                
                # Validate batch
                batch_results = await self.phone_validator.validate_batch_async(batch)
                
                # Save results to database
                for result in batch_results:
                    validation_result = ValidationResult(
                        job_id=job.id,
                        validation_type='phone',
                        phone_number=result.number,
                        is_valid=result.is_valid,
                        formatted_international=result.formatted_international,
                        formatted_national=result.formatted_national,
                        country_code=result.country_code,
                        country_name=result.country_name,
                        carrier=result.carrier_name,
                        number_type=result.number_type,
                        timezone=json.dumps(result.timezones) if result.timezones else None,
                        error_message=result.error_message,
                        validation_time=0.1  # Phone validation is fast
                    )
                    db.add(validation_result)
                    
                    if result.is_valid:
                        valid_count += 1
                
                validated_count += len(batch_results)
                
                # Update progress tracker
                progress_tracker.update_progress(job.id, validated_count, valid_count)
                
                # Get formatted progress
                progress_text = progress_tracker.get_formatted_progress(job.id)
                
                await message.edit_text(progress_text)
                
                # Commit batch results
                db.commit()
            
            # Update job completion
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.processed_items = len(phone_numbers)
            job.valid_items = valid_count
            job.invalid_items = len(phone_numbers) - valid_count
            db.commit()
            
            # Complete progress tracking
            progress_tracker.complete_job(job.id, True)
            
            # Update user usage
            if not user.has_active_subscription():
                user.use_trial_validations('phone', len(phone_numbers))
                db.commit()
            
            # Show final results
            invalid_count = len(phone_numbers) - valid_count
            final_text = f"""✅ Phone Validation Complete!

📊 Results Summary:
• Total numbers: {len(phone_numbers)}
• Valid: {valid_count}
• Invalid: {invalid_count}
• Success Rate: {(valid_count/len(phone_numbers)*100):.1f}%

📁 File: {filename or 'Manual Input'}
⏱️ Completed: {datetime.now().strftime('%H:%M')}"""
            
            await message.edit_text(
                final_text,
                reply_markup=self.keyboards.validation_results(job.id)
            )
            
        except Exception as e:
            logger.error(f"Error in phone validation process: {e}")
            if 'job' in locals():
                job.status = "failed"
                try:
                    db.commit()
                except:
                    db.rollback()
            
            await message.edit_text(
                "❌ Validation failed. Please try again or contact support.",
                reply_markup=self.keyboards.main_menu()
            )
        finally:
            # Always release validation slot
            validation_queue.release()
    
    async def handle_file_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle file upload for email or phone validation"""
        document = update.message.document
        telegram_user = update.effective_user
        
        with SessionLocal() as db:
            user = db.query(User).filter(User.telegram_id == str(telegram_user.id)).first()
            
            if not user:
                await update.message.reply_text(
                    "❌ User not found. Please start with /start",
                    reply_markup=self.keyboards.main_menu()
                )
                return
            
            # Check file size
            if document.file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
                await update.message.reply_text(
                    f"❌ File too large. Maximum size is {MAX_FILE_SIZE_MB}MB",
                    reply_markup=self.keyboards.main_menu()
                )
                return
            
            # Check file type
            allowed_types = ['text/plain', 'text/csv', 'application/vnd.ms-excel', 
                           'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                           'application/pdf']
            
            if document.mime_type not in allowed_types:
                await update.message.reply_text(
                    "❌ Unsupported file type. Please upload CSV, Excel, TXT, or PDF files only.",
                    reply_markup=self.keyboards.main_menu()
                )
                return
            
            # Show processing message
            processing_msg = await update.message.reply_text(
                "📁 Processing your file...",
                reply_markup=self.keyboards.main_menu()
            )
            
            try:
                # Download file
                file = await context.bot.get_file(document.file_id)
                file_path = f"/tmp/{document.file_name}"
                await file.download_to_drive(file_path)
                
                # Determine validation type from context
                validation_type = context.user_data.get('validation_type', 'email')
                
                # Process file based on validation type
                if validation_type == 'email':
                    items, file_info = self.file_processor.process_uploaded_file(file_path, 'email')
                    item_name = "emails"
                else:
                    items, file_info = self.file_processor.process_uploaded_file(file_path, 'phone')
                    item_name = "phone numbers"
                
                if not items:
                    await processing_msg.edit_text(
                        f"❌ No valid {item_name} found in the file.",
                        reply_markup=self.keyboards.main_menu()
                    )
                    return
                
                # Check if user has enough credits using unified trial system
                if not user.has_active_subscription():
                    remaining = user.get_trial_remaining()
                    if len(items) > remaining:
                        await processing_msg.edit_text(
                            f"❌ File contains {len(items)} {item_name}, but you only have {remaining} trial validations remaining.\n\n"
                            "Please subscribe for unlimited access or upload a smaller file.",
                            reply_markup=self.keyboards.subscription_prompt()
                        )
                        return
                
                # Start validation
                if validation_type == 'email':
                    await self.process_email_validation(processing_msg, user, items, db, document.file_name)
                else:
                    await self.process_phone_validation(processing_msg, user, items, db, document.file_name)
                
                # Clean up file
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
            except Exception as e:
                logger.error(f"Error processing file upload: {e}")
                await processing_msg.edit_text(
                    "❌ Error processing file. Please check the format and try again.",
                    reply_markup=self.keyboards.main_menu()
                )
    
    async def process_email_validation(self, message, user: User, emails: list, db: Session, filename: str = None):
        """Process email validation and update progress with enterprise optimizations"""
        from rate_limiter import validation_queue
        
        # Acquire validation slot for enterprise load balancing
        await validation_queue.acquire()
        
        try:
            # Create validation job
            job = ValidationJob(
                user_id=user.id,
                validation_type='email',
                filename=filename or "Manual Input",
                total_items=len(emails),
                total_emails=len(emails),  # For backward compatibility
                status="processing"
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            
            # Start progress tracking
            progress_tracker.start_job(job.id, len(emails), 'email')
            
            # Update message
            await message.edit_text(
                f"🔄 Validating {len(emails)} emails...\n"
                f"Progress: 0/{len(emails)} (0%)",
                reply_markup=None
            )
            
            # Create validator instance
            validator = EmailValidator()
            
            # Process emails in stable batches
            batch_size = 25  # Balanced for stability and speed
            validated_count = 0
            start_time = time.time()
            
            for i in range(0, len(emails), batch_size):
                batch = emails[i:i + batch_size]
                
                # Validate batch with proper executor handling
                batch_results = []
                try:
                    # Use thread pool for CPU-bound validation tasks
                    loop = asyncio.get_running_loop()
                    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                        # Create futures for batch
                        futures = []
                        for email in batch:
                            future = loop.run_in_executor(executor, validator.validate_single_email, email)
                            futures.append(future)
                        
                        # Wait with timeout
                        batch_results = await asyncio.wait_for(
                            asyncio.gather(*futures, return_exceptions=True),
                            timeout=15.0  # 15 second timeout per batch
                        )
                except asyncio.TimeoutError:
                    logger.warning(f"Batch timeout at {validated_count}/{len(emails)}")
                    # Create timeout results for remaining emails
                    for email in batch[len(batch_results):]:
                        batch_results.append(EmailValidationResult(
                            email=email,
                            is_valid=False,
                            syntax_valid=False,
                            domain_exists=False,
                            mx_record_exists=False,
                            smtp_connectable=False,
                            domain="",
                            mx_records=[],
                            error_message="Validation timeout",
                            validation_time=0
                        ))
                except Exception as batch_error:
                    logger.error(f"Batch error: {batch_error}")
                    # Create error results for all emails in batch
                    batch_results = []
                    for email in batch:
                        batch_results.append(EmailValidationResult(
                            email=email,
                            is_valid=False,
                            syntax_valid=False,
                            domain_exists=False,
                            mx_record_exists=False,
                            smtp_connectable=False,
                            domain="",
                            mx_records=[],
                            error_message=f"Batch error: {str(batch_error)}",
                            validation_time=0
                        ))
                
                # Save results from batch
                for result in batch_results:
                    try:
                        if isinstance(result, EmailValidationResult):
                            # Save successful validation result
                            validation_result = ValidationResult(
                                job_id=job.id,
                                validation_type='email',
                                email=result.email,
                                is_valid=result.is_valid,
                                syntax_valid=result.syntax_valid,
                                domain_exists=result.domain_exists,
                                mx_record_exists=result.mx_record_exists,
                                smtp_connectable=result.smtp_connectable,
                                error_message=result.error_message,
                                mx_records=json.dumps(result.mx_records) if result.mx_records else None
                            )
                            db.add(validation_result)
                        elif isinstance(result, Exception):
                            # Handle exception - find corresponding email
                            idx = batch_results.index(result)
                            email = batch[idx] if idx < len(batch) else "unknown"
                            validation_result = ValidationResult(
                                job_id=job.id,
                                email=email,
                                is_valid=False,
                                syntax_valid=False,
                                domain_exists=False,
                                mx_record_exists=False,
                                smtp_connectable=False,
                                error_message=f"Validation error: {str(result)}",
                                mx_records=None
                            )
                            db.add(validation_result)
                    except Exception as save_error:
                        logger.error(f"Error saving validation result for {email}: {save_error}")
                    
                    validated_count += 1
                
                # Batch commit for better database performance
                try:
                    db.commit()
                except Exception as commit_error:
                    logger.error(f"Database commit error: {commit_error}")
                    db.rollback()
                
                # Update progress tracker
                results = db.query(ValidationResult).filter(ValidationResult.job_id == job.id).all()
                current_valid = sum(1 for r in results if r.is_valid)
                progress_tracker.update_progress(job.id, validated_count, current_valid)
                
                # Update UI with formatted progress
                try:
                    progress_text = progress_tracker.get_formatted_progress(job.id)
                    await message.edit_text(progress_text, reply_markup=None)
                except Exception as update_error:
                    logger.debug(f"Progress update failed: {update_error}")  # Ignore rate limits
                
                # Small delay between batches for stability
                await asyncio.sleep(0.05)
            
            # Update job status and counts
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.processed_items = len(emails)
            job.processed_emails = len(emails)  # For backward compatibility
            
            # Update valid/invalid counts from database
            results = db.query(ValidationResult).filter(ValidationResult.job_id == job.id).all()
            valid_count = sum(1 for r in results if r.is_valid)
            job.valid_items = valid_count
            job.valid_emails = valid_count  # For backward compatibility
            job.invalid_items = len(results) - valid_count
            job.invalid_emails = len(results) - valid_count  # For backward compatibility
            
            # Update user usage
            if not user.has_active_subscription():
                user.use_trial_validations('email', len(emails))
            
            db.commit()
            
            # Complete progress tracking
            progress_tracker.complete_job(job.id, True)
            
            # Get results summary
            results = db.query(ValidationResult).filter(ValidationResult.job_id == job.id).all()
            valid_count = sum(1 for r in results if r.is_valid)
            invalid_count = len(results) - valid_count
            
            # Final message without markdown to avoid parsing errors
            final_text = f"""✅ Validation Complete!

📊 Results Summary:
• Total emails: {len(emails)}
• Valid: {valid_count}
• Invalid: {invalid_count}
• Accuracy: {(valid_count/len(emails)*100):.1f}%

📁 File: {filename or 'Manual Input'}
⏱️ Completed: {datetime.now().strftime('%H:%M')}"""
            
            await message.edit_text(
                final_text,
                reply_markup=self.keyboards.validation_results(job.id)
            )
            
        except Exception as e:
            logger.error(f"Error in email validation process: {e}")
            if 'job' in locals():
                job.status = "failed"
                try:
                    db.commit()
                except:
                    db.rollback()
            
            await message.edit_text(
                "❌ Validation failed. Please try again or contact support.",
                reply_markup=self.keyboards.main_menu()
            )
        finally:
            # Always release validation slot
            validation_queue.release()
    
    async def show_job_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, job_id: int, db: Session):
        """Show detailed validation job results"""
        try:
            # Get job and results from database
            job = db.query(ValidationJob).filter(ValidationJob.id == job_id, ValidationJob.user_id == user.id).first()
            if not job:
                await update.callback_query.edit_message_text(
                    "❌ Validation job not found.",
                    reply_markup=self.keyboards.main_menu()
                )
                return
            
            results = db.query(ValidationResult).filter(ValidationResult.job_id == job_id).all()
            
            # Calculate statistics
            total_emails = len(results)
            valid_count = sum(1 for r in results if r.is_valid)
            invalid_count = total_emails - valid_count
            
            # Create details message
            details_text = f"""📊 Validation Job Details

📁 File: {job.filename}
📅 Created: {job.created_at.strftime('%Y-%m-%d %H:%M')}
⚡ Status: {job.status.title()}

📈 Results Summary:
• Total Emails: {total_emails}
• Valid Emails: {valid_count}
• Invalid Emails: {invalid_count}
• Success Rate: {(valid_count/total_emails*100):.1f}%

⏱️ Processing Time: {job.completed_at.strftime('%H:%M') if job.completed_at else 'In Progress'}"""
            
            await update.callback_query.edit_message_text(
                details_text,
                reply_markup=self.keyboards.validation_results(job_id)
            )
            
        except Exception as e:
            logger.error(f"Error showing job details: {e}")
            await update.callback_query.edit_message_text(
                "❌ An error occurred loading job details.",
                reply_markup=self.keyboards.main_menu()
            )
    
    async def download_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, job_id: str, db: Session):
        """Send validation results as CSV file directly through Telegram"""
        try:
            job = db.query(ValidationJob).filter(ValidationJob.id == int(job_id), ValidationJob.user_id == user.id).first()
            if not job:
                await update.callback_query.edit_message_text(
                    "❌ Validation job not found.",
                    reply_markup=self.keyboards.main_menu()
                )
                return
            
            results = db.query(ValidationResult).filter(ValidationResult.job_id == int(job_id)).all()
            
            if not results:
                await update.callback_query.edit_message_text(
                    "❌ No results found for this job.",
                    reply_markup=self.keyboards.main_menu()
                )
                return
            
            # Detect original file format from filename
            validation_type = job.validation_type or 'email'
            original_filename = job.filename or 'Manual Input'
            
            # Determine file format and generate appropriate content
            if original_filename.lower().endswith('.txt') or original_filename == 'Manual Input':
                # Generate TXT format
                content, filename, mime_type = self._create_results_txt(results, validation_type, job.created_at)
            elif original_filename.lower().endswith(('.xlsx', '.xls')):
                # Generate Excel format
                content, filename, mime_type = self._create_results_excel(results, validation_type, job.created_at)
            elif original_filename.lower().endswith('.pdf'):
                # Generate PDF format
                content, filename, mime_type = self._create_results_pdf(results, validation_type, job.created_at)
            else:
                # Default to CSV format
                content, filename, mime_type = self._create_results_csv_formatted(results, validation_type, job.created_at)
            
            # Send processing message
            format_name = filename.split('.')[-1].upper()
            await update.callback_query.edit_message_text(
                f"📤 Preparing your {validation_type} validation results...\n\nSending {format_name} file with {len(results)} records.",
                reply_markup=self.keyboards.back_to_job_details(job_id)
            )
            
            # Send file as document
            from io import BytesIO
            if isinstance(content, bytes):
                file_bytes = BytesIO(content)
            else:
                file_bytes = BytesIO(content.encode('utf-8'))
            file_bytes.name = filename
            
            await update.callback_query.message.reply_document(
                document=file_bytes,
                filename=filename,
                caption=f"📊 {validation_type.title()} Validation Results\n\n📁 Original: {original_filename}\n📈 Records: {len(results)}\n📅 {job.created_at.strftime('%Y-%m-%d %H:%M') if job.created_at else 'Unknown date'}"
            )
            
        except Exception as e:
            logger.error(f"Error sending results file: {e}")
            await update.callback_query.edit_message_text(
                "❌ Error preparing results file. Please try again.",
                reply_markup=self.keyboards.main_menu()
            )
    
    def _create_results_csv_formatted(self, results: list, validation_type: str = 'email', created_at=None) -> tuple:
        """Create CSV content with proper formatting"""
        content = self._create_results_csv(results, validation_type)
        timestamp = created_at.strftime('%Y%m%d_%H%M%S') if created_at else 'unknown'
        filename = f"{validation_type}_validation_results_{timestamp}.csv"
        return content, filename, 'text/csv'
    
    def _create_results_txt(self, results: list, validation_type: str = 'email', created_at=None) -> tuple:
        """Create TXT format results"""
        timestamp = created_at.strftime('%Y%m%d_%H%M%S') if created_at else 'unknown'
        filename = f"{validation_type}_validation_results_{timestamp}.txt"
        
        lines = [f"{validation_type.upper()} VALIDATION RESULTS"]
        lines.append("=" * 50)
        lines.append(f"Generated: {created_at.strftime('%Y-%m-%d %H:%M:%S') if created_at else 'Unknown'}")
        lines.append(f"Total Records: {len(results)}")
        lines.append("")
        
        if validation_type == 'email':
            valid_count = sum(1 for r in results if r.is_valid)
            lines.append(f"Valid Emails: {valid_count}")
            lines.append(f"Invalid Emails: {len(results) - valid_count}")
            lines.append("")
            
            for i, result in enumerate(results, 1):
                lines.append(f"{i}. {result.email or 'N/A'}")
                lines.append(f"   Status: {'VALID' if result.is_valid else 'INVALID'}")
                if result.error_message:
                    lines.append(f"   Error: {result.error_message}")
                if result.formatted_international:
                    lines.append(f"   Format: {result.formatted_international}")
                lines.append("")
        else:  # phone
            valid_count = sum(1 for r in results if r.is_valid)
            lines.append(f"Valid Numbers: {valid_count}")
            lines.append(f"Invalid Numbers: {len(results) - valid_count}")
            lines.append("")
            
            for i, result in enumerate(results, 1):
                lines.append(f"{i}. {result.phone_number or 'N/A'}")
                lines.append(f"   Status: {'VALID' if result.is_valid else 'INVALID'}")
                if result.formatted_international:
                    lines.append(f"   International: {result.formatted_international}")
                if result.country_name:
                    lines.append(f"   Country: {result.country_name}")
                if result.carrier:
                    lines.append(f"   Carrier: {result.carrier}")
                if result.error_message:
                    lines.append(f"   Error: {result.error_message}")
                lines.append("")
        
        content = "\n".join(lines)
        return content, filename, 'text/plain'
    
    def _create_results_excel(self, results: list, validation_type: str = 'email', created_at=None) -> tuple:
        """Create Excel format results"""
        timestamp = created_at.strftime('%Y%m%d_%H%M%S') if created_at else 'unknown'
        filename = f"{validation_type}_validation_results_{timestamp}.xlsx"
        
        try:
            import pandas as pd
            from io import BytesIO
            
            # Prepare data for DataFrame
            data = []
            
            if validation_type == 'email':
                for result in results:
                    data.append({
                        'Email': result.email or '',
                        'Valid': 'Yes' if result.is_valid else 'No',
                        'Syntax Valid': 'Yes' if result.syntax_valid else 'No',
                        'Domain Exists': 'Yes' if result.domain_exists else 'No',
                        'MX Record': 'Yes' if result.mx_record_exists else 'No',
                        'SMTP Connected': 'Yes' if result.smtp_connectable else 'No',
                        'Error Message': result.error_message or '',
                        'MX Records': result.mx_records or ''
                    })
            else:  # phone
                for result in results:
                    data.append({
                        'Phone Number': result.phone_number or '',
                        'Valid': 'Yes' if result.is_valid else 'No',
                        'International Format': result.formatted_international or '',
                        'National Format': result.formatted_national or '',
                        'Country Code': result.country_code or '',
                        'Country': result.country_name or '',
                        'Carrier': result.carrier or '',
                        'Number Type': result.number_type or '',
                        'Timezone': result.timezone or '',
                        'Error Message': result.error_message or ''
                    })
            
            # Create DataFrame and Excel file
            df = pd.DataFrame(data)
            excel_buffer = BytesIO()
            
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=f'{validation_type.title()} Results', index=False)
                
                # Get the workbook and worksheet
                workbook = writer.book
                worksheet = writer.sheets[f'{validation_type.title()} Results']
                
                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            excel_buffer.seek(0)
            return excel_buffer.getvalue(), filename, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            
        except ImportError:
            # Fallback to CSV if pandas/openpyxl not available
            return self._create_results_csv_formatted(results, validation_type, created_at)
        except Exception as e:
            logger.error(f"Error creating Excel file: {e}")
            # Fallback to CSV on error
            return self._create_results_csv_formatted(results, validation_type, created_at)
    
    def _create_results_pdf(self, results: list, validation_type: str = 'email', created_at=None) -> tuple:
        """Create PDF format results"""
        timestamp = created_at.strftime('%Y%m%d_%H%M%S') if created_at else 'unknown'
        filename = f"{validation_type}_validation_results_{timestamp}.pdf"
        
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib import colors
            from io import BytesIO
            
            # Create PDF buffer
            pdf_buffer = BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=30,
                alignment=1  # Center
            )
            story.append(Paragraph(f"{validation_type.upper()} VALIDATION REPORT", title_style))
            
            # Summary info
            summary_style = styles['Normal']
            story.append(Paragraph(f"<b>Generated:</b> {created_at.strftime('%Y-%m-%d %H:%M:%S') if created_at else 'Unknown'}", summary_style))
            story.append(Paragraph(f"<b>Total Records:</b> {len(results)}", summary_style))
            
            valid_count = sum(1 for r in results if r.is_valid)
            invalid_count = len(results) - valid_count
            story.append(Paragraph(f"<b>Valid {validation_type.title()}s:</b> {valid_count}", summary_style))
            story.append(Paragraph(f"<b>Invalid {validation_type.title()}s:</b> {invalid_count}", summary_style))
            story.append(Paragraph(f"<b>Success Rate:</b> {(valid_count/len(results)*100):.1f}%", summary_style))
            story.append(Spacer(1, 20))
            
            # Results table
            if validation_type == 'email':
                # Email table headers
                table_data = [['Email', 'Status', 'Syntax', 'Domain', 'MX', 'SMTP', 'Error']]
                
                for result in results:
                    table_data.append([
                        result.email or 'N/A',
                        'VALID' if result.is_valid else 'INVALID',
                        'Yes' if result.syntax_valid else 'No',
                        'Yes' if result.domain_exists else 'No',
                        'Yes' if result.mx_record_exists else 'No',
                        'Yes' if result.smtp_connectable else 'No',
                        (result.error_message or '')[:30] + ('...' if result.error_message and len(result.error_message) > 30 else '')
                    ])
            else:  # phone
                # Phone table headers
                table_data = [['Phone Number', 'Status', 'International', 'Country', 'Carrier', 'Error']]
                
                for result in results:
                    table_data.append([
                        result.phone_number or 'N/A',
                        'VALID' if result.is_valid else 'INVALID',
                        result.formatted_international or 'N/A',
                        result.country_name or 'N/A',
                        result.carrier or 'N/A',
                        (result.error_message or '')[:30] + ('...' if result.error_message and len(result.error_message) > 30 else '')
                    ])
            
            # Create table with styling
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(table)
            
            # Build PDF
            doc.build(story)
            pdf_buffer.seek(0)
            
            return pdf_buffer.getvalue(), filename, 'application/pdf'
            
        except ImportError:
            # Fallback to TXT if reportlab not available
            return self._create_results_txt(results, validation_type, created_at)
        except Exception as e:
            logger.error(f"Error creating PDF file: {e}")
            # Fallback to TXT on error
            return self._create_results_txt(results, validation_type, created_at)
    
    def _create_results_csv(self, results: list, validation_type: str = 'email') -> str:
        """Create CSV content from validation results"""
        from io import StringIO
        import csv
        
        output = StringIO()
        
        if validation_type == 'email':
            fieldnames = [
                'email', 'is_valid', 'syntax_valid', 'domain_exists', 
                'mx_record_exists', 'smtp_connectable', 'error_message', 'mx_records'
            ]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results:
                writer.writerow({
                    'email': result.email or '',
                    'is_valid': 'Yes' if result.is_valid else 'No',
                    'syntax_valid': 'Yes' if result.syntax_valid else 'No',
                    'domain_exists': 'Yes' if result.domain_exists else 'No',
                    'mx_record_exists': 'Yes' if result.mx_record_exists else 'No',
                    'smtp_connectable': 'Yes' if result.smtp_connectable else 'No',
                    'error_message': result.error_message or '',
                    'mx_records': result.mx_records or ''
                })
        else:  # phone
            fieldnames = [
                'phone_number', 'is_valid', 'formatted_international', 'formatted_national',
                'country_code', 'country_name', 'carrier', 'number_type', 'timezone', 'error_message'
            ]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results:
                writer.writerow({
                    'phone_number': result.phone_number or '',
                    'is_valid': 'Yes' if result.is_valid else 'No',
                    'formatted_international': result.formatted_international or '',
                    'formatted_national': result.formatted_national or '',
                    'country_code': result.country_code or '',
                    'country_name': result.country_name or '',
                    'carrier': result.carrier or '',
                    'number_type': result.number_type or '',
                    'timezone': result.timezone or '',
                    'error_message': result.error_message or ''
                })
        
        return output.getvalue()
    
    async def show_job_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, db: Session, page: int = 0):
        """Show user's validation job history with pagination"""
        try:
            # Get jobs for this user, paginated
            jobs_per_page = 5
            offset = page * jobs_per_page
            
            jobs = db.query(ValidationJob).filter(
                ValidationJob.user_id == user.id
            ).order_by(ValidationJob.created_at.desc()).offset(offset).limit(jobs_per_page).all()
            
            # Get total count for pagination
            total_jobs = db.query(ValidationJob).filter(ValidationJob.user_id == user.id).count()
            total_pages = (total_jobs + jobs_per_page - 1) // jobs_per_page
            
            if not jobs:
                await update.callback_query.edit_message_text(
                    "📋 **Job History**\n\nNo validation jobs found.\n\nStart your first validation to see history here!",
                    reply_markup=self.keyboards.main_menu(),
                    parse_mode='Markdown'
                )
                return
            
            # Build history message
            history_text = f"📋 **Job History** (Page {page + 1} of {max(1, total_pages)})\n\n"
            
            for job in jobs:
                # Get job statistics
                results = db.query(ValidationResult).filter(ValidationResult.job_id == job.id).all()
                valid_count = sum(1 for r in results if r.is_valid)
                total_count = len(results)
                
                # Status emoji
                status_emoji = {
                    'completed': '✅',
                    'processing': '🔄', 
                    'failed': '❌',
                    'pending': '⏳'
                }.get(job.status, '❓')
                
                # Validation type
                val_type = (job.validation_type or 'email').title()
                
                # Format date
                date_str = job.created_at.strftime('%m/%d %H:%M') if job.created_at else 'Unknown'
                
                # Add job info
                history_text += f"{status_emoji} **Job #{job.id}** - {val_type}\n"
                history_text += f"📁 {job.filename or 'Manual Input'}\n"
                history_text += f"📊 {valid_count}/{total_count} valid ({(valid_count/total_count*100):.0f}%)\n" if total_count > 0 else f"📊 {total_count} items\n"
                history_text += f"📅 {date_str}\n\n"
            
            # Create inline keyboard with job buttons
            keyboard = []
            for job in jobs:
                status_emoji = {
                    'completed': '✅',
                    'processing': '🔄', 
                    'failed': '❌',
                    'pending': '⏳'
                }.get(job.status, '❓')
                
                keyboard.append([
                    InlineKeyboardButton(
                        f"{status_emoji} Job #{job.id} - View Details",
                        callback_data=f"details_{job.id}"
                    )
                ])
            
            # Add navigation
            nav_row = []
            if page > 0:
                nav_row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"history_page_{page-1}"))
            if page < total_pages - 1:
                nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"history_page_{page+1}"))
            
            if nav_row:
                keyboard.append(nav_row)
            
            keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
            
            await update.callback_query.edit_message_text(
                history_text.strip(),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error showing job history: {e}")
            await update.callback_query.edit_message_text(
                "❌ Error loading job history. Please try again.",
                reply_markup=self.keyboards.main_menu()
            )
    
    async def show_recent_jobs(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, db: Session):
        """Show recent validation jobs for the user"""
        try:
            # Get 5 most recent jobs
            jobs = db.query(ValidationJob).filter(
                ValidationJob.user_id == user.id
            ).order_by(ValidationJob.created_at.desc()).limit(5).all()
            
            if not jobs:
                await update.callback_query.edit_message_text(
                    "📋 **Recent Jobs**\n\nNo validation jobs found.\n\nStart your first validation to see jobs here!",
                    reply_markup=self.keyboards.main_menu(),
                    parse_mode='Markdown'
                )
                return
            
            # Build jobs message
            jobs_text = "📋 **Recent Validation Jobs**\n\n"
            
            for job in jobs:
                # Get job statistics
                results = db.query(ValidationResult).filter(ValidationResult.job_id == job.id).all()
                valid_count = sum(1 for r in results if r.is_valid)
                total_count = len(results)
                
                # Status emoji
                status_emoji = {
                    'completed': '✅',
                    'processing': '🔄', 
                    'failed': '❌',
                    'pending': '⏳'
                }.get(job.status, '❓')
                
                # Validation type
                val_type = (job.validation_type or 'email').title()
                
                # Format date
                date_str = job.created_at.strftime('%m/%d %H:%M') if job.created_at else 'Unknown'
                
                # Add job info
                jobs_text += f"{status_emoji} **Job #{job.id}** - {val_type}\n"
                jobs_text += f"📁 {job.filename or 'Manual Input'}\n"
                if total_count > 0:
                    success_rate = (valid_count/total_count*100) if total_count > 0 else 0
                    jobs_text += f"📊 {valid_count}/{total_count} valid ({success_rate:.0f}%)\n"
                else:
                    jobs_text += f"📊 {total_count} items\n"
                jobs_text += f"📅 {date_str}\n\n"
            
            # Create inline keyboard with job buttons
            keyboard = []
            for job in jobs:
                status_emoji = {
                    'completed': '✅',
                    'processing': '🔄', 
                    'failed': '❌',
                    'pending': '⏳'
                }.get(job.status, '❓')
                
                keyboard.append([
                    InlineKeyboardButton(
                        f"{status_emoji} Job #{job.id} - Details",
                        callback_data=f"details_{job.id}"
                    )
                ])
            
            # Add navigation buttons
            keyboard.extend([
                [InlineKeyboardButton("📊 View All History", callback_data="job_history")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ])
            
            await update.callback_query.edit_message_text(
                jobs_text.strip(),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error showing recent jobs: {e}")
            await update.callback_query.edit_message_text(
                "❌ Error loading recent jobs. Please try again.",
                reply_markup=self.keyboards.main_menu()
            )
