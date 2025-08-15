"""
Custom filters for Media Search Bot
"""

from pyrogram import filters
from pyrogram.types import Message
from config import Config

config = Config()

def admin_filter():
    """Filter for admin users only"""
    async def func(_, __, message: Message):
        if not message.from_user:
            return False
        return config.is_admin(message.from_user.id)
    
    return filters.create(func)

def auth_user_filter():
    """Filter for authorized users"""
    async def func(_, __, message: Message):
        if not message.from_user:
            return False
        return config.is_auth_user(message.from_user.id)
    
    return filters.create(func)

def channel_filter():
    """Filter for configured channels"""
    return filters.chat(config.CHANNELS)

def private_filter():
    """Filter for private messages only"""
    return filters.private

def media_filter():
    """Filter for media messages"""
    return (
        filters.document | 
        filters.video | 
        filters.audio | 
        filters.photo | 
        filters.animation | 
        filters.voice | 
        filters.video_note
    )
