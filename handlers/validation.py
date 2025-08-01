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
from telegram import Update
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
        data = query.data
        telegram_user = update.effective_user
        
        with SessionLocal() as db:
            user = db.query(User).filter(User.telegram_id == str(telegram_user.id)).first()
            
            if data == 'validate_emails':
                await self.show_validation_menu(update, context, user, 'email')
            
            elif data == 'validate_phones':
                await self.show_validation_menu(update, context, user, 'phone')
            
            elif data == 'upload_file':
                await self.show_file_upload_options(update, context, 'email')
                
            elif data.startswith('upload_file_'):
                validation_type = data.split('_')[-1]
                await self.show_file_upload_options(update, context, validation_type)
            
            elif data == 'enter_emails':
                await self.start_email_input(update, context)
                
            elif data == 'enter_phones':
                await self.start_phone_input(update, context)
            
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
            
            elif data == 'start_validation':
                await self.start_validation_from_input(update, context)
                
            elif data == 'start_phone_validation':
                await self.start_phone_validation_from_input(update, context)
    
    async def show_validation_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, validation_type: str = 'email'):
        """Show validation options for email or phone"""
        with SessionLocal() as db:
            user = db.query(User).filter(User.telegram_id == str(user.telegram_id)).first()
            
            # Check user's validation capacity
            if user.has_active_subscription():
                capacity_info = "✅ **Unlimited validations**"
            else:
                from config import TRIAL_EMAIL_LIMIT
                remaining = TRIAL_EMAIL_LIMIT - user.trial_emails_used
                capacity_info = f"🆓 **Trial:** {remaining} validations remaining"
            
            if validation_type == 'email':
                title = "📧 **Email Validation**"
                item_name = "emails"
                format_info = """**Supported formats:**
• CSV with email column
• Excel files (.xlsx, .xls)
• Text files (one email per line)
• Max file size: {MAX_FILE_SIZE_MB}MB"""
            else:
                title = "📱 **Phone Number Validation**"
                item_name = "phone numbers"
                format_info = """**Supported formats:**
• CSV with phone column
• Excel files (.xlsx, .xls)
• Text files (one number per line)
• International format supported (+1234567890)
• Max file size: {MAX_FILE_SIZE_MB}MB"""
            
            menu_text = f"""
{title}

{capacity_info}

**How would you like to validate {item_name}?**

📁 **Upload File** - CSV, Excel, or TXT files
✍️ **Enter {item_name.title()}** - Type or paste {item_name}
📊 **Recent Jobs** - View your validation history

{format_info}
            """
            
            query = update.callback_query
            await query.edit_message_text(
                menu_text,
                reply_markup=self.keyboards.validation_menu(validation_type),
                parse_mode='Markdown'
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
            
        upload_text = f"""
📁 **File Upload**

Choose your file format for {item_name}:

**📄 CSV File**
{column_info}
• UTF-8 encoding recommended

**📊 Excel File**
• .xlsx or .xls formats supported
{column_info}

**📝 Text File**
{line_format}
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
            
            # Check credits
            if not user.has_active_subscription():
                from config import TRIAL_EMAIL_LIMIT
                remaining = TRIAL_EMAIL_LIMIT - user.trial_emails_used
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
            reply_markup=self.keyboards.phone_input_menu(),
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
                "❌ No valid phone numbers found. Please enter valid phone numbers or click 'Start Validation' when done.",
                reply_markup=self.keyboards.phone_input_menu()
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
            reply_markup=self.keyboards.phone_input_menu()
        )
    
    async def start_phone_validation_from_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start validation from manually entered phone numbers"""
        phones = context.user_data.get('collected_phones', [])
        
        if not phones:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    "❌ No phone numbers entered. Please enter some numbers first.",
                    reply_markup=self.keyboards.phone_input_menu()
                )
            else:
                await update.message.reply_text(
                    "❌ No phone numbers entered. Please enter some numbers first.",
                    reply_markup=self.keyboards.phone_input_menu()
                )
            return
        
        # Clear input state
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
            
            # Check credits
            if not user.has_active_subscription():
                from config import TRIAL_EMAIL_LIMIT
                remaining = TRIAL_EMAIL_LIMIT - user.trial_emails_used
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
                        carrier_name=result.carrier_name,
                        number_type=result.number_type,
                        timezones=json.dumps(result.timezones) if result.timezones else None,
                        error_message=result.error_message,
                        validation_time=0.1  # Phone validation is fast
                    )
                    db.add(validation_result)
                    
                    if result.is_valid:
                        valid_count += 1
                
                validated_count += len(batch_results)
                
                # Update progress
                progress = int((validated_count / len(phone_numbers)) * 100)
                elapsed = time.time() - start_time
                rate = validated_count / elapsed if elapsed > 0 else 0
                eta = (len(phone_numbers) - validated_count) / rate if rate > 0 else 0
                
                await message.edit_text(
                    f"📱 Validating phone numbers...\n\n"
                    f"Progress: {validated_count}/{len(phone_numbers)} ({progress}%)\n"
                    f"{create_progress_bar(progress)}\n\n"
                    f"⚡ Speed: {rate:.1f} numbers/second\n"
                    f"⏱️ ETA: {format_duration(eta)}"
                )
                
                # Commit batch results
                db.commit()
            
            # Update job completion
            job.status = "completed"
            job.completed_at = datetime.now()
            job.validated_items = len(phone_numbers)
            job.valid_items = valid_count
            job.invalid_items = len(phone_numbers) - valid_count
            db.commit()
            
            # Update user usage
            if not user.has_active_subscription():
                user.trial_emails_used += len(phone_numbers)
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
                           'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']
            
            if document.mime_type not in allowed_types:
                await update.message.reply_text(
                    "❌ Unsupported file type. Please upload CSV, Excel, or TXT files only.",
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
                
                # Check if user has enough credits
                if not user.has_active_subscription():
                    from config import TRIAL_EMAIL_LIMIT
                    remaining = TRIAL_EMAIL_LIMIT - user.trial_emails_used
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
                total_emails=len(emails),
                filename=filename or "Manual Input",
                status="processing"
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            
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
                
                # Update progress every batch 
                progress = (validated_count / len(emails)) * 100
                progress_bar = create_progress_bar(progress)
                
                # Update UI every batch for better feedback
                try:
                    elapsed = time.time() - start_time
                    speed = validated_count / elapsed if elapsed > 0 else 0
                    eta = (len(emails) - validated_count) / speed if speed > 0 else 0
                    
                    await message.edit_text(
                        f"🔄 Validating emails...\n"
                        f"Progress: {validated_count}/{len(emails)} ({progress:.1f}%)\n"
                        f"{progress_bar}\n"
                        f"Speed: {speed:.1f} emails/sec\n"
                        f"ETA: {int(eta)}s" if eta < 300 else f"ETA: {int(eta/60)}m",
                        reply_markup=None
                    )
                except Exception as update_error:
                    logger.debug(f"Progress update failed: {update_error}")  # Ignore rate limits
                
                # Small delay between batches for stability
                await asyncio.sleep(0.05)
            
            # Update job status
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            
            # Update user usage
            if not user.has_active_subscription():
                user.trial_emails_used += len(emails)
            
            db.commit()
            
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
        """Download validation results as CSV file"""
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
            
            # Sort results: valid emails first, then invalid
            valid_results = [r for r in results if r.is_valid]
            invalid_results = [r for r in results if not r.is_valid]
            sorted_results = valid_results + invalid_results
            
            # Create CSV content
            import io
            import csv
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(['Email', 'Status', 'Valid', 'Reason', 'Domain', 'MX Records', 'SMTP Check'])
            
            # Add section marker for valid emails
            if valid_results:
                writer.writerow(['=== VALID EMAILS ===', '', '', '', '', '', ''])
                for result in valid_results:
                    writer.writerow([
                        result.email,
                        'Valid',
                        'Yes',
                        'Valid email - all checks passed',
                        result.domain or '',
                        json.loads(result.mx_records)[0] if result.mx_records else '',
                        'Yes'
                    ])
            
            # Add section marker for invalid emails
            if invalid_results:
                writer.writerow(['', '', '', '', '', '', ''])  # Empty row
                writer.writerow(['=== INVALID EMAILS ===', '', '', '', '', '', ''])
                for result in invalid_results:
                    writer.writerow([
                        result.email,
                        'Invalid',
                        'No',
                        result.error_message or 'Failed validation',
                        result.domain or '',
                        json.loads(result.mx_records)[0] if result.mx_records else '',
                        'Yes' if result.smtp_connectable else 'No'
                    ])
            
            # Convert to bytes
            csv_content = output.getvalue().encode('utf-8')
            output.close()
            
            # Send file
            filename = f"validation_results_{job_id}.csv"
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=io.BytesIO(csv_content),
                filename=filename,
                caption=f"📊 Validation results for job #{job_id}\n\n"
                       f"Total emails: {len(results)}\n"
                       f"Valid: {sum(1 for r in results if r.is_valid)}\n"
                       f"Invalid: {sum(1 for r in results if not r.is_valid)}"
            )
            
        except Exception as e:
            logger.error(f"Error downloading results: {e}")
            await update.callback_query.edit_message_text(
                "❌ Error generating download file.",
                reply_markup=self.keyboards.main_menu()
            )
    
    async def show_recent_jobs(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, db: Session):
        """Show user's recent validation jobs"""
        try:
            # Get recent jobs (last 10)
            jobs = db.query(ValidationJob).filter(
                ValidationJob.user_id == user.id
            ).order_by(ValidationJob.created_at.desc()).limit(10).all()
            
            if not jobs:
                await update.callback_query.edit_message_text(
                    "📋 **Recent Jobs**\n\nNo validation jobs found.\n\nUpload an email list to get started!",
                    reply_markup=self.keyboards.main_menu(),
                    parse_mode='Markdown'
                )
                return
            
            # Format jobs list
            jobs_text = "📋 **Recent Validation Jobs**\n\n"
            
            for job in jobs:
                status_emoji = "✅" if job.status == "completed" else "⏳" if job.status == "processing" else "❌"
                
                # Get result count
                result_count = db.query(ValidationResult).filter(ValidationResult.job_id == job.id).count()
                valid_count = db.query(ValidationResult).filter(
                    ValidationResult.job_id == job.id,
                    ValidationResult.is_valid == True
                ).count()
                
                jobs_text += f"""
{status_emoji} **Job #{job.id}**
📁 {job.filename or 'Manual input'}
📅 {job.created_at.strftime('%Y-%m-%d %H:%M')}
📊 {valid_count}/{result_count} valid emails
⚡ {job.status.title()}

"""
            
            await update.callback_query.edit_message_text(
                jobs_text,
                reply_markup=self.keyboards.recent_jobs_menu(jobs),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error showing recent jobs: {e}")
            await update.callback_query.edit_message_text(
                "❌ Error loading recent jobs.",
                reply_markup=self.keyboards.main_menu()
            )
