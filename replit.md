# Media Search Bot

## Overview

This is a Telegram bot that automatically indexes media files from configured channels and provides inline search functionality. The bot allows users to search for documents, videos, audio files, and other media through Telegram's inline query system. It includes comprehensive admin management features, user authentication, ban system, and statistics tracking.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Core Components

**Bot Framework**: Built using Pyrogram library for Telegram Bot API interactions, providing asynchronous message handling and inline query support.

**Database Layer**: Uses MongoDB with Motor (async driver) for storing media file metadata including file names, captions, sizes, and indexing information. Text indexes are created for efficient searching across file names and captions.

**Storage System**: Implements JSON-based storage for user management data (banned users list) and bot statistics. Data is automatically saved at regular intervals to prevent loss.

**Plugin Architecture**: Modular design with separate handlers for:
- Channel post processing (automatic media indexing)
- Command handling (admin and user commands)
- Inline query processing (search functionality)

**Configuration Management**: Environment variable-based configuration system supporting:
- API credentials and tokens
- Database connection settings
- Admin and authorized user lists
- Channel configuration for auto-indexing
- Customizable bot messages

### Key Design Patterns

**Asynchronous Processing**: All operations use async/await patterns for non-blocking execution, allowing concurrent handling of multiple requests.

**Error Handling**: Comprehensive error handling for Telegram API errors, database connection issues, and session management problems.

**Rate Limiting**: Built-in query rate limiting to prevent spam and manage bot performance.

**Auto-Save Mechanism**: Periodic saving of user data and statistics to prevent data loss.

### Authentication & Authorization

**Multi-Level Access Control**:
- Admin users with full bot management capabilities
- Authorized users who can use the bot
- Channel subscription requirements
- Ban system for blocking problematic users

**Session Management**: Automatic session recovery and retry mechanisms for handling Telegram API session issues.

## External Dependencies

**Telegram Bot API**: Core integration through Pyrogram library for bot functionality, message handling, and inline queries.

**MongoDB Database**: Used for storing and indexing media file metadata with text search capabilities.

**Flask Web Server**: Provides keep-alive functionality and health check endpoints for hosting platform compatibility (specifically optimized for Render).

**File Storage**: Local JSON files for user management data and bot statistics that require persistence.

**Logging System**: Comprehensive logging configuration for monitoring bot operations and debugging.

The architecture is designed to be scalable and maintainable, with clear separation of concerns between data storage, bot logic, and external service integrations.