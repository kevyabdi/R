from flask import Flask, jsonify, request
from threading import Thread
import logging
import json
import os
from datetime import datetime

# Suppress Flask's default logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Media Search Bot is running with admin management features!"

@app.route('/status')
def status():
    try:
        # Load bot stats
        stats = {}
        if os.path.exists('bot_stats.json'):
            with open('bot_stats.json', 'r') as f:
                stats = json.load(f)
        
        return jsonify({
            "status": "online",
            "message": "Media Search Bot is active and indexing files",
            "features": {
                "inline_search": "enabled",
                "media_indexing": "active",
                "admin_management": "enabled",
                "ban_system": "active",
                "broadcast_system": "enabled",
                "statistics": "tracking"
            },
            "bot_stats": stats,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint for Render"""
    try:
        # Check if essential files exist
        files_status = {
            "banned_users": os.path.exists('banned_users.json'),
            "bot_stats": os.path.exists('bot_stats.json'),
            "logging_config": os.path.exists('logging.conf')
        }
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "web_server": "running",
                "file_system": "accessible",
                "json_databases": files_status,
                "mongodb": "configured"
            }
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/features')
def features():
    return jsonify({
        "media_search": {
            "inline_query": "Search files using @botname query",
            "file_types": ["documents", "videos", "audio", "photos"],
            "caption_search": "Search by file captions and names",
            "channel_indexing": "Automatic indexing from configured channels"
        },
        "admin_commands": [
            "/ban <user_id> - Ban user from using bot",
            "/unban <user_id> - Unban user",
            "/stats - View bot statistics",
            "/broadcast <message> - Send message to all users",
            "/index - Force index channel files",
            "/delete <file_id> - Delete file from database",
            "/logger - Get log file",
            "/total - Show total indexed files"
        ],
        "user_commands": [
            "/start - Welcome message",
            "Inline query - @botname <search_term>",
            "Channel subscription required if AUTH_CHANNEL is set"
        ],
        "database": {
            "mongodb": "Media files and metadata",
            "json_files": "User management and statistics"
        }
    })

@app.route('/admin/stats')
def admin_stats():
    """Admin statistics endpoint"""
    try:
        stats = {}
        banned_users = []
        
        # Load stats
        if os.path.exists('bot_stats.json'):
            with open('bot_stats.json', 'r') as f:
                stats = json.load(f)
        
        # Load banned users
        if os.path.exists('banned_users.json'):
            with open('banned_users.json', 'r') as f:
                banned_users = json.load(f)
        
        return jsonify({
            "statistics": stats,
            "banned_users_count": len(banned_users),
            "banned_users": banned_users,
            "last_updated": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Not Found",
        "message": "The requested endpoint does not exist",
        "available_endpoints": ["/", "/status", "/health", "/features", "/admin/stats"]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Internal Server Error",
        "message": "An unexpected error occurred in the web server"
    }), 500

def run():
    """Run the Flask web server"""
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except Exception as e:
        logging.error(f"Failed to start web server: {e}")

def keep_alive():
    """Start the keep-alive server in a separate thread"""
    try:
        t = Thread(target=run)
        t.daemon = True
        t.start()
        print("✅ Keep-alive server started on port 5000 with health endpoints")
        return True
    except Exception as e:
        print(f"❌ Failed to start keep-alive server: {e}")
        return False

if __name__ == "__main__":
    keep_alive()
