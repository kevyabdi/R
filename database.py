"""
Database management for Media Search Bot
Handles MongoDB operations for media file storage and indexing
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError
from config import Config

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.config = Config()
        self.client = None
        self.db = None
        self.collection = None
        self._connected = False

    async def initialize(self):
        """Initialize database connection and indexes"""
        try:
            # Connect to MongoDB
            self.client = AsyncIOMotorClient(self.config.DATABASE_URI)
            self.db = self.client[self.config.DATABASE_NAME]
            self.collection = self.db[self.config.COLLECTION_NAME]

            # Test connection
            await self.client.admin.command('ping')
            self._connected = True

            # Create indexes for better search performance
            await self._create_indexes()

            logger.info(f"✅ Database connected: {self.config.DATABASE_NAME}")

        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise

    async def _create_indexes(self):
        """Create necessary indexes for efficient searching"""
        try:
            # Text index for searching
            await self.collection.create_index([
                ("file_name", "text"),
                ("caption", "text"),
                ("mime_type", "text")
            ])

            # Compound indexes for filtering
            await self.collection.create_index([
                ("file_type", 1),
                ("file_size", 1)
            ])

            # Index for file_id (unique)
            await self.collection.create_index("file_id", unique=True)

            # Index for channel_id
            await self.collection.create_index("channel_id")

            logger.info("📊 Database indexes created successfully")

        except Exception as e:
            logger.error(f"❌ Error creating indexes: {e}")

    async def save_file(self, file_data: Dict[str, Any]) -> bool:
        """Save file metadata to database"""
        try:
            if not self._connected:
                logger.error("❌ Database not connected")
                return False

            await self.collection.insert_one(file_data)
            logger.debug(f"💾 Saved file: {file_data.get('file_name', 'Unknown')}")
            return True

        except DuplicateKeyError:
            logger.debug(f"🔄 File already exists: {file_data.get('file_id')}")
            return False
        except Exception as e:
            logger.error(f"❌ Error saving file: {e}")
            return False

    async def search_files(self, query: str, file_type: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Search for files by query and optional file type"""
        try:
            if not self._connected:
                logger.error("❌ Database not connected")
                return []

            # Build search query
            search_filter = {}

            if query.strip():
                # Use regex search for better partial matching
                # This will match any part of the filename, case-insensitive
                search_conditions = []
                
                # Search in file_name
                search_conditions.append({"file_name": {"$regex": query, "$options": "i"}})
                
                # Also search in caption if USE_CAPTION_FILTER is enabled
                if hasattr(self.config, 'USE_CAPTION_FILTER') and self.config.USE_CAPTION_FILTER:
                    search_conditions.append({"caption": {"$regex": query, "$options": "i"}})
                
                # Use $or to search in multiple fields
                if len(search_conditions) > 1:
                    search_filter["$or"] = search_conditions
                else:
                    search_filter = search_conditions[0]

            if file_type:
                if "$or" in search_filter:
                    search_filter = {"$and": [search_filter, {"file_type": file_type}]}
                else:
                    search_filter["file_type"] = file_type

            # Execute search with projection to limit returned fields
            # Sort by date (newest first) when no specific query
            sort_order = [("date", -1)] if not query.strip() else [("_id", 1)]
            
            cursor = self.collection.find(
                search_filter,
                {
                    "_id": 0,
                    "file_id": 1,
                    "file_name": 1,
                    "file_size": 1,
                    "file_type": 1,
                    "mime_type": 1,
                    "caption": 1,
                    "channel_id": 1,
                    "message_id": 1
                }
            ).sort(sort_order).limit(limit)

            results = await cursor.to_list(length=limit)
            logger.debug(f"🔍 Search '{query}' returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"❌ Error searching files: {e}")
            return []

    async def delete_file(self, file_id: str) -> bool:
        """Delete a file from database by file_id"""
        try:
            if not self._connected:
                logger.error("❌ Database not connected")
                return False

            result = await self.collection.delete_one({"file_id": file_id})

            if result.deleted_count > 0:
                logger.info(f"🗑️ Deleted file: {file_id}")
                return True
            else:
                logger.warning(f"⚠️ File not found for deletion: {file_id}")
                return False

        except Exception as e:
            logger.error(f"❌ Error deleting file: {e}")
            return False

    async def get_total_files(self) -> int:
        """Get total number of indexed files"""
        try:
            if not self._connected:
                return 0

            count = await self.collection.count_documents({})
            return count

        except Exception as e:
            logger.error(f"❌ Error getting file count: {e}")
            return 0

    async def get_channel_stats(self) -> Dict[str, int]:
        """Get file statistics by channel"""
        try:
            if not self._connected:
                return {}

            pipeline = [
                {"$group": {"_id": "$channel_id", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]

            cursor = self.collection.aggregate(pipeline)
            results = await cursor.to_list(length=None)

            stats = {}
            for result in results:
                channel_id = result["_id"]
                count = result["count"]
                stats[str(channel_id)] = count

            return stats

        except Exception as e:
            logger.error(f"❌ Error getting channel stats: {e}")
            return {}

    async def get_file_type_stats(self) -> Dict[str, int]:
        """Get file statistics by type"""
        try:
            if not self._connected:
                return {}

            pipeline = [
                {"$group": {"_id": "$file_type", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]

            cursor = self.collection.aggregate(pipeline)
            results = await cursor.to_list(length=None)

            stats = {}
            for result in results:
                file_type = result["_id"]
                count = result["count"]
                stats[file_type or "unknown"] = count

            return stats

        except Exception as e:
            logger.error(f"❌ Error getting file type stats: {e}")
            return {}

    async def cleanup_old_files(self, days: int = 30) -> int:
        """Remove files older than specified days (optional maintenance)"""
        try:
            if not self._connected:
                return 0

            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=days)

            # This would require a timestamp field in the documents
            # For now, just return 0 as we don't have automatic cleanup
            return 0

        except Exception as e:
            logger.error(f"❌ Error cleaning up old files: {e}")
            return 0

    def is_connected(self) -> bool:
        """Check if database is connected"""
        return self._connected

    async def close_connection(self):
        """Close database connection"""
        try:
            if self.client:
                self.client.close()
                self._connected = False
                logger.info("🔐 Database connection closed")
        except Exception as e:
            logger.error(f"❌ Error closing database connection: {e}")