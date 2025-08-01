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
        return (self.trial_emails_used + count) <= 10

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
        """Activate the subscription"""
        self.status = 'active'
        self.activated_at = datetime.utcnow()
        self.expires_at = datetime.utcnow() + timedelta(days=30)
    
    def days_remaining(self):
        """Get days remaining in subscription"""
        if not self.expires_at or not self.is_active():
            return 0
        remaining = self.expires_at - datetime.utcnow()
        return max(0, remaining.days)

class ValidationJob(Base):
    __tablename__ = 'validation_jobs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Job details
    filename = Column(String, nullable=False)
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
        if self.total_emails == 0:
            return 0
        return int((self.processed_emails / self.total_emails) * 100)
    
    def is_completed(self):
        """Check if job is completed"""
        return self.status in ['completed', 'failed']

class ValidationResult(Base):
    __tablename__ = 'validation_results'
    
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey('validation_jobs.id'), nullable=False)
    
    # Email details
    email = Column(String, nullable=False, index=True)
    is_valid = Column(Boolean, default=False)
    
    # Validation details
    syntax_valid = Column(Boolean, default=False)
    domain_exists = Column(Boolean, default=False)
    mx_record_exists = Column(Boolean, default=False)
    smtp_connectable = Column(Boolean, default=False)
    
    # Additional info
    domain = Column(String, nullable=True)
    mx_records = Column(Text, nullable=True)  # JSON string
    error_message = Column(String, nullable=True)
    validation_time = Column(Float, default=0.0)  # seconds
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    job = relationship("ValidationJob", back_populates="results")
    
    def __repr__(self):
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
