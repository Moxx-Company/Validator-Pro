"""
Telegram inline keyboard definitions
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class Keyboards:
    @staticmethod
    def main_menu():
        """Main menu keyboard"""
        keyboard = [
            [InlineKeyboardButton("🎯 Validate Emails", callback_data="validate_emails")],
            [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")],
            [InlineKeyboardButton("💎 Subscription", callback_data="subscription")],
            [InlineKeyboardButton("❓ Help", callback_data="help")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def onboarding():
        """Onboarding keyboard"""
        keyboard = [
            [InlineKeyboardButton("🚀 Get Started", callback_data="start_onboarding")],
            [InlineKeyboardButton("ℹ️ Learn More", callback_data="learn_more")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def subscription_menu(has_active=False):
        """Subscription management keyboard"""
        if has_active:
            keyboard = [
                [InlineKeyboardButton("📊 Subscription Status", callback_data="sub_status")],
                [InlineKeyboardButton("💳 Payment History", callback_data="payment_history")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
            ]
        else:
            keyboard = [
                [InlineKeyboardButton("💎 Subscribe Now", callback_data="subscribe")],
                [InlineKeyboardButton("🆓 Start Free Trial", callback_data="start_trial")],
                [InlineKeyboardButton("ℹ️ Subscription Info", callback_data="sub_info")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
            ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def payment_methods():
        """Payment method selection"""
        keyboard = [
            [InlineKeyboardButton("₿ Bitcoin (BTC)", callback_data="pay_btc")],
            [InlineKeyboardButton("⟠ Ethereum (ETH)", callback_data="pay_eth")],
            [InlineKeyboardButton("Ł Litecoin (LTC)", callback_data="pay_ltc")],
            [InlineKeyboardButton("🐕 Dogecoin (DOGE)", callback_data="pay_doge")],
            [InlineKeyboardButton("💰 USDT (TRC20)", callback_data="pay_usdt_trc20")],
            [InlineKeyboardButton("💵 USDT (ERC20)", callback_data="pay_usdt_erc20")],
            [InlineKeyboardButton("⚡ TRON (TRX)", callback_data="pay_trx")],
            [InlineKeyboardButton("🟡 BNB Smart Chain", callback_data="pay_bsc")],
            [InlineKeyboardButton("🔙 Back", callback_data="subscription")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def validation_menu():
        """Email validation options"""
        keyboard = [
            [InlineKeyboardButton("📁 Upload File", callback_data="upload_file")],
            [InlineKeyboardButton("✍️ Enter Emails", callback_data="enter_emails")],
            [InlineKeyboardButton("📊 Recent Jobs", callback_data="recent_jobs")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def file_upload_options():
        """File upload format options"""
        keyboard = [
            [InlineKeyboardButton("📄 CSV File", callback_data="upload_csv")],
            [InlineKeyboardButton("📊 Excel File", callback_data="upload_excel")],
            [InlineKeyboardButton("📝 Text File", callback_data="upload_txt")],
            [InlineKeyboardButton("🔙 Back", callback_data="validate_emails")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def job_actions(job_id):
        """Actions for a validation job"""
        keyboard = [
            [InlineKeyboardButton("📥 Download Results", callback_data=f"download_{job_id}")],
            [InlineKeyboardButton("📊 View Details", callback_data=f"details_{job_id}")],
            [InlineKeyboardButton("🔙 Back", callback_data="recent_jobs")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def dashboard_menu():
        """Dashboard navigation"""
        keyboard = [
            [InlineKeyboardButton("📈 Usage Stats", callback_data="usage_stats")],
            [InlineKeyboardButton("📋 Recent Activity", callback_data="recent_activity")],
            [InlineKeyboardButton("💎 Subscription Info", callback_data="sub_status")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def help_menu():
        """Help and support options"""
        keyboard = [
            [InlineKeyboardButton("📖 User Guide", callback_data="user_guide")],
            [InlineKeyboardButton("❓ FAQ", callback_data="faq")],
            [InlineKeyboardButton("💬 Contact Support", callback_data="contact_support")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def confirm_action(action, data=""):
        """Generic confirmation keyboard"""
        keyboard = [
            [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{action}_{data}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def back_to_menu():
        """Simple back to menu button"""
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def subscription_prompt():
        """Prompt to subscribe when trial limit exceeded"""
        keyboard = [
            [InlineKeyboardButton("💎 Subscribe Now", callback_data="subscribe")],
            [InlineKeyboardButton("ℹ️ Subscription Info", callback_data="sub_info")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def validation_results(job_id):
        """Actions for completed validation results"""
        keyboard = [
            [InlineKeyboardButton("📥 Download CSV", callback_data=f"download_{job_id}")],
            [InlineKeyboardButton("📊 View Details", callback_data=f"details_{job_id}")],
            [InlineKeyboardButton("🔁 Validate More", callback_data="validate_emails")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def recent_jobs_menu(jobs):
        """Menu for recent validation jobs"""
        keyboard = []
        
        # Add buttons for each job (max 5 to avoid overcrowding)
        for job in jobs[:5]:
            status_emoji = "✅" if job.status == "completed" else "⏳" if job.status == "processing" else "❌"
            keyboard.append([
                InlineKeyboardButton(
                    f"{status_emoji} Job #{job.id} - {job.filename or 'Manual'}",
                    callback_data=f"details_{job.id}"
                )
            ])
        
        # Navigation buttons
        keyboard.extend([
            [InlineKeyboardButton("🔁 Validate More", callback_data="validate_emails")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def email_input_menu():
        """Menu for email input mode"""
        keyboard = [
            [InlineKeyboardButton("✅ Start Validation", callback_data="start_validation")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
