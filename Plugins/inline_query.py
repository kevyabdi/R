"""
Inline query handler for Media Search Bot
Handles inline search functionality
"""

from pyrogram import Client, filters
from pyrogram.types import InlineQuery, InlineQueryResultCachedDocument, InlineQueryResultCachedVideo, InlineQueryResultCachedAudio, InlineQueryResultCachedPhoto
import logging
import asyncio
from config import Config
from storage import Storage
from database_manager import db_manager

logger = logging.getLogger(__name__)

# Initialize components
config = Config()
storage = Storage()

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if not size_bytes:
        return "Unknown"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

@Client.on_inline_query()
async def inline_query_handler(client: Client, inline_query: InlineQuery):
    """Handle inline queries for file search"""
    try:
        user_id = inline_query.from_user.id
        query = inline_query.query.strip()
        
        # Check if user is banned
        if storage.is_banned(user_id):
            await inline_query.answer(
                results=[],
                cache_time=0,
                switch_pm_text="❌ You are banned",
                switch_pm_parameter="banned"
            )
            return
        
        # Check authorization
        if config.AUTH_USERS and not config.is_auth_user(user_id):
            await inline_query.answer(
                results=[],
                cache_time=0,
                switch_pm_text="❌ Not authorized",
                switch_pm_parameter="unauthorized"
            )
            return
        
        # Check channel subscription if required
        if config.AUTH_CHANNEL:
            try:
                member = await client.get_chat_member(config.AUTH_CHANNEL, user_id)
                if member.status in ["left", "kicked"]:
                    await inline_query.answer(
                        results=[],
                        cache_time=0,
                        switch_pm_text="Join Channel First",
                        switch_pm_parameter="join_channel"
                    )
                    return
            except Exception as e:
                logger.error(f"Error checking channel membership: {e}")
        
        # Handle empty query - show recent files
        if not query:
            db = await db_manager.get_database()
            files = await db.search_files("", None, limit=20)  # Get recent files
            
            if not files:
                await inline_query.answer(
                    results=[],
                    cache_time=0,
                    switch_pm_text="🔍 No files available",
                    switch_pm_parameter="help"
                )
                return
            
            # Create results for recent files
            results = []
            for i, file_data in enumerate(files[:10]):  # Show only 10 recent files
                try:
                    file_id = file_data.get("file_id")
                    file_name = file_data.get("file_name", "Unknown File")
                    file_size = file_data.get("file_size", 0)
                    file_type = file_data.get("file_type", "unknown")
                    caption = file_data.get("caption", "")
                    
                    # Format file size
                    size_str = format_file_size(file_size)
                    
                    # Create description
                    description = f"📦 {size_str} • 🔖 {file_type.title()}"
                    
                    # Create result based on file type
                    if file_type == "video":
                        result = InlineQueryResultCachedVideo(
                            id=f"recent_video_{i}",
                            video_file_id=file_id,
                            title=file_name,
                            description=description,
                            caption=f"📹 {file_name}\n📦 Size: {size_str}"
                        )
                    elif file_type == "audio":
                        result = InlineQueryResultCachedAudio(
                            id=f"recent_audio_{i}",
                            audio_file_id=file_id,
                            caption=f"🎵 {file_name}\n📦 Size: {size_str}"
                        )
                    elif file_type == "photo":
                        result = InlineQueryResultCachedPhoto(
                            id=f"recent_photo_{i}",
                            photo_file_id=file_id,
                            title=file_name,
                            description=description,
                            caption=f"🖼️ {file_name}\n📦 Size: {size_str}"
                        )
                    else:
                        result = InlineQueryResultCachedDocument(
                            id=f"recent_doc_{i}",
                            document_file_id=file_id,
                            title=file_name,
                            description=description,
                            caption=f"📁 {file_name}\n📦 Size: {size_str}"
                        )
                    
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"Error creating recent file result: {e}")
                    continue
            
            await inline_query.answer(
                results=results,
                cache_time=60,
                switch_pm_text=f"📚 {len(files)} files available",
                switch_pm_parameter="browse"
            )
            return
        
        # Parse query for file type filtering
        file_type = None
        search_terms = query
        
        if " | " in query:
            parts = query.split(" | ")
            if len(parts) == 2:
                search_terms = parts[0].strip()
                file_type_input = parts[1].strip().lower()
                
                # Map file type aliases
                type_mapping = {
                    "video": "video",
                    "doc": "document", 
                    "document": "document",
                    "audio": "audio",
                    "photo": "photo",
                    "image": "photo"
                }
                file_type = type_mapping.get(file_type_input)
        
        # Search files in database
        db = await db_manager.get_database()
        files = await db.search_files(search_terms, file_type, limit=50)
        
        # Track the query
        await storage.track_user_query(user_id, query)
        
        if not files:
            await inline_query.answer(
                results=[],
                cache_time=5,
                switch_pm_text="❌ No files found",
                switch_pm_parameter="no_results"
            )
            return
        
        # Create inline results
        results = []
        
        for i, file_data in enumerate(files):
            try:
                file_id = file_data.get("file_id")
                file_name = file_data.get("file_name", "Unknown File")
                file_size = file_data.get("file_size", 0)
                file_type = file_data.get("file_type", "unknown")
                caption = file_data.get("caption", "")
                mime_type = file_data.get("mime_type", "")
                
                # Format file size
                size_str = format_file_size(file_size)
                
                # Create description
                description_parts = []
                if size_str != "Unknown":
                    description_parts.append(f"📦 {size_str}")
                if mime_type:
                    description_parts.append(f"📄 {mime_type}")
                if file_type:
                    description_parts.append(f"🔖 {file_type.title()}")
                
                description = " • ".join(description_parts)
                
                # Create result based on file type using cached file IDs
                if file_type == "video":
                    result = InlineQueryResultCachedVideo(
                        id=f"video_{i}",
                        video_file_id=file_id,
                        title=file_name,
                        description=description,
                        caption=caption[:1024] if caption else f"📹 {file_name}\n📦 Size: {size_str}"
                    )
                elif file_type == "audio":
                    result = InlineQueryResultCachedAudio(
                        id=f"audio_{i}",
                        audio_file_id=file_id,
                        caption=caption[:1024] if caption else f"🎵 {file_name}\n📦 Size: {size_str}"
                    )
                elif file_type == "photo":
                    result = InlineQueryResultCachedPhoto(
                        id=f"photo_{i}",
                        photo_file_id=file_id,
                        title=file_name,
                        description=description,
                        caption=caption[:1024] if caption else f"🖼️ {file_name}\n📦 Size: {size_str}"
                    )
                else:
                    # For documents and other file types
                    result = InlineQueryResultCachedDocument(
                        id=f"doc_{i}",
                        document_file_id=file_id,
                        title=file_name,
                        description=description,
                        caption=caption[:1024] if caption else f"📁 {file_name}\n📦 Size: {size_str}"
                    )
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error creating inline result for file {file_data.get('file_id')}: {e}")
                continue
        
        # Answer the inline query
        await inline_query.answer(
            results=results,
            cache_time=config.CACHE_TIME,
            switch_pm_text=f"📊 {len(results)} files found",
            switch_pm_parameter="results"
        )
        
        logger.info(f"🔍 Inline query '{query}' by user {user_id} returned {len(results)} results")
        
    except Exception as e:
        logger.error(f"❌ Error handling inline query: {e}")
        try:
            await inline_query.answer(
                results=[],
                cache_time=0,
                switch_pm_text="❌ Search error occurred",
                switch_pm_parameter="error"
            )
        except Exception as answer_error:
            logger.error(f"❌ Error sending error response: {answer_error}")

@Client.on_chosen_inline_result()
async def chosen_inline_result_handler(client: Client, chosen_inline_result):
    """Handle chosen inline results for statistics"""
    try:
        user_id = chosen_inline_result.from_user.id
        result_id = chosen_inline_result.result_id
        query = chosen_inline_result.query
        
        # Track the result selection
        await storage.increment_stat("files_shared")
        
        logger.info(f"📤 User {user_id} selected result {result_id} for query '{query}'")
        
    except Exception as e:
        logger.error(f"❌ Error handling chosen inline result: {e}")
