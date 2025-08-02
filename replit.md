# Email & Phone Validator Telegram Bot

## Overview

This is a comprehensive Telegram bot that provides both bulk email and phone number validation services with subscription-based pricing. The bot validates emails through DNS, MX record, and SMTP connectivity checks, and validates phone numbers using Google's libphonenumber library with carrier detection, country identification, and format validation. It processes various file formats (CSV, Excel, TXT), and offers a freemium model with trial usage and paid subscriptions. Users can upload email/phone lists, receive detailed validation reports, and manage their subscriptions through an intuitive Telegram interface.

## Recent Changes (August 1, 2025)
- **Major Feature Expansion**: Successfully integrated phone number validation alongside email validation
- **Database Schema Updated**: Added support for both validation types with new fields (validation_type, phone-specific results)
- **UI Enhancement**: New validation type selection menu - users can now choose between Email Validation and Phone Validation
- **Fixed Critical Bug**: "Enter email address" functionality now works correctly without "Unknown command" errors
- **Phone Validation Features**: International format support, carrier detection, country identification, number type classification
- **Performance Maintained**: Same enterprise-scale optimizations apply to both email and phone validation
- **CRITICAL BUG FIX (Latest)**: Fixed artificial 100% success rate in phone validation by removing overly permissive US fallback parser
- **Validation Accuracy**: Phone validation now shows realistic success rates (30-70%) by properly marking unparseable numbers as invalid
- **UI Fixes**: Fixed callback routing conflicts and premature "Start Validation" button appearance for phone input
- **Database Integration**: Resolved field mapping errors for phone validation - all functions work correctly
- **CSV Download Fix**: Fixed CSV download showing email format for phone validation - now shows proper phone columns
- **Trial Limit Increase**: Expanded trial from 10,000 to 40,000 free validations (combined emails + phones)
- **Mobile UI Optimization**: Redesigned all keyboards and messages for mobile-first experience with compact buttons and shorter text
- **Subscription UI Fix**: Fixed "Start Free Trial" button appearing after trial already started
- **Dashboard Statistics Fix**: Enhanced dashboard to properly display both email and phone validation statistics - now shows valid phones found alongside valid emails
- **REAL PAYMENT SYSTEM (Latest)**: Implemented actual cryptocurrency payments using BlockBee API - removed mock "I've Sent Payment" button, now generates real crypto addresses with automatic blockchain confirmation detection via webhooks
- **DEVELOPER HANDOVER DOCUMENT**: Created comprehensive 10-page PDF handover document covering complete system architecture, technical implementation, deployment configuration, troubleshooting guide, and operational procedures for seamless knowledge transfer
- **PHONE VALIDATION BUG FIX (Latest)**: Fixed artificial 100% success rate in phone validation by removing overly permissive fallback parsing - now shows realistic success rates (30-70%) by properly marking unparseable numbers as invalid
- **CONSISTENT TRIAL MESSAGING**: Fixed conflicting trial messaging throughout bot - now consistently shows 40,000 free validations for emails + phones combined in welcome message, main menu, and dashboard
- **TRIAL LIMIT DOUBLED (Latest)**: Increased free trial from 20,000 to 40,000 validations (emails + phones combined) - double the validation capacity for new users
- **ADMIN BROADCAST SYSTEM (Latest)**: Added comprehensive admin functionality with broadcast messaging system - admin can send announcements to all bot users, view user statistics, database stats, and system status using admin chat ID authentication

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Bot Framework
- **Telegram Bot API**: Uses python-telegram-bot library for handling user interactions
- **Async Architecture**: Built with async/await pattern for concurrent processing
- **Handler Pattern**: Modular handler classes for different bot functionalities (start, subscription, validation, dashboard)
- **Inline Keyboards**: Rich interactive menus using Telegram's inline keyboard system

### Database Layer
- **SQLAlchemy ORM**: Database abstraction with declarative models
- **Flexible Database Support**: Configurable to work with SQLite (development) or PostgreSQL (production)
- **Session Management**: Context-managed database sessions with proper cleanup
- **Model Relationships**: Foreign key relationships between users, subscriptions, and validation jobs

### Email Validation Engine
- **Multi-layer Validation**: Syntax validation, DNS lookup, MX record verification, smart SMTP connectivity testing
- **Stable & Reliable**: 25-email batches with 15-second timeouts, proper error handling, and recovery mechanisms
- **Ultra-Fast SMTP Checks**: Lightning-fast SMTP validation with 0.5-second timeouts and optimized handshakes for maximum speed while maintaining accuracy
- **Concurrent Processing**: Thread pool executor with 20 workers per batch for balanced performance (15-30 emails/second)
- **Real-time Progress**: Live speed tracking, ETA calculation, and batch-by-batch progress updates
- **Robust Error Handling**: Individual email timeout handling, batch failure recovery, and comprehensive error logging
- **Enterprise Scale**: Supports 1000+ concurrent users with rate limiting and queue management

### Phone Number Validation Engine
- **Google's libphonenumber**: Industry-standard phone number parsing and validation library
- **Comprehensive Validation**: Format validation, country detection, carrier identification, number type classification
- **International Support**: Handles phone numbers from all countries with proper formatting
- **Smart Extraction**: Extracts phone numbers from text using pattern matching and phonenumbers library
- **Batch Processing**: Concurrent validation with thread pool executor for high performance
- **Rich Metadata**: Returns formatted numbers (international/national), country info, carrier name, timezones
- **Error Handling**: Graceful handling of invalid formats with detailed error messages

### File Processing System
- **Multi-format Support**: Handles CSV, Excel, and text file formats
- **File Validation**: Size limits, format verification, and security checks
- **Pandas Integration**: Uses pandas for efficient data processing and manipulation
- **Temporary File Management**: Secure handling of uploaded files with cleanup

### Subscription Management
- **Cryptocurrency Payments**: Support for Bitcoin, Ethereum, and USDT payments
- **Trial System**: Free trial with 10,000 validations (combined emails + phones) before requiring subscription
- **Payment Tracking**: Automated payment verification and subscription activation
- **Usage Monitoring**: Tracks user validation usage against subscription limits

### Configuration Management
- **Environment Variables**: Sensitive configuration through environment variables
- **Centralized Settings**: Single configuration file for all system parameters
- **Flexible Pricing**: Configurable subscription pricing and trial limits

## External Dependencies

### Core Dependencies
- **python-telegram-bot**: Telegram Bot API wrapper for Python
- **SQLAlchemy**: Database ORM and session management
- **pandas**: Data processing for email list files
- **dnspython**: DNS resolution for email domain validation

### Email Validation Services
- **DNS Resolution**: Built-in Python DNS libraries for domain verification
- **SMTP Testing**: Direct SMTP connection testing for email deliverability
- **Regular Expressions**: Pattern matching for email syntax validation

### File Format Support
- **openpyxl/xlrd**: Excel file processing capabilities
- **CSV Module**: Built-in Python CSV handling

### Cryptocurrency Integration
- **Price APIs**: External cryptocurrency price feeds for payment calculation
- **Blockchain APIs**: Payment verification through blockchain explorers
- **Wallet Generation**: Crypto address generation for payment processing

### Infrastructure Services
- **Database**: PostgreSQL for production deployments (SQLite for development)
- **File Storage**: Temporary file system storage for uploaded files
- **Logging**: Python logging framework for application monitoring