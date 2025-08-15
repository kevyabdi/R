"""
Storage management for Media Search Bot
Handles JSON-based user management and statistics
"""

import json
import os
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class Storage:
    def __init__(self):
        self.banned_users_file = "banned_users.json"
        self.stats_file = "bot_stats.json"
        
        # In-memory storage
        self.banned_users = set()
        self.user_stats = {}
        self.bot_stats = {
            "total_users": 0,
            "total_queries": 0,
            "total_files": 0,
            "banned_users": 0,
            "start_time": None,
            "last_updated": None
        }
        
        # Auto-save interval (5 minutes)
        self.auto_save_interval = 300
        self._auto_save_task = None
    
    async def load_data(self):
        """Load data from JSON files"""
        try:
            await self._load_banned_users()
            await self._load_bot_stats()
            
            # Start auto-save task
            self._auto_save_task = asyncio.create_task(self._auto_save_loop())
            
            logger.info("✅ Storage data loaded successfully")
        except Exception as e:
            logger.error(f"❌ Error loading storage data: {e}")
    
    async def save_data(self):
        """Save all data to JSON files"""
        try:
            await self._save_banned_users()
            await self._save_bot_stats()
            logger.info("💾 Storage data saved successfully")
        except Exception as e:
            logger.error(f"❌ Error saving storage data: {e}")
    
    async def _load_banned_users(self):
        """Load banned users from JSON file"""
        try:
            if os.path.exists(self.banned_users_file):
                with open(self.banned_users_file, 'r') as f:
                    data = json.load(f)
                    self.banned_users = set(data.get('banned_users', []))
            else:
                await self._save_banned_users()  # Create file with empty data
            
            logger.info(f"📋 Loaded {len(self.banned_users)} banned users")
        except Exception as e:
            logger.error(f"❌ Error loading banned users: {e}")
            self.banned_users = set()
    
    async def _save_banned_users(self):
        """Save banned users to JSON file"""
        try:
            data = {
                "banned_users": list(self.banned_users),
                "last_updated": datetime.now().isoformat()
            }
            
            with open(self.banned_users_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Error saving banned users: {e}")
    
    async def _load_bot_stats(self):
        """Load bot statistics from JSON file"""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r') as f:
                    saved_stats = json.load(f)
                    self.bot_stats.update(saved_stats)
            else:
                self.bot_stats["start_time"] = datetime.now().isoformat()
                await self._save_bot_stats()  # Create file with initial data
            
            logger.info("📊 Bot statistics loaded")
        except Exception as e:
            logger.error(f"❌ Error loading bot stats: {e}")
    
    async def _save_bot_stats(self):
        """Save bot statistics to JSON file"""
        try:
            self.bot_stats["last_updated"] = datetime.now().isoformat()
            self.bot_stats["banned_users"] = len(self.banned_users)
            
            with open(self.stats_file, 'w') as f:
                json.dump(self.bot_stats, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Error saving bot stats: {e}")
    
    async def _auto_save_loop(self):
        """Auto-save loop running in background"""
        while True:
            try:
                await asyncio.sleep(self.auto_save_interval)
                await self.save_data()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in auto-save loop: {e}")
    
    # User management methods
    def is_banned(self, user_id: int) -> bool:
        """Check if user is banned"""
        return user_id in self.banned_users
    
    async def ban_user(self, user_id: int) -> bool:
        """Ban a user"""
        if user_id not in self.banned_users:
            self.banned_users.add(user_id)
            await self._save_banned_users()
            logger.info(f"🚫 User {user_id} banned")
            return True
        return False
    
    async def unban_user(self, user_id: int) -> bool:
        """Unban a user"""
        if user_id in self.banned_users:
            self.banned_users.remove(user_id)
            await self._save_banned_users()
            logger.info(f"✅ User {user_id} unbanned")
            return True
        return False
    
    def get_banned_users(self) -> List[int]:
        """Get list of banned users"""
        return list(self.banned_users)
    
    # Statistics methods
    async def update_bot_stats(self, stats: Dict[str, Any]):
        """Update bot statistics"""
        self.bot_stats.update(stats)
        # Don't save immediately to avoid too frequent writes
    
    async def increment_stat(self, stat_name: str, amount: int = 1):
        """Increment a statistic"""
        if stat_name in self.bot_stats:
            self.bot_stats[stat_name] += amount
        else:
            self.bot_stats[stat_name] = amount
    
    def get_bot_stats(self) -> Dict[str, Any]:
        """Get bot statistics"""
        return self.bot_stats.copy()
    
    async def track_user_query(self, user_id: int, query: str):
        """Track user query for statistics"""
        await self.increment_stat("total_queries")
        
        # Track unique users
        if user_id not in self.user_stats:
            self.user_stats[user_id] = {
                "first_seen": datetime.now().isoformat(),
                "query_count": 0
            }
            await self.increment_stat("total_users")
        
        self.user_stats[user_id]["query_count"] += 1
        self.user_stats[user_id]["last_query"] = datetime.now().isoformat()
    
    def cleanup(self):
        """Cleanup storage resources"""
        if self._auto_save_task:
            self._auto_save_task.cancel()
