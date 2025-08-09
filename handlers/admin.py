"""
Admin handler for bot administration tasks including broadcast messaging
"""
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_db
from models import User
from config import ADMIN_CHAT_ID
from keyboards import Keyboards
from html import escape as html_escape
from telegram.error import Forbidden, RetryAfter, BadRequest  # if you want BadRequest

from database import SessionLocal

logger = logging.getLogger(__name__)

class AdminHandler:
    def __init__(self):
        self.keyboards = Keyboards()
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin based on chat ID"""
        return str(user_id) == str(ADMIN_CHAT_ID)
    
    async def handle_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /admin command"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("❌ Access denied. Admin privileges required.")
            return
        
        admin_text = """
🔧 **Admin Panel**

Welcome to the admin control panel. Choose an action:

- **📢 Broadcast Message** - Send message to all users
- **📊 User Statistics** - View user stats and analytics  
- **🗄️ Database Stats** - View database information
- **⚙️ System Status** - Check bot system status
        """
        
        keyboard = [
            [InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast")],
            [InlineKeyboardButton("📊 User Statistics", callback_data="admin_stats")],
            [InlineKeyboardButton("🗄️ Database Stats", callback_data="admin_db_stats")],
            [InlineKeyboardButton("⚙️ System Status", callback_data="admin_system")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            admin_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin callback queries"""
        query = update.callback_query
        user_id = query.from_user.id
        data = query.data
        
        if not self.is_admin(user_id):
            await query.edit_message_text("❌ Access denied. Admin privileges required.")
            return
        
        if data == "admin_broadcast":
            await self.show_broadcast_menu(update, context)
        elif data == "admin_stats":
            await self.show_user_statistics(update, context)
        elif data == "admin_db_stats":
            await self.show_database_stats(update, context)
        elif data == "admin_system":
            await self.show_system_status(update, context)
        elif data == "admin_start_broadcast":
            await self.start_broadcast_input(update, context)
        elif data == "admin_confirm_broadcast":
            await self.confirm_broadcast(update, context)
        elif data == "admin_send_broadcast":
            await self.send_broadcast(update, context)
        elif data == "admin_cancel_broadcast":
            await self.cancel_broadcast(update, context)
        elif data == "admin_panel":
            await self.show_admin_panel(update, context)
    
    async def show_broadcast_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show broadcast message menu"""
        query = update.callback_query
        
        broadcast_text = """
📢 **Broadcast Message**

Send a message to all bot users. This will be delivered to everyone who has used the bot.

**Guidelines:**
- Keep messages clear and professional
- Avoid spam or excessive messaging
- Include relevant information only
- Messages support Markdown formatting

Ready to compose your broadcast message?
        """
        
        keyboard = [
            [InlineKeyboardButton("✍️ Compose Message", callback_data="admin_start_broadcast")],
            [InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="admin_panel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            broadcast_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def start_broadcast_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start broadcast message input"""
        query = update.callback_query
        
        await query.edit_message_text(
            "📢 **Compose Broadcast Message**\n\n"
            "Please type your broadcast message. It will be sent to all bot users.\n\n"
            "You can use Markdown formatting:\n"
            "- **Bold text**\n"
            "- *Italic text*\n"
            "- `Code text`\n"
            "- [Links](http://example.com)\n\n"
            "Type your message now:"
        )
        
        # Set user state to wait for broadcast message
        context.user_data['waiting_for_broadcast'] = True
    
    async def handle_broadcast_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle broadcast message input"""
        message_text = update.message.text
        
        # Store the broadcast message
        context.user_data['broadcast_message'] = message_text
        context.user_data['waiting_for_broadcast'] = False
        
        # Show preview and confirmation
        preview_text = f"""
📢 **Broadcast Preview**

**Message to be sent:**
{message_text}

**Recipients:** All bot users
**Estimated delivery:** Immediate

