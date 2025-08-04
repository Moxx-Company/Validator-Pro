"""
High-Performance Configuration for Large User Base (5000+ Users)
Optimized settings for production deployment
"""
import os

# === DATABASE SCALING ===
# PostgreSQL Connection Pool Settings for High Load
DATABASE_POOL_SIZE = int(os.getenv('DATABASE_POOL_SIZE', '20'))  # Up from 5
DATABASE_MAX_OVERFLOW = int(os.getenv('DATABASE_MAX_OVERFLOW', '50'))  # Up from 10
DATABASE_POOL_TIMEOUT = int(os.getenv('DATABASE_POOL_TIMEOUT', '30'))  # Connection timeout
DATABASE_POOL_RECYCLE = int(os.getenv('DATABASE_POOL_RECYCLE', '1800'))  # 30 minutes
DATABASE_POOL_PRE_PING = True  # Always validate connections

# === CONCURRENCY SCALING ===
# Email Validation - Scale for 5000 users
MAX_CONCURRENT_EMAILS = int(os.getenv('MAX_CONCURRENT_EMAILS', '200'))  # Up from 50
EMAIL_BATCH_SIZE = int(os.getenv('EMAIL_BATCH_SIZE', '50'))  # Larger batches
EMAIL_THREAD_POOL_SIZE = int(os.getenv('EMAIL_THREAD_POOL_SIZE', '100'))  # More threads
EMAIL_VALIDATION_TIMEOUT = int(os.getenv('EMAIL_VALIDATION_TIMEOUT', '15'))  # More time

# Phone Validation - Scale for 5000 users  
MAX_CONCURRENT_PHONES = int(os.getenv('MAX_CONCURRENT_PHONES', '300'))  # Up from default
PHONE_BATCH_SIZE = int(os.getenv('PHONE_BATCH_SIZE', '100'))  # Larger batches
PHONE_THREAD_POOL_SIZE = int(os.getenv('PHONE_THREAD_POOL_SIZE', '150'))  # More threads
PHONE_VALIDATION_TIMEOUT = int(os.getenv('PHONE_VALIDATION_TIMEOUT', '8'))  # Slightly more time

# === RATE LIMITING ===
# User Rate Limits - Prevent abuse while allowing legitimate usage
RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', '300'))  # Up from 120
RATE_LIMIT_PER_HOUR = int(os.getenv('RATE_LIMIT_PER_HOUR', '5000'))  # New hourly limit
RATE_LIMIT_BURST = int(os.getenv('RATE_LIMIT_BURST', '50'))  # Allow bursts

# Global System Limits
MAX_ACTIVE_JOBS = int(os.getenv('MAX_ACTIVE_JOBS', '500'))  # Total concurrent jobs
MAX_QUEUE_SIZE = int(os.getenv('MAX_QUEUE_SIZE', '2000'))  # Up from 200
JOB_TIMEOUT_MINUTES = int(os.getenv('JOB_TIMEOUT_MINUTES', '30'))  # Job max runtime

# === CACHING ===
# Redis Configuration for Performance Caching
REDIS_URL = os.getenv('REDIS_URL')  # Optional Redis for caching
CACHE_VALIDATION_RESULTS = os.getenv('CACHE_VALIDATION_RESULTS', 'true').lower() == 'true'
CACHE_TTL_SECONDS = int(os.getenv('CACHE_TTL_SECONDS', '3600'))  # 1 hour cache
CACHE_MAX_ENTRIES = int(os.getenv('CACHE_MAX_ENTRIES', '100000'))  # 100K entries

# === FILE PROCESSING ===
# Handle larger files for enterprise users
MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '50'))  # Up from 10MB
MAX_RECORDS_PER_FILE = int(os.getenv('MAX_RECORDS_PER_FILE', '100000'))  # 100K records
CHUNK_PROCESSING_SIZE = int(os.getenv('CHUNK_PROCESSING_SIZE', '1000'))  # Process in chunks

# === MONITORING ===
# Performance monitoring settings
ENABLE_METRICS = os.getenv('ENABLE_METRICS', 'true').lower() == 'true'
METRICS_COLLECTION_INTERVAL = int(os.getenv('METRICS_COLLECTION_INTERVAL', '60'))  # seconds
LOG_SLOW_QUERIES = os.getenv('LOG_SLOW_QUERIES', 'true').lower() == 'true'
SLOW_QUERY_THRESHOLD = float(os.getenv('SLOW_QUERY_THRESHOLD', '2.0'))  # seconds

# === TELEGRAM BOT OPTIMIZATION ===
# Handle high message volume
TELEGRAM_WEBHOOK_MAX_CONNECTIONS = int(os.getenv('TELEGRAM_WEBHOOK_MAX_CONNECTIONS', '40'))
TELEGRAM_RATE_LIMIT_PER_SECOND = int(os.getenv('TELEGRAM_RATE_LIMIT_PER_SECOND', '30'))
TELEGRAM_QUEUE_SIZE = int(os.getenv('TELEGRAM_QUEUE_SIZE', '1000'))

# === SMTP VALIDATION SCALING ===
# Email SMTP validation for high volume
SMTP_CONNECTION_POOL_SIZE = int(os.getenv('SMTP_CONNECTION_POOL_SIZE', '20'))
SMTP_MAX_CONNECTIONS_PER_HOST = int(os.getenv('SMTP_MAX_CONNECTIONS_PER_HOST', '5'))
SMTP_CONNECTION_TIMEOUT = int(os.getenv('SMTP_CONNECTION_TIMEOUT', '10'))
SMTP_READ_TIMEOUT = int(os.getenv('SMTP_READ_TIMEOUT', '15'))

# === RESOURCE MANAGEMENT ===
# System resource limits
MAX_MEMORY_USAGE_MB = int(os.getenv('MAX_MEMORY_USAGE_MB', '2048'))  # 2GB limit
CPU_CORES_TO_USE = int(os.getenv('CPU_CORES_TO_USE', '4'))  # Utilize multiple cores
GARBAGE_COLLECTION_THRESHOLD = int(os.getenv('GARBAGE_COLLECTION_THRESHOLD', '1000'))

# === BACKUP & RELIABILITY ===
# Data integrity settings
AUTO_BACKUP_INTERVAL_HOURS = int(os.getenv('AUTO_BACKUP_INTERVAL_HOURS', '6'))
ENABLE_DATABASE_REPLICATION = os.getenv('ENABLE_DATABASE_REPLICATION', 'false').lower() == 'true'
HEALTH_CHECK_INTERVAL_SECONDS = int(os.getenv('HEALTH_CHECK_INTERVAL_SECONDS', '30'))

print(f"🚀 High-Performance Configuration Loaded")
print(f"   Database Pool Size: {DATABASE_POOL_SIZE}")
print(f"   Max Concurrent Jobs: {MAX_ACTIVE_JOBS}")
print(f"   Rate Limit/Min: {RATE_LIMIT_PER_MINUTE}")
print(f"   Max File Size: {MAX_FILE_SIZE_MB}MB")
print(f"   Cache Enabled: {CACHE_VALIDATION_RESULTS}")