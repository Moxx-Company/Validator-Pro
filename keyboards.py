"""
Telegram inline keyboard definitions
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class Keyboards:
    @staticmethod
    def main_menu():
        """Main menu keyboard - mobile optimized"""
        keyboard = [
            [InlineKeyboardButton("📧 Email", callback_data="validate_emails"), InlineKeyboardButton("📱 Phone", callback_data="validate_phones")],
            [InlineKeyboardButton("📊 Stats", callback_data="dashboard"), InlineKeyboardButton("💎 Subscribe", callback_data="subscription")],
            [InlineKeyboardButton("❓ Help", callback_data="help")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def onboarding():
        """Onboarding keyboard"""
        keyboard = [
            [InlineKeyboardButton("🚀 Get Started", callback_data="start_onboarding")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def subscription_menu(has_active=False, trial_started=False):
        """Subscription management keyboard - mobile optimized"""
        if has_active:
            keyboard = [
                [InlineKeyboardButton("📊 Status", callback_data="sub_status"), InlineKeyboardButton("💳 History", callback_data="payment_history")],
                [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
            ]
        else:
            keyboard = [
                [InlineKeyboardButton("💎 Subscribe", callback_data="subscribe"), InlineKeyboardButton("ℹ️ Info", callback_data="sub_info")],
                [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
            ]
            # Only show "Start Free Trial" if trial hasn't been started yet
            if not trial_started:
                keyboard.insert(0, [InlineKeyboardButton("🆓 Start Trial", callback_data="start_trial")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def payment_methods():
        """Payment method selection - mobile optimized"""
        keyboard = [
            [InlineKeyboardButton("₿ Bitcoin", callback_data="pay_btc"), InlineKeyboardButton("⟠ Ethereum", callback_data="pay_eth")],
            [InlineKeyboardButton("Ł Litecoin", callback_data="pay_ltc"), InlineKeyboardButton("🐕 Dogecoin", callback_data="pay_doge")],
            [InlineKeyboardButton("💰 USDT TRC20", callback_data="pay_usdt_trc20"), InlineKeyboardButton("💵 USDT ERC20", callback_data="pay_usdt_erc20")],
            [InlineKeyboardButton("⚡ TRON", callback_data="pay_trx"), InlineKeyboardButton("🟡 BNB Chain", callback_data="pay_bsc")],
            [InlineKeyboardButton("🔙 Back", callback_data="subscription")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def validation_menu(validation_type='email'):
        """Validation options for email or phone - mobile optimized"""
        item_name = "Emails" if validation_type == 'email' else "Phones"
        enter_callback = "enter_emails" if validation_type == 'email' else "enter_phones"
        upload_callback = f"upload_file_{validation_type}"
        recent_callback = f"recent_jobs_{validation_type}"
        
        keyboard = [
            [InlineKeyboardButton("📁 Upload", callback_data=upload_callback), InlineKeyboardButton(f"✍️ Enter {item_name}", callback_data=enter_callback)],
            [InlineKeyboardButton("📊 Recent", callback_data=recent_callback), InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
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
        """Dashboard navigation - mobile optimized"""
        keyboard = [
            [InlineKeyboardButton("📈 Usage", callback_data="usage_stats"), InlineKeyboardButton("📋 Activity", callback_data="recent_activity")],
            [InlineKeyboardButton("💎 Subscription", callback_data="sub_status"), InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
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
        """Actions for completed validation results - mobile optimized"""
        keyboard = [
            [InlineKeyboardButton("📥 Download", callback_data=f"download_{job_id}"), InlineKeyboardButton("📊 Details", callback_data=f"details_{job_id}")],
            [InlineKeyboardButton("🔁 Validate More", callback_data="validate_emails"), InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
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
    
    @staticmethod
    def phone_input_menu():
        """Menu for phone input mode"""
        keyboard = [
            [InlineKeyboardButton("✅ Start Validation", callback_data="start_phone_validation")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
    

