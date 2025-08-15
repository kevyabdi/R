"""
Database Manager - Singleton pattern for shared database access
"""

import logging
from database import Database

logger = logging.getLogger(__name__)

class DatabaseManager:
    _instance = None
    _database = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    
    async def get_database(self):
        """Get or create database instance"""
        if self._database is None:
            self._database = Database()
            await self._database.initialize()
            logger.info("🔄 Database manager initialized")
        return self._database
    
    def reset(self):
        """Reset database instance (for restarts)"""
        self._database = None

# Global instance
db_manager = DatabaseManager()