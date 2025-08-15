"""
Helper utilities for Media Search Bot
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from pyrogram import Client
from pyrogram.types import Message
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def format_duration(seconds: int) -> str:
    """Format duration in seconds to human readable format"""
    if not seconds:
        return "Unknown"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if not size_bytes:
        return "Unknown"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to specified length with ellipsis"""
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."

def extract_search_terms(query: str) -> tuple:
    """Extract search terms and file type from query"""
    file_type = None
    search_terms = query.strip()
    
    # Check for file type specification (query | type)
    if " | " in query:
        parts = query.split(" | ", 1)
        if len(parts) == 2:
            search_terms = parts[0].strip()
            file_type_input = parts[1].strip().lower()
            
            # Map file type aliases
            type_mapping = {
                "video": "video",
                "vid": "video",
                "movie": "video",
                "film": "video",
                "doc": "document",
                "document": "document",
                "pdf": "document",
                "book": "document",
                "audio": "audio",
                "music": "audio",
                "song": "audio",
                "mp3": "audio",
                "photo": "photo",
                "image": "photo",
                "pic": "photo",
                "picture": "photo",
                "animation": "animation",
                "gif": "animation",
                "voice": "voice",
                "sticker": "sticker"
            }
            file_type = type_mapping.get(file_type_input)
    
    return search_terms, file_type

def create_file_link(channel_id: int, message_id: int) -> str:
    """Create Telegram file link"""
    if channel_id < 0:
        # Convert to channel format
        channel_id = str(channel_id)[4:]  # Remove -100 prefix
        return f"https://t.me/c/{channel_id}/{message_id}"
    else:
        return f"https://t.me/{channel_id}/{message_id}"

def get_file_emoji(file_type: str) -> str:
    """Get emoji for file type"""
    emoji_map = {
        "document": "📄",
        "video": "🎥", 
        "audio": "🎵",
        "photo": "🖼️",
        "animation": "🎬",
        "voice": "🎙️",
        "video_note": "🎥",
        "sticker": "🎭"
    }
    return emoji_map.get(file_type, "📁")

def validate_user_id(user_id_str: str) -> Optional[int]:
    """Validate and convert user ID string to integer"""
    try:
        user_id = int(user_id_str)
        if user_id > 0:
            return user_id
    except (ValueError, TypeError):
        pass
    return None

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    if not filename:
        return "unnamed_file"
    
    # Remove or replace problematic characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    if len(filename) > 200:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:190] + ('.' + ext if ext else '')
    
    return filename

async def check_channel_access(client: Client, channel_id: int) -> Dict[str, Any]:
    """Check if bot has access to channel and get info"""
    try:
        chat = await client.get_chat(channel_id)
        me = await client.get_chat_member(channel_id, "me")
        
        return {
            "accessible": True,
            "title": chat.title,
            "type": chat.type,
            "member_count": getattr(chat, 'members_count', 0),
            "bot_status": me.status,
            "can_read": me.privileges.can_read_messages if me.privileges else False
        }
    except Exception as e:
        return {
            "accessible": False,
            "error": str(e)
        }

async def batch_process(items: List[Any], process_func, batch_size: int = 10, delay: float = 0.1):
    """Process items in batches with delay to avoid rate limits"""
    results = []
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_results = await asyncio.gather(
            *[process_func(item) for item in batch],
            return_exceptions=True
        )
        results.extend(batch_results)
        
        # Add delay between batches
        if delay > 0 and i + batch_size < len(items):
            await asyncio.sleep(delay)
    
    return results

def calculate_uptime(start_time: str) -> str:
    """Calculate bot uptime from start time string"""
    try:
        start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        now = datetime.now(start.tzinfo) if start.tzinfo else datetime.now()
        uptime = now - start
        
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m {seconds}s"
            
    except Exception as e:
        logger.error(f"Error calculating uptime: {e}")
        return "Unknown"

class RateLimiter:
    """Simple rate limiter for user actions"""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}
    
    def is_allowed(self, user_id: int) -> bool:
        """Check if user is allowed to make request"""
        now = datetime.now()
        
        if user_id not in self.requests:
            self.requests[user_id] = []
        
        # Clean old requests
        cutoff = now - timedelta(seconds=self.window_seconds)
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id] 
            if req_time > cutoff
        ]
        
        # Check if under limit
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        
        # Add current request
        self.requests[user_id].append(now)
        return True
    
    def get_reset_time(self, user_id: int) -> Optional[int]:
        """Get seconds until rate limit resets"""
        if user_id not in self.requests or not self.requests[user_id]:
            return None
        
        oldest_request = min(self.requests[user_id])
        reset_time = oldest_request + timedelta(seconds=self.window_seconds)
        remaining = (reset_time - datetime.now()).total_seconds()
        
        return max(0, int(remaining))

# Global rate limiter instance
query_rate_limiter = RateLimiter(max_requests=20, window_seconds=60)
