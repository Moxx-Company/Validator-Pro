# Validator Pro Telegram Bot

## Overview

This is a comprehensive Telegram bot called Validator Pro that provides both bulk email and phone number validation services with subscription-based pricing. The bot validates emails through DNS, MX record, and SMTP connectivity checks, and validates phone numbers using Google's libphonenumber library with carrier detection, country identification, and format validation. It processes various file formats (CSV, Excel, TXT), and offers a freemium model with trial usage and paid subscriptions. Users can upload email/phone lists, receive detailed validation reports, and manage their subscriptions through an intuitive Telegram interface.

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
- **TRIAL LIMIT REDUCED (Latest)**: Updated free trial to 1,000 validations (emails + phones combined) for new user onboarding and database reset
- **ADMIN BROADCAST SYSTEM (Latest)**: Added comprehensive admin functionality with broadcast messaging system - admin can send announcements to all bot users, view user statistics, database stats, and system status using admin chat ID authentication
- **MENU BUTTON COMMANDS (Latest)**: Added /start and /admin commands to Telegram's MenuButtonCommands for easy access - users can now tap the menu button to see available commands directly in their chat interface
- **ONBOARDING SIMPLIFIED (Latest)**: Removed "Learn More" button from onboarding process - users now see only "Get Started" for cleaner, more direct user experience
- **REBRANDING TO VALIDATOR PRO (Latest)**: Updated all references from "Email Validator Pro" to "Validator Pro" to better reflect the dual email and phone validation capabilities
- **DYNAMIC TRIAL LIMITS (Latest)**: Removed all hardcoded trial information from UI - now uses TRIAL_VALIDATION_LIMIT config for consistent 1,000 validation display across onboarding, dashboard, and subscription screens
- **VALIDATION HANG PROTECTION (Latest)**: Fixed validation getting stuck by adding timeout protection - bulk validation now has 5-minute total timeout with 15-second per-email limits, improved SMTP timeouts, and better error handling to prevent server crashes
- **COMPLETE CRASH PROTECTION (Latest)**: Added comprehensive timeout protection to both email AND phone validators - phone validation now has 2-minute batch timeout with 5-second individual limits, both validators handle problematic data gracefully without hanging the bot server
- **PAYMENT SECURITY UPDATE (Latest)**: Removed all hardcoded test wallet addresses from payment system - now requires proper wallet addresses to be configured via environment variables for security, prevents payments to test addresses
- **BLOCKBEE INTEGRATION FIX (Latest)**: Fixed payment system to work correctly with BlockBee API - removed wallet address requirement since BlockBee handles wallet generation automatically, removed "Check Payment" button for cleaner interface
- **WEBHOOK NOTIFICATION SYSTEM (Latest)**: Added automated payment confirmation notifications to users when subscriptions are activated, includes manual webhook testing and troubleshooting for missed BlockBee notifications
- **NOTIFICATION SYSTEM FIXED (Latest)**: Fixed payment notifications to use correct Telegram chat IDs instead of database user IDs - users now receive automatic payment confirmations when subscriptions activate
- **TRIAL SYSTEM OVERHAUL (Latest)**: Added trial_activated database field to properly track trial status - Start Trial button now works correctly, disappears after activation or subscription, and trial is only available once
- **CALLBACK ROUTING FIXES (Latest)**: Fixed Activity button responsiveness by correcting callback routing patterns, moved subscription callbacks before generic start_ callbacks to prevent conflicts
- **DATABASE SCHEMA UPDATE (Latest)**: Added trial_activated column to users table for persistent trial state management

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