"""
Dashboard and analytics handler
"""
import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import SessionLocal
from models import User, ValidationJob, ValidationResult, UsageStats
from keyboards import Keyboards
from utils import format_duration, create_progress_bar

logger = logging.getLogger(__name__)

class DashboardHandler:
    def __init__(self):
        self.keyboards = Keyboards()
    
    async def show_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user dashboard"""
        telegram_user = update.effective_user
        
        with SessionLocal() as db:
            user = db.query(User).filter(User.telegram_id == str(telegram_user.id)).first()
            
            if not user:
                await update.message.reply_text("Please start the bot first with /start")
                return
            
            # Get user statistics
            stats = self.get_user_statistics(user, db)
            
            # Format dashboard
            dashboard_text = f"""
📊 **Your Dashboard**

👤 **Account Info:**
• Name: {user.full_name}
• Member since: {user.created_at.strftime('%B %Y')}
• Last active: {user.last_active.strftime('%Y-%m-%d')}

💎 **Subscription:**
{stats['subscription_info']}

📈 **Usage Statistics:**
• Total validations: {stats['total_validations']:,}
• Valid emails found: {stats['valid_emails']:,}
• Success rate: {stats['success_rate']}%
• Total jobs: {stats['total_jobs']}

🏆 **This Month:**
• Validations: {stats['month_validations']:,}
• Jobs completed: {stats['month_jobs']}
• Average accuracy: {stats['month_accuracy']}%