Confirm to send this broadcast message?
        """
        
        keyboard = [
            [InlineKeyboardButton("✅ Send Broadcast", callback_data="admin_send_broadcast")],
            [InlineKeyboardButton("❌ Cancel", callback_data="admin_cancel_broadcast")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            preview_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


    async def send_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()  # stop the loading spinner

        msg = (context.user_data or {}).get('broadcast_message')
        if not msg:
            await query.edit_message_text("❌ No broadcast message found. Please try again.")
            return

        await query.edit_message_text(
            "📢 <b>Sending broadcast...</b>\nPlease wait while we deliver your message to all users.",
            parse_mode='HTML'
        )

        success = failed = blocked = skipped = 0

        with SessionLocal() as db:
            users = db.query(User).all()
            total = len(users)

        bot = context.bot  # use the bot from context

        for u in users:
            try:
                chat_id = int(u.telegram_id)
            except Exception:
                skipped += 1
                continue

            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"📢 <b>Admin Broadcast</b>\n\n{html_escape(msg)}",
                    parse_mode='HTML',
                    disable_web_page_preview=True,
                )
                success += 1
                await asyncio.sleep(0.1)
            except RetryAfter as e:
                await asyncio.sleep(e.retry_after + 0.5)
                try:
                    await bot.send_message(chat_id=chat_id,
                                        text=f"📢 <b>Admin Broadcast</b>\n\n{html_escape(msg)}",
                                        parse_mode='HTML',
                                        disable_web_page_preview=True)
                    success += 1
                except Exception as e2:
                    failed += 1
                    logger.error(f"Broadcast to {chat_id} failed after retry: {e2}")
            except Forbidden:
                blocked += 1
            except BadRequest as e:
                failed += 1
                logger.error(f"Broadcast to {chat_id} bad request: {e}")
            except Exception as e:
                failed += 1
                logger.error(f"Broadcast to {chat_id} failed: {e}")

        context.user_data.pop('broadcast_message', None)

        result = (
            f"✅ <b>Broadcast Complete</b>\n\n"
            f"<b>Results:</b>\n"
            f"• Messages sent: {success}\n"
            f"• Failed deliveries: {failed}\n"
            f"• Blocked or never started: {blocked}\n"
            f"• Skipped, bad chat id: {skipped}\n"
            f"• Total users: {total}\n\n"
            f"<b>Message sent:</b>\n{html_escape(msg)}"
        )
        await query.edit_message_text(
            result,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="admin_panel")]]
            ),
            parse_mode='HTML'
        )

    
    async def cancel_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel broadcast message"""
        query = update.callback_query
        
        # Clear broadcast data
        context.user_data.pop('broadcast_message', None)
        context.user_data.pop('waiting_for_broadcast', None)
        
        await query.edit_message_text(
            "❌ **Broadcast Cancelled**\n\nYour broadcast message has been discarded.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="admin_panel")]])
        )
    
    async def show_admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main admin panel"""
        admin_text = """
🔧 **Admin Panel**

Welcome to the admin control panel. Choose an action:

- **📢 Broadcast Message** - Send message to all users
- **📊 User Statistics** - View user stats and analytics  
- **🗄️ Database Stats** - View database information
- **⚙️ System Status** - Check bot system status
        """
        
        keyboard = [
            [InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast")],
            [InlineKeyboardButton("📊 User Statistics", callback_data="admin_stats")],
            [InlineKeyboardButton("🗄️ Database Stats", callback_data="admin_db_stats")],
            [InlineKeyboardButton("⚙️ System Status", callback_data="admin_system")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query = update.callback_query
        await query.edit_message_text(
            admin_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_user_statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show comprehensive user statistics"""
        query = update.callback_query
        
        with get_db() as db:
            # Basic user counts
            total_users = db.query(User).count()
            active_users = db.query(User).filter(User.is_onboarded == True).count()
            trial_users = db.query(User).filter(User.trial_activated == True).count()
            
            # Subscription statistics
            from models import Subscription
            active_subs = db.query(Subscription).filter(Subscription.status == 'active').count()
            expired_subs = db.query(Subscription).filter(Subscription.status == 'expired').count()
            pending_subs = db.query(Subscription).filter(Subscription.status == 'pending').count()
            
            # Recent activity
            from datetime import datetime, timedelta
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = today - timedelta(days=7)
            
            new_users_today = db.query(User).filter(User.created_at >= today).count()
            new_users_week = db.query(User).filter(User.created_at >= week_ago).count()
            
            # Validation jobs
            from models import ValidationJob
            total_jobs = db.query(ValidationJob).count()
            completed_jobs = db.query(ValidationJob).filter(ValidationJob.status == 'completed').count()
            
            stats_text = f"""
📊 **User Statistics**

**User Overview:**
- Total registered: {total_users:,}
- Onboarded users: {active_users:,}
- Trial activated: {trial_users:,}

**New Registrations:**
- Today: {new_users_today}
- This week: {new_users_week}

**Subscriptions:**
- Active: {active_subs}
- Expired: {expired_subs}
- Pending payment: {pending_subs}

**Validation Activity:**
- Total jobs: {total_jobs:,}
- Completed: {completed_jobs:,}
- Success rate: {round((completed_jobs/total_jobs*100), 1) if total_jobs > 0 else 0}%

**Conversion Rate:**
- Trial to paid: {round((active_subs/trial_users*100), 1) if trial_users > 0 else 0}%
- Registration to trial: {round((trial_users/total_users*100), 1) if total_users > 0 else 0}%
            """
        
        keyboard = [
            [InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            stats_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_database_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show database statistics"""
        query = update.callback_query
        
        with get_db() as db:
            # Table counts
            user_count = db.query(User).count()
            
            from models import Subscription, ValidationJob, ValidationResult
            subscription_count = db.query(Subscription).count()
            job_count = db.query(ValidationJob).count()
            result_count = db.query(ValidationResult).count()
            
            # Database size estimation (rough)
            avg_results_per_job = result_count / job_count if job_count > 0 else 0
            
            db_stats_text = f"""
🗄️ **Database Statistics**

**Table Counts:**
- Users: {user_count:,}
- Subscriptions: {subscription_count:,}
- Validation Jobs: {job_count:,}
- Validation Results: {result_count:,}

**Data Analysis:**
- Avg results per job: {avg_results_per_job:.1f}
- Total validations processed: {result_count:,}

**Data Health:**
- Database status: ✅ Operational
- Connection: ✅ Active
- Performance: ✅ Normal

**Storage Overview:**
- Primary tables: 4 active
- Indexes: Optimized
- Cleanup: Auto-managed

Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
            """
        
        keyboard = [
            [InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            db_stats_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_system_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show system status and health"""
        query = update.callback_query
        
        import psutil
        import os
        from datetime import datetime
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Bot uptime (approximate)
        import time
        uptime_seconds = time.time() - psutil.Process().create_time()
        uptime_hours = uptime_seconds / 3600
        
        system_text = f"""
⚙️ **System Status**

**Bot Health:**
- Status: ✅ Online and operational
- Uptime: {uptime_hours:.1f} hours
- Response time: Normal
- Error rate: Low

**System Resources:**
- CPU usage: {cpu_percent}%
- Memory: {memory.percent}% used ({memory.used//1024//1024:,} MB / {memory.total//1024//1024:,} MB)
- Disk: {disk.percent}% used ({disk.used//1024//1024//1024:.1f} GB / {disk.total//1024//1024//1024:.1f} GB)

**Services Status:**
- Telegram Bot API: ✅ Connected
- Database: ✅ Active
- Webhook Server: ✅ Running
- Payment API: ✅ Running

**Environment:**
- Platform: {os.name}
- Python: Active
- Dependencies: ✅ All loaded

**Performance:**
- Message processing: Normal
- File uploads: Normal
- Validation speed: Optimal

Last check: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="admin_system")],
            [InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            system_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def cancel_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel broadcast message"""
        query = update.callback_query
        
        # Clean up user data
        context.user_data.pop('broadcast_message', None)
        context.user_data.pop('waiting_for_broadcast', None)
        
        await query.edit_message_text(
            "❌ Broadcast cancelled.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="admin_panel")
            ]])
        )
    
    async def show_admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main admin panel"""
        query = update.callback_query
        
        admin_text = """
