"""
Database models for the email validator bot
"""
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    language_code = Column(String, default='en')
    
    # Onboarding status
    is_onboarded = Column(Boolean, default=False)
    trial_emails_used = Column(Integer, default=0)
    trial_phones_used = Column(Integer, default=0)
    trial_activated = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="user")
    validation_jobs = relationship("ValidationJob", back_populates="user")
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"
    
    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.username or f"User_{self.telegram_id}"
    
    @property
    def trial_validations_used(self):
        """Total trial validations used (emails + phones combined)"""
        emails_used = self.trial_emails_used or 0
        phones_used = self.trial_phones_used or 0
        return emails_used + phones_used
    
    def has_active_subscription(self):
        """Check if user has an active subscription"""
        return any(sub.is_active() for sub in self.subscriptions)
    
    def get_active_subscription(self):
        """Get the active subscription if any"""
        for sub in self.subscriptions:
            if sub.is_active():
                return sub
        return None
    
    def can_validate_emails(self, count=1):
        """Check if user can validate emails"""
        if self.has_active_subscription():
            return True
        from config import TRIAL_VALIDATION_LIMIT
        return (self.trial_emails_used + count) <= TRIAL_VALIDATION_LIMIT
    
    def can_validate_phones(self, count=1):
        """Check if user can validate phone numbers"""
        if self.has_active_subscription():
            return True
        from config import TRIAL_VALIDATION_LIMIT
        return (self.trial_phones_used + count) <= TRIAL_VALIDATION_LIMIT
    
    def can_validate(self, validation_type='email', count=1):
        """Check if user can validate items (unified trial system)"""
        if self.has_active_subscription():
            return True
        
        from config import TRIAL_VALIDATION_LIMIT
        emails_used = self.trial_emails_used or 0
        phones_used = self.trial_phones_used or 0
        total_used = emails_used + phones_used
        return (total_used + count) <= TRIAL_VALIDATION_LIMIT
    
    def get_trial_remaining(self):
        """Get remaining trial validations"""
        from config import TRIAL_VALIDATION_LIMIT
        emails_used = self.trial_emails_used or 0
        phones_used = self.trial_phones_used or 0
        total_used = emails_used + phones_used
        return max(0, TRIAL_VALIDATION_LIMIT - total_used)
    
    def use_trial_validations(self, validation_type='email', count=1):
        """Use trial validations"""
        if validation_type == 'email':
            self.trial_emails_used = (self.trial_emails_used or 0) + count
        else:
            self.trial_phones_used = (self.trial_phones_used or 0) + count

class Subscription(Base):
    __tablename__ = 'subscriptions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Subscription details
    status = Column(String, default='pending')  # pending, active, expired, cancelled
    amount_usd = Column(Float, nullable=False)
    currency = Column(String, default='USD')
    
    # Crypto payment details
    payment_address = Column(String, nullable=True)
    payment_amount_crypto = Column(Float, nullable=True)
    payment_currency_crypto = Column(String, nullable=True)
    transaction_hash = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    activated_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Notification tracking
    expiry_warning_sent = Column(Boolean, default=False)  # 3-day warning sent
    expiry_final_notice_sent = Column(Boolean, default=False)  # Final notice sent
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")
    
    def __repr__(self):
        return f"<Subscription(id={self.id}, status={self.status})>"
    
    def is_active(self):
        """Check if subscription is currently active"""
        if self.status != 'active':
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return True
    
    def activate(self):
        """Activate the subscription with mathematically precise duration"""
        from config import SUBSCRIPTION_DURATION_DAYS
        
        self.status = 'active'
        self.activated_at = datetime.utcnow()
        # Use configuration value for precise duration calculation
        self.expires_at = datetime.utcnow() + timedelta(days=SUBSCRIPTION_DURATION_DAYS)
    
    def days_remaining(self):
        """Get days remaining in subscription with precise calculation"""
        if not self.expires_at or not self.is_active():
            return 0
        
        remaining = self.expires_at - datetime.utcnow()
        
        # Include partial days in calculation for accuracy
        # If there are hours remaining on the final day, count it as a full day
        days_with_hours = remaining.total_seconds() / 86400  # 86400 seconds per day
        
        return max(0, int(days_with_hours) + (1 if days_with_hours % 1 > 0 else 0))

class ValidationJob(Base):
    __tablename__ = 'validation_jobs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Job details
    validation_type = Column(String, default='email')  # 'email' or 'phone'
    filename = Column(String, nullable=False)
    total_items = Column(Integer, default=0)  # Generic field for emails or phones
    processed_items = Column(Integer, default=0)  # Generic field
    valid_items = Column(Integer, default=0)  # Generic field
    invalid_items = Column(Integer, default=0)  # Generic field
    
    # Legacy email-specific fields (for backward compatibility)
    total_emails = Column(Integer, default=0)
    processed_emails = Column(Integer, default=0)
    valid_emails = Column(Integer, default=0)
    invalid_emails = Column(Integer, default=0)
    
    # Status
    status = Column(String, default='pending')  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)
    
    # File paths
    input_file_path = Column(String, nullable=True)
    output_file_path = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="validation_jobs")
    results = relationship("ValidationResult", back_populates="job")
    
    def __repr__(self):
        return f"<ValidationJob(id={self.id}, status={self.status})>"
    
    @property
    def progress_percentage(self):
        """Get completion percentage"""
        total = self.total_items if self.total_items > 0 else self.total_emails
        processed = self.processed_items if self.total_items > 0 else self.processed_emails
        if total == 0:
            return 0
        return int((processed / total) * 100)
    
    def is_completed(self):
        """Check if job is completed"""
        return self.status in ['completed', 'failed']

class ValidationResult(Base):
    __tablename__ = 'validation_results'
    
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey('validation_jobs.id'), nullable=False)
    validation_type = Column(String, default='email')  # 'email' or 'phone'
    
    # Email details
    email = Column(String, nullable=True, index=True)
    is_valid = Column(Boolean, default=False)
    
    # Email validation details
    syntax_valid = Column(Boolean, default=False)
    domain_exists = Column(Boolean, default=False)
    mx_record_exists = Column(Boolean, default=False)
    smtp_connectable = Column(Boolean, default=False)
    domain = Column(String, nullable=True)
    mx_records = Column(Text, nullable=True)  # JSON string
    
    # Phone number details
    phone_number = Column(String, nullable=True, index=True)
    formatted_international = Column(String, nullable=True)
    formatted_national = Column(String, nullable=True)
    country_code = Column(String, nullable=True)
    country_name = Column(String, nullable=True)
    carrier = Column(String, nullable=True)
    number_type = Column(String, nullable=True)
    timezone = Column(String, nullable=True)
    
    # Common fields
    error_message = Column(String, nullable=True)
    validation_time = Column(Float, default=0.0)  # seconds
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    job = relationship("ValidationJob", back_populates="results")
    
    def __repr__(self):
        if self.validation_type == 'phone':
            return f"<ValidationResult(phone={self.phone_number}, is_valid={self.is_valid})>"
        else:
            return f"<ValidationResult(email={self.email}, is_valid={self.is_valid})>"

class UsageStats(Base):
    __tablename__ = 'usage_stats'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Daily usage tracking
    date = Column(DateTime, nullable=False, index=True)
    emails_validated = Column(Integer, default=0)
    validation_jobs = Column(Integer, default=0)
    
    # Performance metrics
    avg_validation_time = Column(Float, default=0.0)
    success_rate = Column(Float, default=0.0)
    
    def __repr__(self):
        return f"<UsageStats(user_id={self.user_id}, date={self.date})>"