What would you like to explore?
            """
            
            if update.message:
                await update.message.reply_text(
                    dashboard_text,
                    reply_markup=self.keyboards.dashboard_menu(),
                    parse_mode='Markdown'
                )
            else:
                query = update.callback_query
                await query.edit_message_text(
                    dashboard_text,
                    reply_markup=self.keyboards.dashboard_menu(),
                    parse_mode='Markdown'
                )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle dashboard-related callbacks"""
        query = update.callback_query
        data = query.data
        telegram_user = update.effective_user
        
        with SessionLocal() as db:
            user = db.query(User).filter(User.telegram_id == str(telegram_user.id)).first()
            
            if data == 'dashboard':
                await self.show_dashboard(update, context)
            
            elif data == 'usage_stats':
                await self.show_usage_statistics(update, context, user, db)
            
            elif data == 'recent_activity':
                await self.show_recent_activity(update, context, user, db)
    
    def get_user_statistics(self, user: User, db: Session) -> dict:
        """Get comprehensive user statistics"""
        # Basic job statistics
        total_jobs = db.query(ValidationJob).filter(ValidationJob.user_id == user.id).count()
        completed_jobs = db.query(ValidationJob).filter(
            ValidationJob.user_id == user.id,
            ValidationJob.status == 'completed'
        ).all()
        
        # Email statistics - get from actual validation results
        job_ids = [job.id for job in completed_jobs]
        
        if job_ids:
            # Count total validation results
            total_validations = db.query(ValidationResult).filter(
                ValidationResult.job_id.in_(job_ids)
            ).count()
            
            # Count valid emails
            valid_emails = db.query(ValidationResult).filter(
                ValidationResult.job_id.in_(job_ids),
                ValidationResult.is_valid == True
            ).count()
        else:
            total_validations = 0
            valid_emails = 0
            
        success_rate = round((valid_emails / total_validations * 100), 1) if total_validations > 0 else 0
        
        # Subscription info
        if user.has_active_subscription():
            active_sub = user.get_active_subscription()
            days_remaining = active_sub.days_remaining()
            subscription_info = f"✅ Active ({days_remaining} days remaining)"
        else:
            trial_remaining = user.get_trial_remaining()
            emails_used = user.trial_emails_used or 0
            phones_used = user.trial_phones_used or 0
            subscription_info = f"🆓 Trial ({trial_remaining} validations remaining)\n    📧 Emails used: {emails_used}\n    📱 Phones used: {phones_used}"
        
        # Monthly statistics
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_jobs = db.query(ValidationJob).filter(
            ValidationJob.user_id == user.id,
            ValidationJob.created_at >= month_start,
            ValidationJob.status == 'completed'
        ).all()
        
        # Monthly statistics - get from actual validation results
        month_job_ids = [job.id for job in month_jobs]
        
        if month_job_ids:
            month_validations = db.query(ValidationResult).filter(
                ValidationResult.job_id.in_(month_job_ids)
            ).count()
            
            month_valid = db.query(ValidationResult).filter(
                ValidationResult.job_id.in_(month_job_ids),
                ValidationResult.is_valid == True
            ).count()
        else:
            month_validations = 0
            month_valid = 0
            
        month_accuracy = round((month_valid / month_validations * 100), 1) if month_validations > 0 else 0
        
        return {
            'total_jobs': total_jobs,
            'total_validations': total_validations,
            'valid_emails': valid_emails,
            'success_rate': success_rate,
            'subscription_info': subscription_info,
            'month_jobs': len(month_jobs),
            'month_validations': month_validations,
            'month_accuracy': month_accuracy
        }
    
    async def show_usage_statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, db: Session):
        """Show detailed usage statistics"""
        # Get statistics for different time periods
        now = datetime.utcnow()
        
        # Today
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_jobs = db.query(ValidationJob).filter(
            ValidationJob.user_id == user.id,
            ValidationJob.created_at >= today_start,
            ValidationJob.status == 'completed'
        ).all()
        
        # This week
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_jobs = db.query(ValidationJob).filter(
            ValidationJob.user_id == user.id,
            ValidationJob.created_at >= week_start,
            ValidationJob.status == 'completed'
        ).all()
        
        # This month
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_jobs = db.query(ValidationJob).filter(
            ValidationJob.user_id == user.id,
            ValidationJob.created_at >= month_start,
            ValidationJob.status == 'completed'
        ).all()
        
        # All time
        all_jobs = db.query(ValidationJob).filter(
            ValidationJob.user_id == user.id,
            ValidationJob.status == 'completed'
        ).all()
        
        def calculate_stats(jobs):
            if not jobs:
                return {'jobs': 0, 'emails': 0, 'valid': 0, 'rate': 0}
            
            total_emails = sum(job.total_emails for job in jobs)
            valid_emails = sum(job.valid_emails for job in jobs)
            rate = round((valid_emails / total_emails * 100), 1) if total_emails > 0 else 0
            
            return {
                'jobs': len(jobs),
                'emails': total_emails,
                'valid': valid_emails,
                'rate': rate
            }
        
        today_stats = calculate_stats(today_jobs)
        week_stats = calculate_stats(week_jobs)
        month_stats = calculate_stats(month_jobs)
        all_stats = calculate_stats(all_jobs)
        
        stats_text = f"""
📈 **Detailed Usage Statistics**

📅 **Today:**
• Jobs: {today_stats['jobs']}
• Emails validated: {today_stats['emails']:,}
• Success rate: {today_stats['rate']}%

📊 **This Week:**
• Jobs: {week_stats['jobs']}
• Emails validated: {week_stats['emails']:,}
• Success rate: {week_stats['rate']}%

📆 **This Month:**
• Jobs: {month_stats['jobs']}
• Emails validated: {month_stats['emails']:,}
• Success rate: {month_stats['rate']}%

🏆 **All Time:**
• Jobs: {all_stats['jobs']}
• Emails validated: {all_stats['emails']:,}
• Valid emails found: {all_stats['valid']:,}
• Overall success rate: {all_stats['rate']}%

**Account Status:**
• Member since: {user.created_at.strftime('%B %d, %Y')}
• Trial emails used: {user.trial_emails_used}/10
        """
        
        if user.has_active_subscription():
            active_sub = user.get_active_subscription()
            stats_text += f"\n• Subscription expires: {active_sub.expires_at.strftime('%B %d, %Y')}"
        
        query = update.callback_query
        await query.edit_message_text(
            stats_text,
            reply_markup=self.keyboards.dashboard_menu(),
            parse_mode='Markdown'
        )
    
    async def show_recent_activity(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, db: Session):
        """Show recent user activity"""
        # Get recent jobs
        recent_jobs = db.query(ValidationJob).filter(
            ValidationJob.user_id == user.id
        ).order_by(ValidationJob.created_at.desc()).limit(15).all()
        
        if not recent_jobs:
            activity_text = """
📋 **Recent Activity**

No recent activity found.

Start validating emails to see your activity history here.
            """
        else:
            activity_text = "📋 **Recent Activity**\n\n"
            
            for job in recent_jobs:
                # Status emoji
                status_emoji = {
                    'pending': '⏳',
                    'processing': '🔄',
                    'completed': '✅',
                    'failed': '❌'
                }.get(job.status, '❓')
                
                # Time ago
                time_diff = datetime.utcnow() - job.created_at
                if time_diff.days > 0:
                    time_ago = f"{time_diff.days}d ago"
                elif time_diff.seconds > 3600:
                    hours = time_diff.seconds // 3600
                    time_ago = f"{hours}h ago"
                elif time_diff.seconds > 60:
                    minutes = time_diff.seconds // 60
                    time_ago = f"{minutes}m ago"
                else:
                    time_ago = "Just now"
                
                # Success rate for completed jobs
                success_info = ""
                if job.status == 'completed' and job.total_emails > 0:
                    success_rate = round((job.valid_emails / job.total_emails) * 100, 1)
                    success_info = f" ({success_rate}% valid)"
                
                activity_text += f"""
{status_emoji} **{job.filename}**  
{job.total_emails} emails{success_info}  
{time_ago}

"""
            
            # Add summary
            completed_jobs = [j for j in recent_jobs if j.status == 'completed']
            total_recent_emails = sum(job.total_emails for job in completed_jobs)
            
            if total_recent_emails > 0:
                total_recent_valid = sum(job.valid_emails for job in completed_jobs)
                avg_success_rate = round((total_recent_valid / total_recent_emails) * 100, 1)
                
                activity_text += f"""
📊 **Recent Summary:**
• {len(completed_jobs)} completed jobs
• {total_recent_emails:,} emails validated
• {avg_success_rate}% average success rate
                """
        
        query = update.callback_query
        await query.edit_message_text(
            activity_text,
            reply_markup=self.keyboards.dashboard_menu(),
            parse_mode='Markdown'
        )
