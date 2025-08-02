"""
Admin handler for bot administration tasks including broadcast messaging
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_db
from models import User
from config import ADMIN_CHAT_ID
from keyboards import Keyboards
from utils import escape_markdown

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

• **📢 Broadcast Message** - Send message to all users
• **📊 User Statistics** - View user stats and analytics  
• **🗄️ Database Stats** - View database information
• **⚙️ System Status** - Check bot system status
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
• Keep messages clear and professional
• Avoid spam or excessive messaging
• Include relevant information only
• Messages support Markdown formatting

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
            "• **Bold text**\n"
            "• *Italic text*\n"
            "• `Code text`\n"
            "• [Links](http://example.com)\n\n"
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
        """Send broadcast message to all users"""
        query = update.callback_query
        broadcast_message = context.user_data.get('broadcast_message')
        
        if not broadcast_message:
            await query.edit_message_text("❌ No broadcast message found. Please try again.")
            return
        
        # Update status message
        await query.edit_message_text("📤 Sending broadcast message to all users...")
        
        # Get all users from database
        db = next(get_db())
        try:
            users = db.query(User).all()
            total_users = len(users)
            sent_count = 0
            failed_count = 0
            
            for user in users:
                try:
                    await context.bot.send_message(
                        chat_id=int(user.telegram_id),
                        text=f"📢 **System Announcement**\n\n{broadcast_message}",
                        parse_mode='Markdown'
                    )
                    sent_count += 1
                except Exception as e:
                    logger.warning(f"Failed to send broadcast to user {user.telegram_id}: {e}")
                    failed_count += 1
        finally:
            db.close()
        
        # Send completion report
        report_text = f"""
✅ **Broadcast Complete**

**Results:**
• Total users: {total_users}
• Messages sent: {sent_count}
• Failed deliveries: {failed_count}
• Success rate: {(sent_count/total_users*100):.1f}%

**Message sent:**
{broadcast_message}
        """
        
        keyboard = [
            [InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="admin_panel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            report_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # Clean up user data
        context.user_data.pop('broadcast_message', None)
    
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

• **📢 Broadcast Message** - Send message to all users
• **📊 User Statistics** - View user stats and analytics  
• **🗄️ Database Stats** - View database information
• **⚙️ System Status** - Check bot system status
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
            active_subscriptions = db.query(User).filter(User.subscription_active == True).count()
            
            # Get validation statistics
            from models import ValidationJob
            total_validations = db.query(ValidationJob).count()
            email_validations = db.query(ValidationJob).filter(ValidationJob.validation_type == 'email').count()
            phone_validations = db.query(ValidationJob).filter(ValidationJob.validation_type == 'phone').count()
        finally:
            db.close()
        
        stats_text = f"""
📊 **User Statistics**

**Users:**
• Total registered users: {total_users}
• Active subscribers: {active_subscriptions}
• Free trial users: {total_users - active_subscriptions}

**Validations:**
• Total validation jobs: {total_validations}
• Email validations: {email_validations}
• Phone validations: {phone_validations}

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
• Users: {users_count}
• Validation Jobs: {jobs_count}
• Subscriptions: {subscriptions_count}

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
• CPU Usage: {cpu_percent}%
• Memory Usage: {memory.percent}%
• Available Memory: {memory.available // (1024**2)} MB

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