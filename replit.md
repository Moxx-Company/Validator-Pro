# Email Validator Telegram Bot

## Overview

This is a Telegram bot that provides bulk email validation services with subscription-based pricing. The bot validates emails through DNS, MX record, and SMTP connectivity checks, processes various file formats (CSV, Excel, TXT), and offers a freemium model with trial usage and paid subscriptions. Users can upload email lists, receive detailed validation reports, and manage their subscriptions through an intuitive Telegram interface.

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
- **Enterprise Performance**: DNS caching, 100 concurrent workers, 25-email batches for optimal throughput
- **Smart SMTP Checks**: Intelligent SMTP validation that skips checks for reliable providers (Gmail, Yahoo, etc.) for maximum speed
- **Concurrent Processing**: Thread pool executor for handling multiple email validations simultaneously (15-25 emails/second)
- **Timeout Management**: 30-second batch timeouts with graceful failure handling to prevent hanging
- **Result Tracking**: Detailed validation results with timing and error information
- **Enterprise Scale**: Supports 1000+ concurrent users with rate limiting and queue management

### File Processing System
- **Multi-format Support**: Handles CSV, Excel, and text file formats
- **File Validation**: Size limits, format verification, and security checks
- **Pandas Integration**: Uses pandas for efficient data processing and manipulation
- **Temporary File Management**: Secure handling of uploaded files with cleanup

### Subscription Management
- **Cryptocurrency Payments**: Support for Bitcoin, Ethereum, and USDT payments
- **Trial System**: Free trial with limited validations before requiring subscription
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