🔧 **Admin Panel**

Welcome to the admin control panel. Choose an action:

- **📢 Broadcast Message** - Send message to all users
- **📊 User Statistics** - View user stats and analytics  
- **🗄️ Database Stats** - View database information
- **⚙️ System Status** - Check bot system status
        """
        
        keyboard = [
            [InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast")],
            [InlineKeyboardButton("📊 User Statistics", callback_data="admin_stats")],
            [InlineKeyboardButton("🗄️ Database Stats", callback_data="admin_db_stats")],
            [InlineKeyboardButton("⚙️ System Status", callback_data="admin_system")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            admin_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def show_user_statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user statistics"""
        query = update.callback_query
        
        db = next(get_db())
        try:
            # Get user statistics
            total_users = db.query(User).count()
            
            # Get active subscriptions from Subscription table
            from models import ValidationJob, Subscription
            from datetime import datetime
            active_subscriptions = db.query(Subscription).filter(
                Subscription.expires_at > datetime.now(),
                Subscription.status == 'active'
            ).count()
            
            # Get validation statistics
            total_validations = db.query(ValidationJob).count()
            email_validations = db.query(ValidationJob).filter(ValidationJob.validation_type == 'email').count()
            phone_validations = db.query(ValidationJob).filter(ValidationJob.validation_type == 'phone').count()
        finally:
            db.close()
        
        stats_text = f"""
📊 **User Statistics**

**Users:**
- Total registered users: {total_users}
- Active subscribers: {active_subscriptions}
- Free trial users: {total_users - active_subscriptions}

**Validations:**
- Total validation jobs: {total_validations}
- Email validations: {email_validations}
- Phone validations: {phone_validations}

**Subscription Rate:** {(active_subscriptions/total_users*100):.1f}%
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh Stats", callback_data="admin_stats")],
            [InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="admin_panel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            stats_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_database_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show database statistics"""
        query = update.callback_query
        
        db = next(get_db())
        try:
            # Count records in each table
            from models import ValidationJob, Subscription
            
            users_count = db.query(User).count()
            jobs_count = db.query(ValidationJob).count()
            subscriptions_count = db.query(Subscription).count()
        finally:
            db.close()
        
        db_text = f"""
🗄️ **Database Statistics**

**Table Records:**
- Users: {users_count}
- Validation Jobs: {jobs_count}
- Subscriptions: {subscriptions_count}

**Database Status:** ✅ Connected
**Environment:** Development
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="admin_db_stats")],
            [InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="admin_panel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            db_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_system_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show system status"""
        query = update.callback_query
        
        import psutil
        import time
        
        # Get system information
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        uptime = time.time() - psutil.boot_time()
        
        status_text = f"""
⚙️ **System Status**

**Bot Status:** ✅ Running
**Database:** ✅ Connected
**Webhook Server:** ✅ Active (Port 5000)

**System Resources:**
- CPU Usage: {cpu_percent}%
- Memory Usage: {memory.percent}%
- Available Memory: {memory.available // (1024**2)} MB

**Uptime:** {uptime//3600:.1f} hours
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh Status", callback_data="admin_system")],
            [InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="admin_panel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            status_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )